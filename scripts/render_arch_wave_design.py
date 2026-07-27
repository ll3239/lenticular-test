#!/usr/bin/env python3
"""Clean front-elevation concept sheet for the arch-wave exterior."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch


def main() -> None:
    out = Path("output/previews/arch_wave/arch_wave_design.png")
    fig, ax = plt.subplots(figsize=(12, 6), dpi=180)
    fig.patch.set_facecolor("#f7f3eb")
    ax.set_facecolor("#f7f3eb")
    ax.set_xlim(-18, 225)
    ax.set_ylim(-12, 112)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Arch Wave exterior — rounded, wavy top rim, fine vertical flutes",
        fontsize=15, fontweight="bold", pad=14,
    )

    body = FancyBboxPatch(
        (0, 0), 206.4, 88,
        boxstyle="round,pad=0,rounding_size=11",
        linewidth=2.3, edgecolor="#5e5448", facecolor="#d8c7ad", zorder=1,
    )
    ax.add_patch(body)

    # Three smooth arches are added only above the existing front rim.
    x = np.linspace(12, 194.4, 300)
    span = (194.4 - 12) / 3
    phase = ((x - 12) % span) / span
    wave = 88 + 4.5 * np.sin(np.pi * phase)
    ax.fill_between(x, 87.5, wave, color="#d8c7ad", zorder=2)
    ax.plot(x, wave, color="#5e5448", linewidth=2.3, zorder=3)

    # Exterior vertical flutes.
    for xpos in np.arange(18, 195, 12):
        ax.plot([xpos, xpos], [9, 78], color="#9f8d74", linewidth=1.4, alpha=0.8, zorder=2)
        ax.plot([xpos + 1.2, xpos + 1.2], [9, 78], color="#e9ddca", linewidth=0.8, alpha=0.9, zorder=2)

    ax.plot([10, 196.4], [8, 8], color="#aa987f", linewidth=1.4, alpha=0.8)
    ax.annotate(
        "3 soft round arches\nTOP RIM ONLY (+4.5 mm)",
        xy=(103.2, 92.4), xytext=(103.2, 106),
        ha="center", va="center", fontsize=10, fontweight="bold", color="#554b40",
        arrowprops=dict(arrowstyle="->", color="#776a59", lw=1.5),
    )
    ax.annotate(
        "Fine vertical flutes\n1.6 mm wide / 1.2 mm relief",
        xy=(174, 48), xytext=(218, 54),
        ha="left", va="center", fontsize=9, color="#554b40",
        arrowprops=dict(arrowstyle="->", color="#776a59", lw=1.4),
    )
    ax.annotate(
        "10 mm rounded corners",
        xy=(5, 5), xytext=(35, 13),
        ha="center", fontsize=9, color="#554b40",
        arrowprops=dict(arrowstyle="->", color="#776a59", lw=1.4),
    )
    ax.text(
        103.2, -8,
        "Exterior decoration only — all internal compartments remain unchanged",
        ha="center", fontsize=10, color="#2d6d43", fontweight="bold",
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
