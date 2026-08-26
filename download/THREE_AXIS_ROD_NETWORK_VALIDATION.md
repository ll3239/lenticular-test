# Three-axis rod-network validation

**Result: PASS**

- Actual STL SHA-256: `7e86f8907554161aa8a46234ae50aa6b9568231bc769e4faf04802e7b57d9afd`
- Watertight / mesh components: `True` / `1`
- Reconstructed volume / fraction: `36830.1 mm³` / `0.2946` (void `0.7054`)
- Rod width: `1.25 mm`; triangles: `71264`
- Center X/Y/Z slice occupancy: `{'x': 0.31125, 'y': 0.360625, 'z': 0.38125}`

| Axis | Own r | MAE | Cross-talk margin | Comparison |
|---|---:|---:|---:|---|
| X | 0.734 | 0.192 | 0.739 | `output/three_axis_rod_network_projections/axis_x.png` |
| Y | 0.673 | 0.193 | 0.238 | `output/three_axis_rod_network_projections/axis_y.png` |
| Z | 0.807 | 0.105 | 0.755 | `output/three_axis_rod_network_projections/axis_z.png` |

Opposite faces are mirrored views of the same axis projection, not extra images.

## Method

Occupancy is reconstructed from oriented, axis-aligned faces in the actual STL. Projections and connectivity use that reconstruction, not generator state.

## Honest limitations

- A binary single-material object cannot reproduce three arbitrary grayscale images exactly; these are jointly optimized low-resolution density projections.
- The default trio 01/04/05 was selected from all six photos because its largest absolute pairwise preprocessed-target correlation is below 0.177. The complete six-photo selection matrix is recorded in this report.
- Projection validation measures line-integral occupancy, not a calibrated optical render. Real appearance depends on filament, lighting, and background.
- Voxel rods are 1.25 mm at default settings, printable with a 0.4 mm nozzle, but many bridges run horizontally; use supports or rotate and inspect the slicer.
- Axis-aligned scan conversion is specific to this voxel STL representation; it is not a general-purpose occupancy test for arbitrary meshes.
