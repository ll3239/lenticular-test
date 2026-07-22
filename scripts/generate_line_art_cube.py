#!/usr/bin/env python3
"""
Generate cube STL from cross-line op art (vertical + horizontal line paintings).

Each face stores ridge height from the combined line pattern.
Two-flip face: vertical ridges = image A, horizontal component = image B.
Six-face cube: each face = vertical line painting of one image.
"""

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image

from line_art import load_gray, compose_cross_lines, line_screen_vertical

FACE_NAMES = ["front", "back", "right", "left", "top", "bottom"]


def add_triangle(verts, faces, v0, v1, v2):
    i0 = len(verts)
    verts.extend([v0, v1, v2])
    faces.append((i0, i0 + 1, i0 + 2))


def add_quad(verts, faces, v0, v1, v2, v3):
    add_triangle(verts, faces, v0, v1, v2)
    add_triangle(verts, faces, v0, v2, v3)


def write_stl(path, verts, faces, header="Line art cube"):
    triangles = []
    for i0, i1, i2 in faces:
        v0, v1, v2 = np.array(verts[i0]), np.array(verts[i1]), np.array(verts[i2])
        n = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(n)
        n = n / norm if norm > 1e-9 else np.array([0, 0, 1])
        triangles.append((n, v0, v1, v2))
    hdr = header.encode()[:80].ljust(80, b"\0")
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(struct.pack("<I", len(triangles)))
        for n, v0, v1, v2 in triangles:
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))


def _pt(face, u, v, d, s):
    if face == "front": return (u, s + d, v)
    if face == "back": return (u, -d, v)
    if face == "right": return (s + d, u, v)
    if face == "left": return (-d, u, v)
    if face == "top": return (u, v, s + d)
    if face == "bottom": return (u, v, -d)
    raise ValueError(face)


def _inner(face, u, v, s, e):
    if face == "front": return (u, s - e, v)
    if face == "back": return (u, e, v)
    if face == "right": return (s - e, u, v)
    if face == "left": return (e, u, v)
    if face == "top": return (u, v, s - e)
    if face == "bottom": return (u, v, e)
    raise ValueError(face)


def line_density_field(gray, spacing):
    """Combined vertical+horizontal line density 0..1 (darker image = taller ridges)."""
    h, w = gray.shape
    field = np.zeros((h, w))
    for x in range(0, w, spacing):
        dark = 1.0 - np.mean(gray[:, min(x, w - 1)])
        x1 = min(x + spacing, w)
        field[:, x:x1] = np.maximum(field[:, x:x1], dark)
    for y in range(0, h, spacing):
        dark = 1.0 - np.mean(gray[min(y, h - 1), :])
        y1 = min(y + spacing, h)
        field[y:y1, :] = np.maximum(field[y:y1, :], dark * 0.85)
    return field


def cross_density_field(img_a, img_b, spacing):
    h, w = img_a.shape
    vert = np.zeros((h, w))
    horiz = np.zeros((h, w))
    for x in range(0, w, spacing):
        dark = 1.0 - np.mean(img_a[:, min(x, w - 1)])
        x1 = min(x + spacing, w)
        vert[:, x:x1] = dark
    for y in range(0, h, spacing):
        dark = 1.0 - np.mean(img_b[min(y, h - 1), :])
        y1 = min(y + spacing, h)
        horiz[y:y1, :] = dark
    return np.maximum(vert, horiz * 0.9)


def add_face_from_field(verts, faces, face, field, size, embed, min_h, max_h):
    rows, cols = field.shape
    du, dv = size / cols, size / rows
    for r in range(rows):
        for c in range(cols):
            u0, u1 = c * du, (c + 1) * du
            v0, v1 = r * dv, (r + 1) * dv
            h = min_h + field[r, c] * (max_h - min_h)
            ibl = _inner(face, u0, v0, size, embed)
            ibr = _inner(face, u1, v0, size, embed)
            itr = _inner(face, u1, v1, size, embed)
            itl = _inner(face, u0, v1, size, embed)
            obl = _pt(face, u0, v0, h, size)
            obr = _pt(face, u1, v0, h, size)
            otr = _pt(face, u1, v1, h, size)
            otl = _pt(face, u0, v1, h, size)
            add_quad(verts, faces, ibl, ibr, obr, obl)
            add_quad(verts, faces, ibr, itr, otr, obr)
            add_quad(verts, faces, itr, itl, otl, otr)
            add_quad(verts, faces, itl, ibl, obl, otl)


def add_core(verts, faces, size, embed):
    s = size - embed
    c = [
        (embed, embed, embed), (s, embed, embed), (s, s, embed), (embed, s, embed),
        (embed, embed, s), (s, embed, s), (s, s, s), (embed, s, s),
    ]
    for q in [(0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(0,3,7,4),(1,2,6,5)]:
        add_quad(verts, faces, *(c[i] for i in q))


def build_two_flip(img_a, img_b, size=50, cols=48, spacing=6):
    verts, faces = [], []
    embed, min_h, max_h = 1.2, 0.3, 1.5
    ga, gb = load_gray(img_a, cols), load_gray(img_b, cols)
    field = cross_density_field(ga, gb, max(2, spacing * cols // 80))
    add_core(verts, faces, size, embed)
    add_face_from_field(verts, faces, "front", field, size, embed, min_h, max_h)
    for f in ["back", "right", "left", "top", "bottom"]:
        plain = np.full((cols, cols), 0.1)
        add_face_from_field(verts, faces, f, plain, size, embed, 0.05, 0.15)
    return verts, faces


def build_six_face(image_paths, size=50, cols=40, spacing=6):
    verts, faces = [], []
    embed, min_h, max_h = 1.2, 0.3, 1.5
    add_core(verts, faces, size, embed)
    sp = max(2, spacing * cols // 80)
    for i, face in enumerate(FACE_NAMES):
        if i < len(image_paths):
            g = load_gray(image_paths[i], cols)
            field = line_density_field(g, sp)
        else:
            field = np.full((cols, cols), 0.1)
        add_face_from_field(verts, faces, face, field, size, embed, min_h, max_h)
    return verts, faces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["two_flip", "six_faces"], required=True)
    parser.add_argument("--images", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=float, default=50)
    parser.add_argument("--cols", type=int, default=48)
    args = parser.parse_args()

    if args.mode == "two_flip":
        verts, faces = build_two_flip(args.images[0], args.images[1], args.size, args.cols)
    else:
        verts, faces = build_six_face(args.images[:6], args.size, args.cols)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_stl(args.out, verts, faces)
    print(f"Wrote {args.out} ({len(faces)*2} tris)")


if __name__ == "__main__":
    main()
