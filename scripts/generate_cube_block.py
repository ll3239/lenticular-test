#!/usr/bin/env python3
"""
Generate a square cube block with lenticular-encoded faces.

Modes:
  six_faces  - Up to 6 different photos, one per cube face (walk around the block).
  two_flip   - Front face flips between 2 photos (left/right tilt); solid cube elsewhere.

Each face uses vertical lenticular ridges — no LED, purely geometric.
"""

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image

# Face order: front(+Y), back(-Y), right(+X), left(-X), top(+Z), bottom(-Z)
FACE_NAMES = ["front", "back", "right", "left", "top", "bottom"]


def load_grayscale(path, cols, rows):
    img = Image.open(path).convert("L")
    img = img.resize((cols, rows), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0


def add_triangle(verts, faces, v0, v1, v2):
    i0 = len(verts)
    verts.extend([v0, v1, v2])
    faces.append((i0, i0 + 1, i0 + 2))


def add_quad(verts, faces, v0, v1, v2, v3):
    add_triangle(verts, faces, v0, v1, v2)
    add_triangle(verts, faces, v0, v2, v3)


def write_binary_stl(path, verts, faces, header_text="Lenticular cube block"):
    triangles = []
    for i0, i1, i2 in faces:
        v0, v1, v2 = np.array(verts[i0]), np.array(verts[i1]), np.array(verts[i2])
        edge1 = v1 - v0
        edge2 = v2 - v0
        normal = np.cross(edge1, edge2)
        norm = np.linalg.norm(normal)
        normal = normal / norm if norm > 1e-9 else np.array([0.0, 0.0, 1.0])
        triangles.append((normal, v0, v1, v2))

    header = header_text.encode("ascii", errors="ignore")[:80]
    header = header + b"\0" * (80 - len(header))

    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for normal, v0, v1, v2 in triangles:
            f.write(struct.pack("<3f", *normal))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))


def _height(val, base, min_h, max_h):
    return base + min_h + val * (max_h - min_h)


def _face_point(face, u, v, depth, size):
    """Map face UV (0..size) + outward depth to XYZ."""
    if face == "front":
        return (u, size + depth, v)
    if face == "back":
        return (u, -depth, v)
    if face == "right":
        return (size + depth, u, v)
    if face == "left":
        return (-depth, u, v)
    if face == "top":
        return (u, v, size + depth)
    if face == "bottom":
        return (u, v, -depth)
    raise ValueError(face)


def _inner_face_point(face, u, v, size, embed):
    """Point on cube body (embedded slightly under face surface)."""
    if face == "front":
        return (u, size - embed, v)
    if face == "back":
        return (u, embed, v)
    if face == "right":
        return (size - embed, u, v)
    if face == "left":
        return (embed, u, v)
    if face == "top":
        return (u, v, size - embed)
    if face == "bottom":
        return (u, v, embed)
    raise ValueError(face)


def add_single_image_face(verts, faces, face, img, size, cols, rows, embed, min_h, max_h):
    """One image encoded as vertical lenticular ridges on a cube face."""
    du = size / cols
    dv = size / rows

    for row in range(rows):
        v0 = row * dv
        v1 = (row + 1) * dv
        for col in range(cols):
            u0 = col * du
            u1 = (col + 1) * du
            h = _height(img[row, col], 0.0, min_h, max_h)

            inner_bl = _inner_face_point(face, u0, v0, size, embed)
            inner_br = _inner_face_point(face, u1, v0, size, embed)
            inner_tr = _inner_face_point(face, u1, v1, size, embed)
            inner_tl = _inner_face_point(face, u0, v1, size, embed)

            outer_bl = _face_point(face, u0, v0, h, size)
            outer_br = _face_point(face, u1, v0, h, size)
            outer_tr = _face_point(face, u1, v1, h, size)
            outer_tl = _face_point(face, u0, v1, h, size)

            add_quad(verts, faces, inner_bl, inner_br, outer_br, outer_bl)
            add_quad(verts, faces, inner_br, inner_tr, outer_tr, outer_br)
            add_quad(verts, faces, inner_tr, inner_tl, outer_tl, outer_tr)
            add_quad(verts, faces, inner_tl, inner_bl, outer_bl, outer_tl)

            if row == 0:
                add_quad(verts, faces, inner_bl, inner_br, inner_tr, inner_tl)
            if row == rows - 1:
                add_quad(verts, faces, outer_bl, outer_br, outer_tr, outer_tl)


def add_flip_image_face(verts, faces, face, img_a, img_b, size, cols, rows, embed, min_h, max_h):
    """Two images: left tilt = A, right tilt = B (sloped lenticular ridges)."""
    du = size / cols
    dv = size / rows

    for row in range(rows):
        v0 = row * dv
        v1 = (row + 1) * dv
        for col in range(cols):
            u0 = col * du
            u1 = (col + 1) * du
            um = (u0 + u1) * 0.5

            ha = _height(img_a[row, col], 0.0, min_h, max_h)
            hb = _height(img_b[row, col], 0.0, min_h, max_h)
            peak = max(ha, hb) + min_h * 0.5

            inner_bl = _inner_face_point(face, u0, v0, size, embed)
            inner_br = _inner_face_point(face, u1, v0, size, embed)
            inner_tr = _inner_face_point(face, u1, v1, size, embed)
            inner_tl = _inner_face_point(face, u0, v1, size, embed)

            mid_b0 = _face_point(face, um, v0, peak, size)
            mid_b1 = _face_point(face, um, v1, peak, size)
            left_b0 = _face_point(face, u0, v0, ha, size)
            left_b1 = _face_point(face, u0, v1, ha, size)
            right_b0 = _face_point(face, u1, v0, hb, size)
            right_b1 = _face_point(face, u1, v1, hb, size)

            add_quad(verts, faces, inner_bl, inner_br, mid_b0, left_b0)
            add_quad(verts, faces, left_b0, mid_b0, mid_b1, left_b1)
            add_quad(verts, faces, left_b1, mid_b1, inner_tr, inner_tl)
            add_quad(verts, faces, inner_tl, inner_tr, inner_br, inner_bl)

            add_quad(verts, faces, inner_br, inner_tr, mid_b1, mid_b0)
            add_quad(verts, faces, mid_b0, mid_b1, right_b1, right_b0)
            add_quad(verts, faces, right_b0, right_b1, inner_tr, inner_br)

            if row == 0:
                add_quad(verts, faces, inner_bl, inner_br, inner_tr, inner_tl)
            if row == rows - 1:
                add_quad(verts, faces, left_b0, mid_b0, mid_b1, left_b1)
                add_quad(verts, faces, mid_b0, right_b0, right_b1, mid_b1)


def add_solid_face(verts, faces, face, size, embed):
    """Plain flat cube face (no image)."""
    inner = [
        _inner_face_point(face, 0, 0, size, embed),
        _inner_face_point(face, size, 0, size, embed),
        _inner_face_point(face, size, size, size, embed),
        _inner_face_point(face, 0, size, size, embed),
    ]
    outer = [
        _face_point(face, 0, 0, 0.05, size),
        _face_point(face, size, 0, 0.05, size),
        _face_point(face, size, size, 0.05, size),
        _face_point(face, 0, size, 0.05, size),
    ]
    add_quad(verts, faces, inner[0], inner[1], outer[1], outer[0])
    add_quad(verts, faces, inner[1], inner[2], outer[2], outer[1])
    add_quad(verts, faces, inner[2], inner[3], outer[3], outer[2])
    add_quad(verts, faces, inner[3], inner[0], outer[0], outer[3])
    add_quad(verts, faces, inner[0], inner[1], inner[2], inner[3])


def add_core_cube(verts, faces, size, embed):
    """Fill cube interior so the block is solid."""
    s = size - embed
    corners = [
        (embed, embed, embed),
        (s, embed, embed),
        (s, s, embed),
        (embed, s, embed),
        (embed, embed, s),
        (s, embed, s),
        (s, s, s),
        (embed, s, s),
    ]
    # 6 faces of inner core
    quads = [
        (0, 1, 2, 3),  # bottom z=embed
        (4, 5, 6, 7),  # top
        (0, 1, 5, 4),  # front y=embed
        (2, 3, 7, 6),  # back y=s
        (0, 3, 7, 4),  # left
        (1, 2, 6, 5),  # right
    ]
    for q in quads:
        add_quad(verts, faces, *(corners[i] for i in q))


def build_six_face_cube(image_paths, size=50.0, cols=40, rows=40):
    verts, faces = [], []
    embed, min_h, max_h = 1.0, 0.2, 1.2

    add_core_cube(verts, faces, size, embed)

    for i, face in enumerate(FACE_NAMES):
        if i < len(image_paths) and image_paths[i]:
            img = load_grayscale(image_paths[i], cols, rows)
            add_single_image_face(verts, faces, face, img, size, cols, rows, embed, min_h, max_h)
        else:
            add_solid_face(verts, faces, face, size, embed)

    return verts, faces


def build_two_flip_cube(image_a, image_b, size=50.0, cols=40, rows=40, flip_faces=None):
    """Lenticular flip on 1-2 faces; remaining faces plain."""
    if flip_faces is None:
        flip_faces = ["front"]

    verts, faces = [], []
    embed, min_h, max_h = 1.0, 0.2, 1.2

    img_a = load_grayscale(image_a, cols, rows)
    img_b = load_grayscale(image_b, cols, rows)

    add_core_cube(verts, faces, size, embed)

    for face in FACE_NAMES:
        if face in flip_faces:
            add_flip_image_face(verts, faces, face, img_a, img_b, size, cols, rows, embed, min_h, max_h)
        else:
            add_solid_face(verts, faces, face, size, embed)

    return verts, faces


def main():
    parser = argparse.ArgumentParser(description="Generate lenticular cube block STL")
    parser.add_argument("--mode", choices=["six_faces", "two_flip"], required=True)
    parser.add_argument("--size", type=float, default=50.0, help="Cube edge length mm")
    parser.add_argument("--cols", type=int, default=40)
    parser.add_argument("--rows", type=int, default=40)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--images", type=Path, nargs="+", help="Image paths (6 for six_faces, 2 for two_flip)")
    parser.add_argument("--flip-faces", nargs="+", default=["front"], choices=FACE_NAMES)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.mode == "six_faces":
        if not args.images or len(args.images) < 1:
            raise SystemExit("six_faces needs 1-6 images")
        paths = args.images[:6]
        verts, faces = build_six_face_cube(paths, args.size, args.cols, args.rows)
        label = f"6-face cube ({len(paths)} photos)"
    else:
        if not args.images or len(args.images) < 2:
            raise SystemExit("two_flip needs 2 images")
        verts, faces = build_two_flip_cube(
            args.images[0], args.images[1], args.size, args.cols, args.rows, args.flip_faces
        )
        label = f"2-flip cube (faces: {', '.join(args.flip_faces)})"

    write_binary_stl(args.out, verts, faces, f"Lenticular {label}")
    print(f"Wrote {args.out}")
    print(f"  Mode: {label}")
    print(f"  Size: {args.size}mm cube, {len(faces)*2} triangles")


if __name__ == "__main__":
    main()
