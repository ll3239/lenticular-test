#!/usr/bin/env python3
"""2D top-down layout diagram (like the hand sketch)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).parent))
from generate_entryway_storage_box import LAYOUT_COMPACT, LAYOUT_MODULAR, Layout

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

LABELS = {
    "earphones_other": "耳机+其他",
    "essential_oils": "精油×6",
    "keys": "钥匙",
    "card_1": "卡",
    "card_2": "卡",
    "receipts": "收据",
    "power_bank_1": "充电宝",
    "power_bank_2": "充电宝",
    "data_cable": "数据线",
    "letters": "信件",
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
    fig, ax = plt.subplots(figsize=(8, 9), dpi=160)
    fig.patch.set_facecolor("#fafafa")
    ax.set_facecolor("#f0f0f0")
    ax.set_aspect("equal")
    ax.set_xlim(-5, layout.w_int + 5)
    ax.set_ylim(-5, layout.l_int + 5)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=14, pad=12)
    ax.set_xlabel("宽度 (mm)")
    ax.set_ylabel("长度 (mm) — 门口在上")

    # Outer tray
    tray = FancyBboxPatch(
        (0, 0), layout.w_int, layout.l_int,
        boxstyle="round,pad=0,rounding_size=8",
        linewidth=2, edgecolor="#333", facecolor="#e8e8e8", zorder=0,
    )
    ax.add_patch(tray)

    for c in layout.compartments():
        if c.name == "letters":
            continue
        h = c.y1 - c.y0
        w = c.x1 - c.x0
        patch = FancyBboxPatch(
            (c.x0, c.y0), w, h,
            boxstyle="round,pad=0,rounding_size=4",
            linewidth=1.2, edgecolor="#555",
            facecolor=COLORS.get(c.name, "#ddd"), zorder=1,
        )
        ax.add_patch(patch)
        ax.text(
            (c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2,
            LABELS.get(c.name, c.name),
            ha="center", va="center", fontsize=9, color="#333",
        )

    c = next(x for x in layout.compartments() if x.name == "letters")
    patch = FancyBboxPatch(
        (c.x0, c.y0), c.x1 - c.x0, c.y1 - c.y0,
        boxstyle="round,pad=0,rounding_size=4",
        linewidth=1.2, edgecolor="#555", facecolor=COLORS["letters"], zorder=1,
    )
    ax.add_patch(patch)
    ax.text((c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2, "信件", ha="center", va="center", fontsize=10)

    ax.annotate("", xy=(layout.w_int + 2, 0), xytext=(layout.w_int + 2, layout.l_int),
                arrowprops=dict(arrowstyle="<->", color="#888"))
    ax.text(layout.w_int + 8, layout.l_int / 2, f"{layout.l_int:.0f}mm", rotation=90, va="center", fontsize=8, color="#666")
    ax.annotate("", xy=(0, layout.l_int + 2), xytext=(layout.w_int, layout.l_int + 2),
                arrowprops=dict(arrowstyle="<->", color="#888"))
    ax.text(layout.w_int / 2, layout.l_int + 8, f"{layout.w_int:.0f} mm", ha="center", fontsize=8, color="#666")

    ax.text(4, 4, "← 门口", fontsize=9, color="#c44", fontweight="bold")
    ax.text(4, layout.l_int - 12, "靠墙 →", fontsize=9, color="#666")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("output/previews"))
    args = parser.parse_args()
    draw_layout(
        LAYOUT_MODULAR,
        f"长方形分块布局 · 内尺寸 {LAYOUT_MODULAR.w_int:.0f}×{LAYOUT_MODULAR.l_int:.0f} mm",
        args.out_dir / "layout_modular_top.png",
    )
    draw_layout(
        LAYOUT_COMPACT,
        f"旧版紧凑布局 · 内尺寸 {LAYOUT_COMPACT.w_int:.0f}×{LAYOUT_COMPACT.l_int:.0f} mm",
        args.out_dir / "layout_compact_top.png",
    )


if __name__ == "__main__":
    main()
