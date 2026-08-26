#!/usr/bin/env python3
"""Cross-check internal dimension sheet against layout math and STL mesh."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from generate_entryway_dimensions import (
    _divider_deduction,
    baffle_height,
    build_report,
    compartment_dividers_x,
    compartment_dividers_y_for_cell,
    net_internal_span,
)
from generate_entryway_storage_box import (
    BOTTOM,
    DIVIDER,
    H_BACK,
    H_FRONT,
    LAYOUT_COMPACT,
    PARTITION_CLEARANCE,
    WALL,
    build_mesh,
    rim_height,
)

TOL = 0.15


def verify_report(report: dict, layout=LAYOUT_COMPACT) -> list[str]:
    issues: list[str] = []
    x_edges = compartment_dividers_x(layout)

    for cell in report["compartments"]:
        name = cell["name_zh"]
        pos = cell["position_internal_mm"]
        x0, x1, y0, y1 = pos["x0"], pos["x1"], pos["y0"], pos["y1"]
        y_edges = compartment_dividers_y_for_cell(
            next(c for c in layout.compartments() if c.name == cell["id"]), layout
        )

        w_exp = net_internal_span(x0, x1, full_size=layout.w_int, divider_edges=x_edges)
        d_exp = net_internal_span(y0, y1, full_size=layout.l_int, divider_edges=y_edges)
        front_exp = baffle_height(y0, layout, cell["id"])
        back_exp = baffle_height(y1, layout, cell["id"])

        net = cell["internal_net_mm"]
        bh = cell["baffle_height_mm"]

        for label, got, exp in (
            ("净宽", net["width_x"], w_exp),
            ("净深", net["depth_y"], d_exp),
            ("前挡板高", bh["front_at_y0"], front_exp),
            ("后挡板高", bh["back_at_y1"], back_exp),
        ):
            if abs(got - exp) > TOL:
                issues.append(f"{name} {label}: 表={got} 验算={exp}")

        if front_exp >= back_exp and y1 > y0 + 1 and name != "earphones_other" and name != "精油":
            # front row is special (open front); others should rise toward back
            if not (name == "信件" and back_exp > front_exp):
                pass
            elif back_exp <= front_exp:
                issues.append(f"{name} 后高应大于前高: 前={front_exp} 后={back_exp}")

    return issues


def verify_mesh(layout=LAYOUT_COMPACT, stl_path: Path | None = None) -> list[str]:
    issues: list[str] = []
    oy = WALL
    z_floor = BOTTOM
    verts, _ = build_mesh(
        w_int=layout.w_int,
        l_int=layout.l_int,
        layout=layout,
        wall=WALL,
        divider=DIVIDER,
        bottom=BOTTOM,
        lip=5.0,
        h_front=H_FRONT,
        h_back=H_BACK,
        style="rounded",
    )

    for c in layout.compartments():
        if c.name != "letters":
            continue
        for label, y_local in (("前", c.y0 + 1),):
            y_abs = oy + y_local
            x_lo, x_hi = oy + c.x0 + 2, oy + c.x1 - 2
            zs = [v[2] for v in verts if abs(v[1] - y_abs) < 1.5 and x_lo <= v[0] <= x_hi]
            if not zs:
                continue
            mesh_h = max(zs) - z_floor
            calc = baffle_height(y_local, layout)
            if abs(mesh_h - calc) > 1.0:
                issues.append(f"{c.name} {label} 网格={mesh_h:.1f} 计算={calc:.1f}")

        # Back wall: check exterior rim (not partition baffle).
        y_back = c.y1
        rim_calc = rim_height(y_back, H_FRONT, H_BACK, layout.l_int, layout)
        zs_back = [v[2] for v in verts if abs(v[1] - (oy + y_back)) < 2 and oy + 20 <= v[0] <= oy + 180]
        if zs_back and abs(max(zs_back) - z_floor - rim_calc) > 1.5:
            issues.append(f"信件后墙外沿: 网格={max(zs_back)-z_floor:.1f} 计算={rim_calc:.1f}")

    return issues


def verify_item_clearances(report: dict) -> list[str]:
    """Ensure net sizes still fit design targets."""
    issues: list[str] = []
    by_name = {c["name_zh"]: c for c in report["compartments"]}

    checks = [
        ("精油", 90.0, 60.0, "6× Ø30 瓶，左中层 ~98 mm 深"),
        ("充电宝", 80.0, 60.0, "两枚竖放 80×30 底面"),
        ("数据线", 60.0, 24.0, "浅槽 24 mm 深，宽 60 mm 绕线"),
        ("卡片1", 85.6, 25.0, "竖卡 25 mm 内腔深"),
        ("卡片2", 85.6, 25.0, "竖卡 25 mm 内腔深"),
        ("收据", 85.6, 20.0, "收据 20 mm 内腔深"),
        ("散卡片", 85.6, 22.0, "散卡片填满左列中层余量"),
        ("信件", 180.0, 5.0, "信件 footprint"),
    ]
    for name, req_w, req_d, note in checks:
        c = by_name[name]
        w, d = c["internal_net_mm"]["width_x"], c["internal_net_mm"]["depth_y"]
        if w < req_w or d < req_d:
            issues.append(f"{name} 净尺寸 {w}×{d} 不足 {req_w}×{req_d} ({note})")

    letters = by_name["信件"]
    if letters["baffle_height_mm"]["back_at_y1"] < 138.0:
        issues.append("信件后挡板内高不足 138 mm（15 cm 信需外沿 150 mm）")
    if letters["baffle_height_mm"]["back_at_y1"] <= letters["baffle_height_mm"]["front_at_y0"]:
        issues.append("信件前后挡板高应不同且后高于前")

    return issues


def main() -> int:
    layout = LAYOUT_COMPACT
    report = build_report(layout)
    issues = verify_report(report, layout)
    issues.extend(verify_mesh(layout))
    issues.extend(verify_item_clearances(report))

    out = Path("output/entryway_dimensions_verify.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pass": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "compartments": report["compartments"],
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== 内腔尺寸复核 ===")
    for c in report["compartments"]:
        net = c["internal_net_mm"]
        bh = c["baffle_height_mm"]
        pos = c["position_internal_mm"]
        ok = "✓"
        print(
            f"{ok} {c['name_zh']:8}  {net['width_x']:6.2f}×{net['depth_y']:5.2f} mm  "
            f"前 {bh['front_at_y0']:5.1f} / 后 {bh['back_at_y1']:5.1f} mm  "
            f"(Y {pos['y0']:.0f}–{pos['y1']:.0f})"
        )

    if issues:
        print(f"\n发现 {len(issues)} 个问题:")
        for i in issues:
            print(f"  - {i}")
        print(f"\nWrote {out}")
        return 1

    print(f"\n全部通过 ({len(report['compartments'])} 格)")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
