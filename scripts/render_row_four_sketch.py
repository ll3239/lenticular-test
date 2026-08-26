#!/usr/bin/env python3
"""Draw the user's target layout: four large cells in one row, letters at back."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

sys.path.insert(0, str(Path(__file__).parent))
from entryway_layouts import LAYOUT_PRESETS

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

W, D = 400.0, 130.0


def draw(out: Path) -> None:
    preset = LAYOUT_PRESETS["row_four"]
    fig, ax = plt.subplots(figsize=(14, 5.5), dpi=180)
    fig.patch.set_facecolor("#fffef8")
    ax.set_facecolor("#fffef8")
    ax.set_xlim(-20, W + 40)
    ax.set_ylim(-25, D + 40)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Target layout — 4 cells in ONE row, mail at back\n"
        "横长方形 · 四格一排 · 信件在最后",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )

    tray = FancyBboxPatch(
        (0, 0), W, D,
        boxstyle="round,pad=0,rounding_size=8",
        linewidth=2.5, edgecolor="#222", facecolor="#f5f5f0", zorder=0,
    )
    ax.add_patch(tray)

    colors = {
        "earphones_other": "#c8d8e8",
        "essential_oils": "#b8dcc8",
        "keys": "#e8dcc8",
        "card_1": "#ece8d8",
        "card_2": "#ece8d8",
        "receipts": "#e0d0c0",
        "power_bank_1": "#d0d8e8",
        "power_bank_2": "#d0d8e8",
        "data_cable": "#d8e0d0",
        "letters": "#e8e0d0",
    }
    labels = {
        "earphones_other": "耳机+其他",
        "essential_oils": "精油×6",
        "keys": "钥匙",
        "card_1": "卡",
        "card_2": "卡",
        "receipts": "收据",
        "power_bank_1": "充电宝↑",
        "power_bank_2": "充电宝↑",
        "data_cable": "数据线",
        "letters": "信件",
    }

    for c in preset.compartments:
        dy0, dy1 = D - c.y1, D - c.y0
        ax.add_patch(
            FancyBboxPatch(
                (c.x0, dy0), c.x1 - c.x0, dy1 - dy0,
                boxstyle="round,pad=0,rounding_size=4",
                linewidth=1.5, edgecolor="#333", facecolor=colors[c.name], zorder=1,
            )
        )
        if c.name in ("earphones_other", "essential_oils", "letters"):
            ax.text((c.x0 + c.x1) / 2, (dy0 + dy1) / 2, labels[c.name], ha="center", va="center", fontsize=10)
        elif c.name in ("keys", "receipts", "data_cable"):
            ax.text((c.x0 + c.x1) / 2, (dy0 + dy1) / 2, labels[c.name], ha="center", va="center", fontsize=8)
        elif c.name.startswith("power_bank"):
            ax.text((c.x0 + c.x1) / 2, (dy0 + dy1) / 2, labels[c.name], ha="center", va="center", fontsize=8)
        elif c.name.startswith("card"):
            ax.text((c.x0 + c.x1) / 2, (dy0 + dy1) / 2, labels[c.name], ha="center", va="center", fontsize=7)

    ax.annotate("", xy=(0, D + 10), xytext=(W, D + 10), arrowprops=dict(arrowstyle="<->", lw=2, color="#333"))
    ax.text(W / 2, D + 18, "40 cm  (沿墙)", ha="center", fontsize=12, fontweight="bold")
    ax.annotate("", xy=(-12, 0), xytext=(-12, D), arrowprops=dict(arrowstyle="<->", lw=2, color="#333"))
    ax.text(-22, D / 2, "13 cm", rotation=90, va="center", ha="center", fontsize=12, fontweight="bold")

    ax.text(W / 2, -15, "↓ 门口 DOOR", ha="center", fontsize=11, color="#c33", fontweight="bold")
    ax.text(W / 2, D + 32, "↑ 靠墙 BACK / 信件", ha="center", fontsize=11, color="#555", fontweight="bold")

    sx0, sy0 = W + 16, 24
    ax.add_patch(
        Polygon(
            [(sx0, sy0), (sx0 + 26, sy0 + 4), (sx0 + 26, sy0 + 48), (sx0, sy0 + 44)],
            closed=True, fill=False, edgecolor="#666", lw=1.8,
        )
    )
    ax.text(sx0 + 32, sy0 + 24, "侧面\n信件端\n更高", fontsize=8, color="#666", va="center")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> None:
    draw(Path("output/previews/layout_row_four_sketch.png"))


if __name__ == "__main__":
    main()
