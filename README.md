# Lenticular / depth-line photo cube (Bambu P1S)

Square cube where each face encodes a different photo as **connected vertical lines at continuous depth** (darker → deeper into the cube). No LED required.

## Latest print file

- `output/cube_connected_depth.stl` — 50 mm cube, 6 faces, connected depth lines  
- `output/cube_10mm_fulldepth.stl` — small 10 mm example  

## Preview

```bash
cd /path/to/lenticular-test
python3 -m http.server 8766
# open http://localhost:8766/viewer/
```

Photo vs line comparisons: `output/line_blank_faces/*_compare.png`

## Regenerate

```bash
python3 scripts/generate_connected_depth_lines.py \
  --images images/complex/01_photo.png images/complex/02_photo.png images/complex/03_photo.png \
           images/complex/04_photo.png images/complex/05_photo.png images/complex/06_photo.png \
  --out output/cube_connected_depth.stl --size 50 --lines 48 \
  --preview-dir output/line_blank_faces
```

## Aurora ellipse lampshade (floor lamp)

One-piece clip-on shade for ~13"×6" pill lamp heads (Govee Torchiere class).

```bash
python3 scripts/generate_aurora_shade.py --out output/aurora_ellipse_shade.stl
```

Print tips: black PLA, 0.2 mm layers, 3 walls, no supports (tabs print vertically). Slide down onto lamp head; pull up to remove.

Custom size (mm):

```bash
python3 scripts/generate_aurora_shade.py \
  --major 330 --minor 152 --clearance 102 --height 112 --seed 42 \
  --out output/aurora_ellipse_shade.stl
```

## Bambu tips

- 0.2 mm nozzle if available  
- 0.1 mm layers, white PLA, 100% infill  
- Print with one face flat on the bed  
