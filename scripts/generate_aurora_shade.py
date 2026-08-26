#!/usr/bin/env python3
"""Generate a printable clip-on aurora shade for a pill-shaped floor lamp.

Outputs:
  aurora_ellipse_shade.stl       Complete assembled model
  aurora_ellipse_shade_left.stl  Left print-bed half
  aurora_ellipse_shade_right.stl Right print-bed half
  aurora_fit_test_ring.stl       Low-cost fit test before the full print

The default 330 x 152 mm opening is based on approximate measurements and
should be replaced with exact measurements at the black rim's grip line.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

try:
    import trimesh
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Run: python3 -m pip install trimesh manifold3d"
    ) from exc


INCH = 25.4
DEFAULT_LENGTH = 13.0 * INCH
DEFAULT_WIDTH = 6.0 * INCH
DEFAULT_HEIGHT = 4.35 * INCH


def capsule_points(length: float, width: float, segments: int = 48) -> np.ndarray:
    """Return a counter-clockwise stadium/capsule outline."""
    radius = width / 2.0
    straight = max(0.0, length / 2.0 - radius)
    points = []
    for angle in np.linspace(-math.pi / 2, math.pi / 2, segments // 2 + 1):
        points.append((straight + radius * math.cos(angle), radius * math.sin(angle)))
    for angle in np.linspace(math.pi / 2, 3 * math.pi / 2, segments // 2 + 1):
        points.append((-straight + radius * math.cos(angle), radius * math.sin(angle)))
    return np.asarray(points[:-1], dtype=float)


def loft_mesh(
    outlines: list[np.ndarray],
    heights: list[float],
    cap_bottom: bool = True,
    cap_top: bool = True,
) -> trimesh.Trimesh:
    """Create a closed loft from equal-sized 2D outlines."""
    count = len(outlines[0])
    vertices = np.vstack(
        [
            np.column_stack((outline, np.full(count, z)))
            for outline, z in zip(outlines, heights)
        ]
    )
    faces: list[tuple[int, int, int]] = []

    for layer in range(len(outlines) - 1):
        lower = layer * count
        upper = (layer + 1) * count
        for i in range(count):
            j = (i + 1) % count
            faces.extend(
                [
                    (lower + i, lower + j, upper + j),
                    (lower + i, upper + j, upper + i),
                ]
            )

    if cap_bottom:
        center = len(vertices)
        vertices = np.vstack((vertices, [0.0, 0.0, heights[0]]))
        for i in range(count):
            j = (i + 1) % count
            faces.append((center, i, j))

    if cap_top:
        center = len(vertices)
        vertices = np.vstack((vertices, [0.0, 0.0, heights[-1]]))
        offset = (len(outlines) - 1) * count
        for i in range(count):
            j = (i + 1) % count
            faces.append((center, offset + j, offset + i))

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)
    mesh.fix_normals()
    return mesh


def capsule_loft(
    length: float,
    width: float,
    height: float,
    flare: float = 0.015,
    bottom_z: float = 0.0,
) -> trimesh.Trimesh:
    """Closed capsule loft with a subtle top flare."""
    levels = [0.0, 0.58, 1.0]
    scales = [1.0, 1.0, 1.0 + flare]
    outlines = [
        capsule_points(length * scale, width * scale) for scale in scales
    ]
    heights = [bottom_z + height * level for level in levels]
    return loft_mesh(outlines, heights)


def box(extents: tuple[float, float, float], center: tuple[float, float, float]):
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    return mesh


def irregular_ray_cutters(
    length: float,
    width: float,
    height: float,
    top_thickness: float,
    seed: int,
    ray_count: int,
) -> list[trimesh.Trimesh]:
    """Make asymmetric radial slot cutters through the top only."""
    rng = np.random.default_rng(seed)
    cutters = []
    angles = np.sort(rng.uniform(0, 2 * math.pi, ray_count))
    z = height - top_thickness / 2.0

    for index, angle in enumerate(angles):
        slot_length = rng.uniform(length * 0.18, length * 0.46)
        slot_width = rng.uniform(4.0, 10.0)
        center_r = rng.uniform(length * 0.05, length * 0.18)
        curve = rng.uniform(-0.16, 0.16)

        # Two overlapping segments create a subtle organic bend.
        for segment in range(2):
            local_angle = angle + curve * segment
            local_length = slot_length * (0.58 if segment else 0.52)
            radial = center_r + slot_length * (0.24 + 0.28 * segment)
            cutter = box(
                (local_length, slot_width * (1.0 - 0.18 * segment), top_thickness + 4.0),
                (local_length / 2.0, 0.0, z),
            )
            rotation = trimesh.transformations.rotation_matrix(
                local_angle, [0.0, 0.0, 1.0]
            )
            cutter.apply_transform(rotation)
            cutter.apply_translation(
                (
                    radial * math.cos(angle),
                    radial * math.sin(angle),
                    0.0,
                )
            )
            cutters.append(cutter)

        # A few rays get round "star" apertures.
        if index % 4 == 0:
            radius = rng.uniform(2.5, 5.0)
            star = trimesh.creation.cylinder(
                radius=radius,
                height=top_thickness + 4.0,
                sections=24,
            )
            radial = rng.uniform(length * 0.12, length * 0.36)
            star.apply_translation(
                (radial * math.cos(angle), radial * math.sin(angle), z)
            )
            cutters.append(star)

    # Central glow opening prevents a dark dead spot.
    center = trimesh.creation.cylinder(
        radius=10.0,
        height=top_thickness + 4.0,
        sections=32,
    )
    center.apply_translation((0.0, 0.0, z))
    cutters.append(center)
    return cutters


def grip_pads(
    opening_length: float,
    opening_width: float,
    clearance: float,
    grip: float,
    pad_height: float = 14.0,
) -> list[trimesh.Trimesh]:
    """Four replaceable-by-parameter friction pads connected to the wall."""
    pads = []
    z = pad_height / 2.0 + 2.0
    pad_depth = 2.2 + grip
    pad_length = 24.0
    overlap = 0.5

    side_inner = opening_width / 2.0 + clearance
    for sign in (-1.0, 1.0):
        y = sign * (side_inner - pad_depth / 2.0 + overlap)
        pad = box(
            (pad_length, pad_depth, pad_height),
            (0.0, y, z),
        )
        pads.append(pad)

    end_inner = opening_length / 2.0 + clearance
    for sign in (-1.0, 1.0):
        x = sign * (end_inner - pad_depth / 2.0 + overlap)
        pad = box(
            (pad_depth, pad_length, pad_height),
            (x, 0.0, z),
        )
        pads.append(pad)
    return pads


def boolean_union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.union(meshes, engine="manifold")
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return result


def make_shade(
    opening_length: float,
    opening_width: float,
    height: float,
    wall: float,
    top_thickness: float,
    clearance: float,
    grip: float,
    seed: int,
    ray_count: int,
) -> trimesh.Trimesh:
    """Build a single watertight shade solid."""
    outer = capsule_loft(
        opening_length + 2.0 * wall,
        opening_width + 2.0 * wall,
        height,
    )
    inner = capsule_loft(
        opening_length + 2.0 * clearance,
        opening_width + 2.0 * clearance,
        height - top_thickness + 2.0,
        flare=0.0,
        bottom_z=-1.0,
    )
    shell = trimesh.boolean.difference([outer, inner], engine="manifold")

    cutters = irregular_ray_cutters(
        opening_length,
        opening_width,
        height,
        top_thickness,
        seed,
        ray_count,
    )
    shell = trimesh.boolean.difference(
        [shell, boolean_union(cutters)],
        engine="manifold",
    )

    pads = grip_pads(opening_length, opening_width, clearance, grip)
    shade = boolean_union([shell, *pads])
    shade.remove_unreferenced_vertices()
    shade.fix_normals()
    return shade


def split_for_print(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """Split along X=0 so each half fits a 256 mm square bed."""
    bounds = mesh.bounds
    span = max(mesh.extents) + 20.0
    left_box = box(
        (span, span, span),
        (-span / 2.0, 0.0, (bounds[0, 2] + bounds[1, 2]) / 2.0),
    )
    right_box = box(
        (span, span, span),
        (span / 2.0, 0.0, (bounds[0, 2] + bounds[1, 2]) / 2.0),
    )
    left = trimesh.boolean.intersection([mesh, left_box], engine="manifold")
    right = trimesh.boolean.intersection([mesh, right_box], engine="manifold")
    return left, right


def orient_cut_face_down(
    mesh: trimesh.Trimesh, right_half: bool
) -> trimesh.Trimesh:
    """Put the flat split face on the bed for support-free printing."""
    oriented = mesh.copy()
    angle = -math.pi / 2.0 if right_half else math.pi / 2.0
    oriented.apply_transform(
        trimesh.transformations.rotation_matrix(angle, [0.0, 1.0, 0.0])
    )
    oriented.apply_translation((0.0, 0.0, -oriented.bounds[0, 2]))
    return oriented


def make_fit_ring(
    opening_length: float,
    opening_width: float,
    wall: float,
    clearance: float,
    grip: float,
) -> trimesh.Trimesh:
    """Create a 16 mm high ring to verify fit before the full print."""
    height = 16.0
    outer = capsule_loft(
        opening_length + 2.0 * wall,
        opening_width + 2.0 * wall,
        height,
        flare=0.0,
    )
    inner = capsule_loft(
        opening_length + 2.0 * clearance,
        opening_width + 2.0 * clearance,
        height + 2.0,
        flare=0.0,
        bottom_z=-1.0,
    )
    ring = trimesh.boolean.difference([outer, inner], engine="manifold")
    ring = boolean_union(
        [
            ring,
            *grip_pads(
                opening_length,
                opening_width,
                clearance,
                grip,
                pad_height=12.0,
            ),
        ]
    )
    ring.fix_normals()
    return ring


def validate(mesh: trimesh.Trimesh, name: str) -> None:
    if not mesh.is_watertight:
        raise RuntimeError(f"{name} is not watertight")
    if not mesh.is_winding_consistent:
        raise RuntimeError(f"{name} has inconsistent winding")
    if mesh.volume <= 0:
        raise RuntimeError(f"{name} has invalid volume")


def export(mesh: trimesh.Trimesh, path: Path) -> None:
    validate(mesh, path.name)
    mesh.export(path)
    print(
        f"{path}: {len(mesh.faces)} triangles, "
        f"{np.round(mesh.extents, 1).tolist()} mm"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/aurora_ellipse_shade.stl"),
    )
    parser.add_argument("--length", "--major", dest="length", type=float, default=DEFAULT_LENGTH)
    parser.add_argument("--width", "--minor", dest="width", type=float, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=float, default=DEFAULT_HEIGHT)
    parser.add_argument("--wall", type=float, default=2.0)
    parser.add_argument("--top-thickness", type=float, default=2.4)
    parser.add_argument(
        "--clearance",
        type=float,
        default=1.2,
        help="XY clearance around measured black rim (mm)",
    )
    parser.add_argument(
        "--grip",
        type=float,
        default=0.5,
        help="Inward friction-pad interference (mm)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rays", type=int, default=14)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    stem = args.out.stem

    shade = make_shade(
        args.length,
        args.width,
        args.height,
        args.wall,
        args.top_thickness,
        args.clearance,
        args.grip,
        args.seed,
        args.rays,
    )
    left, right = split_for_print(shade)
    left = orient_cut_face_down(left, right_half=False)
    right = orient_cut_face_down(right, right_half=True)
    fit_ring = make_fit_ring(
        args.length,
        args.width,
        args.wall,
        args.clearance,
        args.grip,
    )
    fit_left, fit_right = split_for_print(fit_ring)
    fit_left = orient_cut_face_down(fit_left, right_half=False)
    fit_right = orient_cut_face_down(fit_right, right_half=True)

    export(shade, args.out)
    export(left, args.out.with_name(f"{stem}_left.stl"))
    export(right, args.out.with_name(f"{stem}_right.stl"))
    export(fit_ring, args.out.with_name("aurora_fit_test_ring.stl"))
    export(fit_left, args.out.with_name("aurora_fit_test_ring_left.stl"))
    export(fit_right, args.out.with_name("aurora_fit_test_ring_right.stl"))


if __name__ == "__main__":
    main()
