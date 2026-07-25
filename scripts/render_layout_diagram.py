#!/usr/bin/env python3
"""2D top-down layout diagrams for all rectangular layout presets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).parent))
from entryway_layouts import LAYOUT_PRESETS, LayoutPreset
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


def _draw_gutters(ax, layout: Layout) -> None:
    if layout.gutter <= 0:
        return
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
                facecolor="#d0d0d0",
                alpha=0.65,
                zorder=0.5,
            )
        )
    if layout.margin_x > 0 or layout.margin_y > 0:
        ax.add_patch(
            FancyBboxPatch(
                (0, 0),
                layout.w_int,
                layout.l_int,
                boxstyle="round,pad=0,rounding_size=6",
                linewidth=0,
                facecolor="none",
                edgecolor="#999",
                linestyle="--",
                zorder=0.2,
            )
        )


def draw_preset(
    preset: LayoutPreset,
    *,
    out: Path,
    ax=None,
    show_dims: bool = True,
) -> None:
    w_int, l_int = preset.w_int, preset.l_int
    compartments = preset.compartments
    layout = preset.layout

    standalone = ax is None
    if standalone:
        fig_w = max(9.0, w_int / 24.0)
        fig_h = max(4.2, l_int / 30.0)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=160)
        fig.patch.set_facecolor("#fafafa")
    ax.set_facecolor("#f0f0f0")
    ax.set_aspect("equal")
    ax.set_xlim(-6, w_int + 14)
    ax.set_ylim(-6, l_int + 14)
    ax.invert_yaxis()
    title = f"{preset.name_zh}  {preset.name_en}\n{preset.tagline}"
    ax.set_title(title, fontsize=10 if not standalone else 12, pad=6, fontweight="bold")

    tray = FancyBboxPatch(
        (0, 0),
        w_int,
        l_int,
        boxstyle="round,pad=0,rounding_size=8",
        linewidth=2.0,
        edgecolor="#333",
        facecolor="#e8e8e8",
        zorder=0,
    )
    ax.add_patch(tray)

    if layout is not None:
        _draw_gutters(ax, layout)

    for c in compartments:
        w, h = c.x1 - c.x0, c.y1 - c.y0
        rounding = 5 if c.name == "letters" and preset.id == "mail_spine" else 4
        patch = FancyBboxPatch(
            (c.x0, c.y0),
            w,
            h,
            boxstyle=f"round,pad=0,rounding_size={rounding}",
            linewidth=1.2,
            edgecolor="#555",
            facecolor=COLORS.get(c.name, "#ddd"),
            zorder=1,
        )
        ax.add_patch(patch)
        fs = 7 if w < 35 or h < 35 else 8
        ax.text(
            (c.x0 + c.x1) / 2,
            (c.y0 + c.y1) / 2,
            LABELS.get(c.name, c.name),
            ha="center",
            va="center",
            fontsize=fs,
            color="#333",
            linespacing=1.1,
        )

    if show_dims:
        ax.text(
            w_int / 2,
            l_int + 8,
            f"W {w_int:.0f} mm",
            ha="center",
            fontsize=9,
            color="#222",
            fontweight="bold",
        )
        ax.text(
            w_int + 8,
            l_int / 2,
            f"D {l_int:.0f}",
            rotation=90,
            va="center",
            fontsize=9,
            color="#222",
            fontweight="bold",
        )

    ax.text(4, 4, "DOOR", fontsize=8, color="#c44", fontweight="bold")
    ax.text(4, l_int - 10, "WALL", fontsize=8, color="#666")
    ax.set_xticks([])
    ax.set_yticks([])

    if standalone:
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {out}  ({w_int:.0f} x {l_int:.0f} mm)")


def draw_comparison(out: Path) -> None:
    presets = [LAYOUT_PRESETS["row_four"], *[p for p in LAYOUT_PRESETS.values() if p.id != "row_four"]]
    fig, axes = plt.subplots(2, 3, figsize=(18, 11), dpi=150)
    fig.patch.set_facecolor("#fafafa")
    fig.suptitle(
        "Layout variants — same cell sizes, different rectangular shapes\n"
        "格子尺寸相同 · 五种横长方形造型",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )
    for ax, preset in zip(axes.flat, presets):
        draw_preset(preset, out=out, ax=ax, show_dims=True)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(
        0.5,
        0.55,
        "Each cell keeps sketch sizes:\n"
        "100×100 · 100×80 · 100×30 …\n\n"
        "Pick one layout → we export STL\n"
        "with matching 3D style.",
        ha="center",
        va="center",
        fontsize=11,
        color="#444",
        transform=axes.flat[-1].transAxes,
        bbox=dict(boxstyle="round,pad=0.8", facecolor="#fff", edgecolor="#ccc"),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("output/layouts"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for preset in LAYOUT_PRESETS.values():
        draw_preset(
            preset,
            out=args.out_dir / f"entryway_{preset.id}_top.png",
        )

    draw_comparison(args.out_dir / "compare_all_layouts.png")

    # Legacy filenames for older links
    previews = Path("output/previews")
    previews.mkdir(parents=True, exist_ok=True)
    draw_preset(LAYOUT_PRESETS["classic"], out=previews / "layout_compact_top.png")
    draw_preset(
        LayoutPreset(
            id="modular",
            name_zh="横长分块",
            name_en="Modular",
            tagline=f"{LAYOUT_MODULAR.w_int:.0f}×{LAYOUT_MODULAR.l_int:.0f} mm",
            style="rounded",
            layout=LAYOUT_MODULAR,
        ),
        out=previews / "layout_modular_top.png",
    )


if __name__ == "__main__":
    main()
