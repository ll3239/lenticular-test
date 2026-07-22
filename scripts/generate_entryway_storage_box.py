#!/usr/bin/env python3
"""
Generate a sloped entryway storage organizer STL for Bambu Lab printers.

Layout (internal, mm) — top view, Y=0 is the shallow "letters" front:

  +----------------------+  Y=0
  |      信件 / letters   |  30 mm deep
  +----------+-----------+
  | keys     | power bank|  \
  | card     | power bank|   } 80 mm
  | card     | data cable|
  | receipts |           |
  +----------+-----------+  Y=110
  | earphones| earphones |
  | + oils   | + oils    |  100 mm
  +----------+-----------+  Y=210

Outer walls slope in height from front (shallow) to back (deep).
"""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Compartment:
    name: str
    x0: float
    x1: float
    y0: float
    y1: float
    depth: float  # usable internal height from floor (mm)


# --- defaults derived from sketch + typical item sizes (override via CLI) ---
WALL = 2.0
DIVIDER = 1.5
BOTTOM = 2.0

W_INT = 200.0
L_INT = 210.0

# Outer rim height at front (Y=0) and back (Y=L_INT) — linear slope between.
H_FRONT = 30.0
H_BACK = 50.0

COMPARTMENTS: tuple[Compartment, ...] = (
    Compartment("letters", 0, 200, 0, 30, 25),
    Compartment("keys", 0, 100, 30, 50, 22),
    Compartment("card_1", 0, 100, 50, 70, 12),
    Compartment("card_2", 0, 100, 70, 90, 12),
    Compartment("receipts", 0, 100, 90, 110, 28),
    Compartment("power_bank_1", 100, 200, 30, 60, 18),
    Compartment("power_bank_2", 100, 200, 60, 90, 18),
    Compartment("data_cable", 100, 200, 90, 110, 32),
    Compartment("earphones_oils_L", 0, 100, 110, 210, 45),
    Compartment("earphones_oils_R", 100, 200, 110, 210, 45),
)


def rim_height(y: float, h_front: float, h_back: float, length: float) -> float:
    t = np.clip(y / length, 0.0, 1.0)
    return h_front + (h_back - h_front) * t


def add_triangle(verts: list, faces: list, v0, v1, v2) -> None:
    i0 = len(verts)
    verts.extend([v0, v1, v2])
    faces.append((i0, i0 + 1, i0 + 2))


def add_quad(verts: list, faces: list, v0, v1, v2, v3) -> None:
    add_triangle(verts, faces, v0, v1, v2)
    add_triangle(verts, faces, v0, v2, v3)


def add_box(verts: list, faces: list, x0, y0, z0, x1, y1, z1) -> None:
    """Axis-aligned box. Coordinates may be in any order."""
    xa, xb = (x0, x1) if x0 <= x1 else (x1, x0)
    ya, yb = (y0, y1) if y0 <= y1 else (y1, y0)
    za, zb = (z0, z1) if z0 <= z1 else (z1, z0)
    blf = (xa, ya, za)
    brf = (xb, ya, za)
    brb = (xb, yb, za)
    blb = (xa, yb, za)
    tlf = (xa, ya, zb)
    trf = (xb, ya, zb)
    trb = (xb, yb, zb)
    tlb = (xa, yb, zb)
    add_quad(verts, faces, blf, brf, trf, tlf)  # front
    add_quad(verts, faces, brb, blb, tlb, trb)  # back
    add_quad(verts, faces, blb, blf, tlf, tlb)  # left
    add_quad(verts, faces, brf, brb, trb, trf)  # right
    add_quad(verts, faces, blf, brb, trb, tlf)  # bottom
    add_quad(verts, faces, tlf, trf, trb, tlb)  # top


def add_sloped_side_wall(
    verts: list,
    faces: list,
    *,
    side: str,
    y0: float,
    y1: float,
    x_face: float,
    thickness: float,
    h_front: float,
    h_back: float,
    length: float,
    z_floor: float,
) -> None:
    """Vertical wall panel with sloped top edge along Y."""
    z0 = z_floor
    z_front = z_floor + rim_height(y0, h_front, h_back, length)
    z_back = z_floor + rim_height(y1, h_front, h_back, length)
    if side == "left":
        x0, x1 = x_face, x_face + thickness
    elif side == "right":
        x0, x1 = x_face - thickness, x_face
    else:
        raise ValueError(side)

    # Outer face (CCW from outside)
    if side == "left":
        add_quad(verts, faces, (x0, y0, z0), (x0, y1, z0), (x0, y1, z_back), (x0, y0, z_front))
        add_quad(verts, faces, (x1, y1, z0), (x1, y0, z0), (x1, y0, z_front), (x1, y1, z_back))
    else:
        add_quad(verts, faces, (x1, y0, z0), (x1, y1, z0), (x1, y1, z_back), (x1, y0, z_front))
        add_quad(verts, faces, (x0, y1, z0), (x0, y0, z0), (x0, y0, z_front), (x0, y1, z_back))

    add_quad(verts, faces, (x0, y0, z0), (x1, y0, z0), (x1, y0, z_front), (x0, y0, z_front))
    add_quad(verts, faces, (x0, y1, z0), (x1, y1, z0), (x1, y1, z_back), (x0, y1, z_back))
    add_quad(verts, faces, (x0, y0, z_front), (x1, y0, z_front), (x1, y1, z_back), (x0, y1, z_back))


def add_front_back_wall(
    verts: list,
    faces: list,
    *,
    edge: str,
    x0: float,
    x1: float,
    y_face: float,
    thickness: float,
    height: float,
    z_floor: float,
) -> None:
    z0 = z_floor
    z1 = z_floor + height
    if edge == "front":
        y0, y1 = y_face, y_face + thickness
        add_quad(verts, faces, (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))
        add_quad(verts, faces, (x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1))
    else:
        y0, y1 = y_face - thickness, y_face
        add_quad(verts, faces, (x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1))
        add_quad(verts, faces, (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))

    add_quad(verts, faces, (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
    add_quad(verts, faces, (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))


def add_horizontal_divider(
    verts: list,
    faces: list,
    *,
    x0: float,
    x1: float,
    y_center: float,
    thickness: float,
    divider_height: float,
    z_floor: float,
) -> None:
    y0 = y_center - thickness / 2
    y1 = y_center + thickness / 2
    add_box(verts, faces, x0, y0, z_floor, x1, y1, z_floor + divider_height)


def add_vertical_divider(
    verts: list,
    faces: list,
    *,
    y0: float,
    y1: float,
    x_center: float,
    thickness: float,
    divider_height: float,
    z_floor: float,
) -> None:
    x0 = x_center - thickness / 2
    x1 = x_center + thickness / 2
    add_box(verts, faces, x0, y0, z_floor, x1, y1, z_floor + divider_height)


def build_mesh(
    compartments: tuple[Compartment, ...],
    *,
    wall: float,
    divider: float,
    bottom: float,
    w_int: float,
    l_int: float,
    h_front: float,
    h_back: float,
) -> tuple[list, list]:
    verts: list = []
    faces: list = []

    ox = wall
    oy = wall
    oz = 0.0
    outer_w = w_int + 2 * wall
    outer_l = l_int + 2 * wall

    # Floor
    add_box(verts, faces, 0, 0, oz, outer_w, outer_l, oz + bottom)

    z_floor = oz + bottom

    # Outer walls (sloped sides)
    add_sloped_side_wall(
        verts,
        faces,
        side="left",
        y0=oy,
        y1=oy + l_int,
        x_face=ox,
        thickness=wall,
        h_front=h_front,
        h_back=h_back,
        length=l_int,
        z_floor=z_floor,
    )
    add_sloped_side_wall(
        verts,
        faces,
        side="right",
        y0=oy,
        y1=oy + l_int,
        x_face=ox + w_int,
        thickness=wall,
        h_front=h_front,
        h_back=h_back,
        length=l_int,
        z_floor=z_floor,
    )
    add_front_back_wall(
        verts,
        faces,
        edge="front",
        x0=ox,
        x1=ox + w_int,
        y_face=oy,
        thickness=wall,
        height=h_front,
        z_floor=z_floor,
    )
    add_front_back_wall(
        verts,
        faces,
        edge="back",
        x0=ox,
        x1=ox + w_int,
        y_face=oy + l_int,
        thickness=wall,
        height=h_back,
        z_floor=z_floor,
    )

    def divider_h(y_mid: float, depth: float) -> float:
        rim = rim_height(y_mid - oy, h_front, h_back, l_int)
        return min(depth, rim - 1.0)

    # Full-width shelf under letters section (optional lip — use shallow divider)
    add_horizontal_divider(
        verts,
        faces,
        x0=ox,
        x1=ox + w_int,
        y_center=oy + 30,
        thickness=divider,
        divider_height=divider_h(oy + 30, 25),
        z_floor=z_floor,
    )

    # Center column divider (middle + bottom)
    add_vertical_divider(
        verts,
        faces,
        y0=oy + 30,
        y1=oy + l_int,
        x_center=ox + 100,
        thickness=divider,
        divider_height=divider_h(oy + 160, 45),
        z_floor=z_floor,
    )

    # Left column horizontal dividers (height from compartment above each shelf)
    for y_edge, depth in ((50, 22), (70, 12), (90, 12)):
        add_horizontal_divider(
            verts,
            faces,
            x0=ox,
            x1=ox + 100,
            y_center=oy + y_edge,
            thickness=divider,
            divider_height=divider_h(oy + y_edge, depth),
            z_floor=z_floor,
        )

    # Right column horizontal dividers
    for y_edge, depth in ((60, 18), (90, 18), (110, 32)):
        add_horizontal_divider(
            verts,
            faces,
            x0=ox + 100,
            x1=ox + w_int,
            y_center=oy + y_edge,
            thickness=divider,
            divider_height=divider_h(oy + y_edge, depth),
            z_floor=z_floor,
        )

    # Major shelf between middle and bottom bays
    add_horizontal_divider(
        verts,
        faces,
        x0=ox,
        x1=ox + w_int,
        y_center=oy + 110,
        thickness=divider,
        divider_height=divider_h(oy + 110, 45),
        z_floor=z_floor,
    )

    return verts, faces


def write_binary_stl(path: Path, verts: list, faces: list, header_text: str = "Entryway storage box") -> None:
    triangles = []
    for i0, i1, i2 in faces:
        v0, v1, v2 = np.array(verts[i0]), np.array(verts[i1]), np.array(verts[i2])
        edge1 = v1 - v0
        edge2 = v2 - v0
        normal = np.cross(edge1, edge2)
        norm = np.linalg.norm(normal)
        normal = normal / norm if norm > 1e-9 else np.array([0.0, 0.0, 1.0])
        triangles.append((normal, v0, v1, v2))

    header = header_text.encode("ascii", errors="ignore")[:80]
    header = header + b"\0" * (80 - len(header))

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for normal, v0, v1, v2 in triangles:
            f.write(struct.pack("<3f", *normal))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))


def write_spec_json(path: Path, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kwargs, f, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sloped entryway storage box STL for Bambu Lab")
    parser.add_argument("--out", type=Path, default=Path("output/entryway_storage_box.stl"))
    parser.add_argument("--spec-out", type=Path, default=Path("output/entryway_storage_box_spec.json"))
    parser.add_argument("--wall", type=float, default=WALL)
    parser.add_argument("--divider", type=float, default=DIVIDER)
    parser.add_argument("--bottom", type=float, default=BOTTOM)
    parser.add_argument("--width", type=float, default=W_INT, help="Internal width (mm)")
    parser.add_argument("--length", type=float, default=L_INT, help="Internal length (mm)")
    parser.add_argument("--h-front", type=float, default=H_FRONT, help="Outer rim height at letters end (mm)")
    parser.add_argument("--h-back", type=float, default=H_BACK, help="Outer rim height at back end (mm)")
    args = parser.parse_args()

    verts, faces = build_mesh(
        COMPARTMENTS,
        wall=args.wall,
        divider=args.divider,
        bottom=args.bottom,
        w_int=args.width,
        l_int=args.length,
        h_front=args.h_front,
        h_back=args.h_back,
    )
    write_binary_stl(args.out, verts, faces, "Entryway storage box - Bambu")

    spec = {
        "internal_mm": {"width": args.width, "length": args.length},
        "outer_mm": {
            "width": args.width + 2 * args.wall,
            "length": args.length + 2 * args.wall,
            "height_front": args.h_front + args.bottom,
            "height_back": args.h_back + args.bottom,
        },
        "slope": {
            "front_rim_mm": args.h_front,
            "back_rim_mm": args.h_back,
            "note": "Linear slope along length; letters end is shallow, earphones/oils end is deep.",
        },
        "compartments_mm": [
            {
                "name": c.name,
                "x0": c.x0,
                "x1": c.x1,
                "y0": c.y0,
                "y1": c.y1,
                "internal_depth": c.depth,
            }
            for c in COMPARTMENTS
        ],
        "print_notes": {
            "software": "Import STL into Bambu Studio (not MakerWorld MakerLab — that is for sharing models).",
            "orientation": "Print flat on the bottom face (largest flat side down).",
            "material": "PLA or PETG, 0.2 mm layers, 2-3 walls, 15-20% infill (mostly solid walls).",
            "bed_size_check": "Needs ~204 x 214 mm bed (fits Bambu P1/X1/A1 series).",
        },
    }
    write_spec_json(args.spec_out, **spec)

    print(f"Wrote {args.out} ({len(faces) * 2} triangles)")
    print(f"Wrote {args.spec_out}")
    print(
        f"Outer footprint: {spec['outer_mm']['width']:.1f} x {spec['outer_mm']['length']:.1f} mm, "
        f"height {spec['outer_mm']['height_front']:.1f} -> {spec['outer_mm']['height_back']:.1f} mm"
    )


if __name__ == "__main__":
    main()
