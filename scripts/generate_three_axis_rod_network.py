#!/usr/bin/env python3
"""Generate a connected 50 mm voxel-rod network optimized for three projections."""

import argparse
import json
from collections import deque
from itertools import combinations
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageEnhance, ImageOps

AXES = ("X", "Y", "Z")


def load_target(path: Path, n: int) -> np.ndarray:
    image = Image.open(path).convert("L")
    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(1.15)
    image = image.resize((n, n), Image.Resampling.LANCZOS)
    dark = 1.0 - np.asarray(image, dtype=np.float64) / 255.0
    # Remove unprintable tonal detail and retain a nonzero background.
    dark = np.clip((dark - 0.08) / 0.92, 0.0, 1.0)
    # Density projection cannot produce true white without disconnecting the
    # network, so reserve an explicit 18% structural-density floor.
    return 0.18 + 0.82 * dark


def correlation(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a.ravel() - a.mean(), b.ravel() - b.mean()
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def select_default_images(n: int) -> tuple[list[Path], list[list[float]]]:
    """Choose the first trio minimizing worst absolute target correlation."""
    paths = sorted(Path("images/complex").glob("*_photo.png"))
    if len(paths) < 3:
        raise ValueError("at least three images/complex/*_photo.png files are required")
    targets = [load_target(path, n) for path in paths]
    matrix = [[correlation(a, b) for b in targets] for a in targets]
    trio = min(combinations(range(len(paths)), 3),
               key=lambda c: (max(abs(matrix[a][b])
                                  for a, b in combinations(c, 2)), c))
    return [paths[i] for i in trio], matrix


def projections(occ: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # Display rows are +Z/+Y respectively; exact orientation is documented.
    return occ.sum(0).T, occ.sum(1).T, occ.sum(2).T


def scaffold(n: int) -> np.ndarray:
    """Three-dimensional connected line scaffold, including the geometric center."""
    occ = np.zeros((n, n, n), dtype=bool)
    q = sorted(set((0, n // 2, n - 1)))
    # A sparse cubic rod lattice. All rods intersect and every depth region is used.
    for a in q:
        for b in q:
            occ[:, a, b] = True
            occ[a, :, b] = True
            occ[a, b, :] = True
    return occ


def optimize(targets: tuple[np.ndarray, ...], n: int, max_fraction: float,
             seed: int) -> tuple[np.ndarray, list[dict]]:
    occ = scaffold(n)
    rng = np.random.default_rng(seed)
    history = []
    # All three projections necessarily have the same total mass. Normalize each
    # photo to that physically compatible total before joint optimization.
    target_counts = [np.clip(t / t.mean() * n * 0.24, 1.0, n * 0.78) for t in targets]
    current = list(projections(occ))
    limit = int(max_fraction * n ** 3)
    # Connected growth: candidates must touch the existing network by a face.
    for batch in range(80):
        neighbor = np.zeros_like(occ)
        neighbor[1:] |= occ[:-1]; neighbor[:-1] |= occ[1:]
        neighbor[:, 1:] |= occ[:, :-1]; neighbor[:, :-1] |= occ[:, 1:]
        neighbor[:, :, 1:] |= occ[:, :, :-1]; neighbor[:, :, :-1] |= occ[:, :, 1:]
        xyz = np.argwhere(neighbor & ~occ)
        if not len(xyz) or occ.sum() >= limit:
            break
        if len(xyz) > 45000:
            xyz = xyz[rng.choice(len(xyz), 45000, replace=False)]
        x, y, z = xyz.T
        # Reduction in squared projection error from adding each candidate voxel.
        score = (
            2 * (target_counts[0][z, y] - current[0][z, y]) - 1
            + 2 * (target_counts[1][z, x] - current[1][z, x]) - 1
            + 2 * (target_counts[2][y, x] - current[2][y, x]) - 1
        )
        positive = np.flatnonzero(score > 0)
        if not len(positive):
            break
        take_n = min(max(64, n * n // 3), len(positive), limit - int(occ.sum()))
        chosen = positive[np.argpartition(score[positive], -take_n)[-take_n:]]
        pts = xyz[chosen]
        occ[pts[:, 0], pts[:, 1], pts[:, 2]] = True
        current = list(projections(occ))
        history.append({"batch": batch, "voxels": int(occ.sum()),
                        "best_candidate_score": float(score[chosen].max())})
    # A cubical surface is non-manifold where two occupied voxels meet only
    # diagonally across an edge. Fill those tiny edge pinches deterministically.
    for _ in range(20):
        before = int(occ.sum())
        for axis in range(3):
            view = np.moveaxis(occ, axis, 0)
            for layer in view:
                a, b, c, d = layer[:-1, :-1], layer[1:, :-1], layer[:-1, 1:], layer[1:, 1:]
                diag1 = a & d & ~b & ~c
                diag2 = b & c & ~a & ~d
                b[diag1] = True; a[diag2] = True
        if int(occ.sum()) == before:
            break
    # Enclosed one-voxel air pockets create separate STL boundary shells. Fill
    # only voids that cannot reach the exterior, preserving the open network.
    exterior = np.zeros_like(occ)
    queue = deque()
    for point in np.argwhere(~occ):
        x, y, z = point
        if x in (0, n - 1) or y in (0, n - 1) or z in (0, n - 1):
            exterior[x, y, z] = True
            queue.append((x, y, z))
    while queue:
        point = queue.popleft()
        for axis in range(3):
            for delta in (-1, 1):
                adjacent = list(point)
                adjacent[axis] += delta
                if (0 <= adjacent[axis] < n
                        and not occ[tuple(adjacent)]
                        and not exterior[tuple(adjacent)]):
                    exterior[tuple(adjacent)] = True
                    queue.append(tuple(adjacent))
    cavities = ~occ & ~exterior
    occ[cavities] = True
    history.append({"filled_enclosed_void_voxels": int(cavities.sum())})
    history.append({"regularized_voxels": int(occ.sum())})
    return occ, history


def voxel_surface(occ: np.ndarray, cell: float) -> trimesh.Trimesh:
    vertices, faces, lookup = [], [], {}
    # Corners are shared, yielding a compact, watertight manifold surface.
    def vertex(p):
        if p not in lookup:
            lookup[p] = len(vertices); vertices.append(np.asarray(p) * cell)
        return lookup[p]
    directions = [
        ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
        ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
        ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
        ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
        ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
        ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
    ]
    n = occ.shape[0]
    for x, y, z in np.argwhere(occ):
        for (dx, dy, dz), corners in directions:
            xx, yy, zz = x + dx, y + dy, z + dz
            if 0 <= xx < n and 0 <= yy < n and 0 <= zz < n and occ[xx, yy, zz]:
                continue
            quad = [vertex((x + a, y + b, z + c)) for a, b, c in corners]
            faces.extend(((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])))
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)
    trimesh.repair.fix_normals(mesh, multibody=False)
    return mesh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", nargs=3, type=Path)
    parser.add_argument("--out", type=Path, default=Path("output/three_axis_rod_network.stl"))
    parser.add_argument("--state", type=Path, default=Path("output/three_axis_rod_network_state.npz"))
    parser.add_argument("--size", type=float, default=50.0)
    parser.add_argument("--resolution", type=int, default=40)
    parser.add_argument("--max-volume-fraction", type=float, default=0.30)
    parser.add_argument("--seed", type=int, default=597)
    args = parser.parse_args()
    if args.size / args.resolution < 0.45:
        raise SystemExit("voxel rod width must be at least 0.45 mm")
    all_image_matrix = None
    if args.images is None:
        args.images, all_image_matrix = select_default_images(args.resolution)
    targets = tuple(load_target(p, args.resolution) for p in args.images)
    occ, history = optimize(targets, args.resolution,
                            args.max_volume_fraction, args.seed)
    mesh = voxel_surface(occ, args.size / args.resolution)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(args.out)
    np.savez_compressed(args.state, occupancy=occ, target_x=targets[0],
                        target_y=targets[1], target_z=targets[2],
                        images=np.asarray([str(p) for p in args.images]),
                        size=args.size, history=json.dumps(history),
                        all_image_correlation_matrix=json.dumps(all_image_matrix))
    print(json.dumps({"stl": str(args.out), "voxels": int(occ.sum()),
                      "volume_fraction": float(occ.mean()), "triangles": len(mesh.faces),
                      "watertight": bool(mesh.is_watertight),
                      "components": len(mesh.split(only_watertight=False))}, indent=2))


if __name__ == "__main__":
    main()
