#!/usr/bin/env python3
"""2D top-down layout diagram (like the hand sketch)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).parent))
from generate_entryway_storage_box import LAYOUT_COMPACT, LAYOUT_MODULAR, Layout

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

LABELS = {
    "earphones_other": "Earphones\n耳机+其他",
    "essential_oils": "Oils x6\n精油",
    "keys": "Keys\n钥匙",
    "card_1": "Card\n卡",
    "card_2": "Card\n卡",
    "receipts": "Receipts\n收据",
    "power_bank_1": "PB\n充电宝",
    "power_bank_2": "PB\n充电宝",
    "data_cable": "Cable\n数据线",
    "letters": "Mail\n信件",
}


COLORS = {
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


def draw_layout(layout: Layout, title: str, out: Path) -> None:
    # Wide figure so the tray reads as 横长方形 on screen (width > depth)
    fig_w = max(10.0, layout.w_int / 22.0)
    fig_h = max(4.5, layout.l_int / 28.0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=160)
    fig.patch.set_facecolor("#fafafa")
    ax.set_facecolor("#f0f0f0")
    ax.set_aspect("equal")
    ax.set_xlim(-8, layout.w_int + 18)
    ax.set_ylim(-8, layout.l_int + 18)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=13, pad=10, fontweight="bold")
    ax.set_xlabel(f"Width along wall / 沿墙宽度 (mm)  →  {layout.w_int:.0f}", fontsize=10)
    ax.set_ylabel(f"Depth from door / 进深 (mm)  ↓  {layout.l_int:.0f}", fontsize=10)

    tray = FancyBboxPatch(
        (0, 0),
        layout.w_int,
        layout.l_int,
        boxstyle="round,pad=0,rounding_size=8",
        linewidth=2.2,
        edgecolor="#333",
        facecolor="#e8e8e8",
        zorder=0,
    )
    ax.add_patch(tray)

    for c in layout.compartments():
        w, h = c.x1 - c.x0, c.y1 - c.y0
        patch = FancyBboxPatch(
            (c.x0, c.y0),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=4",
            linewidth=1.2,
            edgecolor="#555",
            facecolor=COLORS.get(c.name, "#ddd"),
            zorder=1,
        )
        ax.add_patch(patch)
        ax.text(
            (c.x0 + c.x1) / 2,
            (c.y0 + c.y1) / 2,
            LABELS.get(c.name, c.name),
            ha="center",
            va="center",
            fontsize=8,
            color="#333",
            linespacing=1.15,
        )

    # Gutter hints (dashed)
    gx0 = layout.x_left1
    gx1 = layout.x_right0
    for gy0, gy1 in (
        (layout.y_front1, layout.y_mid0),
        (layout.y_mid1, layout.y_letters0),
    ):
        ax.add_patch(
            FancyBboxPatch(
                (gx0, gy0),
                gx1 - gx0,
                gy1 - gy0,
                linewidth=0,
                facecolor="#d8d8d8",
                alpha=0.55,
                zorder=0.5,
            )
        )

    ax.annotate(
        "",
        xy=(0, layout.l_int + 4),
        xytext=(layout.w_int, layout.l_int + 4),
        arrowprops=dict(arrowstyle="<->", color="#444", lw=1.5),
    )
    ax.text(
        layout.w_int / 2,
        layout.l_int + 10,
        f"W {layout.w_int:.0f} mm",
        ha="center",
        fontsize=10,
        color="#222",
        fontweight="bold",
    )

    ax.annotate(
        "",
        xy=(layout.w_int + 4, 0),
        xytext=(layout.w_int + 4, layout.l_int),
        arrowprops=dict(arrowstyle="<->", color="#444", lw=1.5),
    )
    ax.text(
        layout.w_int + 12,
        layout.l_int / 2,
        f"D {layout.l_int:.0f}",
        rotation=90,
        va="center",
        fontsize=10,
        color="#222",
        fontweight="bold",
    )

    ax.text(6, 6, "DOOR / 门口", fontsize=9, color="#c44", fontweight="bold")
    ax.text(6, layout.l_int - 14, "WALL / 靠墙", fontsize=9, color="#666")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}  ({layout.w_int:.0f} x {layout.l_int:.0f} mm, W>D: {layout.w_int > layout.l_int})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("output/previews"))
    args = parser.parse_args()
    draw_layout(
        LAYOUT_MODULAR,
        f"Landscape tray  宽 {LAYOUT_MODULAR.w_int:.0f} mm  ×  深 {LAYOUT_MODULAR.l_int:.0f} mm",
        args.out_dir / "layout_modular_top.png",
    )
    draw_layout(
        LAYOUT_COMPACT,
        f"Compact (old)  {LAYOUT_COMPACT.w_int:.0f} x {LAYOUT_COMPACT.l_int:.0f} mm",
        args.out_dir / "layout_compact_top.png",
    )


if __name__ == "__main__":
    main()
