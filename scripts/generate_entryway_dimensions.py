#!/usr/bin/env python3
"""Generate internal dimension sheets for each compartment (front/back baffle heights, width, depth)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_entryway_storage_box import (
    DIVIDER,
    H_BACK,
    H_FRONT,
    LAYOUT_COMPACT,
    PARTITION_CLEARANCE,
    Compartment,
    Layout,
    rim_height,
)

COMPARTMENT_ZH = {
    "earphones_other": "耳机/杂物",
    "essential_oils": "精油",
    "keys": "钥匙",
    "card_1": "卡片1",
    "card_2": "卡片2",
    "receipts": "收据",
    "power_bank_1": "充电宝1",
    "power_bank_2": "充电宝2",
    "data_cable": "数据线",
    "letters": "信件",
}


def _divider_deduction(a0: float, a1: float, edge: float, full_size: float) -> float:
    """How much a divider on `edge` reduces usable span of [a0, a1]."""
    if edge < a0 or edge > a1:
        return 0.0
    if a0 < edge < a1:
        return DIVIDER
    # Divider exactly on a cell boundary — half thickness stays inside this cell.
    if edge == a0 and a0 > 0:
        return DIVIDER / 2
    if edge == a1 and a1 < full_size:
        return DIVIDER / 2
    return 0.0


def net_internal_span(
    a0: float,
    a1: float,
    *,
    full_size: float,
    divider_edges: tuple[float, ...] = (),
) -> float:
    """Usable span along one axis after 1.5 mm dividers on internal boundaries."""
    span = a1 - a0
    for edge in divider_edges:
        span -= _divider_deduction(a0, a1, edge, full_size)
    return round(span, 2)


def compartment_dividers_x(layout: Layout) -> tuple[float, ...]:
    x_div = (layout.x_left1 + layout.x_right0) / 2
    return (x_div,)


def compartment_dividers_y(layout: Layout) -> tuple[float, ...]:
    ym0, ym1 = layout.y_mid0, layout.y_mid1
    return (
        layout.y_front1 + layout.gutter / 2,
        layout.y_mid1 + layout.gutter / 2,
        ym0 + 20,
        ym0 + 40,
        ym0 + 60,
        ym0 + 30,
        ym0 + 60,
        ym1,
    )


def baffle_height(y: float, layout: Layout) -> float:
    """Internal usable height at local Y (floor → partition top, ~10 mm below rim)."""
    rim = rim_height(y, H_FRONT, H_BACK, layout.l_int, layout)
    return round(rim - PARTITION_CLEARANCE, 1)


def compartment_dims(c: Compartment, layout: Layout) -> dict:
    x_edges = compartment_dividers_x(layout)
    y_edges = compartment_dividers_y(layout)

    width_net = net_internal_span(c.x0, c.x1, full_size=layout.w_int, divider_edges=x_edges)
    depth_net = net_internal_span(c.y0, c.y1, full_size=layout.l_int, divider_edges=y_edges)

    front_h = baffle_height(c.y0, layout)
    back_h = baffle_height(c.y1, layout)

    return {
        "id": c.name,
        "name_zh": COMPARTMENT_ZH.get(c.name, c.name),
        "name_en": c.name,
        "position_internal_mm": {
            "x0": c.x0,
            "x1": c.x1,
            "y0": c.y0,
            "y1": c.y1,
            "note": "Y=0 为门口（前），Y 增大靠墙（后）",
        },
        "internal_net_mm": {
            "width_x": width_net,
            "depth_y": depth_net,
        },
        "internal_bbox_mm": {
            "width_x": round(c.x1 - c.x0, 2),
            "depth_y": round(c.y1 - c.y0, 2),
        },
        "baffle_height_mm": {
            "front_at_y0": front_h,
            "back_at_y1": back_h,
            "note": "内腔可用高度：外沿高度减 10 mm 挡板间隙；前后因坡度不同",
        },
        "rim_height_mm": {
            "front_at_y0": round(front_h + PARTITION_CLEARANCE, 1),
            "back_at_y1": round(back_h + PARTITION_CLEARANCE, 1),
        },
    }


def build_report(layout: Layout | None = None) -> dict:
    layout = layout or LAYOUT_COMPACT
    cells = [compartment_dims(c, layout) for c in layout.compartments()]
    return {
        "title": "玄关收纳盒 — 内腔尺寸明细",
        "orientation": "俯视：X 为左右宽，Y 为前后深；Y=0 是门口，Y 最大处贴墙。",
        "internal_footprint_mm": {"width_x": layout.w_int, "depth_y": layout.l_int},
        "divider_thickness_mm": DIVIDER,
        "partition_clearance_mm": PARTITION_CLEARANCE,
        "slope_rim_mm": {"front_y0": H_FRONT, "back_y_max": H_BACK},
        "compartments": cells,
    }


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# 玄关收纳盒 — 内腔尺寸验证表",
        "",
        report["orientation"],
        "",
        f"- 内腔总 footprint：**{report['internal_footprint_mm']['width_x']:.0f} × "
        f"{report['internal_footprint_mm']['depth_y']:.0f} mm**（宽 × 深）",
        f"- 挡板厚度：{report['divider_thickness_mm']:.1f} mm；挡板顶比外沿低 "
        f"{report['partition_clearance_mm']:.0f} mm",
        f"- 外沿高度：门口 Y=0 处 {report['slope_rim_mm']['front_y0']:.0f} mm → "
        f"墙侧 {report['slope_rim_mm']['back_y_max']:.0f} mm（梯形坡度）",
        "",
        "## 每格净尺寸（已扣共用挡板）",
        "",
        "| 区域 | 净宽 (X) mm | 净深 (Y) mm | 前挡板高 mm | 后挡板高 mm | 内腔坐标 Y 范围 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for c in report["compartments"]:
        pos = c["position_internal_mm"]
        net = c["internal_net_mm"]
        bh = c["baffle_height_mm"]
        lines.append(
            f"| {c['name_zh']} | {net['width_x']:.2f} | {net['depth_y']:.2f} | "
            f"{bh['front_at_y0']:.1f} | {bh['back_at_y1']:.1f} | "
            f"{pos['y0']:.0f} → {pos['y1']:.0f} |"
        )

    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- **净宽 / 净深**：格与格之间的 1.5 mm 挡板各占一半（0.75 mm），已从数值中扣除。",
            "- **前挡板高**：该格 *门口侧*（Y 较小）的内腔可用高度。",
            "- **后挡板高**：该格 *墙侧*（Y 较大）的内腔可用高度。",
            "- 中间区各格前后高度不同，是因为外壁与挡板随 Y 方向梯形升高。",
            "- **信件区**同样延续坡度：前侧（Y≈198）低于后侧（Y=228 贴墙处 150 mm 外沿）。",
            "",
            "## 俯视分区示意",
            "",
            "```",
            "  Y=0 门口（低 3 cm）                              ",
            "  ┌──────────100──────────┬──────────100──────────┐",
            "  │      耳机/杂物         │        精油           │ 100",
            "  ├──────────100──────────┼──────────100──────────┤",
            "  │ 钥匙 │卡1│卡2│ 收据   │ 充1 │ 充2 │ 数据线    │  98",
            "  ├───────────────────────┴───────────────────────┤",
            "  │                    信件 (200 宽)                 │  30",
            "  └─────────────────────────────────────────────────┘  Y=228 墙",
            "  X=0                                              X=200",
            "```",
            "",
            "完整 SVG 尺寸图：`output/entryway_dimensions.svg`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_svg(report: dict, path: Path) -> None:
    layout = LAYOUT_COMPACT
    w, h = layout.w_int, layout.l_int
    scale = 2.6
    pad = 80
    svg_w = w * scale + pad * 2
    svg_h = h * scale + pad * 2 + 120

    def sx(x: float) -> float:
        return pad + x * scale

    def sy(y: float) -> float:
        return pad + y * scale

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w:.0f}" height="{svg_h:.0f}" '
        f'viewBox="0 0 {svg_w:.0f} {svg_h:.0f}">',
        "<style>",
        "  .title { font: bold 20px sans-serif; fill: #111; }",
        "  .subtitle { font: 13px sans-serif; fill: #444; }",
        "  .cell { fill: #f7f3ee; stroke: #8b6914; stroke-width: 1.5; }",
        "  .label { font: bold 13px sans-serif; fill: #222; }",
        "  .dim { font: 11px sans-serif; fill: #333; }",
        "  .axis { font: 12px sans-serif; fill: #666; }",
        "  .arrow { stroke: #666; stroke-width: 1; marker-end: url(#arr); }",
        "</style>",
        '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        '<path d="M0,0 L6,3 L0,6 Z" fill="#666"/></marker></defs>',
        f'<text x="{svg_w/2:.0f}" y="32" text-anchor="middle" class="title">内腔尺寸图（单位 mm）</text>',
        f'<text x="{svg_w/2:.0f}" y="52" text-anchor="middle" class="subtitle">'
        "Y=0 门口 → Y=228 墙；数字为净宽×净深，下方为前挡板高/后挡板高</text>",
    ]

    for c in report["compartments"]:
        pos = c["position_internal_mm"]
        net = c["internal_net_mm"]
        bh = c["baffle_height_mm"]
        x0, x1, y0, y1 = pos["x0"], pos["x1"], pos["y0"], pos["y1"]
        cx = (sx(x0) + sx(x1)) / 2
        cy = (sy(y0) + sy(y1)) / 2
        box_w = (x1 - x0) * scale
        box_h = (y1 - y0) * scale
        parts.append(
            f'<rect class="cell" x="{sx(x0):.1f}" y="{sy(y0):.1f}" '
            f'width="{box_w:.1f}" height="{box_h:.1f}"/>'
        )
        parts.append(f'<text x="{cx:.1f}" y="{cy - 14:.1f}" text-anchor="middle" class="label">{c["name_zh"]}</text>')
        parts.append(
            f'<text x="{cx:.1f}" y="{cy + 2:.1f}" text-anchor="middle" class="dim">'
            f'宽 {net["width_x"]:.1f} × 深 {net["depth_y"]:.1f}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{cy + 16:.1f}" text-anchor="middle" class="dim">'
            f'前 {bh["front_at_y0"]:.0f} / 后 {bh["back_at_y1"]:.0f}</text>'
        )

    # Outer frame
    parts.append(
        f'<rect fill="none" stroke="#333" stroke-width="2" '
        f'x="{sx(0):.1f}" y="{sy(0):.1f}" width="{w*scale:.1f}" height="{h*scale:.1f}"/>'
    )

    # Axis labels
    parts.append(f'<text x="{sx(w/2):.1f}" y="{sy(h) + 36:.1f}" text-anchor="middle" class="axis">宽 X = {w:.0f} mm</text>')
    parts.append(f'<text x="24" y="{sy(h/2):.1f}" class="axis" transform="rotate(-90 24 {sy(h/2):.1f})">深 Y = {h:.0f} mm</text>')
    parts.append(f'<text x="{sx(w/2):.1f}" y="{sy(-8):.1f}" text-anchor="middle" class="axis">门口 Y=0</text>')
    parts.append(f'<text x="{sx(w/2):.1f}" y="{sy(h+18):.1f}" text-anchor="middle" class="axis">墙 Y={h:.0f}</text>')

    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate internal compartment dimension sheets.")
    parser.add_argument("--json-out", type=Path, default=Path("output/entryway_dimensions.json"))
    parser.add_argument("--md-out", type=Path, default=Path("output/ENTRYWAY_DIMENSIONS.md"))
    parser.add_argument("--svg-out", type=Path, default=Path("output/entryway_dimensions.svg"))
    args = parser.parse_args()

    report = build_report(LAYOUT_COMPACT)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    write_markdown(report, args.md_out)
    write_svg(report, args.svg_out)
    print(f"Wrote {args.json_out}")
    print(f"Wrote {args.md_out}")
    print(f"Wrote {args.svg_out}")


if __name__ == "__main__":
    main()
