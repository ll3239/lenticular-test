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

## Aurora clip-on lampshade (floor lamp)

Removable capsule/ellipse shade for ~13"×6" pill lamp heads (Govee
Torchiere class). The generator validates watertight geometry and creates:

- assembled reference STL
- left/right halves already oriented with the seam on the print bed
- low-filament fit-test ring and printable left/right fit-test halves

```bash
python3 -m pip install -r requirements.txt
python3 scripts/generate_aurora_shade.py --out output/aurora_ellipse_shade.stl
```

For a 256 mm bed, print `*_left.stl` and `*_right.stl`, then glue the flat
center seam. Print the two `aurora_fit_test_ring_*.stl` files first and tape
them together temporarily to check the fit before committing to the full
shade.

Print tips: black PLA, 0.2 mm layers, 3 walls, no supports. Slide the assembled
shade down over the lamp head; pull upward to remove.

Custom size (mm):

```bash
python3 scripts/generate_aurora_shade.py \
  --length 330 --width 152 --height 110 \
  --clearance 1.2 --grip 0.5 --seed 42 \
  --out output/aurora_ellipse_shade.stl
```

`--length` and `--width` are the exact black-rim dimensions. `--clearance`
adds room around that measurement; `--grip` controls the four inward friction
pads.

## Bambu tips

- 0.2 mm nozzle if available  
- 0.1 mm layers, white PLA, 100% infill  
- Print with one face flat on the bed  
