#!/usr/bin/env python3
"""Generate internal dimension sheets for each compartment (front/back baffle heights, width, depth)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_entryway_storage_box import (
    CARD_SLOT_INTERNAL_H,
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
    "receipts": "收据",
    "card_1": "卡片1",
    "card_2": "卡片2",
    "misc_cards": "散卡片",
    "power_banks": "充电宝",
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


def compartment_dividers_y_for_cell(c: Compartment, layout: Layout) -> tuple[float, ...]:
    """Horizontal divider Y positions that actually cross this cell."""
    ym0, ym1 = layout.y_mid0, layout.y_mid1
    xl0, xl1, xr0, xr1 = layout.x_left0, layout.x_left1, layout.x_right0, layout.x_right1
    edges: list[float] = []

    y_front_zone = layout.y_front1 + layout.gutter / 2
    y_letters_zone = layout.y_mid1 + layout.gutter / 2
    if c.y0 <= y_front_zone <= c.y1:
        edges.append(y_front_zone)
    if c.name == "letters" or (c.x0 <= xl0 and c.x1 >= xr1):
        if c.y0 <= y_letters_zone <= c.y1:
            edges.append(y_letters_zone)

    spans_left = c.x0 < xl1 and c.x1 > xl0
    spans_right = c.x0 < xr1 and c.x1 > xr0
    if spans_right and not spans_left and c.y0 < layout.y_mid0 - 0.01:
        y0 = layout.y_front0
        edges.extend([
            y0 + layout.left_receipts_span,
            y0 + layout.left_receipts_span + layout.left_card_span,
            y0 + layout.left_receipts_span + 2 * layout.left_card_span,
        ])
    elif spans_right and not spans_left and c.y0 >= layout.y_mid0 - 0.01:
        edges.append(layout.y_mid0 + layout.right_cable_span)

    return tuple(sorted(set(edges)))


def baffle_height(y: float, layout: Layout, compartment_id: str = "") -> float:
    """Internal usable height at local Y (floor → partition top, ~10 mm below rim)."""
    rim = rim_height(y, H_FRONT, H_BACK, layout.l_int, layout)
    h = rim - PARTITION_CLEARANCE
    if compartment_id in ("card_1", "card_2"):
        h = min(h, CARD_SLOT_INTERNAL_H)
    return round(h, 1)


def compartment_dims(c: Compartment, layout: Layout) -> dict:
    x_edges = compartment_dividers_x(layout)
    y_edges = compartment_dividers_y_for_cell(c, layout)

    width_net = net_internal_span(c.x0, c.x1, full_size=layout.w_int, divider_edges=x_edges)
    depth_net = net_internal_span(c.y0, c.y1, full_size=layout.l_int, divider_edges=y_edges)

    front_h = baffle_height(c.y0, layout, c.name)
    back_h = baffle_height(c.y1, layout, c.name)

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
            "- **净宽 / 净深**：内腔可用尺寸（已扣除挡板占用的 1.5 mm）。",
            "- **前挡板高**：该格 *门口侧*（Y 较小）的内腔可用高度。",
            "- **后挡板高**：该格 *墙侧*（Y 较大）的内腔可用高度。",
            "- 卡片1/2 挡板高度限制在 **80 mm** 内腔（适配约 8 cm 卡包），比后方斜面更低、更好拿。",
            "- **信件区**同样延续坡度：前侧（Y≈198）低于后侧（Y=228 贴墙处 150 mm 外沿）。",
            "",
            "## 俯视分区示意",
            "",
            "```",
            "  Y=0 门口（低 3 cm）                              ",
            "  ┌──────────100──────────┬──────────100──────────┐",
            "  │      耳机/杂物         │ 收据│卡1│卡2│散卡      │ 100",
            "  ├──────────100──────────┼──────────100──────────┤",
            "  │        精油           │ gutter │ 数据线 │ 充电宝   │  98",
            "  ├───────────────────────┴───────────────────────┤",
            "  │                    信件 (201.5 宽)               │  30",
            "  └─────────────────────────────────────────────────┘  Y=229 墙",
            "  X=0                                            X=201.5",
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
        f"Y=0 门口 → Y={h:.1f} 墙；数字为净宽×净深，下方为前挡板高/后挡板高</text>",
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
    parts.append(f'<text x="{sx(w/2):.1f}" y="{sy(h) + 36:.1f}" text-anchor="middle" class="axis">宽 X = {w:.1f} mm</text>')
    parts.append(f'<text x="24" y="{sy(h/2):.1f}" class="axis" transform="rotate(-90 24 {sy(h/2):.1f})">深 Y = {h:.1f} mm</text>')
    parts.append(f'<text x="{sx(w/2):.1f}" y="{sy(-8):.1f}" text-anchor="middle" class="axis">门口 Y=0</text>')
    parts.append(f'<text x="{sx(w/2):.1f}" y="{sy(h+18):.1f}" text-anchor="middle" class="axis">墙 Y={h:.1f}</text>')

    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def write_html(report: dict, path: Path) -> None:
    fp = report["internal_footprint_mm"]
    rows = []
    for c in report["compartments"]:
        net = c["internal_net_mm"]
        bh = c["baffle_height_mm"]
        pos = c["position_internal_mm"]
        rows.append(
            f"<tr><td>{c['name_zh']}</td>"
            f"<td>{net['width_x']:.2f}</td><td>{net['depth_y']:.2f}</td>"
            f"<td>{bh['front_at_y0']:.1f}</td><td>{bh['back_at_y1']:.1f}</td>"
            f"<td>{pos['y0']:.0f} → {pos['y1']:.0f}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>门口收纳盒 · 内腔尺寸图</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", sans-serif;
      background: #0f1117; color: #e8eaef; padding: 16px 20px 40px;
      max-width: 980px; margin: 0 auto;
    }}
    h1 {{ font-size: 20px; margin-bottom: 6px; }}
    p.sub {{ color: #8b92a3; font-size: 14px; line-height: 1.55; margin-bottom: 16px; }}
    a {{ color: #6b9fff; }}
    .nav {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
    .nav a {{
      background: #22262f; border: 1px solid #3a4050; border-radius: 8px;
      padding: 8px 12px; text-decoration: none; font-size: 13px; color: #e8eaef;
    }}
    .svg-wrap {{
      background: #fff; border-radius: 14px; border: 1px solid #2a3040;
      padding: 12px; margin-bottom: 20px; overflow-x: auto;
    }}
    .svg-wrap object {{ width: 100%; max-width: 684px; display: block; margin: 0 auto; }}
    table {{
      width: 100%; border-collapse: collapse; font-size: 13px;
      background: #181b22; border: 1px solid #2a3040; border-radius: 12px; overflow: hidden;
    }}
    th, td {{ padding: 10px 12px; text-align: right; border-bottom: 1px solid #2a3040; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: #1e2330; color: #c8d0e0; font-weight: 600; }}
    tr:last-child td {{ border-bottom: none; }}
    .note {{
      margin-top: 16px; padding: 14px; background: #181b22;
      border: 1px solid #2e3340; border-radius: 12px; font-size: 13px; color: #9aa3b5; line-height: 1.55;
    }}
  </style>
</head>
<body>
  <h1>门口收纳盒 · 内腔尺寸验证</h1>
  <p class="sub">
    内腔 footprint <strong>{fp['width_x']:.1f} × {fp['depth_y']:.1f} mm</strong>；
    左中层 <strong>精油 100×97 mm</strong>；右前排 <strong>收据/卡片/散卡</strong>；
    右中层为 <strong>数据线（前 24 mm）</strong> + <strong>充电宝（后 ≥60 mm）</strong>。
  </p>
  <div class="nav">
    <a href="entryway.html">3D 预览</a>
    <a href="preview.html">综合预览页</a>
    <a href="gallery.html">截图画廊</a>
    <a href="../output/entryway_dimensions.svg">下载 SVG</a>
    <a href="../output/ENTRYWAY_DIMENSIONS.md">Markdown 尺寸表</a>
  </div>

  <div class="svg-wrap">
    <object type="image/svg+xml" data="../output/entryway_dimensions.svg" aria-label="内腔尺寸 SVG">
      <img src="../output/entryway_dimensions.svg" alt="内腔尺寸图" />
    </object>
  </div>

  <table>
    <thead>
      <tr>
        <th>区域</th><th>净宽 mm</th><th>净深 mm</th>
        <th>前挡板高</th><th>后挡板高</th><th>Y 范围</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>

  <div class="note">
    数字为扣除 1.5 mm 共用挡板后的净尺寸。挡板顶比外沿低 {report['partition_clearance_mm']:.0f} mm。
    外廓约 205.5 × 232.8 mm，P1S 256 mm 热床可一次打印。
  </div>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate internal compartment dimension sheets.")
    parser.add_argument("--json-out", type=Path, default=Path("output/entryway_dimensions.json"))
    parser.add_argument("--md-out", type=Path, default=Path("output/ENTRYWAY_DIMENSIONS.md"))
    parser.add_argument("--svg-out", type=Path, default=Path("output/entryway_dimensions.svg"))
    parser.add_argument("--html-out", type=Path, default=Path("viewer/dimensions.html"))
    args = parser.parse_args()

    report = build_report(LAYOUT_COMPACT)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    write_markdown(report, args.md_out)
    write_svg(report, args.svg_out)
    write_html(report, args.html_out)
    print(f"Wrote {args.json_out}")
    print(f"Wrote {args.md_out}")
    print(f"Wrote {args.svg_out}")
    print(f"Wrote {args.html_out}")


if __name__ == "__main__":
    main()
