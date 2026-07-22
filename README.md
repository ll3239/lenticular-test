# Lenticular / depth-line photo cube (Bambu P1S)

Square cube where each face encodes a different photo as **connected vertical lines at continuous depth** (darker → deeper into the cube). No LED required.

## Entryway storage box (sloped organizer)

Hand-sketched layout: letters / keys / cards / receipts / power banks / cables / earphones + oils.

```bash
python3 scripts/generate_entryway_storage_box.py
# -> output/entryway_storage_box.stl  (~204 x 214 mm footprint, fits Bambu bed)
# -> output/entryway_storage_box_spec.json
```

Open the STL in **Bambu Studio** (File → Import), place flat on the bed, slice, and send to the printer. See spec JSON for compartment depths and assumed item sizes.

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

## Bambu tips

- 0.2 mm nozzle if available  
- 0.1 mm layers, white PLA, 100% infill  
- Print with one face flat on the bed  
