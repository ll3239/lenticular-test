#!/usr/bin/env python3
"""
Cube faces = dense straight lines whose DEPTH follows the image continuously.

For a cube of size S (e.g. 10mm or 50mm):
  - Each face's lines go from near the surface all the way inward
    toward the center (almost S/2 — the full usable depth of that half).
  - Depth is continuous from the photo (e.g. 1.5mm, 3.7mm…), not fixed 2/4 buckets.
  - Darker → deeper into the cube; lighter → closer to the surface.
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


def write_stl(path, verts, faces, header="Continuous depth line cube"):
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
    """depth_from_surface: 0 = outer surface, positive = into cube toward opposite face."""
    if face == "front":
        return (u, size - depth_from_surface, v)
    if face == "back":
        return (size - u, depth_from_surface, v)
    if face == "right":
        return (size - depth_from_surface, size - u, v)
    if face == "left":
        return (depth_from_surface, u, v)
    if face == "top":
        return (u, v, size - depth_from_surface)
    if face == "bottom":
        return (u, size - v, depth_from_surface)
    raise ValueError(face)


def add_box(verts, faces, face, u0, u1, v0, v1, d0, d1, size):
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
    add_quad(verts, faces, p[0], p[1], p[2], p[3])
    add_quad(verts, faces, p[5], p[4], p[7], p[6])
    add_quad(verts, faces, p[0], p[3], p[7], p[4])
    add_quad(verts, faces, p[1], p[5], p[6], p[2])
    add_quad(verts, faces, p[0], p[4], p[5], p[1])
    add_quad(verts, faces, p[3], p[2], p[6], p[7])


def depth_from_image(dark, d_min, d_max):
    """Continuous depth — any value in [d_min, d_max], e.g. 1.5, 3.7 mm."""
    return d_min + float(np.clip(dark, 0.0, 1.0)) * (d_max - d_min)


def add_face_continuous_depth_lines(
    verts,
    faces,
    face,
    gray,
    size,
    n_lines,
    d_min,
    d_max,
    line_thickness_ratio=0.82,
    segment_mm=1.5,
    bar_thickness=None,
):
    """
    Dense straight vertical lines. Each segment sits at a continuous depth
    based on local image darkness — spanning d_min..d_max (full half-cube).
    """
    rows, cols = gray.shape
    pitch = size / n_lines
    line_w = pitch * line_thickness_ratio
    if bar_thickness is None:
        # Rod thickness along depth axis — thin enough to stack many shades
        bar_thickness = max(0.25, min(0.8, (d_max - d_min) / 20.0))

    n_seg = max(12, int(round(size / segment_mm)))
    seg_h = size / n_seg

    for li in range(n_lines):
        u_c = (li + 0.5) * pitch
        u0 = u_c - line_w * 0.5
        u1 = u_c + line_w * 0.5
        col = min(int((li + 0.5) / n_lines * cols), cols - 1)
        c0, c1 = max(0, col - 1), min(cols, col + 2)

        # Build continuous depth samples, then merge nearly-equal depths
        samples = []
        for si in range(n_seg):
            v0 = si * seg_h
            v1 = (si + 1) * seg_h
            row = min(int((si + 0.5) / n_seg * rows), rows - 1)
            dark = 1.0 - float(np.mean(gray[row, c0:c1]))
            d = depth_from_image(dark, d_min, d_max)
            samples.append((v0, v1, d))

        # Merge if depths within tolerance (keeps fine values like 1.5 vs 3.7,
        # but limits triangle count on large cubes)
        merge_eps = max(0.12, (d_max - d_min) / 80.0)
        merged = []
        cv0, cv1, cd = samples[0]
        for v0, v1, d in samples[1:]:
            if abs(d - cd) < merge_eps:
                cv1 = v1
                cd = 0.5 * (cd + d)
            else:
                merged.append((cv0, cv1, cd))
                cv0, cv1, cd = v0, v1, d
        merged.append((cv0, cv1, cd))

        for v0, v1, d_center in merged:
            # Straight bar centered on the image depth, extending ± half thickness
            half = bar_thickness * 0.5
            d0 = max(0.05, d_center - half)
            d1 = min(d_max + half, d_center + half)
            if d1 <= d0 + 0.08:
                d1 = d0 + 0.2
            add_box(verts, faces, face, u0, u1, v0, v1, d0, d1, size)


def add_inner_core(verts, faces, size, core_inset):
    e = core_inset
    s = size - core_inset
    if s <= e + 0.5:
        # Tiny residual core if faces almost meet
        mid = size * 0.5
        r = 0.4
        e, s = mid - r, mid + r
    c = [
        (e, e, e), (s, e, e), (s, s, e), (e, s, e),
        (e, e, s), (s, e, s), (s, s, s), (e, s, s),
    ]
    for q in [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (2, 6, 7, 3), (0, 3, 7, 4), (1, 5, 6, 2)]:
        add_quad(verts, faces, *(c[i] for i in q))


def preview_continuous(gray, d_min, d_max, n_lines, size_mm, out_path):
    h, w = gray.shape
    out = Image.new("RGB", (w, h), (245, 243, 238))
    draw = ImageDraw.Draw(out)
    pitch = w / n_lines
    line_w = pitch * 0.82
    n_seg = 32
    seg_h = h / n_seg

    for li in range(n_lines):
        u_c = (li + 0.5) * pitch
        col = min(int((li + 0.5) / n_lines * w), w - 1)
        for si in range(n_seg):
            v0 = int(si * seg_h)
            v1 = int((si + 1) * seg_h)
            row = min(int((si + 0.5) / n_seg * h), h - 1)
            dark = 1.0 - float(gray[row, col])
            d = depth_from_image(dark, d_min, d_max)
            t = (d - d_min) / max(1e-6, (d_max - d_min))
            # Deeper = darker in preview
            shade = int(40 + (1 - t) * 190)
            ink = (shade, shade, max(0, shade - 8))
            x0 = int(u_c - line_w * 0.5)
            x1 = int(u_c + line_w * 0.5)
            draw.rectangle([x0, v0, x1, max(v0 + 1, v1 - 1)], fill=ink)

    # Caption strip with depth range
    draw.rectangle([0, h - 18, w, h], fill=(30, 30, 30))
    draw.text((6, h - 15), f"depth {d_min:.1f}-{d_max:.1f}mm (cube {size_mm:.0f}mm)", fill=(220, 220, 220))
    out.save(out_path)


def build_cube(image_paths, size=50.0, n_lines=None, sample_res=None):
    # Lines scale with size: ~1mm pitch
    if n_lines is None:
        n_lines = max(12, int(round(size / 1.0)))
    if sample_res is None:
        sample_res = max(64, min(160, n_lines * 3))

    # Full usable depth: surface → almost center (entire half of the cube)
    d_min = max(0.15, size * 0.02)
    d_max = size * 0.5 - max(0.3, size * 0.02)

    verts, faces = [], []
    add_inner_core(verts, faces, size, core_inset=d_max + 0.2)

    # Longer segments on larger cubes → fewer boxes, still continuous depths
    segment_mm = max(1.0, size / 20.0)

    for i, face in enumerate(FACE_NAMES):
        if i >= len(image_paths):
            continue
        gray = load_gray(image_paths[i], sample_res)
        print(f"  face {face}…")
        add_face_continuous_depth_lines(
            verts, faces, face, gray, size,
            n_lines=n_lines,
            d_min=d_min,
            d_max=d_max,
            segment_mm=segment_mm,
        )

    return verts, faces, d_min, d_max, n_lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=float, default=50.0, help="Cube edge mm (e.g. 10 or 50)")
    parser.add_argument("--lines", type=int, default=None, help="Override line count (default ~1/mm)")
    parser.add_argument("--preview-dir", type=Path, default=None)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    # Peek depth range for previews
    d_min = max(0.15, args.size * 0.02)
    d_max = args.size * 0.5 - max(0.3, args.size * 0.02)
    n_lines = args.lines if args.lines else max(12, int(round(args.size / 1.0)))

    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(args.images[:6]):
            g = load_gray(p, 512)
            preview_continuous(
                g, d_min, d_max, n_lines, args.size,
                args.preview_dir / f"{i+1:02d}_fulldepth.png",
            )
            print(f"  preview {i+1:02d}")

    verts, faces, d_min, d_max, n_lines = build_cube(args.images[:6], args.size, args.lines)
    write_stl(args.out, verts, faces)
    print(f"Wrote {args.out}")
    print(f"  {args.size}mm cube, {n_lines} dense straight lines/face")
    print(f"  continuous depth {d_min:.2f}–{d_max:.2f} mm (full half-cube, any value e.g. 1.5, 3.7)")
    print(f"  {len(faces)*2} triangles")


if __name__ == "__main__":
    main()
