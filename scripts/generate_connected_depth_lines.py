#!/usr/bin/env python3
"""
Cube faces = CONNECTED vertical line ribbons with continuous depth from the photo.

Each vertical line is one continuous strip (not floating disconnected boxes).
Depth spans nearly the full half-cube; darker = deeper.
Strong contrast so the image reads clearly in 3D.
"""

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageFont

FACE_NAMES = ["front", "back", "right", "left", "top", "bottom"]


def load_gray(path, size, contrast=2.4):
    img = Image.open(path).convert("L")
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    # Slight sharpen via unsharp-ish: blend with max filter for edges
    arr = np.asarray(img.resize((size, size), Image.LANCZOS), dtype=np.float64) / 255.0
    # Gamma push: midtones toward extremes so photo silhouette is clearer
    arr = np.clip(arr, 0, 1)
    arr = np.where(arr > 0.5, 0.5 + (arr - 0.5) ** 0.85, 0.5 - (0.5 - arr) ** 0.85)
    return np.clip(arr, 0, 1)


def add_tri(verts, faces, a, b, c):
    i = len(verts)
    verts.extend([a, b, c])
    faces.append((i, i + 1, i + 2))


def add_quad(verts, faces, a, b, c, d):
    add_tri(verts, faces, a, b, c)
    add_tri(verts, faces, a, c, d)


def write_stl(path, verts, faces, header="Connected depth line cube"):
    # Faster binary write
    n = len(faces)
    hdr = header.encode("ascii", "ignore")[:80].ljust(80, b"\0")
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(struct.pack("<I", n))
        for i0, i1, i2 in faces:
            v0 = np.asarray(verts[i0], dtype=np.float64)
            v1 = np.asarray(verts[i1], dtype=np.float64)
            v2 = np.asarray(verts[i2], dtype=np.float64)
            normal = np.cross(v1 - v0, v2 - v0)
            nn = np.linalg.norm(normal)
            if nn > 1e-9:
                normal /= nn
            else:
                normal = np.array([0.0, 0.0, 1.0])
            f.write(struct.pack("<3f", *normal))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))


def face_point(face, u, v, depth_from_surface, size):
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


def depth_from_image(dark, d_min, d_max):
    return d_min + float(np.clip(dark, 0.0, 1.0)) * (d_max - d_min)


def add_connected_line_ribbon(
    verts, faces, face, u0, u1, depth_profile, size, back_depth
):
    """
    One continuous vertical LINE: connected strip from top to bottom.
    depth_profile: list of (v, depth_front) samples sorted by v ascending.
    Ribbon goes from depth_front → back_depth (solid connected bar).
    Adjacent samples share edges → fully connected geometry.
    """
    n = len(depth_profile)
    if n < 2:
        return

    # For each sample, 4 corners of the cross-section ring; stitch as strip
    # At each v: outer-left, outer-right, inner-right, inner-left
    rings = []
    for v, d_front in depth_profile:
        d0 = max(0.05, min(d_front, back_depth - 0.15))
        d1 = back_depth
        rings.append([
            face_point(face, u0, v, d0, size),
            face_point(face, u1, v, d0, size),
            face_point(face, u1, v, d1, size),
            face_point(face, u0, v, d1, size),
        ])

    # Cap bottom
    r0 = rings[0]
    add_quad(verts, faces, r0[0], r0[1], r0[2], r0[3])
    # Cap top
    rn = rings[-1]
    add_quad(verts, faces, rn[0], rn[3], rn[2], rn[1])

    # Connect consecutive rings (4 walls) — THIS is the connected line
    for i in range(n - 1):
        a = rings[i]
        b = rings[i + 1]
        # outer (toward surface) face of the line
        add_quad(verts, faces, a[0], a[1], b[1], b[0])
        # inner (deep) face
        add_quad(verts, faces, a[2], a[3], b[3], b[2])
        # left wall
        add_quad(verts, faces, a[0], b[0], b[3], a[3])
        # right wall
        add_quad(verts, faces, a[1], a[2], b[2], b[1])


def add_face_backplane(verts, faces, face, size, back_depth, thickness=1.2):
    """Solid back plate so the face isn't empty — lines connect into this."""
    d0 = back_depth
    d1 = min(size * 0.49, back_depth + thickness)
    corners = [
        face_point(face, 0, 0, d0, size),
        face_point(face, size, 0, d0, size),
        face_point(face, size, size, d0, size),
        face_point(face, 0, size, d0, size),
        face_point(face, 0, 0, d1, size),
        face_point(face, size, 0, d1, size),
        face_point(face, size, size, d1, size),
        face_point(face, 0, size, d1, size),
    ]
    add_quad(verts, faces, corners[0], corners[1], corners[2], corners[3])
    add_quad(verts, faces, corners[5], corners[4], corners[7], corners[6])
    add_quad(verts, faces, corners[0], corners[3], corners[7], corners[4])
    add_quad(verts, faces, corners[1], corners[5], corners[6], corners[2])
    add_quad(verts, faces, corners[0], corners[4], corners[5], corners[1])
    add_quad(verts, faces, corners[3], corners[2], corners[6], corners[7])


def add_face_connected_lines(verts, faces, face, gray, size, n_lines, d_min, d_max):
    rows, cols = gray.shape
    pitch = size / n_lines
    # Almost touching neighbors so surface looks dense & connected as a field of lines
    line_w = pitch * 0.92
    back_depth = d_max + max(0.4, size * 0.02)

    # Fine sampling along height for clear photo detail
    n_samp = max(40, int(round(size * 1.6)))  # ~0.6mm steps on 50mm
    # Snap samples to image rows
    for li in range(n_lines):
        u_c = (li + 0.5) * pitch
        u0 = u_c - line_w * 0.5
        u1 = u_c + line_w * 0.5
        # Map line to image column range
        c0 = int(li / n_lines * cols)
        c1 = int((li + 1) / n_lines * cols)
        c1 = max(c0 + 1, c1)

        profile = []
        for si in range(n_samp + 1):
            v = size * si / n_samp
            row = min(int(si / n_samp * (rows - 1)), rows - 1)
            dark = 1.0 - float(np.mean(gray[row, c0:c1]))
            d = depth_from_image(dark, d_min, d_max)
            profile.append((v, d))

        add_connected_line_ribbon(verts, faces, face, u0, u1, profile, size, back_depth)

    add_face_backplane(verts, faces, face, size, back_depth)


def add_inner_core(verts, faces, size, core_inset):
    e = core_inset
    s = size - core_inset
    if s <= e + 0.4:
        mid = size * 0.5
        e, s = mid - 0.3, mid + 0.3
    c = [
        (e, e, e), (s, e, e), (s, s, e), (e, s, e),
        (e, e, s), (s, e, s), (s, s, s), (e, s, s),
    ]
    for q in [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (2, 6, 7, 3), (0, 3, 7, 4), (1, 5, 6, 2)]:
        add_quad(verts, faces, *(c[i] for i in q))


def make_comparison(photo_path, gray, d_min, d_max, n_lines, size_mm, out_path):
    """Side-by-side: original photo | depth-line preview — so image is obvious."""
    h = 512
    photo = Image.open(photo_path).convert("RGB").resize((h, h), Image.LANCZOS)
    # Depth viz as continuous vertical connected lines
    depth_img = Image.new("RGB", (h, h), (230, 228, 222))
    draw = ImageDraw.Draw(depth_img)
    pitch = h / n_lines
    line_w = pitch * 0.92
    rows, cols = gray.shape

    for li in range(n_lines):
        u_c = (li + 0.5) * pitch
        c0 = int(li / n_lines * cols)
        c1 = max(c0 + 1, int((li + 1) / n_lines * cols))
        x0 = int(u_c - line_w * 0.5)
        x1 = int(u_c + line_w * 0.5)
        for y in range(h):
            row = min(int(y / h * (rows - 1)), rows - 1)
            dark = 1.0 - float(np.mean(gray[row, c0:c1]))
            d = depth_from_image(dark, d_min, d_max)
            t = (d - d_min) / max(1e-6, d_max - d_min)
            # Deeper = darker; also slight blue so depth reads in viewer thumbs
            shade = int(255 * (1 - t))
            ink = (shade, shade, max(0, shade - 20))
            for x in range(x0, min(x1 + 1, h)):
                depth_img.putpixel((x, y), ink)

    # Composite comparison
    pad = 16
    label_h = 36
    canvas = Image.new("RGB", (h * 2 + pad * 3, h + pad * 2 + label_h), (24, 24, 28))
    canvas.paste(photo, (pad, pad + label_h))
    canvas.paste(depth_img, (pad * 2 + h, pad + label_h))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 10), "Original photo", fill=(200, 200, 200))
    d.text((pad * 2 + h, 10), f"Connected depth lines ({d_min:.1f}-{d_max:.1f}mm)", fill=(200, 200, 200))
    canvas.save(out_path)


def build_cube(image_paths, size=50.0, n_lines=None):
    if n_lines is None:
        n_lines = max(24, int(round(size / 0.9)))  # denser ~0.9mm

    d_min = max(0.2, size * 0.02)
    d_max = size * 0.48  # almost full half-depth
    sample_res = max(96, n_lines * 3)

    verts, faces = [], []
    add_inner_core(verts, faces, size, core_inset=d_max + 1.5)

    for i, face in enumerate(FACE_NAMES):
        if i >= len(image_paths):
            continue
        print(f"  face {face}…")
        gray = load_gray(image_paths[i], sample_res)
        add_face_connected_lines(verts, faces, face, gray, size, n_lines, d_min, d_max)

    return verts, faces, d_min, d_max, n_lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=float, default=50.0)
    parser.add_argument("--lines", type=int, default=None)
    parser.add_argument("--preview-dir", type=Path, default=None)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    d_min = max(0.2, args.size * 0.02)
    d_max = args.size * 0.48
    n_lines = args.lines if args.lines else max(24, int(round(args.size / 0.9)))

    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(args.images[:6]):
            g = load_gray(p, 512)
            make_comparison(
                p, g, d_min, d_max, n_lines, args.size,
                args.preview_dir / f"{i+1:02d}_compare.png",
            )
            print(f"  compare {i+1:02d}")

    verts, faces, d_min, d_max, n_lines = build_cube(args.images[:6], args.size, args.lines)
    print(f"  writing {len(faces)} triangles…")
    write_stl(args.out, verts, faces)
    print(f"Wrote {args.out}")
    print(f"  {args.size}mm cube, {n_lines} CONNECTED vertical lines/face")
    print(f"  continuous depth {d_min:.2f}-{d_max:.2f} mm (full half-cube)")
    print(f"  {len(faces)*2} triangles")


if __name__ == "__main__":
    main()
