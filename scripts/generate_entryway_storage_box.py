#!/usr/bin/env python3
"""
Generate a sloped entryway storage organizer STL for Bambu Lab printers.

Layout (internal mm, top view). Y=0 is the entryway FRONT (lip here); back = letters.

Modular layout — same cell sizes (100×100, 100×80, …) with gutters between blocks:

  ┌─ margin ─┬──100──┬ gutter ┬──100──┬─ margin ─┐
  │ earphones│       │        │  oils  │          │  100
  ├──────────┴───────┤        ├────────┴──────────┤
  │ keys / cards …   │ gutter │ power banks …     │   80
  ├──────────────────┴────────┴───────────────────┤
  │              letters (full width)              │   30
  └────────────────────────────────────────────────┘
        → 横长方形 footprint: 宽 252 × 深 238 mm (外廓 256×242, 贴墙放)
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


@dataclass(frozen=True)
class Layout:
    """Compartment grid with gutters — cells keep original sketch sizes."""

    col_w: float = 100.0
    gutter: float = 10.0
    margin_x: float = 21.0  # wider side margins → 横长方形 (宽 > 深)
    margin_y: float = 4.0
    front_h: float = 100.0
    # 98 mm gives two 30 mm power banks and a 30 mm cable bundle real
    # clearance after accounting for the 1.5 mm dividers.
    mid_h: float = 98.0
    letters_h: float = 30.0

    @property
    def w_int(self) -> float:
        return 2 * self.margin_x + 2 * self.col_w + self.gutter

    @property
    def l_int(self) -> float:
        return (
            2 * self.margin_y
            + self.front_h
            + self.gutter
            + self.mid_h
            + self.gutter
            + self.letters_h
        )

    @property
    def x_left0(self) -> float:
        return self.margin_x

    @property
    def x_left1(self) -> float:
        return self.margin_x + self.col_w

    @property
    def x_right0(self) -> float:
        return self.x_left1 + self.gutter

    @property
    def x_right1(self) -> float:
        return self.x_right0 + self.col_w

    @property
    def y_front0(self) -> float:
        return self.margin_y

    @property
    def y_front1(self) -> float:
        return self.y_front0 + self.front_h

    @property
    def y_mid0(self) -> float:
        return self.y_front1 + self.gutter

    @property
    def y_mid1(self) -> float:
        return self.y_mid0 + self.mid_h

    @property
    def y_letters0(self) -> float:
        return self.y_mid1 + self.gutter

    @property
    def y_letters1(self) -> float:
        return self.y_letters0 + self.letters_h

    def compartments(self) -> tuple[Compartment, ...]:
        xl0, xl1, xr0, xr1 = self.x_left0, self.x_left1, self.x_right0, self.x_right1
        yf0, yf1 = self.y_front0, self.y_front1
        ym0, ym1 = self.y_mid0, self.y_mid1
        yl0, yl1 = self.y_letters0, self.y_letters1
        return (
            Compartment("earphones_other", xl0, xl1, yf0, yf1, 48),
            Compartment("essential_oils", xr0, xr1, yf0, yf1, 82),
            Compartment("keys", xl0, xl1, ym0, ym0 + 24, 22),
            Compartment("card_1", xl0, xl1, ym0 + 24, ym0 + 46, 12),
            Compartment("card_2", xl0, xl1, ym0 + 46, ym0 + 68, 12),
            Compartment("receipts", xl0, xl1, ym0 + 68, ym1, 28),
            Compartment("power_bank_1", xr0, xr1, ym0, ym0 + 33, 112),
            Compartment("power_bank_2", xr0, xr1, ym0 + 33, ym0 + 66, 112),
            Compartment("data_cable", xr0, xr1, ym0 + 66, ym1, 32),
            Compartment("letters", 0, self.w_int, yl0, yl1, 25),
        )


LAYOUT_COMPACT = Layout(gutter=0, margin_x=0, margin_y=0)  # corrected 200×228
LAYOUT_MODULAR = Layout()


WALL = 2.0
DIVIDER = 1.5
BOTTOM = 2.0
LIP = 5.0

DEFAULT_LAYOUT = LAYOUT_COMPACT
W_INT = DEFAULT_LAYOUT.w_int
L_INT = DEFAULT_LAYOUT.l_int

H_FRONT = 86.0
H_BACK = 92.0

COMPARTMENTS = DEFAULT_LAYOUT.compartments()


def rim_height(y: float, h_front: float, h_back: float, length: float) -> float:
    """Linear rim along Y: low at front (y=0), high at back / letters (y=L)."""
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
    add_quad(verts, faces, blf, blb, brb, brf)
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
    cap_ends: bool = True,
) -> None:
    z0 = z_floor
    z_at_y0 = z_floor + rim_height(y0 - y_origin, h_front, h_back, length)
    z_at_y1 = z_floor + rim_height(y1 - y_origin, h_front, h_back, length)
    if side == "left":
        x0, x1 = x_face - thickness, x_face
    elif side == "right":
        x0, x1 = x_face, x_face + thickness
    else:
        raise ValueError(side)

    if side == "left":
        add_quad(verts, faces, (x0, y0, z0), (x0, y1, z0), (x0, y1, z_at_y1), (x0, y0, z_at_y0))
        add_quad(verts, faces, (x1, y1, z0), (x1, y0, z0), (x1, y0, z_at_y0), (x1, y1, z_at_y1))
    else:
        add_quad(verts, faces, (x1, y0, z0), (x1, y1, z0), (x1, y1, z_at_y1), (x1, y0, z_at_y0))
        add_quad(verts, faces, (x0, y1, z0), (x0, y0, z0), (x0, y0, z_at_y0), (x0, y1, z_at_y1))

    if cap_ends:
        add_quad(verts, faces, (x0, y0, z0), (x1, y0, z0), (x1, y0, z_at_y0), (x0, y0, z_at_y0))
        add_quad(verts, faces, (x0, y1, z0), (x1, y1, z0), (x1, y1, z_at_y1), (x0, y1, z_at_y1))
    add_quad(verts, faces, (x0, y0, z_at_y0), (x1, y0, z_at_y0), (x1, y1, z_at_y1), (x0, y1, z_at_y1))
    add_quad(verts, faces, (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))


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
    cap_ends: bool = True,
) -> None:
    z0 = z_floor
    z1 = z_floor + height
    if edge == "front":
        y0, y1 = y_face - thickness, y_face
        add_quad(verts, faces, (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))
        add_quad(verts, faces, (x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1))
    else:
        y0, y1 = y_face, y_face + thickness
        add_quad(verts, faces, (x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1))
        add_quad(verts, faces, (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))

    add_quad(verts, faces, (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
    add_quad(verts, faces, (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))
    if cap_ends:
        add_quad(verts, faces, (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0))
        add_quad(verts, faces, (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))


def add_rounded_corner_wall(
    verts: list,
    faces: list,
    *,
    cx: float,
    cy: float,
    angle0: float,
    angle1: float,
    inner_radius: float,
    thickness: float,
    oy: float,
    length: float,
    h_front: float,
    h_back: float,
    z_floor: float,
    segments: int = 8,
) -> None:
    """Quarter-annulus wall joining shortened straight walls."""
    outer_radius = inner_radius + thickness
    angles = np.linspace(angle0, angle1, segments + 1)
    for a0, a1 in zip(angles[:-1], angles[1:]):
        def point(radius: float, angle: float, top: bool):
            x = cx + radius * np.cos(angle)
            y = cy + radius * np.sin(angle)
            z = z_floor
            if top:
                z += rim_height(y - oy, h_front, h_back, length)
            return (x, y, z)

        oi0, oi1 = point(outer_radius, a0, False), point(outer_radius, a1, False)
        ot0, ot1 = point(outer_radius, a0, True), point(outer_radius, a1, True)
        ii0, ii1 = point(inner_radius, a0, False), point(inner_radius, a1, False)
        it0, it1 = point(inner_radius, a0, True), point(inner_radius, a1, True)
        add_quad(verts, faces, oi0, oi1, ot1, ot0)
        add_quad(verts, faces, ii1, ii0, it0, it1)
        add_quad(verts, faces, ot0, ot1, it1, it0)
        add_quad(verts, faces, ii0, ii1, oi1, oi0)

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
    # Overlap the front wall instead of merely touching it; this produces a
    # robust boolean union and avoids non-manifold coplanar seams.
    y0 = y_front - wall
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


def _add_dividers_row_four(
    verts: list,
    faces: list,
    *,
    ox: float,
    oy: float,
    divider: float,
    z_floor: float,
    divider_h,
) -> None:
    """One row of four 100 mm bays + letters band at back (y=100–130)."""
    row_y1 = 100.0
    add_horizontal_divider(
        verts, faces, x0=ox, x1=ox + 400.0, y_center=oy + row_y1,
        thickness=divider, divider_height=divider_h(oy + row_y1, 25), z_floor=z_floor,
    )
    for x_div in (100.0, 200.0, 300.0):
        add_vertical_divider(
            verts, faces, y0=oy, y1=oy + row_y1, x_center=ox + x_div,
            thickness=divider, divider_height=divider_h(oy + row_y1 / 2, 82), z_floor=z_floor,
        )
    for y_edge, depth in ((20, 22), (40, 12), (60, 12)):
        add_horizontal_divider(
            verts, faces, x0=ox + 200.0, x1=ox + 300.0, y_center=oy + y_edge,
            thickness=divider, divider_height=divider_h(oy + y_edge, depth), z_floor=z_floor,
        )
    for y_edge, depth in ((30, 112), (60, 112), (80, 32)):
        add_horizontal_divider(
            verts, faces, x0=ox + 300.0, x1=ox + 400.0, y_center=oy + y_edge,
            thickness=divider, divider_height=divider_h(oy + y_edge, depth), z_floor=z_floor,
        )


def _add_dividers_mail_spine(
    verts: list,
    faces: list,
    *,
    ox: float,
    oy: float,
    divider: float,
    z_floor: float,
    divider_h,
) -> None:
    """Core 200×180 grid + full-height letters spine at x=200–230."""
    xl0, xl1, xr0, xr1 = 0.0, 100.0, 100.0, 200.0
    yf1, ym0, ym1 = 100.0, 100.0, 180.0
    spine_x = 200.0

    add_horizontal_divider(
        verts, faces, x0=ox, x1=ox + spine_x, y_center=oy + yf1,
        thickness=divider, divider_height=divider_h(oy + yf1, 82), z_floor=z_floor,
    )
    add_horizontal_divider(
        verts, faces, x0=ox, x1=ox + spine_x, y_center=oy + ym1,
        thickness=divider, divider_height=divider_h(oy + ym1, 25), z_floor=z_floor,
    )
    add_vertical_divider(
        verts, faces, y0=oy, y1=oy + ym1, x_center=ox + 100.0,
        thickness=divider, divider_height=divider_h(oy + 50, 82), z_floor=z_floor,
    )
    add_vertical_divider(
        verts, faces, y0=oy, y1=oy + 210.0, x_center=ox + spine_x,
        thickness=divider, divider_height=divider_h(oy + 105, 210), z_floor=z_floor,
    )
    for y_edge, depth in ((ym0 + 24, 22), (ym0 + 46, 12), (ym0 + 68, 12)):
        add_horizontal_divider(
            verts, faces, x0=ox + xl0, x1=ox + xl1, y_center=oy + y_edge,
            thickness=divider, divider_height=divider_h(oy + y_edge, depth), z_floor=z_floor,
        )
    for y_edge, depth in ((ym0 + 33, 112), (ym0 + 66, 112), (ym1, 32)):
        add_horizontal_divider(
            verts, faces, x0=ox + xr0, x1=ox + xr1, y_center=oy + y_edge,
            thickness=divider, divider_height=divider_h(oy + y_edge, depth), z_floor=z_floor,
        )


def _add_dividers_grid(
    verts: list,
    faces: list,
    *,
    ox: float,
    oy: float,
    layout: Layout,
    w_int: float,
    divider: float,
    z_floor: float,
    divider_h,
    letters_at_back: bool,
) -> None:
    xl0, xl1 = layout.x_left0, layout.x_left1
    xr0, xr1 = layout.x_right0, layout.x_right1
    yf1 = layout.y_front1
    ym0, ym1 = layout.y_mid0, layout.y_mid1
    x_col_div = (layout.x_left1 + layout.x_right0) / 2
    gx1 = xr1  # grid content width for partial shelves

    add_horizontal_divider(
        verts, faces, x0=ox, x1=ox + (w_int if letters_at_back else gx1),
        y_center=oy + yf1 + layout.gutter / 2,
        thickness=divider, divider_height=divider_h(oy + yf1, 82), z_floor=z_floor,
    )
    if letters_at_back:
        add_horizontal_divider(
            verts, faces, x0=ox, x1=ox + w_int, y_center=oy + ym1 + layout.gutter / 2,
            thickness=divider, divider_height=divider_h(oy + ym1, 25), z_floor=z_floor,
        )
    add_vertical_divider(
        verts, faces, y0=oy + layout.y_front0, y1=oy + ym1, x_center=ox + x_col_div,
        thickness=divider, divider_height=divider_h(oy + layout.y_front0 + 50, 82), z_floor=z_floor,
    )
    for y_edge, depth in ((ym0 + 20, 22), (ym0 + 40, 12), (ym0 + 60, 12)):
        add_horizontal_divider(
            verts, faces, x0=ox + xl0, x1=ox + xl1, y_center=oy + y_edge,
            thickness=divider, divider_height=divider_h(oy + y_edge, depth), z_floor=z_floor,
        )
    for y_edge, depth in ((ym0 + 30, 112), (ym0 + 60, 112), (ym1, 32)):
        add_horizontal_divider(
            verts, faces, x0=ox + xr0, x1=ox + xr1, y_center=oy + y_edge,
            thickness=divider, divider_height=divider_h(oy + y_edge, depth), z_floor=z_floor,
        )


def build_mesh(
    *,
    w_int: float,
    l_int: float,
    layout: Layout,
    wall: float,
    divider: float,
    bottom: float,
    lip: float,
    h_front: float,
    h_back: float,
    style: str = "minimal",
    preset_id: str = "classic",
) -> tuple[list, list]:
    verts: list = []
    faces: list = []

    ox = wall
    oy = wall
    oz = 0.0
    outer_w = w_int + 2 * wall
    outer_l = l_int + 2 * wall

    rounded_walls = style == "rounded"
    corner_radius = 10.0
    if style in ("rounded", "accent"):
        from entryway_styles import apply_rounded_base

        corner_r = corner_radius + wall if rounded_walls else 8.0
        apply_rounded_base(verts, faces, outer_w=outer_w, outer_l=outer_l, bottom=bottom, radius=corner_r)
    else:
        add_box(verts, faces, 0, 0, oz, outer_w, outer_l, oz + bottom)
    z_floor = oz + bottom

    add_sloped_side_wall(
        verts, faces, side="left",
        y0=oy + (corner_radius if rounded_walls else -wall),
        y1=oy + l_int - (corner_radius if rounded_walls else -wall), y_origin=oy,
        x_face=ox, thickness=wall, h_front=h_front, h_back=h_back,
        length=l_int, z_floor=z_floor, cap_ends=not rounded_walls,
    )
    add_sloped_side_wall(
        verts, faces, side="right",
        y0=oy + (corner_radius if rounded_walls else -wall),
        y1=oy + l_int - (corner_radius if rounded_walls else -wall), y_origin=oy,
        x_face=ox + w_int, thickness=wall, h_front=h_front, h_back=h_back,
        length=l_int, z_floor=z_floor, cap_ends=not rounded_walls,
    )
    add_front_back_wall(
        verts, faces, edge="front",
        x0=ox + (corner_radius if rounded_walls else -wall),
        x1=ox + w_int - (corner_radius if rounded_walls else -wall), y_face=oy,
        thickness=wall, height=h_front, z_floor=z_floor, cap_ends=not rounded_walls,
    )
    add_front_back_wall(
        verts, faces, edge="back",
        x0=ox + (corner_radius if rounded_walls else -wall),
        x1=ox + w_int - (corner_radius if rounded_walls else -wall), y_face=oy + l_int,
        thickness=wall, height=h_back, z_floor=z_floor, cap_ends=not rounded_walls,
    )
    if rounded_walls:
        corner_specs = (
            (ox + corner_radius, oy + corner_radius, np.pi, 1.5 * np.pi),
            (ox + w_int - corner_radius, oy + corner_radius, 1.5 * np.pi, 2 * np.pi),
            (ox + w_int - corner_radius, oy + l_int - corner_radius, 0, 0.5 * np.pi),
            (ox + corner_radius, oy + l_int - corner_radius, 0.5 * np.pi, np.pi),
        )
        for cx, cy, angle0, angle1 in corner_specs:
            add_rounded_corner_wall(
                verts, faces, cx=cx, cy=cy, angle0=angle0, angle1=angle1,
                inner_radius=corner_radius, thickness=wall, oy=oy, length=l_int,
                h_front=h_front, h_back=h_back, z_floor=z_floor,
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

    if preset_id == "mail_spine":
        _add_dividers_mail_spine(
            verts, faces, ox=ox, oy=oy, divider=divider, z_floor=z_floor, divider_h=divider_h,
        )
    elif preset_id == "row_four":
        _add_dividers_row_four(
            verts, faces, ox=ox, oy=oy, divider=divider, z_floor=z_floor, divider_h=divider_h,
        )
    else:
        _add_dividers_grid(
            verts, faces, ox=ox, oy=oy, layout=layout, w_int=w_int, divider=divider,
            z_floor=z_floor, divider_h=divider_h, letters_at_back=True,
        )

    if style != "minimal":
        from entryway_styles import apply_style

        apply_style(
            style,
            verts,
            faces,
            ox=ox,
            oy=oy,
            w_int=w_int,
            l_int=l_int,
            wall=wall,
            bottom=bottom,
            z_floor=z_floor,
            h_front=h_front,
            h_back=h_back,
            outer_w=outer_w,
            outer_l=outer_l,
            layout=layout,
        )

    return verts, faces


def write_binary_stl(path: Path, verts: list, faces: list, header_text: str = "Entryway storage box") -> None:
    # Merge overlapping closed solids into one watertight body. Bambu Studio
    # can repair overlapping shells, but exporting a clean union is safer and
    # makes automated geometry checks deterministic.
    try:
        import trimesh

        mesh = trimesh.Trimesh(vertices=np.asarray(verts), faces=np.asarray(faces), process=True)
        mesh.merge_vertices()
        parts = list(mesh.split(only_watertight=False))
        for part in parts:
            trimesh.repair.fix_normals(part, multibody=False)
        if parts and all(part.is_volume for part in parts):
            united = trimesh.boolean.union(parts, engine="manifold")
            if united is not None and united.is_volume:
                verts = united.vertices.tolist()
                faces = united.faces.tolist()
    except (ImportError, ValueError):
        # Keep the dependency-light raw export available for development.
        # The committed production STL is always checked by check_entryway_fit.py.
        pass

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


def bambu_print_settings() -> dict:
    """Optimized Bambu Studio parameters for this organizer."""
    return {
        "recommended_material": {
            "primary": "PETG",
            "alternative": "PLA",
            "reason": "PETG is tougher for dividers and daily entryway use; PLA is fine for indoor light use.",
        },
        "preset_files": {
            "petg_process": "bambu/entryway_box_process_petg.json",
            "petg_filament": "bambu/entryway_box_filament_petg.json",
            "pla_process": "bambu/entryway_box_process_pla.json",
            "pla_filament": "bambu/entryway_box_filament_pla.json",
            "guide": "bambu/PRINT_GUIDE.md",
            "import": "Bambu Studio → File → Import → Import Configs → select JSON pair",
        },
        "orientation": {
            "placement": "Bottom face flat on bed (Z up = box height)",
            "supports": False,
            "brim_mm_petg": 5,
            "brim_mm_pla": 3,
        },
        "process_petg": {
            "layer_height_mm": 0.2,
            "line_width_mm": 0.42,
            "wall_loops": 3,
            "top_shell_layers": 5,
            "bottom_shell_layers": 6,
            "sparse_infill_percent": 18,
            "sparse_infill_pattern": "gyroid",
            "detect_thin_wall": True,
            "enable_support": False,
            "initial_layer_speed_mm_s": 35,
            "outer_wall_speed_mm_s": 100,
            "sparse_infill_speed_mm_s": 220,
        },
        "process_pla": {
            "layer_height_mm": 0.2,
            "line_width_mm": 0.42,
            "wall_loops": 3,
            "top_shell_layers": 5,
            "bottom_shell_layers": 6,
            "sparse_infill_percent": 20,
            "sparse_infill_pattern": "gyroid",
            "detect_thin_wall": True,
            "enable_support": False,
            "initial_layer_speed_mm_s": 40,
            "outer_wall_speed_mm_s": 120,
            "sparse_infill_speed_mm_s": 250,
        },
        "temperatures": {
            "petg": {"nozzle_c": 245, "nozzle_first_layer_c": 250, "bed_c": 78, "fan_max_percent": 40},
            "pla": {"nozzle_c": 220, "nozzle_first_layer_c": 225, "bed_c": 60, "fan_max_percent": 100},
        },
        "estimates": {
            "time_hours": "3.5-5",
            "filament_grams": "180-220",
            "nozzle_mm": 0.4,
        },
        "optional_fine_nozzle": {
            "nozzle_mm": 0.2,
            "layer_height_mm": 0.1,
            "wall_loops": 4,
            "note": "Use if 1.5 mm dividers look weak; print time roughly doubles.",
        },
    }


def main() -> None:
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from entryway_layouts import LAYOUT_PRESETS, preset_catalog
    from entryway_styles import STYLES, style_catalog

    parser = argparse.ArgumentParser(description="Generate sloped entryway storage box STL for Bambu Lab")
    parser.add_argument("--out", type=Path, default=Path("output/entryway_storage_box.stl"))
    parser.add_argument("--spec-out", type=Path, default=Path("output/entryway_storage_box_spec.json"))
    parser.add_argument(
        "--style",
        choices=list(STYLES.keys()),
        default="rounded",
        help="Visual style variant (use --all-styles to export every version)",
    )
    parser.add_argument(
        "--layout",
        choices=("modular", "compact"),
        default="compact",
        help="compact = corrected 200×228 mm sketch layout; modular = gapped wider tray",
    )
    parser.add_argument(
        "--preset",
        choices=tuple(LAYOUT_PRESETS.keys()),
        default=None,
        help="Layout preset (overrides --layout when set)",
    )
    parser.add_argument(
        "--all-layouts",
        action="store_true",
        help="Export every layout preset STL to output/layouts/",
    )
    parser.add_argument("--all-styles", action="store_true", help="Write all style STLs to output/styles/")
    parser.add_argument("--wall", type=float, default=WALL)
    parser.add_argument("--divider", type=float, default=DIVIDER)
    parser.add_argument("--bottom", type=float, default=BOTTOM)
    parser.add_argument("--lip", type=float, default=LIP)
    parser.add_argument("--gutter", type=float, default=10.0, help="Gap between blocks (mm, modular layout)")
    parser.add_argument("--margin-x", type=float, default=21.0, help="Side inner margin (mm)")
    parser.add_argument("--margin-y", type=float, default=4.0, help="Front/back inner margin (mm)")
    parser.add_argument("--h-front", type=float, default=H_FRONT, help="Rim height at entryway front (mm)")
    parser.add_argument("--h-back", type=float, default=H_BACK, help="Rim height at back / letters end (mm)")
    args = parser.parse_args()

    def resolve_preset(preset_id: str):
        preset = LAYOUT_PRESETS[preset_id]
        grid = preset.layout if preset.is_grid() else LAYOUT_COMPACT
        return preset, grid, preset.w_int, preset.l_int, preset.compartments

    layout = LAYOUT_COMPACT
    w_int, l_int = layout.w_int, layout.l_int
    compartments = layout.compartments()
    preset_id = "classic"

    if args.preset:
        preset, layout, w_int, l_int, compartments = resolve_preset(args.preset)
        preset_id = args.preset
    elif args.layout != "compact":
        layout = Layout(gutter=args.gutter, margin_x=args.margin_x, margin_y=args.margin_y)
        w_int, l_int = layout.w_int, layout.l_int
        compartments = layout.compartments()

    style = args.style
    if args.preset:
        style = LAYOUT_PRESETS[args.preset].style if not args.all_styles else args.style

    if args.all_layouts:
        layouts_dir = Path("output/layouts")
        layouts_dir.mkdir(parents=True, exist_ok=True)
        for pid, preset in LAYOUT_PRESETS.items():
            _, grid, w_int, l_int, compartments = resolve_preset(pid)
            verts, faces = build_mesh(
                w_int=w_int,
                l_int=l_int,
                layout=grid,
                wall=args.wall,
                divider=args.divider,
                bottom=args.bottom,
                lip=args.lip,
                h_front=args.h_front,
                h_back=args.h_back,
                style=preset.style,
                preset_id=pid,
            )
            out = layouts_dir / f"entryway_{pid}.stl"
            write_binary_stl(out, verts, faces, f"Entryway {pid} - Bambu")
            print(f"Wrote {out} [{pid}/{preset.style}] ({len(faces) * 2} triangles, {w_int:.0f}x{l_int:.0f} mm)")
        catalog_path = layouts_dir / "catalog.json"
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump({"layouts": preset_catalog(), "viewer": "viewer/gallery.html"}, f, indent=2, ensure_ascii=False)
        print(f"Wrote {catalog_path}")
        if not args.all_styles and args.preset is None:
            import shutil

            shutil.copy(layouts_dir / "entryway_classic.stl", args.out)
        layout, w_int, l_int, compartments = resolve_preset("classic")[1:]

    build_single = (not args.all_layouts) or args.all_styles or args.preset
    if build_single:
        styles_to_build = list(STYLES.keys()) if args.all_styles else [style]
        mesh_kw = dict(
            w_int=w_int,
            l_int=l_int,
            layout=layout,
            wall=args.wall,
            divider=args.divider,
            bottom=args.bottom,
            lip=args.lip,
            h_front=args.h_front,
            h_back=args.h_back,
            preset_id=preset_id if args.preset or args.layout == "compact" else "classic",
        )

        for st in styles_to_build:
            if args.all_styles:
                out = Path(f"output/styles/entryway_box_{st}.stl")
            elif args.preset and args.preset != "classic":
                out = Path(f"output/layouts/entryway_{args.preset}.stl")
            else:
                out = args.out
            verts, faces = build_mesh(**mesh_kw, style=st)
            write_binary_stl(out, verts, faces, f"Entryway box {st} - Bambu")
            print(f"Wrote {out} [{st}] ({len(faces) * 2} triangles)")

    if args.all_styles:
        import shutil

        styles_dir = Path("output/styles")
        styles_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(styles_dir / "entryway_box_rounded.stl", "output/entryway_storage_box.stl")
        catalog_path = styles_dir / "catalog.json"
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump({"styles": style_catalog(), "viewer": "viewer/entryway.html"}, f, indent=2, ensure_ascii=False)
        print(f"Wrote {catalog_path}")

    spec = {
        "style": args.style if not args.all_styles else "all",
        "layout": args.preset or args.layout,
        "layout_presets": preset_catalog() if args.all_layouts else None,
        "style_variants": style_catalog(),
        "orientation": "Y=0 is entryway front (with lip); back = letters.",
        "internal_mm": {"width": w_int, "length": l_int},
        "layout_mm": {
            "gutter": layout.gutter,
            "margin_x": layout.margin_x,
            "margin_y": layout.margin_y,
            "cell_width": layout.col_w,
            "note": "Same cell sizes as original sketch; extra size = gutters + margins.",
        },
        "outer_mm": {
            "width": w_int + 2 * args.wall,
            "length": l_int + 2 * args.wall,
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
            for c in compartments
        ],
        "print_notes": {
            "software": "Bambu Studio — import STL + optional preset JSON from bambu/",
            "orientation": "Print flat on the bottom face.",
            "see_also": "bambu/PRINT_GUIDE.md",
        },
        "bambu_optimized": bambu_print_settings(),
    }
    path = args.spec_out
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)

    print(f"Wrote {args.spec_out}")
    print(
        f"Outer: {spec['outer_mm']['width']:.0f} x {spec['outer_mm']['length']:.0f} mm, "
        f"height front {spec['outer_mm']['height_front']:.0f} mm -> back {spec['outer_mm']['height_back']:.0f} mm"
    )
    if args.all_styles:
        print("Preview: python3 -m http.server 8766  →  http://localhost:8766/viewer/entryway.html")


if __name__ == "__main__":
    main()
