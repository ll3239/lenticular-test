#!/usr/bin/env python3
"""
One-piece elliptical clip-on aurora lampshade STL.

Opening ~13" x 6" (330 x 152 mm), inner clearance ~4" (102 mm).
Push down from above; four flexible tabs grip the lamp rim.
"""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

import numpy as np

DEFAULT_MAJOR_MM = 13.0 * 25.4
DEFAULT_MINOR_MM = 6.0 * 25.4
DEFAULT_CLEARANCE_MM = 4.0 * 25.4


def add_tri(verts: list, faces: list, a, b, c) -> None:
    i = len(verts)
    verts.extend([a, b, c])
    faces.append((i, i + 1, i + 2))


def add_quad(verts: list, faces: list, a, b, c, d) -> None:
    add_tri(verts, faces, a, b, c)
    add_tri(verts, faces, a, c, d)


def write_binary_stl(path: Path, verts: list, faces: list, header: str) -> None:
    hdr = header.encode("ascii", errors="ignore")[:80].ljust(80, b"\0")
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(struct.pack("<I", len(faces)))
        for i0, i1, i2 in faces:
            v0 = np.asarray(verts[i0], dtype=np.float64)
            v1 = np.asarray(verts[i1], dtype=np.float64)
            v2 = np.asarray(verts[i2], dtype=np.float64)
            n = np.cross(v1 - v0, v2 - v0)
            nn = np.linalg.norm(n)
            n = n / nn if nn > 1e-9 else np.array([0.0, 0.0, 1.0])
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))


def ellipse_r(a: float, b: float, theta: float) -> float:
    c, s = math.cos(theta), math.sin(theta)
    return (a * b) / math.sqrt(max((b * c) ** 2 + (a * s) ** 2, 1e-9))


def make_rays(seed: int, n: int = 18) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        out.append(
            {
                "a0": float(rng.uniform(0, 2 * math.pi)),
                "a1": float(rng.uniform(0.06, 0.16)),
                "r1": float(rng.uniform(0.55, 1.0)),
            }
        )
    out.sort(key=lambda r: r["a0"])
    return out


def build_body(
    verts: list,
    faces: list,
    major: float,
    minor: float,
    height: float,
    wall: float,
    clearance: float,
    flare: float,
    nz: int,
    ntheta: int,
) -> None:
    outer_a = major / 2 + wall
    outer_b = minor / 2 + wall
    inner_a = major / 2 - 0.8
    inner_b = minor / 2 - 0.8
    dome_z = max(clearance * 0.72, height * 0.58)

    og = [[None] * (ntheta + 1) for _ in range(nz + 1)]
    ig = [[None] * (ntheta + 1) for _ in range(nz + 1)]

    for iz in range(nz + 1):
        z = height * iz / nz
        dh = 0.0 if z <= dome_z else 1.0 - (1.0 - (z - dome_z) / max(height - dome_z, 1e-6)) ** 2
        osf = 1.0 + flare * dh
        isf = 1.0 - 0.05 * dh
        for it in range(ntheta + 1):
            th = 2 * math.pi * it / ntheta
            c, s = math.cos(th), math.sin(th)
            ox, oy = outer_a * osf * c, outer_b * osf * s
            ix, iy = inner_a * isf * c, inner_b * isf * s
            og[iz][it] = len(verts)
            verts.append((ox, oy, z))
            ig[iz][it] = len(verts)
            verts.append((ix, iy, max(0.0, z - wall * 0.2)))

    for iz in range(nz):
        for it in range(ntheta):
            o00, o01 = og[iz][it], og[iz][it + 1]
            o10, o11 = og[iz + 1][it], og[iz + 1][it + 1]
            add_quad(verts, faces, verts[o00], verts[o10], verts[o11], verts[o01])
            i00, i01 = ig[iz][it], ig[iz][it + 1]
            i10, i11 = ig[iz + 1][it], ig[iz + 1][it + 1]
            add_quad(verts, faces, verts[i00], verts[i01], verts[i11], verts[i10])

    for it in range(ntheta):
        add_quad(
            verts,
            faces,
            verts[ig[0][it]],
            verts[ig[0][it + 1]],
            verts[og[0][it + 1]],
            verts[og[0][it]],
        )


def build_aurora_top_wedges(
    verts: list,
    faces: list,
    major: float,
    minor: float,
    z0: float,
    wall: float,
    rays: list[dict],
) -> None:
    outer_a = major / 2 + wall * 1.2
    outer_b = minor / 2 + wall * 1.2
    inner_a = major / 2 - 0.8
    inner_b = minor / 2 - 0.8
    z1 = z0 + wall
    two_pi = 2 * math.pi
    n = len(rays)

    for i, ray in enumerate(rays):
        nxt = rays[(i + 1) % n]
        a_start = (ray["a0"] + ray["a1"] * 0.45) % two_pi
        a_end = (nxt["a0"] - nxt["a1"] * 0.45) % two_pi
        if a_end <= a_start:
            a_end += two_pi

        steps = 6
        angs = [a_start + (a_end - a_start) * j / steps for j in range(steps + 1)]
        r_frac = 0.5 * (ray["r1"] + nxt["r1"])

        for j in range(steps):
            th0, th1 = angs[j], angs[j + 1]
            thm = 0.5 * (th0 + th1)
            ro0 = ellipse_r(outer_a, outer_b, th0 % two_pi)
            ro1 = ellipse_r(outer_a, outer_b, th1 % two_pi)
            rm = ellipse_r(outer_a, outer_b, thm % two_pi) * r_frac
            ri = max(inner_a, inner_b) * 0.22

            def p(r, th, z):
                t = th % two_pi
                return (r * math.cos(t), r * math.sin(t), z)

            ot0, ot1, otm = p(ro0, th0, z1), p(ro1, th1, z1), p(rm, thm, z1)
            ob0, ob1, obm = p(ro0, th0, z0), p(ro1, th1, z0), p(rm, thm, z0)
            it0, it1, itm = p(ri, th0, z1), p(ri, th1, z1), p(ri * (0.4 + 0.6 * r_frac), thm, z1)
            ib0, ib1, ibm = p(ri, th0, z0), p(ri, th1, z0), p(ri * (0.4 + 0.6 * r_frac), thm, z0)

            add_quad(verts, faces, ot0, otm, itm, it0)
            add_quad(verts, faces, otm, ot1, it1, itm)
            add_quad(verts, faces, ot0, it0, ib0, ob0)
            add_quad(verts, faces, ot1, it1, ib1, ob1)
            add_quad(verts, faces, otm, ot1, ob1, obm)
            add_quad(verts, faces, itm, it1, ib1, ibm)
            add_quad(verts, faces, otm, obm, ibm, itm)

    ri = max(inner_a, inner_b) * 0.12
    ro = ri + wall

    def p(r, th, z):
        return (r * math.cos(th), r * math.sin(th), z)

    for k in range(16):
        th0 = 2 * math.pi * k / 16
        th1 = 2 * math.pi * (k + 1) / 16
        add_quad(verts, faces, p(ro, th0, z1), p(ro, th1, z1), p(ro, th1, z0), p(ro, th0, z0))
        add_quad(verts, faces, p(ri, th0, z0), p(ri, th1, z0), p(ri, th1, z1), p(ri, th0, z1))


def build_solid_ribs(
    verts: list,
    faces: list,
    major: float,
    minor: float,
    z0: float,
    wall: float,
    rays: list[dict],
    steps: int = 5,
) -> None:
    outer_a = major / 2 + wall * 1.2
    outer_b = minor / 2 + wall * 1.2
    inner_a = major / 2 - 0.8
    inner_b = minor / 2 - 0.8
    z1 = z0 + wall
    two_pi = 2 * math.pi

    for ray in rays:
        a0 = ray["a0"]
        half = ray["a1"] * 0.45
        angs = [a0 - half + (2 * half) * j / steps for j in range(steps + 1)]
        for j in range(steps):
            th0, th1 = angs[j] % two_pi, angs[j + 1] % two_pi

            def p(r, th, z):
                return (r * math.cos(th), r * math.sin(th), z)

            ro0 = ellipse_r(outer_a, outer_b, th0)
            ro1 = ellipse_r(outer_a, outer_b, th1)
            ri0 = ellipse_r(inner_a, inner_b, th0)
            ri1 = ellipse_r(inner_a, inner_b, th1)
            add_quad(verts, faces, p(ro0, th0, z1), p(ro1, th1, z1), p(ro1, th1, z0), p(ro0, th0, z0))
            add_quad(verts, faces, p(ri0, th0, z0), p(ri1, th1, z0), p(ri1, th1, z1), p(ri0, th0, z1))


def build_clip_tabs(
    verts: list,
    faces: list,
    major: float,
    minor: float,
    tab_h: float,
    tab_w: float,
    tab_t: float,
    hook: float,
) -> None:
    a = major / 2
    b = minor / 2
    for k in range(4):
        th = 2 * math.pi * k / 4 + math.pi / 8
        cx, cy = a * math.cos(th), b * math.sin(th)
        nx = -math.cos(th) / max(a, 1e-6)
        ny = -math.sin(th) / max(b, 1e-6)
        nl = math.hypot(nx, ny)
        nx, ny = nx / nl, ny / nl
        tx, ty = -ny, nx
        hw = tab_w * 0.5

        def corner(sx, sz):
            return (cx + tx * sx + nx * tab_t, cy + ty * sx + ny * tab_t, sz)

        b0, b1 = corner(-hw, 0), corner(hw, 0)
        t0, t1 = corner(-hw, tab_h), corner(hw, tab_h)
        h0 = (cx + nx * (tab_t - hook) + tx * (-hw * 0.65), cy + ny * (tab_t - hook) + ty * (-hw * 0.65), tab_h * 0.55)
        h1 = (cx + nx * (tab_t - hook) + tx * (hw * 0.65), cy + ny * (tab_t - hook) + ty * (hw * 0.65), tab_h * 0.55)
        add_quad(verts, faces, b0, b1, t1, t0)
        add_quad(verts, faces, t0, t1, h1, h0)
        add_quad(verts, faces, h0, h1, b1, b0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("output/aurora_ellipse_shade.stl"))
    ap.add_argument("--major", type=float, default=DEFAULT_MAJOR_MM)
    ap.add_argument("--minor", type=float, default=DEFAULT_MINOR_MM)
    ap.add_argument("--height", type=float, default=112.0)
    ap.add_argument("--clearance", type=float, default=DEFAULT_CLEARANCE_MM)
    ap.add_argument("--wall", type=float, default=1.6)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    verts: list = []
    faces: list = []
    rays = make_rays(args.seed)

    build_body(verts, faces, args.major, args.minor, args.height, args.wall, args.clearance, 0.08, 44, 72)
    build_aurora_top_wedges(verts, faces, args.major, args.minor, args.height, args.wall, rays)
    build_solid_ribs(verts, faces, args.major, args.minor, args.height, args.wall, rays)
    build_clip_tabs(verts, faces, args.major, args.minor, 14.0, 16.0, 1.4, 1.8)

    write_binary_stl(
        args.out,
        verts,
        faces,
        header=f"Aurora ellipse shade {args.major:.0f}x{args.minor:.0f}mm",
    )
    print(f"Wrote {args.out} ({len(faces)} triangles)")


if __name__ == "__main__":
    main()
