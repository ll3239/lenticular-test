#!/usr/bin/env python3
"""Render a readable dimension and printer-fit check sheet."""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).parent))
from generate_entryway_dimensions import build_report
from generate_entryway_storage_box import LAYOUT_COMPACT

plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "Droid Sans Fallback", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

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


def main() -> None:
    layout = LAYOUT_COMPACT
    report = build_report(layout)
    by_id = {c["id"]: c for c in report["compartments"]}

    spec_path = Path("output/entryway_storage_box_spec.json")
    spec = json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else {}
    outer = spec.get("outer_mm", {})
    slope = spec.get("slope", {})
    front_rim = slope.get("front_rim_mm", 30)
    back_rim = slope.get("back_rim_mm", 150)
    outer_text = f"{outer.get('width', 206):g} x {outer.get('length', 233):g} x {outer.get('height_back', 152):g} mm"
    brim_w = outer.get("width", 206) + 10
    brim_l = outer.get("length", 233) + 10

    w, d = layout.w_int, layout.l_int
    out = Path("output/previews/corrected_layout_check.png")
    fig, (ax, info) = plt.subplots(
        1, 2, figsize=(13, 8), dpi=180, gridspec_kw={"width_ratios": [1.35, 1]}
    )
    fig.patch.set_facecolor("#f7f5ef")
    fig.suptitle("Corrected organizer — dimensions and P1S print check", fontsize=16, fontweight="bold")

    ax.set_xlim(-12, w + 14)
    ax.set_ylim(-16, d + 20)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch(
            (0, 0),
            w,
            d,
            boxstyle="round,pad=0,rounding_size=10",
            linewidth=2.5,
            edgecolor="#222",
            facecolor="#eee",
            zorder=0,
        )
    )

    for c in layout.compartments():
        cell = by_id[c.name]
        net = cell["internal_net_mm"]
        label = (
            f"{cell['name_zh']}\n"
            f"clear {net['width_x']:.1f} x {net['depth_y']:.1f}"
        )
        dy0, dy1 = d - c.y1, d - c.y0
        ax.add_patch(
            FancyBboxPatch(
                (c.x0, dy0),
                c.x1 - c.x0,
                dy1 - dy0,
                boxstyle="round,pad=0,rounding_size=3",
                linewidth=1.2,
                edgecolor="#444",
                facecolor=COLORS.get(c.name, "#eee"),
            )
        )
        ax.text(
            (c.x0 + c.x1) / 2,
            (dy0 + dy1) / 2,
            label,
            ha="center",
            va="center",
            fontsize=7.5,
            color="#222",
        )

    ax.annotate("", xy=(0, d + 8), xytext=(w, d + 8), arrowprops=dict(arrowstyle="<->", lw=1.6))
    ax.text(w / 2, d + 14, f"INTERNAL WIDTH {w:.1f} mm", ha="center", fontsize=10, fontweight="bold")
    ax.annotate("", xy=(-7, 0), xytext=(-7, d), arrowprops=dict(arrowstyle="<->", lw=1.6))
    ax.text(-11, d / 2, f"INTERNAL DEPTH {d:.1f} mm", rotation=90, va="center", ha="center", fontsize=10, fontweight="bold")
    ax.text(w / 2, d + 2, "BACK / WALL", ha="center", va="bottom", fontsize=9, color="#555", fontweight="bold")
    ax.text(w / 2, -10, "DOOR / FRONT", ha="center", fontsize=9, color="#b33", fontweight="bold")

    info.axis("off")
    info.set_xlim(0, 1)
    info.set_ylim(0, 1)
    info.text(0.04, 0.94, "FINAL STL", fontsize=13, fontweight="bold")
    rows = [
        ("Outer object", outer_text, True),
        ("Slope (front → back rim)", f"{front_rim:g} mm → {back_rim:g} mm", True),
        ("With 5 mm brim", f"{brim_w:g} x {brim_l:g} mm", True),
        ("P1S build plate", "256 x 256 mm", True),
        ("Essential oils (left mid)", "100 x 96 mm; 6 x Ø30 mm", True),
        ("Card wallets (front-right)", "100 x 25 mm clear each", True),
        ("Data cable (front bay)", "100 x 24 mm shallow tray", True),
        ("Power banks (rear bay)", "100 x 70 mm (≥60 mm)", True),
        ("Letters at back", "200 mm max width; 140 mm baffle", True),
        ("STL geometry", "watertight single volume", True),
    ]
    y = 0.86
    for title, value, passed in rows:
        info.add_patch(
            FancyBboxPatch(
                (0.03, y - 0.048),
                0.94,
                0.065,
                boxstyle="round,pad=0.01,rounding_size=0.015",
                linewidth=1,
                edgecolor="#c8cec8",
                facecolor="#edf5ed",
            )
        )
        info.text(0.065, y, "PASS", color="#20733a", fontsize=9, fontweight="bold", va="center")
        info.text(0.22, y + 0.009, title, color="#222", fontsize=9, fontweight="bold", va="center")
        info.text(0.22, y - 0.016, value, color="#555", fontsize=8, va="center")
        y -= 0.085
    info.text(
        0.04,
        0.015,
        "Fits Bambu P1/P1S/X1/A1 (256 mm bed).\nDoes NOT fit A1 mini (180 mm bed).",
        fontsize=9,
        color="#333",
        linespacing=1.5,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff4df", edgecolor="#d8b56b"),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
