#!/usr/bin/env python3
"""
Cube where EVERY face is solid line-relief 3D:

- Full coverage: every vertical slot is a continuous line (no empty middle)
- Depth varies along each line from the photo (dark = deep, light = shallow)
- Looks 3D from the side because ridges have real height, not flat dots
"""

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

FACE_NAMES = ["front", "back", "right", "left", "top", "bottom"]


def load_gray(path, size, contrast=1.8):
    img = Image.open(path).convert("L")
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = img.resize((size, size), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0


def preview_depth_lines(gray, n_lines=48, out_path=None):
    """2D preview of full-face vertical lines (darker = thicker = deeper look)."""
    h, w = gray.shape
    out = Image.new("RGB", (w, h), (235, 232, 225))
    ink = (20, 20, 24)
    spacing = max(2, w // n_lines)
    max_thick = max(1, spacing - 1)

    for x in range(0, w, spacing):
        for y in range(h):
            x1 = min(x + spacing, w)
            dark = 1.0 - float(np.mean(gray[y, x:x1]))
            # Always draw a line — never leave empty
            thick = max(1, int(round(0.2 * max_thick + dark * 0.8 * max_thick)))
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


def write_stl(path, verts, faces, header="Full depth line cube"):
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


def add_solid_core(verts, faces, size, wall):
    """Solid cube body — middle is FULL, not hollow."""
    # Outer cube almost full size; faces get line relief on top of this body
    e = 0.0
    s = size
    # Use a slightly inset solid so face ridges sit on top of body faces
    inset = wall
    e = inset
    s = size - inset
    c = [
        (e, e, e), (s, e, e), (s, s, e), (e, s, e),
        (e, e, s), (s, e, s), (s, s, s), (e, s, s),
    ]
    # Fill as solid by emitting all 6 faces of the core (watertight shell of solid body)
    for q in [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (2, 6, 7, 3), (0, 3, 7, 4), (1, 5, 6, 2)]:
        add_quad(verts, faces, *(c[i] for i in q))


def add_full_depth_lines(verts, faces, face, gray, size, n_lines=40, min_depth=0.6, max_depth=3.5):
    """
    Cover the ENTIRE face with continuous vertical lines of varying DEPTH.
    Every column has a full-height line — no empty middle.
    Depth follows photo darkness along the line.
    """
    rows, cols = gray.shape
    pitch = size / n_lines
    # High sampling along height for smooth depth changes
    n_samp = max(40, rows // 2)
    dv = size / n_samp
    # Line width: nearly fill pitch so face looks solid with grooves
    half_w = pitch * 0.42

    body = 0.0  # ridge sits on cube body surface (y=size for front etc.)

    for li in range(n_lines):
        u_c = (li + 0.5) * pitch
        u0 = u_c - half_w
        u1 = u_c + half_w
        col = min(int((li + 0.5) / n_lines * cols), cols - 1)
        c0, c1 = max(0, col - 1), min(cols, col + 2)

        # Depth samples along full height (always > 0)
        depths = []
        for si in range(n_samp + 1):
            v = si * dv if si < n_samp else size
            row = min(int(si / n_samp * (rows - 1)), rows - 1)
            dark = 1.0 - float(np.mean(gray[row, c0:c1]))
            d = min_depth + dark * (max_depth - min_depth)
            depths.append((v, d))

        # Build continuous ribbon: for each segment between samples
        for si in range(n_samp):
            v0, d0 = depths[si]
            v1, d1 = depths[si + 1]

            # Outer surface of the line (varying depth)
            a = face_xyz(face, u0, v0, d0, size)
            b = face_xyz(face, u1, v0, d0, size)
            c = face_xyz(face, u1, v1, d1, size)
            d = face_xyz(face, u0, v1, d1, size)

            # Inner surface on cube body
            ai = face_xyz(face, u0, v0, body, size)
            bi = face_xyz(face, u1, v0, body, size)
            ci = face_xyz(face, u1, v1, body, size)
            di = face_xyz(face, u0, v1, body, size)

            add_quad(verts, faces, a, b, c, d)       # outer face of line
            add_quad(verts, faces, ai, a, d, di)     # left wall
            add_quad(verts, faces, b, bi, ci, c)     # right wall

        # Cap top and bottom of each line
        v_bot, d_bot = depths[0]
        v_top, d_top = depths[-1]
        add_quad(
            verts, faces,
            face_xyz(face, u0, v_bot, body, size),
            face_xyz(face, u1, v_bot, body, size),
            face_xyz(face, u1, v_bot, d_bot, size),
            face_xyz(face, u0, v_bot, d_bot, size),
        )
        add_quad(
            verts, faces,
            face_xyz(face, u0, v_top, d_top, size),
            face_xyz(face, u1, v_top, d_top, size),
            face_xyz(face, u1, v_top, body, size),
            face_xyz(face, u0, v_top, body, size),
        )


def add_groove_floors(verts, faces, face, size, n_lines, groove_depth=0.15):
    """Thin floor strips between lines so gaps read as grooves, not holes."""
    pitch = size / n_lines
    half_w = pitch * 0.42
    gap = pitch - 2 * half_w
    if gap < 0.05:
        return
    for li in range(n_lines - 1):
        u0 = (li + 0.5) * pitch + half_w
        u1 = (li + 1.5) * pitch - half_w
        # Recessed groove between lines
        a = face_xyz(face, u0, 0, groove_depth, size)
        b = face_xyz(face, u1, 0, groove_depth, size)
        c = face_xyz(face, u1, size, groove_depth, size)
        d = face_xyz(face, u0, size, groove_depth, size)
        add_quad(verts, faces, a, b, c, d)


def build_cube(image_paths, size=50.0, n_lines=40, min_depth=0.8, max_depth=4.0, sample_res=160):
    verts, faces = [], []
    wall = 2.0  # solid body inset; middle of cube is solid plastic

    add_solid_core(verts, faces, size, wall)

    for i, face in enumerate(FACE_NAMES):
        if i >= len(image_paths):
            continue
        gray = load_gray(image_paths[i], sample_res)
        add_full_depth_lines(
            verts, faces, face, gray, size,
            n_lines=n_lines, min_depth=min_depth, max_depth=max_depth,
        )
        add_groove_floors(verts, faces, face, size, n_lines, groove_depth=0.2)

    return verts, faces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=float, default=50.0)
    parser.add_argument("--lines", type=int, default=40)
    parser.add_argument("--min-depth", type=float, default=0.8)
    parser.add_argument("--max-depth", type=float, default=4.0)
    parser.add_argument("--preview-dir", type=Path, default=None)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(args.images[:6]):
            g = load_gray(p, 512)
            preview_depth_lines(g, args.lines, args.preview_dir / f"{i+1:02d}_depth_lines.png")
            print(f"  preview {i+1:02d}")

    verts, faces = build_cube(
        args.images[:6], args.size, args.lines, args.min_depth, args.max_depth
    )
    write_stl(args.out, verts, faces)
    print(f"Wrote {args.out}")
    print(f"  {args.size}mm solid cube, {args.lines} full-height lines/face")
    print(f"  depth {args.min_depth}–{args.max_depth} mm, {len(faces)*2} triangles")
    print("  Middle is solid; each face is packed with lines of varying depth")


if __name__ == "__main__":
    main()
