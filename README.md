# Lenticular / depth-line photo cube (Bambu P1S)

Square cube where each face encodes a different photo as **connected vertical lines at continuous depth** (darker → deeper into the cube). No LED required.

## Entryway storage box (sloped organizer)

Sloped organizer for letters, receipts, card wallets, power banks, cables,
earphones, and six essential-oil bottles.

```bash
python3 scripts/generate_entryway_storage_box.py
# -> output/entryway_storage_box.stl (205.5 x 232.75 mm, fits P1S)

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
send to the printer. Expect roughly **440–500 g** and **9–14 hours**; use the
slicer's estimate for your filament/profile.

**Print presets (optimized):** import `bambu/entryway_box_process_petg.json` + `bambu/entryway_box_filament_petg.json` (or PLA pair). Full guide: [`bambu/PRINT_GUIDE.md`](bambu/PRINT_GUIDE.md).

See `output/entryway_storage_box_spec.json` for compartment dimensions and `bambu_optimized` slice parameters.

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
