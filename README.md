# Lenticular / depth-line photo cube & Bambu P1S prints

Three printable projects in one repo:

1. **Depth-line photo cube** — six faces, connected vertical ribbons at continuous depth  
2. **Entryway storage box** — sloped organizer for mail, cables, power banks, and essentials  
3. **Aurora clip-on lampshade** — elliptical capsule shade for pill-shaped floor lamps  

## Depth-line photo cube

Square cube where each face encodes a different photo as **connected vertical lines at continuous depth** (darker → deeper into the cube). No LED required.

## Entryway storage box (sloped organizer)

Sloped organizer for letters, receipts, card wallets, power banks, cables,
earphones, and six essential-oil bottles.

```bash
python3 scripts/generate_entryway_storage_box.py
# -> output/entryway_storage_box.stl (206 x 233 mm, fits P1S)

# All 6 visual style variants:
python3 scripts/generate_entryway_storage_box.py --all-styles
# -> output/styles/entryway_box_*.stl

# Single style:
python3 scripts/generate_entryway_storage_box.py --style rounded --out output/my_box.stl
```

**Preview styles in browser:**

```bash
bash scripts/serve_preview.sh
# Computer: http://127.0.0.1:8766/viewer/entryway.html
# Phone (same WiFi): http://192.168.x.x:8766/viewer/entryway.html
```

**Phone tips:** use `serve_preview.sh` (binds `0.0.0.0`). Phone and PC must share WiFi. One finger = rotate, two fingers = zoom/pan.

**Screenshot gallery (works on phone — no 3D needed):**

```bash
python3 scripts/render_entryway_previews.py --all-angles
bash scripts/serve_preview.sh
# Phone: http://192.168.x.x:8766/viewer/gallery.html
```

Key images: `output/previews/compare_all_iso.png` · `compare_all_top.png` · `compare_all_side.png`

| Style | 中文 | 特点 |
|-------|------|------|
| `minimal` | 极简直角 | 干净北欧风，打印最快 |
| `rounded` | 圆角柔和 | 圆角底 + 柔化顶边 |
| `chamfer` | 倒角线框 | 顶部斜切，设计师感 |
| `tiered` | 阶梯分层 | 外壁分段台边 |
| `wells` | 精油定位环 | 6 个圆形瓶位环 |
| `accent` | 双槽装饰 | 圆角 + 侧面装饰槽 |

Open the STL in **Bambu Studio** (File → Import), place the bottom flat on
the bed, keep **supports off**, add a 5 mm PETG brim (3 mm PLA), slice, and
send to the printer. Expect roughly **470–530 g** and **10–15 hours**; use the
slicer's estimate for your filament/profile.

**Print presets (optimized):** import `bambu/entryway_box_process_petg.json` + `bambu/entryway_box_filament_petg.json` (or PLA pair). Full guide: [`bambu/PRINT_GUIDE.md`](bambu/PRINT_GUIDE.md).

See `output/entryway_storage_box_spec.json` for compartment dimensions and `bambu_optimized` slice parameters.

## Latest print file

- `output/three_axis_rod_network.stl` — 50 mm volumetric line network, 3 independent photo projections (X/Y/Z)
- `output/cube_connected_depth.stl` — 50 mm cube, 6 faces, connected depth lines  
- `output/cube_10mm_fulldepth.stl` — small 10 mm example  

### Three-axis volumetric line cube

This is the non-solid concept: the whole cube volume is a connected network
of 1.25 mm rods/voxels with no enclosing shell or hidden solid core. Three
independent photos are reconstructed when viewed along X, Y, and Z; opposite
faces show mirrored versions of those same three projections.

```bash
python3 scripts/generate_three_axis_rod_network.py
python3 scripts/validate_three_axis_rod_network.py
```

The default generator evaluates all six candidate photos and selects a
low-correlation trio so the projections remain distinguishable. Validation
reconstructs occupancy from the exported STL itself. See
`output/THREE_AXIS_ROD_NETWORK_VALIDATION.md`.

This model is a print prototype: horizontal members require careful slicer
inspection and will likely need substantial supports.

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
  --out output/cube_connected_depth.stl --size 50 --lines 50

python3 scripts/validate_connected_depth_cube.py \
  --mesh output/cube_connected_depth.stl \
  --images images/complex/01_photo.png images/complex/02_photo.png images/complex/03_photo.png \
           images/complex/04_photo.png images/complex/05_photo.png images/complex/06_photo.png \
  --preview-dir output/cube_connected_depth_previews \
  --report-json output/cube_connected_depth_validation.json \
  --report-md output/CUBE_CONNECTED_DEPTH_VALIDATION.md
```

The validator requires a 50 × 50 × 50 mm watertight, single-body mesh and
checks every face against a deterministic fixed-angle light simulation with
line-channel self-shadowing. See `output/CUBE_CONNECTED_DEPTH_VALIDATION.md`.

The six images use the local light direction relative to each viewed face.
Rotate the cube (or move the light) to reproduce that incidence angle. The
bottom image is encoded, but bed contact makes it the least reliable face.

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
