#!/usr/bin/env python3
"""Generate one watertight cube shell with photo-controlled line engraving."""

import argparse
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageEnhance, ImageOps

FACE_NAMES = ("front", "back", "right", "left", "top", "bottom")
OUTWARD = {
    "front": (0, 1, 0), "back": (0, -1, 0),
    "right": (1, 0, 0), "left": (-1, 0, 0),
    "top": (0, 0, 1), "bottom": (0, 0, -1),
}


def load_gray(path, resolution, contrast=1.8):
    """Return deterministic, contrast-normalized luminance in display orientation."""
    image = Image.open(path).convert("L")
    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    return np.asarray(
        image.resize((resolution, resolution), Image.Resampling.LANCZOS),
        dtype=np.float64,
    ) / 255.0


def depth_field(gray, lines, max_depth, size=50.0):
    """Encode column-averaged darkness in recessed vertical line channels."""
    resolution = gray.shape[0]
    x = np.linspace(0.0, size, resolution)
    pitch = size / lines
    line_index = np.minimum((x / pitch).astype(int), lines - 1)
    depth = np.empty_like(gray)
    for index in range(lines):
        columns = np.flatnonzero(line_index == index)
        # Column averaging is the physical line-screen bandwidth limit.
        depth[:, columns] = (1.0 - gray[:, columns].mean(axis=1))[:, None]

    # 0.4 mm flat separator and 0.6 mm groove at the default 1.0 mm pitch.
    # The 0.2 mm grid places two top-surface segments around each separator.
    phase = (x % pitch) / pitch
    separator_fraction = 0.4 / pitch
    if separator_fraction >= 0.8:
        raise ValueError("line pitch is too small for a 0.4 mm separator")
    half_separator = separator_fraction / 2.0
    # Boundary samples stay at the top plane, yielding a true 0.4 mm plateau
    # (rather than two slopes meeting at a zero-width separator).
    groove = ((phase > half_separator) & (phase < 1.0 - half_separator)).astype(float)
    depth *= groove[None, :] * max_depth

    # Every face has the exact same undeformed perimeter, making seams weldable.
    depth[[0, -1], :] = 0.0
    depth[:, [0, -1]] = 0.0
    return depth


def face_point(face, u, v, depth, size):
    mappings = {
        "front": (u, size - depth, v),
        "back": (size - u, depth, v),
        "right": (size - depth, size - u, v),
        "left": (depth, u, v),
        "top": (u, v, size - depth),
        "bottom": (u, size - v, depth),
    }
    return mappings[face]


def append_face(vertices, triangles, face, depth, size):
    resolution = depth.shape[0]
    coordinates = np.linspace(0.0, size, resolution)
    start = len(vertices)
    for row, v in enumerate(coordinates):
        for column, u in enumerate(coordinates):
            vertices.append(face_point(face, u, v, depth[row, column], size))

    outward = np.asarray(OUTWARD[face])
    for row in range(resolution - 1):
        for column in range(resolution - 1):
            a = start + row * resolution + column
            b, c, d = a + 1, a + resolution + 1, a + resolution
            candidate = (a, b, c)
            points = np.asarray([vertices[i] for i in candidate])
            if np.dot(np.cross(points[1] - points[0], points[2] - points[0]), outward) < 0:
                triangles.extend(((a, c, b), (a, d, c)))
            else:
                triangles.extend(((a, b, c), (a, c, d)))


def build_cube(image_paths, size=50.0, lines=50, resolution=251, max_depth=0.45):
    if len(image_paths) != 6:
        raise ValueError("exactly six images are required")
    vertices, triangles, fields = [], [], {}
    for face, path in zip(FACE_NAMES, image_paths):
        gray = load_gray(path, resolution)
        field = depth_field(gray, lines, max_depth, size)
        fields[face] = field
        append_face(vertices, triangles, face, field, size)

    mesh = trimesh.Trimesh(vertices=vertices, faces=triangles, process=True)
    mesh.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(mesh, multibody=False)
    return mesh, fields


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, nargs=6, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=float, default=50.0)
    parser.add_argument("--lines", type=int, default=50)
    parser.add_argument("--resolution", type=int, default=251)
    parser.add_argument("--max-depth", type=float, default=0.45)
    args = parser.parse_args()
    if args.resolution < args.lines * 5 + 1:
        raise SystemExit("resolution must be at least 5*lines+1 for 0.4 mm features")
    if not 0 < args.max_depth < args.size / 2:
        raise SystemExit("max-depth must be positive and less than half the cube")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    mesh, _ = build_cube(
        args.images, args.size, args.lines, args.resolution, args.max_depth
    )
    mesh.export(args.out)
    print(
        f"Wrote {args.out}: {len(mesh.faces)} triangles, "
        f"watertight={mesh.is_watertight}, components={len(mesh.split())}, "
        f"bounds={mesh.extents.tolist()}"
    )


if __name__ == "__main__":
    main()
