THREE-AXIS VOLUMETRIC ROD PHOTO CUBE

Model: three_axis_rod_network.stl
Size: 50 x 50 x 50 mm
Nominal rod/voxel width: 1.25 mm
Images: X=01_photo.png, Y=04_photo.png, Z=05_photo.png

This trio is selected automatically from all six candidate photos by minimizing
the largest absolute pairwise correlation after target preprocessing.

Opposite viewpoints show mirrored versions of the same axis image. They are
not independent fourth, fifth, or sixth images.

Suggested starting point for Bambu P1S / 0.4 mm nozzle:
- 0.20 mm layer height
- 2 walls
- 100% infill (the STL already contains the intended voids)
- Arachne wall generator
- Inspect every layer in the slicer
- Use normal/tree supports for long horizontal members, or experimentally
  rotate the model. This network contains unavoidable bridges.

The model is a connected voxel-rod volume with no enclosing shell or hidden
solid core. See THREE_AXIS_ROD_NETWORK_VALIDATION.md and the three PNG files
for measured projection fidelity and limitations.
