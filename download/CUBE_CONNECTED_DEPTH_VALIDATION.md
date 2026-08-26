# Connected depth-line cube validation

**Result: PASS**

- Watertight: `True`
- Connected components / bodies: `1` / `1`
- Matches deterministic encoded mesh: `True`
- Extents: `[50.0, 50.0, 50.0]` mm
- Triangles: `750000`

- Pitch / separator / groove: `1.00` / `0.40` / `0.60` mm

| Face | Depth r | Depth MAE | Render r | Render MAE | Preview |
|---|---:|---:|---:|---:|---|
| front | 0.9896 | 0.0153 | 0.9681 | 0.0691 | `output/cube_connected_depth_previews/front.png` |
| back | 0.9913 | 0.0115 | 0.9613 | 0.0734 | `output/cube_connected_depth_previews/back.png` |
| right | 0.9896 | 0.0144 | 0.9708 | 0.0637 | `output/cube_connected_depth_previews/right.png` |
| left | 0.9924 | 0.0112 | 0.9559 | 0.0870 | `output/cube_connected_depth_previews/left.png` |
| top | 0.9983 | 0.0035 | 0.9582 | 0.0644 | `output/cube_connected_depth_previews/top.png` |
| bottom | 0.9731 | 0.0162 | 0.8897 | 0.0952 | `output/cube_connected_depth_previews/bottom.png` |

Acceptance requires depth r >= 0.90, depth MAE <= 0.15, rendered-light r >= 0.85, and rendered-light exposure-aligned MAE <= 0.10 on every face. The single global linear exposure/black-level fit does not alter spatial content. Render metrics compare the line-decoded self-shadow render with the source at the same bandwidth. Rays use fixed local direction `[-1, 0, 0.75]`; Lambert response, ambient light, and channel occlusion are included.

Print caveat: The bottom face retains its image mapping, but it is against the print bed in the default orientation; bed texture and first-layer limits reduce visibility.

Limitations:
- Lighting direction is fixed in each face's local coordinates; one world-space lamp cannot illuminate all six differently oriented faces at this same angle.
- The renderer models directional Lambert light, ambient fill, and heightfield occlusion, but not printer-layer stair stepping, scattering, gloss, or interreflection.
- The 0.4 mm separator is exactly one nominal 0.4 mm nozzle width; slicer line-width policy, XY compensation, and printer calibration can materially change it.
