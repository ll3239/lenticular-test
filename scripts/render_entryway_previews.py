#!/usr/bin/env python3
"""Render PNG previews of entryway box STL variants."""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

plt.rcParams["font.sans-serif"] = [
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "WenQuanYi Micro Hei",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


STYLES = [
    ("minimal", "极简直角", "#c8cdd8"),
    ("rounded", "圆角柔和", "#d4c4b0"),
    ("arch_wave", "不规则波浪细条纹", "#d7c6ae"),
    ("chamfer", "倒角线框", "#b8c8d8"),
    ("tiered", "阶梯分层", "#c0b8a8"),
    ("wells", "精油定位环", "#b8d0c0"),
    ("accent", "双槽装饰", "#c8b8d8"),
]


def load_stl(path: Path) -> trimesh.Trimesh:
    return trimesh.load(path, force="mesh")


def setup_ax(ax, elev: float, azim: float, title: str = "") -> None:
    ax.set_proj_type("persp")
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("X (mm)", fontsize=8, labelpad=-2)
    ax.set_ylabel("Y (mm)", fontsize=8, labelpad=-2)
    ax.set_zlabel("Z", fontsize=8, labelpad=-2)
    ax.tick_params(labelsize=7)
    if title:
        ax.set_title(title, fontsize=11, pad=8, fontweight="600")
    ax.set_box_aspect([204, 214, 90])


def draw_mesh(ax, mesh: trimesh.Trimesh, color: str, alpha: float = 0.92) -> None:
    verts = mesh.vertices
    faces = mesh.faces
    polys = [verts[f] for f in faces]
    coll = Poly3DCollection(polys, alpha=alpha, linewidths=0.03, edgecolors=(0, 0, 0, 0.08))
    coll.set_facecolor(color)
    ax.add_collection3d(coll)
    mn, mx = verts.min(axis=0), verts.max(axis=0)
    pad = 8
    ax.set_xlim(mn[0] - pad, mx[0] + pad)
    ax.set_ylim(mn[1] - pad, mx[1] + pad)
    ax.set_zlim(mn[2] - pad, mx[2] + pad)
    ax.set_facecolor("#1a1d24")
    ax.xaxis.pane.fill = ax.yaxis.pane.fill = ax.zaxis.pane.fill = False
    ax.grid(True, color="#333", alpha=0.35)


def render_single_views(mesh: trimesh.Trimesh, out_dir: Path, name: str, label_zh: str, color: str) -> None:
    views = [
        ("iso", 28, -55, "3/4 视角"),
        ("top", 90, -90, "俯视图"),
        ("side", 8, 0, "侧面（坡度）"),
        ("front", 8, 90, "正面（门口）"),
    ]
    for key, elev, azim, subtitle in views:
        fig = plt.figure(figsize=(7, 5.5), dpi=140)
        fig.patch.set_facecolor("#12141a")
        ax = fig.add_subplot(111, projection="3d")
        draw_mesh(ax, mesh, color)
        setup_ax(ax, elev, azim, f"{label_zh} · {subtitle}")
        fig.tight_layout()
        path = out_dir / f"{name}_{key}.png"
        fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        print(f"  {path}")


def render_comparison_grid(stl_dir: Path, out_path: Path) -> None:
    cols = 3
    rows = math.ceil(len(STYLES) / cols)
    fig = plt.figure(figsize=(14, 4.5 * rows), dpi=150)
    fig.patch.set_facecolor("#12141a")
    fig.suptitle(f"门口收纳盒 · {len(STYLES)} 款外观对比", fontsize=16, color="#e8eaef", y=0.98, fontweight="bold")

    for i, (sid, label_zh, color) in enumerate(STYLES):
        stl = stl_dir / f"entryway_box_{sid}.stl"
        mesh = load_stl(stl)
        ax = fig.add_subplot(rows, cols, i + 1, projection="3d")
        draw_mesh(ax, mesh, color)
        setup_ax(ax, 26, -52, f"{label_zh}\n({sid})")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_zlabel("")

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def render_topdown_grid(stl_dir: Path, out_path: Path) -> None:
    cols = 3
    rows = math.ceil(len(STYLES) / cols)
    fig = plt.figure(figsize=(14, 4 * rows), dpi=150)
    fig.patch.set_facecolor("#12141a")
    fig.suptitle("俯视图对比 · 分格布局相同", fontsize=15, color="#e8eaef", y=0.98)

    for i, (sid, label_zh, color) in enumerate(STYLES):
        mesh = load_stl(stl_dir / f"entryway_box_{sid}.stl")
        ax = fig.add_subplot(rows, cols, i + 1, projection="3d")
        draw_mesh(ax, mesh, color)
        setup_ax(ax, 90, -90, label_zh)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def render_side_slope(stl_dir: Path, out_path: Path) -> None:
    """Side profile comparison — shows letters end higher."""
    cols = 3
    rows = math.ceil(len(STYLES) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(14, 3.5 * rows), dpi=150)
    fig.patch.set_facecolor("#12141a")
    fig.suptitle("侧面坡度对比 · 信件端（右）最高", fontsize=15, color="#e8eaef")

    for ax_flat, (sid, label_zh, color) in zip(axes.flat, STYLES):
        mesh = load_stl(stl_dir / f"entryway_box_{sid}.stl")
        # Y-Z projection (side view from +X)
        verts = mesh.vertices
        faces = mesh.faces
        polys2d = [verts[f][:, [1, 2]] for f in faces]
        coll = PolyCollection(polys2d, facecolors=color, edgecolors=(0, 0, 0, 0.15), linewidths=0.2, alpha=0.95)
        ax_flat.add_collection(coll)
        mn, mx = verts.min(axis=0), verts.max(axis=0)
        ax_flat.set_xlim(mn[1] - 5, mx[1] + 5)
        ax_flat.set_ylim(mn[2] - 5, mx[2] + 5)
        ax_flat.set_aspect("equal")
        ax_flat.set_title(label_zh, fontsize=11, color="#e8eaef")
        ax_flat.set_xlabel("长度 Y (mm)", fontsize=8, color="#888")
        ax_flat.set_ylabel("高度 Z (mm)", fontsize=8, color="#888")
        ax_flat.set_facecolor("#1a1d24")
        ax_flat.tick_params(colors="#666", labelsize=7)
        for sp in ax_flat.spines.values():
            sp.set_color("#333")
    for ax_flat in axes.flat[len(STYLES):]:
        ax_flat.axis("off")

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stl-dir", type=Path, default=Path("output/styles"))
    parser.add_argument("--out-dir", type=Path, default=Path("output/previews"))
    parser.add_argument("--all-angles", action="store_true", help="Per-style iso/top/side/front PNGs")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    render_comparison_grid(args.stl_dir, args.out_dir / "compare_all_iso.png")
    render_topdown_grid(args.stl_dir, args.out_dir / "compare_all_top.png")
    render_side_slope(args.stl_dir, args.out_dir / "compare_all_side.png")

    if args.all_angles:
        for sid, label_zh, color in STYLES:
            mesh = load_stl(args.stl_dir / f"entryway_box_{sid}.stl")
            sub = args.out_dir / sid
            sub.mkdir(exist_ok=True)
            print(f"[{sid}]")
            render_single_views(mesh, sub, sid, label_zh, color)


if __name__ == "__main__":
    main()
