#!/usr/bin/env python3
"""Generate 4 simple mock images for lenticular testing."""

from pathlib import Path
from PIL import Image, ImageDraw

SIZE = 256
OUT = Path(__file__).resolve().parent.parent / "images"


def make_image(bg, shape_fn, name):
    img = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(img)
    shape_fn(draw)
    path = OUT / name
    img.save(path)
    print(f"  {path}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    margin = 48

    make_image(
        "#E53935",
        lambda d: d.ellipse([margin, margin, SIZE - margin, SIZE - margin], fill="white"),
        "01_red_circle.png",
    )
    make_image(
        "#1E88E5",
        lambda d: d.rectangle([margin, margin, SIZE - margin, SIZE - margin], fill="white"),
        "02_blue_square.png",
    )
    make_image(
        "#43A047",
        lambda d: d.polygon(
            [(SIZE // 2, margin), (SIZE - margin, SIZE - margin), (margin, SIZE - margin)],
            fill="white",
        ),
        "03_green_triangle.png",
    )
    cx, cy = SIZE // 2, SIZE // 2
    r_outer, r_inner = 90, 36
    make_image(
        "#FDD835",
        lambda d: d.polygon(
            [
                (cx, cy - r_outer),
                (cx + r_inner * 0.95, cy - r_inner * 0.31),
                (cx + r_outer * 0.59, cy + r_outer * 0.81),
                (cx - r_inner * 0.59, cy - r_inner * 0.81),
                (cx + r_inner * 0.59, cy - r_inner * 0.81),
                (cx - r_outer * 0.59, cy + r_outer * 0.81),
                (cx - r_inner * 0.95, cy - r_inner * 0.31),
            ],
            fill="white",
        ),
        "04_yellow_star.png",
    )


if __name__ == "__main__":
    main()
