#!/usr/bin/env python3
"""
Convert photos into line-screen paintings (vertical / horizontal / cross weave).

Not photographic textures — images are rebuilt from black lines only:
  - Vertical lines: thickness follows local darkness of photo A
  - Horizontal lines: thickness follows local darkness of photo B
  - Cross weave: both on one canvas (the "line combo" art)
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps


def load_gray(path, size, contrast=1.6):
    img = Image.open(path).convert("L")
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = img.resize((size, size), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0


def line_screen_vertical(gray, spacing=8):
    """Rebuild photo using only vertical lines of varying thickness."""
    h, w = gray.shape
    out = Image.new("RGB", (w, h), (250, 248, 240))
    px = out.load()
    ink = (12, 12, 16)
    max_thick = max(1, spacing - 1)

    for x in range(0, w, spacing):
        for y in range(h):
            # sample local darkness
            x1 = min(x + spacing, w)
            dark = 1.0 - float(np.mean(gray[y, x:x1]))
            thick = max(1, int(round(dark * max_thick)))
            x0 = x + (spacing - thick) // 2
            for t in range(thick):
                xx = min(x0 + t, w - 1)
                px[xx, y] = ink
    return out


def line_screen_horizontal(gray, spacing=8):
    """Rebuild photo using only horizontal lines of varying thickness."""
    h, w = gray.shape
    out = Image.new("RGB", (w, h), (250, 248, 240))
    px = out.load()
    ink = (12, 12, 16)
    max_thick = max(1, spacing - 1)

    for y in range(0, h, spacing):
        for x in range(w):
            y1 = min(y + spacing, h)
            dark = 1.0 - float(np.mean(gray[y:y1, x]))
            thick = max(1, int(round(dark * max_thick)))
            y0 = y + (spacing - thick) // 2
            for t in range(thick):
                yy = min(y0 + t, h - 1)
                px[x, yy] = ink
    return out


def compose_cross_lines(img_a, img_b, spacing=8):
    """
    Line combo: vertical lines from A + horizontal lines from B on one canvas.
    Looking left/right favors vertical (A); up/down favors horizontal (B).
    """
    h, w = img_a.shape
    out = Image.new("RGB", (w, h), (250, 248, 240))
    px = out.load()
    ink = (12, 12, 16)
    max_thick = max(1, spacing - 1)

    # Vertical from image A
    for x in range(0, w, spacing):
        for y in range(h):
            x1 = min(x + spacing, w)
            dark = 1.0 - float(np.mean(img_a[y, x:x1]))
            thick = max(1, int(round(dark * max_thick)))
            x0 = x + (spacing - thick) // 2
            for t in range(thick):
                xx = min(x0 + t, w - 1)
                px[xx, y] = ink

    # Horizontal from image B (overlaid)
    for y in range(0, h, spacing):
        for x in range(w):
            y1 = min(y + spacing, h)
            dark = 1.0 - float(np.mean(img_b[y:y1, x]))
            thick = max(1, int(round(dark * max_thick)))
            y0 = y + (spacing - thick) // 2
            for t in range(thick):
                yy = min(y0 + t, h - 1)
                px[x, yy] = ink

    return out


def face_cross_self(gray, spacing=8):
    """One photo as its own cross-line painting (V + H of same image)."""
    return compose_cross_lines(gray, gray, spacing)


def generate_all(images_dir, out_dir, size=512, spacing=8):
    images_dir = Path(images_dir)
    out_dir = Path(out_dir)
    faces_dir = out_dir / "lineart_faces"
    faces_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(images_dir.glob("*_photo.png"))
    if len(paths) < 6:
        raise SystemExit(f"Need 6 photos in {images_dir}, found {len(paths)}")

    grays = [load_gray(p, size) for p in paths[:6]]

    # 6 faces: each photo as vertical+horizontal line combo of itself
    for i, g in enumerate(grays):
        n = f"{i+1:02d}"
        line_screen_vertical(g, spacing).save(faces_dir / f"{n}_vertical.png")
        line_screen_horizontal(g, spacing).save(faces_dir / f"{n}_horizontal.png")
        face_cross_self(g, spacing).save(faces_dir / f"{n}_cross.png")
        print(f"  face {n}: vertical / horizontal / cross")

    # Pair demos: A vertical + B horizontal woven
    pair_dir = out_dir / "lineart_pair1"
    pair_dir.mkdir(parents=True, exist_ok=True)
    line_screen_vertical(grays[0], spacing).save(pair_dir / "A_vertical_lines.png")
    line_screen_horizontal(grays[1], spacing).save(pair_dir / "B_horizontal_lines.png")
    compose_cross_lines(grays[0], grays[1], spacing).save(pair_dir / "cross_composed.png")
    print(f"Wrote faces → {faces_dir}")
    print(f"Wrote pair demo → {pair_dir}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    generate_all(root / "images" / "complex", root / "output", size=512, spacing=8)
