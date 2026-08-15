#!/usr/bin/env python3
"""
Draw the layout top view from the current compact layout.

- Internal footprint from LAYOUT_COMPACT
- TOP of image = back / wall / 信件
- BOTTOM = door / 门口
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

sys.path.insert(0, str(Path(__file__).parent))
from generate_entryway_dimensions import build_report
from generate_entryway_storage_box import LAYOUT_COMPACT

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

LABELS = {
    "earphones_other": "耳机+其他\n100×100",
    "essential_oils": "精油×6\n100×100",
    "receipts": "收据\n20",
    "card_1": "卡1\n25",
    "card_2": "卡2\n25",
    "misc_cards": "散卡片\n12",
    "data_cable": "数据线\n24 浅",
    "power_banks": "充电宝\n72 深",
    "letters": "信件",
}

COLORS = {
    "earphones_other": "#c8d8e8",
    "essential_oils": "#b8dcc8",
    "receipts": "#e0d0c0",
    "card_1": "#ece8d8",
    "card_2": "#ece8d8",
    "misc_cards": "#e8dcc8",
    "data_cable": "#d8e0d0",
    "power_banks": "#d0d8e8",
    "letters": "#e8e0d0",
}


def draw_top_sketch(out: Path) -> None:
    layout = LAYOUT_COMPACT
    w, h = layout.w_int, layout.l_int
    fig, ax = plt.subplots(figsize=(11, 6.8), dpi=180)
    fig.patch.set_facecolor("#fffef8")

    ax.set_facecolor("#fffef8")
    ax.set_xlim(-15, w + 30)
    ax.set_ylim(-20, h + 35)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        f"Layout (top view)  俯视图 · {w:.1f}×{h:.1f} mm",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )

    tray = FancyBboxPatch(
        (0, 0),
        w,
        h,
        boxstyle="round,pad=0,rounding_size=6",
        linewidth=2.5,
        edgecolor="#222",
        facecolor="#f5f5f0",
        zorder=0,
    )
    ax.add_patch(tray)

    for c in layout.compartments():
        x0, x1, y0, y1 = c.x0, c.x1, c.y0, c.y1
        dy0, dy1 = h - y1, h - y0
        patch = FancyBboxPatch(
            (x0, dy0),
            x1 - x0,
            dy1 - dy0,
            boxstyle="round,pad=0,rounding_size=3",
            linewidth=1.5,
            edgecolor="#333",
            facecolor=COLORS.get(c.name, "#eee"),
            zorder=1,
        )
        ax.add_patch(patch)
        ax.text(
            (x0 + x1) / 2,
            (dy0 + dy1) / 2,
            LABELS.get(c.name, c.name),
            ha="center",
            va="center",
            fontsize=8.5,
            color="#222",
        )

    ax.annotate("", xy=(0, h + 8), xytext=(w, h + 8), arrowprops=dict(arrowstyle="<->", lw=1.8, color="#333"))
    ax.text(w / 2, h + 16, f"{w/10:.2f} cm", ha="center", fontsize=12, fontweight="bold")
    ax.annotate("", xy=(-8, 0), xytext=(-8, h), arrowprops=dict(arrowstyle="<->", lw=1.8, color="#333"))
    ax.text(-18, h / 2, f"{h/10:.2f} cm", rotation=90, va="center", ha="center", fontsize=12, fontweight="bold")

    ax.text(w / 2, -12, "↓ 门口 DOOR", ha="center", fontsize=11, color="#c33", fontweight="bold")
    ax.text(w / 2, h + 28, "↑ 靠墙 BACK / 信件", ha="center", fontsize=11, color="#555", fontweight="bold")

    sx0, sy0 = w + 18, 20
    trap = Polygon(
        [(sx0, sy0), (sx0 + 28, sy0 + 5), (sx0 + 28, sy0 + 55), (sx0, sy0 + 50)],
        closed=True,
        fill=False,
        edgecolor="#666",
        lw=1.8,
    )
    ax.add_patch(trap)
    ax.text(sx0 + 34, sy0 + 28, "侧面\n信件端\n更高", fontsize=8, color="#666", va="center")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> None:
    draw_top_sketch(Path("output/previews/layout_from_sketch.png"))
    _ = build_report(LAYOUT_COMPACT)  # keep import used for future net-label overlay


if __name__ == "__main__":
    main()
