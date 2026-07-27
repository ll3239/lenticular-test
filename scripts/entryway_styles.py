#!/usr/bin/env python3
"""Style catalog and mesh decorators for entryway storage box variants."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def _gen():
    import generate_entryway_storage_box as gen

    return gen


@dataclass(frozen=True)
class StyleInfo:
    id: str
    name_en: str
    name_zh: str
    description: str
    look: str  # short visual hint


STYLES: dict[str, StyleInfo] = {
    "minimal": StyleInfo(
        "minimal",
        "Minimal",
        "极简直角",
        "Clean sharp edges, no decoration. Modern and print-fast.",
        "直角、干净、偏北欧",
    ),
    "rounded": StyleInfo(
        "rounded",
        "Rounded",
        "圆角柔和",
        "True 10 mm rounded outer walls and a 12 mm rounded base.",
        "圆角外壁、圆角底，边缘更温柔",
    ),
    "chamfer": StyleInfo(
        "chamfer",
        "Chamfer",
        "倒角线框",
        "45° chamfer on the top outer edge — crisp designer frame look.",
        "顶部斜切、像线框托盘",
    ),
    "tiered": StyleInfo(
        "tiered",
        "Tiered",
        "阶梯分层",
        "Subtle horizontal ledges on the outside at each layout tier.",
        "外壁分段台阶、建筑感",
    ),
    "wells": StyleInfo(
        "wells",
        "Bottle Wells",
        "精油凹槽",
        "Six circular retaining rings in the oil bay floor to hold bottles.",
        "精油格有圆形定位环",
    ),
    "accent": StyleInfo(
        "accent",
        "Accent Groove",
        "双槽装饰",
        "Rounded base + two horizontal accent grooves on the sides.",
        "圆角 + 侧面装饰槽线",
    ),
}


def add_cylinder_z(
    verts: list,
    faces: list,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    radius: float,
    segments: int = 24,
) -> None:
    gen = _gen()
    add_triangle, add_quad = gen.add_triangle, gen.add_quad

    if z1 < z0:
        z0, z1 = z1, z0
    angles = [2 * math.pi * i / segments for i in range(segments)]
    ring_lo = [(cx + radius * math.cos(a), cy + radius * math.sin(a), z0) for a in angles]
    ring_hi = [(cx + radius * math.cos(a), cy + radius * math.sin(a), z1) for a in angles]
    for i in range(segments):
        j = (i + 1) % segments
        add_quad(verts, faces, ring_lo[i], ring_lo[j], ring_hi[j], ring_hi[i])
    # caps
    center_lo = (cx, cy, z0)
    center_hi = (cx, cy, z1)
    for i in range(segments):
        j = (i + 1) % segments
        add_triangle(verts, faces, center_lo, ring_lo[j], ring_lo[i])
        add_triangle(verts, faces, center_hi, ring_hi[i], ring_hi[j])


def apply_rounded_base(
    verts: list,
    faces: list,
    *,
    outer_w: float,
    outer_l: float,
    bottom: float,
    radius: float = 8.0,
) -> None:
    """Replace sharp bottom footprint with rounded exterior corners (keeps top open)."""
    gen = _gen()
    add_box = gen.add_box

    r = min(radius, outer_w / 2 - 1, outer_l / 2 - 1)
    # Over-build corner blocks then rely on visual merge; add quarter-round columns
    add_box(verts, faces, r, 0, 0, outer_w - r, outer_l, bottom)
    add_box(verts, faces, 0, r, 0, outer_w, outer_l - r, bottom)
    for cx, cy in (
        (r, r),
        (outer_w - r, r),
        (r, outer_l - r),
        (outer_w - r, outer_l - r),
    ):
        add_cylinder_z(verts, faces, cx, cy, 0, bottom, r, segments=12)


def apply_rim_chamfer(
    verts: list,
    faces: list,
    *,
    ox: float,
    oy: float,
    w_int: float,
    l_int: float,
    wall: float,
    h_front: float,
    h_back: float,
    l_int_val: float,
    z_floor: float,
    chamfer: float = 3.0,
) -> None:
    """Top outer 45° chamfer band on front/back/side walls."""
    gen = _gen()
    add_box, rim_height = gen.add_box, gen.rim_height

    outer_w = w_int + 2 * wall
    c = chamfer

    def z_at(y_local: float, extra: float = 0.0) -> float:
        return z_floor + rim_height(y_local, h_front, h_back, l_int_val) + extra

    # Front outer chamfer (wedge outside front face)
    y0 = oy - c
    z0 = z_at(0)
    add_box(verts, faces, ox - c, y0, z0 - c, ox + w_int + c, oy, z0)

    # Back
    y_back = oy + l_int
    z1 = z_at(l_int_val)
    add_box(verts, faces, ox - c, y_back, z1 - c, ox + w_int + c, y_back + wall + c, z1)

    # Left / right side chamfer strips (simplified wedges)
    z_mid = z_at(l_int_val / 2)
    add_box(verts, faces, ox - c, oy, z_mid - c, ox, oy + l_int, z_mid)
    add_box(verts, faces, ox + w_int, oy, z_mid - c, ox + w_int + c, oy + l_int, z_mid)


def apply_tier_ledges(
    verts: list,
    faces: list,
    *,
    ox: float,
    oy: float,
    w_int: float,
    l_int: float,
    wall: float,
    z_floor: float,
    h_front: float,
    h_back: float,
    ledge: float = 1.5,
    band_h: float = 2.0,
) -> None:
    gen = _gen()
    add_box, rim_height = gen.add_box, gen.rim_height

    for y_local in (50, 100, 140, 180):
        y_abs = oy + y_local
        z = z_floor + rim_height(y_local, h_front, h_back, l_int) - band_h
        add_box(verts, faces, ox - ledge, y_abs - 1, z, ox + w_int + ledge, y_abs + 1, z + band_h)


def apply_accent_grooves(
    verts: list,
    faces: list,
    *,
    ox: float,
    oy: float,
    w_int: float,
    l_int: float,
    wall: float,
    z_floor: float,
    h_front: float,
    h_back: float,
    groove_depth: float = 1.2,
    groove_h: float = 2.0,
) -> None:
    gen = _gen()
    add_box, rim_height = gen.add_box, gen.rim_height

    for y_local in (35, 145):
        y_abs = oy + y_local
        z = z_floor + rim_height(y_local, h_front, h_back, l_int) * 0.55
        # Left groove (inset from outer left)
        add_box(
            verts,
            faces,
            ox - wall - groove_depth,
            y_abs - 0.75,
            z,
            ox - wall + 0.01,
            y_abs + 0.75,
            z + groove_h,
        )
        add_box(
            verts,
            faces,
            ox + w_int + wall - 0.01,
            y_abs - 0.75,
            z,
            ox + w_int + wall + groove_depth,
            y_abs + 0.75,
            z + groove_h,
        )


def add_hollow_cylinder_z(
    verts: list,
    faces: list,
    cx: float,
    cy: float,
    z0: float,
    z1: float,
    r_outer: float,
    r_inner: float,
    segments: int = 24,
) -> None:
    gen = _gen()
    add_quad = gen.add_quad

    if z1 < z0:
        z0, z1 = z1, z0
    angles = [2 * math.pi * i / segments for i in range(segments)]
    for i in range(segments):
        j = (i + 1) % segments
        a0, a1 = angles[i], angles[j]
        o0 = (cx + r_outer * math.cos(a0), cy + r_outer * math.sin(a0), z0)
        o1 = (cx + r_outer * math.cos(a1), cy + r_outer * math.sin(a1), z0)
        o2 = (cx + r_outer * math.cos(a1), cy + r_outer * math.sin(a1), z1)
        o3 = (cx + r_outer * math.cos(a0), cy + r_outer * math.sin(a0), z1)
        i0 = (cx + r_inner * math.cos(a0), cy + r_inner * math.sin(a0), z0)
        i1 = (cx + r_inner * math.cos(a1), cy + r_inner * math.sin(a1), z0)
        i2 = (cx + r_inner * math.cos(a1), cy + r_inner * math.sin(a1), z1)
        i3 = (cx + r_inner * math.cos(a0), cy + r_inner * math.sin(a0), z1)
        add_quad(verts, faces, o0, o1, o2, o3)
        add_quad(verts, faces, i1, i0, i3, i2)
        add_quad(verts, faces, o3, o2, i2, i3)
        add_quad(verts, faces, o1, o0, i0, i1)


def apply_oil_wells(
    verts: list,
    faces: list,
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    ring_h: float = 4.0,
    bottle_dia: float = 30.0,
    z_floor: float,
) -> None:
    """Six bottle retaining rings in the oil bay."""
    margin = 12.0
    bay_x0 = x0 + margin
    bay_x1 = x1 - margin
    bay_y0 = y0 + margin
    bay_y1 = y1 - margin
    xs = np.linspace(bay_x0 + bottle_dia / 2, bay_x1 - bottle_dia / 2, 3)
    ys = np.linspace(bay_y0 + bottle_dia / 2, bay_y1 - bottle_dia / 2, 2)
    r_outer = bottle_dia / 2 + 2.5
    r_inner = bottle_dia / 2 - 1.0
    for cx in xs:
        for cy in ys:
            add_hollow_cylinder_z(
                verts, faces, float(cx), float(cy), z_floor - 0.4, z_floor + ring_h, r_outer, r_inner, segments=20
            )


def apply_outer_corner_rounds(
    verts: list,
    faces: list,
    *,
    outer_w: float,
    outer_l: float,
    wall: float,
    z_floor: float,
    h_front: float,
    h_back: float,
    l_int: float,
    radius: float = 10.0,
) -> None:
    """Quarter-round vertical pillars on the four outer footprint corners."""
    gen = _gen()
    rim_height = gen.rim_height

    r = min(radius, outer_w / 2 - 1, outer_l / 2 - 1)
    corners = (
        (r, r, 0.0, h_front),
        (outer_w - r, r, 0.0, h_front),
        (r, outer_l - r, l_int, h_back),
        (outer_w - r, outer_l - r, l_int, h_back),
    )
    for cx, cy, y_local, h_rim in corners:
        z_top = z_floor + h_rim
        add_cylinder_z(verts, faces, cx, cy, z_floor, z_top, r, segments=16)


def apply_soft_rim_cap(
    verts: list,
    faces: list,
    *,
    ox: float,
    oy: float,
    w_int: float,
    l_int: float,
    wall: float,
    z_floor: float,
    h_front: float,
    h_back: float,
    cap_h: float = 2.0,
    inset: float = 1.5,
) -> None:
    gen = _gen()
    add_box, rim_height = gen.add_box, gen.rim_height

    for y_local in np.linspace(0, l_int, 5):
        y_abs = oy + float(y_local)
        z = z_floor + rim_height(float(y_local), h_front, h_back, l_int)
        add_box(
            verts,
            faces,
            ox + inset,
            y_abs - 2,
            z,
            ox + w_int - inset,
            y_abs + 2,
            z + cap_h,
        )


def apply_style(
    style: str,
    verts: list,
    faces: list,
    *,
    ox: float,
    oy: float,
    w_int: float,
    l_int: float,
    wall: float,
    bottom: float,
    z_floor: float,
    h_front: float,
    h_back: float,
    outer_w: float,
    outer_l: float,
    layout=None,
) -> None:
    if style == "minimal":
        return
    if style == "rounded":
        # Rounded base and true quarter-annulus corner walls are constructed
        # directly by build_mesh so they preserve the usable compartment area.
        return
    if style == "chamfer":
        apply_rim_chamfer(
            verts, faces, ox=ox, oy=oy, w_int=w_int, l_int=l_int, wall=wall,
            h_front=h_front, h_back=h_back, l_int_val=l_int, z_floor=z_floor,
        )
    if style == "tiered":
        apply_tier_ledges(
            verts, faces, ox=ox, oy=oy, w_int=w_int, l_int=l_int, wall=wall,
            z_floor=z_floor, h_front=h_front, h_back=h_back,
        )
    if style == "wells":
        if layout is not None:
            comps = {c.name: c for c in layout.compartments()}
            o = comps["essential_oils"]
            apply_oil_wells(
                verts, faces,
                x0=ox + o.x0, x1=ox + o.x1, y0=oy + o.y0, y1=oy + o.y1,
                z_floor=z_floor,
            )
        else:
            apply_oil_wells(verts, faces, x0=ox + 100, x1=ox + 200, y0=oy, y1=oy + 100, z_floor=z_floor)
    if style == "accent":
        apply_accent_grooves(
            verts, faces, ox=ox, oy=oy, w_int=w_int, l_int=l_int, wall=wall,
            z_floor=z_floor, h_front=h_front, h_back=h_back,
        )
        apply_rim_chamfer(
            verts, faces, ox=ox, oy=oy, w_int=w_int, l_int=l_int, wall=wall,
            h_front=h_front, h_back=h_back, l_int_val=l_int, z_floor=z_floor, chamfer=2.0,
        )


def style_catalog() -> list[dict]:
    return [
        {
            "id": s.id,
            "name_en": s.name_en,
            "name_zh": s.name_zh,
            "description": s.description,
            "look": s.look,
            "stl": f"output/styles/entryway_box_{s.id}.stl",
        }
        for s in STYLES.values()
    ]
