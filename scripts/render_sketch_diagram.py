#!/usr/bin/env python3
"""
Draw the layout exactly like the user's hand sketch (top view).

- Internal 200 x 210 mm (20 x 21 cm), each cell keeps original sizes
- TOP of image = back / wall / 信件
- BOTTOM = door / 门口
- WIDTH = 20 cm (horizontal on page)
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

sys.path.insert(0, str(Path(__file__).parent))
from generate_entryway_storage_box import LAYOUT_COMPACT

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# User-confirmed layout (internal mm). y=0 is FRONT/door, y=210 is BACK/letters.
# But we DRAW with wall at TOP of image (y inverted for display).
CELLS = [
    # (x0,x1, y0,y1, color, label) — y from front(0) to back(210)
    (0, 100, 0, 100, "#c8d8e8", "耳机+其他"),
    (100, 200, 0, 100, "#b8dcc8", "精油×6"),
    (0, 100, 100, 120, "#e8dcc8", "钥匙"),
    (0, 100, 120, 140, "#ece8d8", "卡"),
    (0, 100, 140, 160, "#ece8d8", "卡"),
    (0, 100, 160, 180, "#e0d0c0", "收据"),
    (100, 200, 100, 130, "#d0d8e8", "充电宝↑"),
    (100, 200, 130, 160, "#d0d8e8", "充电宝↑"),
    (100, 200, 160, 180, "#d8e0d0", "数据线"),
    (0, 200, 180, 210, "#e8e0d0", "信件"),
]


def draw_top_sketch(out: Path) -> None:
    w, h = 200.0, 210.0
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=180)
    fig.patch.set_facecolor("#fffef8")

    # Paper / notebook feel
    ax.set_facecolor("#fffef8")
    ax.set_xlim(-15, w + 30)
    ax.set_ylim(-20, h + 35)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Hand sketch layout (top view)  俯视图 · 按你的原图", fontsize=14, fontweight="bold", pad=12)

    # Outer tray — horizontal rectangle 20 x 21 cm
    tray = FancyBboxPatch(
        (0, 0), w, h,
        boxstyle="round,pad=0,rounding_size=6",
        linewidth=2.5, edgecolor="#222", facecolor="#f5f5f0", zorder=0,
    )
    ax.add_patch(tray)

    for x0, x1, y0, y1, color, label in CELLS:
        # flip y for display: wall/back (letters) at TOP
        dy0, dy1 = h - y1, h - y0
        patch = FancyBboxPatch(
            (x0, dy0), x1 - x0, dy1 - dy0,
            boxstyle="round,pad=0,rounding_size=3",
            linewidth=1.5, edgecolor="#333", facecolor=color, zorder=1,
        )
        ax.add_patch(patch)
        ax.text((x0 + x1) / 2, (dy0 + dy1) / 2, label, ha="center", va="center", fontsize=9, color="#222")

    # Dimension lines like pencil sketch
    ax.annotate("", xy=(0, h + 8), xytext=(w, h + 8), arrowprops=dict(arrowstyle="<->", lw=1.8, color="#333"))
    ax.text(w / 2, h + 16, "20 cm", ha="center", fontsize=12, fontweight="bold")
    ax.annotate("", xy=(-8, 0), xytext=(-8, h), arrowprops=dict(arrowstyle="<->", lw=1.8, color="#333"))
    ax.text(-18, h / 2, "21 cm", rotation=90, va="center", ha="center", fontsize=12, fontweight="bold")

    ax.text(w / 2, -12, "↓ 门口 DOOR", ha="center", fontsize=11, color="#c33", fontweight="bold")
    ax.text(w / 2, h + 28, "↑ 靠墙 BACK / 信件", ha="center", fontsize=11, color="#555", fontweight="bold")

    # Side slope hint (small trapezoid — letters end higher)
    sx0, sy0 = w + 18, 20
    trap = Polygon(
        [(sx0, sy0), (sx0 + 28, sy0 + 5), (sx0 + 28, sy0 + 55), (sx0, sy0 + 50)],
        closed=True, fill=False, edgecolor="#666", lw=1.8,
    )
    ax.add_patch(trap)
    ax.text(sx0 + 34, sy0 + 28, "侧面\n信件端\n更高", fontsize=8, color="#666", va="center")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> None:
    draw_top_sketch(Path("output/previews/layout_from_sketch.png"))


if __name__ == "__main__":
    main()
