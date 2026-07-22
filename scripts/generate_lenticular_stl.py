#!/usr/bin/env python3
"""
Generate a 3D-printable lenticular flip block STL from two images.

Geometry: alternating vertical bars with sloped tops. Each bar pair forms a
lenticular ridge — the left slope encodes image A, the right slope image B.
Viewed from the left you mostly see A; from the right, B.
"""

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image


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


def build_lenticular_mesh(img_a, img_b, width_mm, height_mm, base_mm, min_ridge, max_ridge):
    rows, cols = img_a.shape
    period_w = width_mm / cols
    row_h = height_mm / rows

    verts = []
    faces = []

    def z_from(val):
        return base_mm + min_ridge + val * (max_ridge - min_ridge)

    for row in range(rows):
        y0 = row * row_h
        y1 = (row + 1) * row_h

        for col in range(cols):
            x0 = col * period_w
            xm = x0 + period_w * 0.5
            x1 = x0 + period_w

            za = z_from(img_a[row, col])
            zb = z_from(img_b[row, col])
            peak = base_mm + max_ridge + max(za - base_mm, zb - base_mm) * 0.35

            # Bottom quad (z = 0)
            bl = (x0, y0, 0.0)
            br = (x1, y0, 0.0)
            tl = (x0, y1, 0.0)
            tr = (x1, y1, 0.0)
            add_quad(verts, faces, bl, br, tr, tl)

            # Left slope (image A) — faces left
            add_quad(
                verts,
                faces,
                (x0, y0, 0.0),
                (xm, y0, peak),
                (xm, y1, peak),
                (x0, y1, 0.0),
            )

            # Right slope (image B) — faces right
            add_quad(
                verts,
                faces,
                (xm, y0, peak),
                (x1, y0, 0.0),
                (x1, y1, 0.0),
                (xm, y1, peak),
            )

            # Back ridge cap along peak
            add_quad(
                verts,
                faces,
                (xm, y0, peak),
                (xm, y1, peak),
                (xm, y1, za),
                (xm, y0, za),
            )

    return verts, faces


def write_binary_stl(path, verts, faces):
    triangles = []
    for i0, i1, i2 in faces:
        v0, v1, v2 = np.array(verts[i0]), np.array(verts[i1]), np.array(verts[i2])
        edge1 = v1 - v0
        edge2 = v2 - v0
        normal = np.cross(edge1, edge2)
        norm = np.linalg.norm(normal)
        if norm > 1e-9:
            normal = normal / norm
        else:
            normal = np.array([0.0, 0.0, 1.0])
        triangles.append((normal, v0, v1, v2))

    with open(path, "wb") as f:
        header = b"Lenticular test block - Bambu P1S" + b"\0" * (80 - 33)
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for normal, v0, v1, v2 in triangles:
            f.write(struct.pack("<3f", *normal))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))


def generate(image_a, image_b, output, cols=64, rows=64, width_mm=60.0, height_mm=60.0):
    img_a = load_grayscale(image_a, cols, rows)
    img_b = load_grayscale(image_b, cols, rows)

    base_mm = 1.2
    min_ridge = 0.3
    max_ridge = 1.8

    verts, faces = build_lenticular_mesh(
        img_a, img_b, width_mm, height_mm, base_mm, min_ridge, max_ridge
    )
    write_binary_stl(output, verts, faces)
    print(f"Wrote {output} ({len(faces) * 2} triangles, {width_mm}x{height_mm} mm)")


def main():
    root = Path(__file__).resolve().parent.parent
    images = root / "images"
    output = root / "output"

    parser = argparse.ArgumentParser()
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cols", type=int, default=64)
    parser.add_argument("--rows", type=int, default=64)
    parser.add_argument("--width", type=float, default=60.0)
    parser.add_argument("--height", type=float, default=60.0)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    generate(args.a, args.b, args.out, args.cols, args.rows, args.width, args.height)


if __name__ == "__main__":
    main()
