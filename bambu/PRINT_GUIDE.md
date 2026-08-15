# Entryway storage box — Bambu Studio print guide

Optimized for a **205.5 × 232.75 × 152 mm** functional organizer with
**1.5 mm dividers**, **2 mm outer walls**, and a **2 mm base**.

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

The full-size model fits P1/P1S/X1/A1. It **does not fit A1 mini**.

## Optimized parameters (summary)

### Orientation & supports

| Setting | Value |
|---------|-------|
| Orientation | Bottom face on bed (largest flat side) |
| Supports | **Off** |
| Brim | **Auto brim 5 mm** (PETG) / **3 mm** (PLA) — reduces corner lift on large footprint |
| Skirt | 1 loop, 2 mm height |

The front lip is a vertical continuation of the front wall, and all other
walls grow vertically from the base. There are no horizontal undersides above
the base, so supports add waste and leave marks without improving the print.

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
| Time | **~9–14 h** (P1S, 0.4 mm nozzle; confirm after slicing) |
| Filament | **~440–500 g** (about 460 g from solid model volume, before purge) |
| Nozzle | **0.4 mm** standard (see 0.2 mm note below) |

The STL's solid volume is about **365 cm³**. Bambu Studio's sliced estimate is
authoritative because speed, flow calibration, purge, and filament density vary.

## 0.2 mm nozzle (optional)

The 0.4 mm nozzle with Arachne/thin-wall detection should resolve the 1.5 mm
dividers. Only switch to 0.2 mm if layer preview shows missing divider lines:

- Use **0.2 mm nozzle** + **0.1 mm layers**
- Wall loops **4**, print speed **−30%**
- Divider quality improves; print time is more than 2×

## Manual checklist in Bambu Studio

- [ ] Object centered on bed (**205.5 × 232.75 mm**; with a 5 mm brim: **215.5 × 242.75 mm**)
- [ ] Fits **P1/P1S/X1/A1 (256 × 256 mm)** with **13.25 mm total** margin on the tighter axis
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

## Verified item envelope

These are design assumptions, not universal product dimensions. Measure unusually
large items before printing.

| Item | Verified usable space | Assumption |
|---|---:|---|
| Earphones / misc | 100 × 100 mm | Up to 90 × 90 mm footprint |
| Essential oils | 100 × 96.5 mm | Six Ø30 × 80 mm bottles, 3×2 |
| Receipts | 100 × 20.75 mm | Folded receipts |
| Card wallet 1 / 2 | 100 × 25 mm each | Up to 85.6 mm wide × 25 mm thick |
| Data cable | 100 × 24 mm | Shallow coiled cable bundle |
| Power banks | 100 × 71 mm | Two 110 × 80 × 30 mm units standing on 80 × 30 mm footprints |
| Letters | 200 × 29.25 mm | Up to 200 mm wide; A4/C5 does not fit unfolded |
