# Entryway storage box — Bambu Studio print guide

Optimized for a **204 × 232 mm** functional organizer with **1.5 mm dividers** and **2 mm walls**.

## Recommended material

| Priority | Material | Why |
|----------|----------|-----|
| **1st** | **PETG** | Tougher dividers, less brittle when keys/cables hit walls, tolerates doorway heat/sun better than PLA |
| 2nd | PLA | Easier, matte look; OK if box stays indoors and is not loaded heavily |

Use **matte / opaque** colors (black, grey, beige) — hides scuffs at the entryway.

## Import presets (fastest)

1. Open **Bambu Studio**
2. **File → Import → Import Configs**
3. Select both JSON files for your material:
   - PETG: `bambu/entryway_box_process_petg.json` + `bambu/entryway_box_filament_petg.json`
   - PLA: `bambu/entryway_box_process_pla.json` + `bambu/entryway_box_filament_pla.json`
4. Choose presets **Entryway Box PETG @BBL X1C** (or PLA) in the slice panel
5. Import `output/entryway_storage_box.stl`, place **flat on the bed** (bottom face down)
6. Slice → print

If your printer profile differs (e.g. only A1 mini), change **Printer** to your machine; process/filament presets still apply.

## Optimized parameters (summary)

### Orientation & supports

| Setting | Value |
|---------|-------|
| Orientation | Bottom face on bed (largest flat side) |
| Supports | **Off** |
| Brim | **Auto brim 5 mm** (PETG) / **3 mm** (PLA) — reduces corner lift on large footprint |
| Skirt | 1 loop, 2 mm height |

### Quality & strength

| Setting | PETG | PLA | Notes |
|---------|------|-----|-------|
| Layer height | 0.20 mm | 0.20 mm | Good balance speed vs. divider quality |
| Line width | 0.42 mm | 0.42 mm | Slightly wider = stronger walls |
| Wall loops | 3 | 3 | Model already has 2 mm shells; loops bond layers |
| Top shells | 5 | 5 | Stiff rim |
| Bottom shells | **6** | **6** | Large flat base — resists flex when loaded |
| Infill | **18% gyroid** | **20% gyroid** | Strong multi-direction fill without long print |
| Thin wall detect | **On** | **On** | Critical for **1.5 mm** dividers |

### Temperatures

| | PETG | PLA |
|---|------|-----|
| Nozzle | 245 °C (first layer 250) | 220 °C (first layer 225) |
| Bed (textured PEI) | 78 °C (first 80) | 60 °C (first 65) |
| Part cooling | 40% max | 100% |

### Speed (stable large flat part)

| | Value |
|---|-------|
| First layer | 35 mm/s (PETG) / 40 mm/s (PLA) |
| Outer walls | 100 / 120 mm/s |
| Inner walls | 150 / 180 mm/s |
| Infill | 220 / 250 mm/s |
| Slow down if layer < 8 s | On |

### AMS / drying

- **PETG**: dry 6 h @ 65 °C if stringing; AMS OK
- **PLA**: AMS OK; avoid high humidity

## Expected print

| | Estimate |
|---|----------|
| Time | ~3.5–5 h (X1/P1, 0.4 mm nozzle) |
| Filament | ~180–220 g |
| Nozzle | **0.4 mm** standard (see 0.2 mm note below) |


## 0.2 mm nozzle (optional)

If dividers look weak or gaps appear:

- Use **0.2 mm nozzle** + **0.1 mm layers**
- Wall loops **4**, print speed **−30%**
- Divider quality improves; print time ~2×

## Manual checklist in Bambu Studio

- [ ] Object centered on bed (204 × 232 mm; with a 5 mm brim: about 214 × 242 mm)
- [ ] Fits **P1/P1S/X1/A1 (256 × 256 mm)** with 14 mm total margin on the tighter axis
- [ ] Does **not** fit **A1 mini (180 × 180 mm)**; use a split model for that printer
- [ ] **Detect thin walls** enabled (Process → Strength → Advanced)
- [ ] **Precise wall** on (better 1.5 mm dividers)
- [ ] No support material
- [ ] Brim on for first PETG print of this size
- [ ] Preview: dividers show as solid lines in layer view

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Corners lift | Increase brim to 8 mm; raise bed temp +2 °C; dry PETG |
| Dividers stringy / broken | Lower speed 20%; enable thin wall; try 0.2 mm nozzle |
| Bottom bows | Increase bottom shells to 8; raise infill to 22% |
| Too tight compartments | Re-generate with `--divider 1.2` (advanced) |
