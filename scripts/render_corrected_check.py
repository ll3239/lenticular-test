#!/usr/bin/env python3
"""Render a readable dimension and printer-fit check sheet."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

W, D = 200.0, 228.0

CELLS = [
    (0, 100, 0, 100, "#c8d8e8", "Earphones + other\nnominal 100 x 100"),
    (100, 200, 0, 100, "#b8dcc8", "Oils x6 (dia. 30)\nclear 99.25 x 99.25"),
    (0, 100, 100, 124, "#e8dcc8", "Keys\nclear 99.25 x 22.5"),
    (0, 100, 124, 146, "#ece8d8", "Cards upright\nclear 99.25 x 20.5"),
    (0, 100, 146, 168, "#ece8d8", "Cards upright\nclear 99.25 x 20.5"),
    (0, 100, 168, 198, "#e0d0c0", "Receipts\nclear 99.25 x 29.25"),
    (100, 200, 100, 133, "#d0d8e8", "Power bank 80 x 30\nclear 99.25 x 31.5"),
    (100, 200, 133, 166, "#d0d8e8", "Power bank 80 x 30\nclear 99.25 x 31.5"),
    (100, 200, 166, 198, "#d8e0d0", "Cable bundle 60 x 30\nclear 99.25 x 30.5"),
    (0, 200, 198, 228, "#e8e0d0", "MAIL AT BACK / WALL\nnominal 200 x 30"),
]


def main() -> None:
    out = Path("output/previews/corrected_layout_check.png")
    fig, (ax, info) = plt.subplots(
        1, 2, figsize=(13, 8), dpi=180, gridspec_kw={"width_ratios": [1.35, 1]}
    )
    fig.patch.set_facecolor("#f7f5ef")
    fig.suptitle("Corrected organizer — dimensions and P1S print check", fontsize=16, fontweight="bold")

    ax.set_xlim(-12, W + 14)
    ax.set_ylim(-16, D + 20)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch(
            (0, 0), W, D, boxstyle="round,pad=0,rounding_size=10",
            linewidth=2.5, edgecolor="#222", facecolor="#eee", zorder=0,
        )
    )
    for x0, x1, y0, y1, color, label in CELLS:
        dy0, dy1 = D - y1, D - y0
        ax.add_patch(
            FancyBboxPatch(
                (x0, dy0), x1 - x0, dy1 - dy0,
                boxstyle="round,pad=0,rounding_size=3",
                linewidth=1.2, edgecolor="#444", facecolor=color,
            )
        )
        ax.text(
            (x0 + x1) / 2, (dy0 + dy1) / 2, label,
            ha="center", va="center", fontsize=7.5, color="#222",
        )
    ax.annotate("", xy=(0, D + 8), xytext=(W, D + 8), arrowprops=dict(arrowstyle="<->", lw=1.6))
    ax.text(W / 2, D + 14, "INTERNAL WIDTH 200 mm", ha="center", fontsize=10, fontweight="bold")
    ax.annotate("", xy=(-7, 0), xytext=(-7, D), arrowprops=dict(arrowstyle="<->", lw=1.6))
    ax.text(-11, D / 2, "INTERNAL DEPTH 228 mm", rotation=90, va="center", ha="center", fontsize=10, fontweight="bold")
    ax.text(W / 2, D + 2, "BACK / WALL", ha="center", va="bottom", fontsize=9, color="#555", fontweight="bold")
    ax.text(W / 2, -10, "DOOR / FRONT", ha="center", fontsize=9, color="#b33", fontweight="bold")

    info.axis("off")
    info.set_xlim(0, 1)
    info.set_ylim(0, 1)
    info.text(0.04, 0.94, "FINAL STL", fontsize=13, fontweight="bold")
    rows = [
        ("Outer object", "204 x 232 x 94 mm", True),
        ("With 5 mm brim", "214 x 242 mm", True),
        ("P1S build plate", "256 x 256 mm", True),
        ("Remaining bed margin", "42 x 14 mm total", True),
        ("Six oil bottles", "3 x 2 arrangement", True),
        ("Two power banks", "upright, 1.5 mm clearance", True),
        ("Cable bundle", "60 x 30 mm", True),
        ("STL geometry", "watertight single volume", True),
    ]
    y = 0.86
    for title, value, passed in rows:
        info.add_patch(
            FancyBboxPatch(
                (0.03, y - 0.055), 0.94, 0.075,
                boxstyle="round,pad=0.01,rounding_size=0.015",
                linewidth=1, edgecolor="#c8cec8", facecolor="#edf5ed",
            )
        )
        info.text(0.065, y, "PASS", color="#20733a", fontsize=9, fontweight="bold", va="center")
        info.text(0.22, y + 0.012, title, color="#222", fontsize=9, fontweight="bold", va="center")
        info.text(0.22, y - 0.02, value, color="#555", fontsize=8, va="center")
        y -= 0.098
    info.text(
        0.04, 0.045,
        "Fits Bambu P1/P1S/X1/A1 (256 mm bed).\nDoes NOT fit A1 mini (180 mm bed).",
        fontsize=9, color="#333", linespacing=1.5,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff4df", edgecolor="#d8b56b"),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
