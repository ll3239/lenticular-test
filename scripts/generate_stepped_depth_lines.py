#!/usr/bin/env python3
"""
Cube faces made of dense STRAIGHT lines at stepped depths.

Shade = how far behind the surface the line sits, e.g.:
  light  → line near surface (0–1 mm behind)
  mid    → ~2 mm behind
  dark   → ~4 mm behind

Every slot gets a full straight line — even, dense packing. No empty middle.
No wavy "bumps" — only straight rectangular bars at discrete depths.
"""

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

FACE_NAMES = ["front", "back", "right", "left", "top", "bottom"]


def load_gray(path, size, contrast=1.9):
    img = Image.open(path).convert("L")
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    return np.asarray(img.resize((size, size), Image.LANCZOS), dtype=np.float64) / 255.0


def add_tri(verts, faces, a, b, c):
    i = len(verts)
    verts.extend([a, b, c])
    faces.append((i, i + 1, i + 2))


def add_quad(verts, faces, a, b, c, d):
    add_tri(verts, faces, a, b, c)
    add_tri(verts, faces, a, c, d)


def write_stl(path, verts, faces, header="Stepped depth line cube"):
    tris = []
    for i0, i1, i2 in faces:
        v0, v1, v2 = np.array(verts[i0]), np.array(verts[i1]), np.array(verts[i2])
        n = np.cross(v1 - v0, v2 - v0)
        nn = np.linalg.norm(n)
        n = n / nn if nn > 1e-9 else np.array([0.0, 0.0, 1.0])
        tris.append((n, v0, v1, v2))
    hdr = header.encode("ascii", "ignore")[:80].ljust(80, b"\0")
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(struct.pack("<I", len(tris)))
        for n, v0, v1, v2 in tris:
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))


def face_point(face, u, v, depth_from_surface, size):
    """
    depth_from_surface: 0 = on outer surface, positive = behind surface (into cube).
    """
    # Outer surface is at the cube face; going "behind" moves inward.
    if face == "front":   # +Y outer
        return (u, size - depth_from_surface, v)
    if face == "back":    # -Y outer
        return (size - u, depth_from_surface, v)
    if face == "right":   # +X outer
        return (size - depth_from_surface, size - u, v)
    if face == "left":    # -X outer
        return (depth_from_surface, u, v)
    if face == "top":     # +Z outer
        return (u, v, size - depth_from_surface)
    if face == "bottom":  # -Z outer
        return (u, size - v, depth_from_surface)
    raise ValueError(face)


def add_box(verts, faces, face, u0, u1, v0, v1, d0, d1, size):
    """Axis-aligned box in face UV + depth (straight rectangular line segment)."""
    # 8 corners: u/v × front/back depth
    p = [
        face_point(face, u0, v0, d0, size),
        face_point(face, u1, v0, d0, size),
        face_point(face, u1, v1, d0, size),
        face_point(face, u0, v1, d0, size),
        face_point(face, u0, v0, d1, size),
        face_point(face, u1, v0, d1, size),
        face_point(face, u1, v1, d1, size),
        face_point(face, u0, v1, d1, size),
    ]
    # Outer (toward surface, smaller depth), inner (deeper), sides
    add_quad(verts, faces, p[0], p[1], p[2], p[3])  # toward surface
    add_quad(verts, faces, p[5], p[4], p[7], p[6])  # deeper face
    add_quad(verts, faces, p[0], p[3], p[7], p[4])
    add_quad(verts, faces, p[1], p[5], p[6], p[2])
    add_quad(verts, faces, p[0], p[4], p[5], p[1])
    add_quad(verts, faces, p[3], p[2], p[6], p[7])


def quantize_depth(dark, depth_levels):
    """Map darkness 0..1 → discrete depth behind surface."""
    # light → shallow (near surface), dark → deep
    idx = int(np.clip(dark, 0, 0.999) * len(depth_levels))
    return depth_levels[idx]


def add_face_straight_depth_lines(
    verts,
    faces,
    face,
    gray,
    size,
    n_lines=50,
    depth_levels=None,
    line_thickness_ratio=0.72,
    segment_mm=2.0,
):
    """
    Dense even vertical slots. Each slot = straight line bars at stepped depths.
    """
    if depth_levels is None:
        # Example: surface, 2mm, 4mm, 6mm behind (as user described)
        depth_levels = [0.4, 2.0, 4.0, 6.0]

    rows, cols = gray.shape
    pitch = size / n_lines
    line_w = pitch * line_thickness_ratio
    # Bar thickness in depth direction (how "fat" the straight rod is)
    bar_depth = min(1.2, (depth_levels[1] - depth_levels[0]) * 0.55 if len(depth_levels) > 1 else 1.0)

    n_seg = max(8, int(round(size / segment_mm)))
    seg_h = size / n_seg

    for li in range(n_lines):
        u_c = (li + 0.5) * pitch
        u0 = u_c - line_w * 0.5
        u1 = u_c + line_w * 0.5
        col = min(int((li + 0.5) / n_lines * cols), cols - 1)
        c0, c1 = max(0, col - 1), min(cols, col + 2)

        # Merge consecutive segments with same quantized depth into longer straight bars
        segs = []
        for si in range(n_seg):
            v0 = si * seg_h
            v1 = (si + 1) * seg_h
            row = min(int((si + 0.5) / n_seg * rows), rows - 1)
            dark = 1.0 - float(np.mean(gray[row, c0:c1]))
            d = quantize_depth(dark, depth_levels)
            segs.append((v0, v1, d))

        merged = []
        cv0, cv1, cd = segs[0]
        for v0, v1, d in segs[1:]:
            if d == cd:
                cv1 = v1
            else:
                merged.append((cv0, cv1, cd))
                cv0, cv1, cd = v0, v1, d
        merged.append((cv0, cv1, cd))

        for v0, v1, d_front in merged:
            # Straight bar from d_front to d_front+bar_depth (into the cube)
            d0 = d_front
            d1 = d_front + bar_depth
            # Keep bar inside cube
            d1 = min(d1, size * 0.45)
            if d1 <= d0 + 0.15:
                d1 = d0 + 0.4
            add_box(verts, faces, face, u0, u1, v0, v1, d0, d1, size)


def add_face_backplane(verts, faces, face, size, plane_depth):
    """Solid back plane deep behind lines so the face isn't see-through empty."""
    # Thin plate at plane_depth covering whole face
    margin = 0.0
    t = 1.5  # thickness of backplane
    d0 = plane_depth
    d1 = min(plane_depth + t, size * 0.48)
    add_box(verts, faces, face, margin, size - margin, margin, size - margin, d0, d1, size)


def add_inner_core(verts, faces, size, core_inset):
    """Dense solid core so the middle of the cube is full plastic."""
    e = core_inset
    s = size - core_inset
    if s <= e:
        return
    c = [
        (e, e, e), (s, e, e), (s, s, e), (e, s, e),
        (e, e, s), (s, e, s), (s, s, s), (e, s, s),
    ]
    for q in [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (2, 6, 7, 3), (0, 3, 7, 4), (1, 5, 6, 2)]:
        add_quad(verts, faces, *(c[i] for i in q))


def preview_stepped(gray, depth_levels, n_lines, out_path):
    """Preview: darker = deeper shade (drawn as thicker/blacker straight lines)."""
    h, w = gray.shape
    # Visualize depth as grayscale bands of straight lines
    out = Image.new("RGB", (w, h), (240, 238, 232))
    draw = ImageDraw.Draw(out)
    pitch = w / n_lines
    line_w = pitch * 0.72
    n_seg = 24
    seg_h = h / n_seg
    # Map depth → ink darkness for preview
    dmin, dmax = min(depth_levels), max(depth_levels)

    for li in range(n_lines):
        u_c = (li + 0.5) * pitch
        col = min(int((li + 0.5) / n_lines * w), w - 1)
        for si in range(n_seg):
            v0 = int(si * seg_h)
            v1 = int((si + 1) * seg_h)
            row = min(int((si + 0.5) / n_seg * h), h - 1)
            dark = 1.0 - float(gray[row, col])
            d = quantize_depth(dark, depth_levels)
            # Deeper → darker ink in preview
            t = (d - dmin) / max(1e-6, (dmax - dmin))
            shade = int(30 + (1 - t) * 180)
            ink = (shade, shade, shade - 5 if shade > 5 else shade)
            x0 = int(u_c - line_w * 0.5)
            x1 = int(u_c + line_w * 0.5)
            draw.rectangle([x0, v0, x1, max(v0 + 1, v1 - 1)], fill=ink)

    out.save(out_path)


def build_cube(image_paths, size=50.0, n_lines=50, depth_levels=None, sample_res=120):
    if depth_levels is None:
        depth_levels = [0.5, 2.0, 4.0, 6.0]

    verts, faces = [], []
    # Core fills the middle; face lines live in the shell outside the core
    max_d = max(depth_levels) + 1.5
    core_inset = max_d + 0.5
    add_inner_core(verts, faces, size, core_inset)

    for i, face in enumerate(FACE_NAMES):
        if i >= len(image_paths):
            continue
        gray = load_gray(image_paths[i], sample_res)
        add_face_backplane(verts, faces, face, size, plane_depth=max(depth_levels) + 0.3)
        add_face_straight_depth_lines(
            verts, faces, face, gray, size,
            n_lines=n_lines,
            depth_levels=depth_levels,
            line_thickness_ratio=0.78,
            segment_mm=2.5,
        )

    return verts, faces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=float, default=50.0)
    parser.add_argument("--lines", type=int, default=50, help="Dense even lines per face")
    parser.add_argument(
        "--depths",
        type=float,
        nargs="+",
        default=[0.5, 2.0, 4.0, 6.0],
        help="Depth steps behind surface in mm (light→dark)",
    )
    parser.add_argument("--preview-dir", type=Path, default=None)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(args.images[:6]):
            g = load_gray(p, 512)
            preview_stepped(g, args.depths, args.lines, args.preview_dir / f"{i+1:02d}_stepped.png")
            print(f"  preview {i+1:02d}_stepped.png")

    verts, faces = build_cube(args.images[:6], args.size, args.lines, args.depths)
    write_stl(args.out, verts, faces)
    print(f"Wrote {args.out}")
    print(f"  {args.size}mm cube, {args.lines} dense straight lines/face")
    print(f"  depth steps behind surface: {args.depths} mm")
    print(f"  {len(faces)*2} triangles — shade = stepped line depth, not surface bumps")


if __name__ == "__main__":
    main()
