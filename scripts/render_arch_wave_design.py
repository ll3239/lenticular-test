#!/usr/bin/env python3
"""Clean front-elevation concept sheet for the arch-wave exterior."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

from entryway_styles import WAVE_PROFILES, wave_height


def main() -> None:
    out = Path("output/previews/arch_wave/arch_wave_design.png")
    fig, ax = plt.subplots(figsize=(12, 7), dpi=180)
    fig.patch.set_facecolor("#f7f3eb")
    ax.set_facecolor("#f7f3eb")
    ax.set_xlim(-18, 225)
    ax.set_ylim(-12, 175)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Organic Wave — larger asymmetric rims + fine vertical flutes",
        fontsize=15, fontweight="bold", pad=14,
    )

    body = FancyBboxPatch(
        (0, 0), 206.4, 152,
        boxstyle="round,pad=0,rounding_size=11",
        linewidth=2.3, edgecolor="#5e5448", facecolor="#d8c7ad", zorder=1,
    )
    ax.add_patch(body)

    x = np.linspace(12, 194.4, 400)
    t = (x - 12) / (194.4 - 12)
    front_wave = 32 + np.array([wave_height(float(v), WAVE_PROFILES["arch_wave"]["front"]) for v in t])
    back_wave = 150 + np.array([wave_height(float(v), WAVE_PROFILES["arch_wave"]["back"]) for v in t])
    ax.fill_between(x, 31.5, front_wave, color="#d8c7ad", zorder=2)
    ax.plot(x, front_wave, color="#5e5448", linewidth=2.3, zorder=4)
    ax.plot(x, back_wave, color="#84745f", linewidth=2.0, zorder=3)

    for xpos in np.arange(18, 195, 12):
        ax.plot([xpos, xpos], [9, 138], color="#9f8d74", linewidth=1.4, alpha=0.8, zorder=2)
        ax.plot([xpos + 1.2, xpos + 1.2], [9, 138], color="#e9ddca", linewidth=0.8, alpha=0.9, zorder=2)

    ax.plot([10, 196.4], [8, 8], color="#aa987f", linewidth=1.4, alpha=0.8)
    ax.annotate(
        "FRONT: 3 overlapping waves\npeak shifted — up to +11 mm",
        xy=(118, 44), xytext=(138, 68),
        ha="center", va="center", fontsize=10, fontweight="bold", color="#554b40",
        arrowprops=dict(arrowstyle="->", color="#776a59", lw=1.5),
    )
    ax.annotate(
        "BACK: 3 unequal waves\nlargest on the right (+9 mm)",
        xy=(158, 156), xytext=(188, 168),
        ha="left", va="center", fontsize=9, color="#554b40",
        arrowprops=dict(arrowstyle="->", color="#776a59", lw=1.4),
    )
    ax.annotate(
        "Fine vertical flutes\n1.6 mm wide / 1.2 mm relief",
        xy=(174, 78), xytext=(218, 92),
        ha="left", va="center", fontsize=9, color="#554b40",
        arrowprops=dict(arrowstyle="->", color="#776a59", lw=1.4),
    )
    ax.text(
        103.2, -8,
        "Exterior decoration only — internal compartments unchanged",
        ha="center", fontsize=10, color="#2d6d43", fontweight="bold",
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
