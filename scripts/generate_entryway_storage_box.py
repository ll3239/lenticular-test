#!/usr/bin/env python3
"""
Generate a sloped entryway storage organizer STL for Bambu Lab printers.

Layout (internal mm, top view). Y=0 is the entryway FRONT (lip here); Y=210 is BACK (letters).

  +----------+-----------+  Y=0   FRONT + lip
  | earphones| 6 oil     |
  | + other  | bottles   |  100 mm
  +----------+-----------+  Y=100
  | keys     | power bank|  (vertical 11 cm)
  | card     | power bank|
  | card     | data cable|  80 mm
  | receipts |           |
  +----------+-----------+  Y=180
  |      letters          |  30 mm
  +-----------------------+  Y=210  BACK
       100 mm    100 mm
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
    depth: float  # internal height from floor (mm)


WALL = 2.0
DIVIDER = 1.5
BOTTOM = 2.0
LIP = 5.0  # front retaining lip height above local rim

W_INT = 200.0
L_INT = 210.0

# Side profile: highest at back (letters), slopes down toward front (entryway).
# Front rim must still clear 80 mm oil bottles.
H_FRONT = 86.0
H_BACK = 92.0

COMPARTMENTS: tuple[Compartment, ...] = (
    Compartment("earphones_other", 0, 100, 0, 100, 48),
    Compartment("essential_oils", 100, 200, 0, 100, 82),  # 6 x dia 30, h 80
    Compartment("keys", 0, 100, 100, 120, 22),
    Compartment("card_1", 0, 100, 120, 140, 12),
    Compartment("card_2", 0, 100, 140, 160, 12),
    Compartment("receipts", 0, 100, 160, 180, 28),
    # Power banks stored vertically: footprint 80 x 30 mm, height 110 mm
    Compartment("power_bank_1", 100, 200, 100, 130, 112),
    Compartment("power_bank_2", 100, 200, 130, 160, 112),
    Compartment("data_cable", 100, 200, 160, 180, 32),
    Compartment("letters", 0, 200, 180, 210, 25),
)


def rim_height(y: float, h_front: float, h_back: float, length: float) -> float:
    """Linear rim: shallow at back (y=L), deeper at front (y=0) — note y measured from front."""
    t = np.clip(y / length, 0.0, 1.0)
    # back (t=1) -> h_back, front (t=0) -> h_front
    return h_front + (h_back - h_front) * t


def add_triangle(verts: list, faces: list, v0, v1, v2) -> None:
    i0 = len(verts)
    verts.extend([v0, v1, v2])
    faces.append((i0, i0 + 1, i0 + 2))


def add_quad(verts: list, faces: list, v0, v1, v2, v3) -> None:
    add_triangle(verts, faces, v0, v1, v2)
    add_triangle(verts, faces, v0, v2, v3)


def add_box(verts: list, faces: list, x0, y0, z0, x1, y1, z1) -> None:
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
    add_quad(verts, faces, blf, brf, trf, tlf)
    add_quad(verts, faces, brb, blb, tlb, trb)
    add_quad(verts, faces, blb, blf, tlf, tlb)
    add_quad(verts, faces, brf, brb, trb, trf)
    add_quad(verts, faces, blf, brb, trb, tlf)
    add_quad(verts, faces, tlf, trf, trb, tlb)


def add_sloped_side_wall(
    verts: list,
    faces: list,
    *,
    side: str,
    y0: float,
    y1: float,
    y_origin: float,
    x_face: float,
    thickness: float,
    h_front: float,
    h_back: float,
    length: float,
    z_floor: float,
) -> None:
    z0 = z_floor
    z_at_y0 = z_floor + rim_height(y0 - y_origin, h_front, h_back, length)
    z_at_y1 = z_floor + rim_height(y1 - y_origin, h_front, h_back, length)
    if side == "left":
        x0, x1 = x_face, x_face + thickness
    elif side == "right":
        x0, x1 = x_face - thickness, x_face
    else:
        raise ValueError(side)

    if side == "left":
        add_quad(verts, faces, (x0, y0, z0), (x0, y1, z0), (x0, y1, z_at_y1), (x0, y0, z_at_y0))
        add_quad(verts, faces, (x1, y1, z0), (x1, y0, z0), (x1, y0, z_at_y0), (x1, y1, z_at_y1))
    else:
        add_quad(verts, faces, (x1, y0, z0), (x1, y1, z0), (x1, y1, z_at_y1), (x1, y0, z_at_y0))
        add_quad(verts, faces, (x0, y1, z0), (x0, y0, z0), (x0, y0, z_at_y0), (x0, y1, z_at_y1))

    add_quad(verts, faces, (x0, y0, z0), (x1, y0, z0), (x1, y0, z_at_y0), (x0, y0, z_at_y0))
    add_quad(verts, faces, (x0, y1, z0), (x1, y1, z0), (x1, y1, z_at_y1), (x0, y1, z_at_y1))
    add_quad(verts, faces, (x0, y0, z_at_y0), (x1, y0, z_at_y0), (x1, y1, z_at_y1), (x0, y1, z_at_y1))


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


def add_front_lip(
    verts: list,
    faces: list,
    *,
    x0: float,
    x1: float,
    y_front: float,
    wall: float,
    lip_h: float,
    rim_z: float,
    lip_thickness: float = 3.0,
) -> None:
    """Retaining lip on the front edge (inside the box)."""
    y0 = y_front
    y1 = y_front + lip_thickness
    z0 = rim_z
    z1 = rim_z + lip_h
    add_box(verts, faces, x0, y0, z0, x1, y1, z1)


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
    *,
    wall: float,
    divider: float,
    bottom: float,
    lip: float,
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

    add_box(verts, faces, 0, 0, oz, outer_w, outer_l, oz + bottom)
    z_floor = oz + bottom

    add_sloped_side_wall(
        verts, faces, side="left", y0=oy, y1=oy + l_int, y_origin=oy,
        x_face=ox, thickness=wall, h_front=h_front, h_back=h_back,
        length=l_int, z_floor=z_floor,
    )
    add_sloped_side_wall(
        verts, faces, side="right", y0=oy, y1=oy + l_int, y_origin=oy,
        x_face=ox + w_int, thickness=wall, h_front=h_front, h_back=h_back,
        length=l_int, z_floor=z_floor,
    )
    add_front_back_wall(
        verts, faces, edge="front", x0=ox, x1=ox + w_int, y_face=oy,
        thickness=wall, height=h_front, z_floor=z_floor,
    )
    add_front_back_wall(
        verts, faces, edge="back", x0=ox, x1=ox + w_int, y_face=oy + l_int,
        thickness=wall, height=h_back, z_floor=z_floor,
    )

    def local_y(y: float) -> float:
        return y - oy

    def divider_h(y_abs: float, depth: float) -> float:
        rim = rim_height(local_y(y_abs), h_front, h_back, l_int)
        return min(depth, rim - 1.0)

    # Front retaining lip (full internal width)
    front_rim_z = z_floor + rim_height(0.0, h_front, h_back, l_int)
    add_front_lip(
        verts, faces,
        x0=ox, x1=ox + w_int, y_front=oy,
        wall=wall, lip_h=lip, rim_z=front_rim_z,
    )

    # Bottom / middle split (y=100)
    add_horizontal_divider(
        verts, faces, x0=ox, x1=ox + w_int, y_center=oy + 100,
        thickness=divider, divider_height=divider_h(oy + 100, 82), z_floor=z_floor,
    )

    # Letters shelf (y=180)
    add_horizontal_divider(
        verts, faces, x0=ox, x1=ox + w_int, y_center=oy + 180,
        thickness=divider, divider_height=divider_h(oy + 180, 25), z_floor=z_floor,
    )

    # Center column (front + middle only; open letters bay spans full width)
    add_vertical_divider(
        verts, faces, y0=oy, y1=oy + 180, x_center=ox + 100,
        thickness=divider, divider_height=divider_h(oy + 50, 82), z_floor=z_floor,
    )

    # Left column shelves in middle section
    for y_edge, depth in ((120, 22), (140, 12), (160, 12)):
        add_horizontal_divider(
            verts, faces, x0=ox, x1=ox + 100, y_center=oy + y_edge,
            thickness=divider, divider_height=divider_h(oy + y_edge, depth), z_floor=z_floor,
        )

    # Right column shelves in middle section
    for y_edge, depth in ((130, 112), (160, 112), (180, 32)):
        add_horizontal_divider(
            verts, faces, x0=ox + 100, x1=ox + w_int, y_center=oy + y_edge,
            thickness=divider, divider_height=divider_h(oy + y_edge, depth), z_floor=z_floor,
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sloped entryway storage box STL for Bambu Lab")
    parser.add_argument("--out", type=Path, default=Path("output/entryway_storage_box.stl"))
    parser.add_argument("--spec-out", type=Path, default=Path("output/entryway_storage_box_spec.json"))
    parser.add_argument("--wall", type=float, default=WALL)
    parser.add_argument("--divider", type=float, default=DIVIDER)
    parser.add_argument("--bottom", type=float, default=BOTTOM)
    parser.add_argument("--lip", type=float, default=LIP)
    parser.add_argument("--width", type=float, default=W_INT)
    parser.add_argument("--length", type=float, default=L_INT)
    parser.add_argument("--h-front", type=float, default=H_FRONT, help="Rim height at entryway front (mm)")
    parser.add_argument("--h-back", type=float, default=H_BACK, help="Rim height at back / letters end (mm)")
    args = parser.parse_args()

    verts, faces = build_mesh(
        wall=args.wall, divider=args.divider, bottom=args.bottom, lip=args.lip,
        w_int=args.width, l_int=args.length, h_front=args.h_front, h_back=args.h_back,
    )
    write_binary_stl(args.out, verts, faces, "Entryway storage box v2 - Bambu")

    spec = {
        "orientation": "Y=0 is entryway front (with lip); Y=210 is back wall (letters).",
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
            "note": "Side view: high at back (letters) -> low at front (entryway). Front rim still clears 80 mm oil bottles.",
        },
        "front_lip_mm": args.lip,
        "item_assumptions": {
            "power_bank_mm": "110 x 80 x 30, stored vertically (110 mm tall, 80 x 30 footprint)",
            "oil_bottle_mm": "height 80, diameter 30, qty 6 in right front bay",
        },
        "compartments_mm": [
            {
                "name": c.name,
                "x0": c.x0, "x1": c.x1, "y0": c.y0, "y1": c.y1,
                "internal_depth": c.depth,
            }
            for c in COMPARTMENTS
        ],
        "print_notes": {
            "software": "Import STL into Bambu Studio.",
            "orientation": "Print flat on the bottom face.",
            "material": "PLA or PETG, 0.2 mm layers, 3 walls, 15-20% infill.",
        },
    }
    path = args.spec_out
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)

    print(f"Wrote {args.out} ({len(faces) * 2} triangles)")
    print(f"Wrote {args.spec_out}")
    print(
        f"Outer: {spec['outer_mm']['width']:.0f} x {spec['outer_mm']['length']:.0f} mm, "
        f"height front {spec['outer_mm']['height_front']:.0f} mm -> back {spec['outer_mm']['height_back']:.0f} mm"
    )


if __name__ == "__main__":
    main()
