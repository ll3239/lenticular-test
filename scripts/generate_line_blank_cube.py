#!/usr/bin/env python3
"""
Generate a printable cube where each face is a LINE + BLANK relief of a photo.

- Vertical (or horizontal) raised ridges = ink lines
- Flat recesses between them = blanks
- Ridge height/thickness follows local darkness of that face's photo

This is the Bambu-ready geometry (STL), not a texture preview.
"""

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

FACE_NAMES = ["front", "back", "right", "left", "top", "bottom"]


def load_gray(path, size, contrast=1.8):
    img = Image.open(path).convert("L")
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = img.resize((size, size), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0


def preview_vertical_lines(gray, spacing=10, out_path=None):
    """2D preview: continuous vertical lines with varying width + blank gaps."""
    h, w = gray.shape
    out = Image.new("RGB", (w, h), (250, 248, 240))
    ink = (15, 15, 20)
    max_thick = max(2, spacing - 2)

    for x in range(0, w, spacing):
        for y in range(h):
            x1 = min(x + spacing, w)
            dark = 1.0 - float(np.mean(gray[y, x:x1]))
            # Very light → blank (no ink in this slot)
            if dark < 0.08:
                continue
            thick = max(1, int(round(0.15 * max_thick + dark * 0.85 * max_thick)))
            x0 = x + (spacing - thick) // 2
            for t in range(thick):
                xx = min(x0 + t, w - 1)
                out.putpixel((xx, y), ink)

    if out_path:
        out.save(out_path)
    return out


def add_tri(verts, faces, a, b, c):
    i = len(verts)
    verts.extend([a, b, c])
    faces.append((i, i + 1, i + 2))


def add_quad(verts, faces, a, b, c, d):
    add_tri(verts, faces, a, b, c)
    add_tri(verts, faces, a, c, d)


def write_stl(path, verts, faces, header="Line relief cube"):
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


def face_xyz(face, u, v, depth, size):
    """u,v in [0,size], depth outward from face."""
    if face == "front":
        return (u, size + depth, v)
    if face == "back":
        return (size - u, -depth, v)
    if face == "right":
        return (size + depth, size - u, v)
    if face == "left":
        return (-depth, u, v)
    if face == "top":
        return (u, v, size + depth)
    if face == "bottom":
        return (u, size - v, -depth)
    raise ValueError(face)


def face_base(face, u, v, size, embed):
    if face == "front":
        return (u, size - embed, v)
    if face == "back":
        return (size - u, embed, v)
    if face == "right":
        return (size - embed, size - u, v)
    if face == "left":
        return (embed, u, v)
    if face == "top":
        return (u, v, size - embed)
    if face == "bottom":
        return (u, size - v, embed)
    raise ValueError(face)


def add_core(verts, faces, size, wall):
    """Hollow-ish solid core so cube is printable as one piece."""
    e = wall
    s = size - wall
    c = [
        (e, e, e), (s, e, e), (s, s, e), (e, s, e),
        (e, e, s), (s, e, s), (s, s, s), (e, s, s),
    ]
    for q in [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (2, 6, 7, 3), (0, 3, 7, 4), (1, 5, 6, 2)]:
        add_quad(verts, faces, *(c[i] for i in q))


def add_blank_face_plate(verts, faces, face, size, embed, plate_h=0.2):
    """Flat recessed plate covering the whole face (the 'blank' background)."""
    corners_u = [0.0, size]
    corners_v = [0.0, size]
    base = [
        face_base(face, 0, 0, size, embed),
        face_base(face, size, 0, size, embed),
        face_base(face, size, size, size, embed),
        face_base(face, 0, size, size, embed),
    ]
    top = [
        face_xyz(face, 0, 0, plate_h, size),
        face_xyz(face, size, 0, plate_h, size),
        face_xyz(face, size, size, plate_h, size),
        face_xyz(face, 0, size, plate_h, size),
    ]
    add_quad(verts, faces, top[0], top[1], top[2], top[3])
    for i in range(4):
        j = (i + 1) % 4
        add_quad(verts, faces, base[i], base[j], top[j], top[i])


def add_vertical_ridges(verts, faces, face, gray, size, embed, n_lines=40, min_h=0.5, max_h=2.0, plate_h=0.2):
    """
    Continuous vertical RIDGES with varying WIDTH (lines) and gaps (blanks).
    Each column is one continuous line from bottom to top; width changes with darkness.
    Light → thin or zero width (blank). Dark → thick raised line.
    """
    rows, cols = gray.shape
    pitch = size / n_lines
    n_samples = max(32, rows // 2)
    sample_h = size / n_samples

    for li in range(n_lines):
        u_center = (li + 0.5) * pitch
        col_idx = min(int((li + 0.5) / n_lines * cols), cols - 1)
        c0 = max(0, col_idx - 1)
        c1 = min(cols, col_idx + 2)

        # Profile along the full height of this line
        profile = []  # (v0, v1, half_width, height)
        for si in range(n_samples):
            v0 = si * sample_h
            v1 = (si + 1) * sample_h
            row_idx = min(int((si + 0.5) / n_samples * rows), rows - 1)
            dark = 1.0 - float(np.mean(gray[row_idx, c0:c1]))

            if dark < 0.10:
                half_w = 0.0  # blank
                height = plate_h
            else:
                half_w = (0.12 + dark * 0.38) * pitch
                half_w = min(half_w, pitch * 0.45)
                height = min_h + dark * (max_h - min_h)
            profile.append((v0, v1, half_w, height))

        # Emit quads only where there is a visible line (half_w > 0)
        for v0, v1, half_w, height in profile:
            if half_w <= 0.02:
                continue
            u0 = u_center - half_w
            u1 = u_center + half_w
            tl = face_xyz(face, u0, v0, height, size)
            tr = face_xyz(face, u1, v0, height, size)
            br = face_xyz(face, u1, v1, height, size)
            bl = face_xyz(face, u0, v1, height, size)
            btl = face_xyz(face, u0, v0, plate_h, size)
            btr = face_xyz(face, u1, v0, plate_h, size)
            bbr = face_xyz(face, u1, v1, plate_h, size)
            bbl = face_xyz(face, u0, v1, plate_h, size)

            add_quad(verts, faces, tl, tr, br, bl)
            add_quad(verts, faces, btl, btr, tr, tl)
            add_quad(verts, faces, bl, br, bbr, bbl)
            add_quad(verts, faces, btl, tl, bl, bbl)
            add_quad(verts, faces, tr, btr, bbr, br)


def build_cube(image_paths, size=50.0, n_lines=36, sample_res=128):
    verts, faces = [], []
    embed = 1.5
    plate_h = 0.25

    add_core(verts, faces, size, embed)

    for i, face in enumerate(FACE_NAMES):
        path = image_paths[i] if i < len(image_paths) else None
        add_blank_face_plate(verts, faces, face, size, embed, plate_h)
        if path:
            gray = load_gray(path, sample_res)
            add_vertical_ridges(
                verts, faces, face, gray, size, embed,
                n_lines=n_lines, min_h=0.5, max_h=1.9, plate_h=plate_h,
            )

    return verts, faces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=float, default=50.0)
    parser.add_argument("--lines", type=int, default=36, help="Vertical lines per face")
    parser.add_argument("--preview-dir", type=Path, default=None)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(args.images[:6]):
            g = load_gray(p, 512)
            preview_vertical_lines(g, spacing=max(6, 512 // args.lines), out_path=args.preview_dir / f"{i+1:02d}_lines.png")
            print(f"  preview {i+1:02d}_lines.png")

    verts, faces = build_cube(args.images[:6], args.size, args.lines)
    write_stl(args.out, verts, faces, "Line blank relief cube 6 faces")
    print(f"Wrote {args.out}")
    print(f"  {args.size}mm cube, {args.lines} lines/face, {len(faces)*2} triangles")
    print("  Each face: raised vertical LINES + recessed BLANKS from one photo")


if __name__ == "__main__":
    main()
