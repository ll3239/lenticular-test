#!/usr/bin/env python3
"""Validate an exported three-axis rod-network STL by reconstructing its voxels."""

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

from generate_three_axis_rod_network import (
    AXES, load_target, projections, select_default_images,
)


def corr(a, b):
    a, b = np.asarray(a).ravel(), np.asarray(b).ravel()
    a, b = a - a.mean(), b - b.mean()
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / d) if d else 0.0


def fit(rendered, target):
    x, y = rendered.ravel(), target.ravel()
    a, b = np.linalg.lstsq(np.column_stack((x, np.ones_like(x))), y, rcond=None)[0]
    adjusted = np.clip(a * rendered + b, 0, 1)
    return adjusted, float(np.mean(np.abs(adjusted - target)))


def reconstruct_boundary_voxels(mesh, n, cell):
    """Reconstruct solid cells by scan-converting oriented STL boundary faces."""
    recovered = np.zeros((n, n, n), dtype=bool)
    centroids = mesh.triangles_center
    normals = mesh.face_normals
    events = {}
    for center, normal in zip(centroids, normals):
        axis = int(np.argmax(np.abs(normal)))
        if abs(normal[axis]) < 0.999:
            raise ValueError("STL has non-axis-aligned triangles")
        if axis != 0:
            continue
        plane = int(round(center[0] / cell))
        y = min(n - 1, int(center[1] / cell))
        z = min(n - 1, int(center[2] / cell))
        events.setdefault((y, z, plane), set()).add(int(np.sign(normal[0])))
    for y in range(n):
        for z in range(n):
            inside = False
            for plane in range(n + 1):
                signs = events.get((y, z, plane), ())
                if 1 in signs:
                    inside = False
                if -1 in signs:
                    inside = True
                if plane < n and inside:
                    recovered[plane, y, z] = True
    return recovered


def component_count(occ):
    unseen = set(map(tuple, np.argwhere(occ))); count = 0
    while unseen:
        count += 1; queue = deque([unseen.pop()])
        while queue:
            p = queue.popleft()
            for axis in range(3):
                for delta in (-1, 1):
                    q = list(p); q[axis] += delta; q = tuple(q)
                    if q in unseen:
                        unseen.remove(q); queue.append(q)
    return count


def comparison(target, projection, path, axis):
    adjusted, mae = fit(projection / projection.max(), target)
    error = np.abs(adjusted - target)
    panels = [target, adjusted, error]
    canvas = Image.new("RGB", (900, 330), "#17191f")
    draw = ImageDraw.Draw(canvas)
    for i, array in enumerate(panels):
        image = Image.fromarray(np.uint8(np.clip(array, 0, 1) * 255), "L")
        image = image.resize((300, 300), Image.Resampling.NEAREST).convert("RGB")
        canvas.paste(image, (i * 300, 30))
    draw.text((8, 8), f"{axis} target", fill="white")
    draw.text((308, 8), f"{axis} actual STL projection", fill="white")
    draw.text((608, 8), f"absolute error (MAE {mae:.3f})", fill="white")
    canvas.save(path)
    return adjusted, mae


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mesh", type=Path, default=Path("output/three_axis_rod_network.stl"))
    p.add_argument("--images", nargs=3, type=Path)
    p.add_argument("--preview-dir", type=Path,
                   default=Path("output/three_axis_rod_network_projections"))
    p.add_argument("--report-json", type=Path,
                   default=Path("output/three_axis_rod_network_validation.json"))
    p.add_argument("--report-md", type=Path,
                   default=Path("output/THREE_AXIS_ROD_NETWORK_VALIDATION.md"))
    p.add_argument("--size", type=float, default=50.0)
    p.add_argument("--resolution", type=int, default=40)
    args = p.parse_args()
    selected_matrix = None
    if args.images is None:
        args.images, selected_matrix = select_default_images(args.resolution)
    mesh = trimesh.load_mesh(args.mesh, process=True)
    cell = args.size / args.resolution
    occ = reconstruct_boundary_voxels(mesh, args.resolution, cell)
    actual = projections(occ)
    targets = tuple(load_target(path, args.resolution) for path in args.images)
    args.preview_dir.mkdir(parents=True, exist_ok=True)
    axis_results = []
    for i, axis in enumerate(AXES):
        adjusted, mae = comparison(targets[i], actual[i],
                                   args.preview_dir / f"axis_{axis.lower()}.png", axis)
        correlations = [corr(adjusted, t) for t in targets]
        others = [x for j, x in enumerate(correlations) if j != i]
        axis_results.append({
            "axis": axis, "image": str(args.images[i]),
            "pearson_to_own_target": correlations[i],
            "exposure_aligned_mae": mae,
            "pearson_to_other_targets": others,
            "crosstalk_margin": correlations[i] - max(others),
            "projection_min_max_voxels": [int(actual[i].min()), int(actual[i].max())],
            "preview": str(args.preview_dir / f"axis_{axis.lower()}.png"),
        })
    center = args.resolution // 2
    center_slices = {
        "x": float(occ[center].mean()), "y": float(occ[:, center].mean()),
        "z": float(occ[:, :, center].mean()),
    }
    topology = {
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "mesh_components": len(mesh.split(only_watertight=False)),
        "reconstructed_voxel_components": component_count(occ),
        "extents_mm": mesh.extents.tolist(), "triangles": len(mesh.faces),
        "sha256": hashlib.sha256(args.mesh.read_bytes()).hexdigest(),
    }
    structure = {
        "resolution": args.resolution, "rod_width_mm": cell,
        "reconstructed_occupied_voxels": int(occ.sum()),
        "volume_mm3": float(occ.sum() * cell ** 3),
        "volume_fraction": float(occ.mean()),
        "void_fraction": float(1 - occ.mean()),
        "center_slice_occupancy_fraction": center_slices,
        "occupancy_reconstruction": "oriented X-face scan conversion of actual STL",
        "opposite_views": "same projection mirrored; only X, Y, Z are independent",
    }
    passed = (
        topology["watertight"] and topology["winding_consistent"]
        and topology["mesh_components"] == 1
        and topology["reconstructed_voxel_components"] == 1
        and max(abs(np.asarray(mesh.extents) - args.size)) < 1e-4
        and cell >= 0.45 and structure["volume_fraction"] < 0.35
        and all(v > 0 for v in center_slices.values())
        and all(x["pearson_to_own_target"] >= 0.65 for x in axis_results)
        and all(x["exposure_aligned_mae"] <= 0.20 for x in axis_results)
        and all(x["crosstalk_margin"] >= 0.03 for x in axis_results)
    )
    report = {
        "passed": bool(passed), "method": (
            "Occupancy is reconstructed from oriented, axis-aligned faces in the actual "
            "STL. Projections and connectivity use that reconstruction, not generator state."),
        "topology": topology, "structure": structure, "axes": axis_results,
        "target_intercorrelation": [[corr(a, b) for b in targets] for a in targets],
        "all_six_target_intercorrelation": selected_matrix,
        "automatic_selection": [str(path) for path in args.images],
        "thresholds": {"own_pearson_min": 0.65, "exposure_aligned_mae_max": 0.20,
                       "crosstalk_margin_min": 0.03, "mesh_components": 1,
                       "volume_fraction_max": 0.35, "minimum_feature_mm": 0.45},
        "limitations": [
            "A binary single-material object cannot reproduce three arbitrary grayscale "
            "images exactly; these are jointly optimized low-resolution density projections.",
            "The default trio 01/04/05 was selected from all six photos because its largest "
            "absolute pairwise preprocessed-target correlation is below 0.177. The complete "
            "six-photo selection matrix is recorded in this report.",
            "Projection validation measures line-integral occupancy, not a calibrated optical "
            "render. Real appearance depends on filament, lighting, and background.",
            "Voxel rods are 1.25 mm at default settings, printable with a 0.4 mm nozzle, but "
            "many bridges run horizontally; use supports or rotate and inspect the slicer.",
            "Axis-aligned scan conversion is specific to this voxel STL representation; it is "
            "not a general-purpose occupancy test for arbitrary meshes.",
        ],
    }
    args.report_json.write_text(json.dumps(report, indent=2) + "\n")
    rows = "\n".join(
        f"| {x['axis']} | {x['pearson_to_own_target']:.3f} | "
        f"{x['exposure_aligned_mae']:.3f} | {x['crosstalk_margin']:.3f} | `{x['preview']}` |"
        for x in axis_results)
    args.report_md.write_text(
        "# Three-axis rod-network validation\n\n"
        f"**Result: {'PASS' if passed else 'FAIL'}**\n\n"
        f"- Actual STL SHA-256: `{topology['sha256']}`\n"
        f"- Watertight / mesh components: `{topology['watertight']}` / "
        f"`{topology['mesh_components']}`\n"
        f"- Reconstructed volume / fraction: `{structure['volume_mm3']:.1f} mm³` / "
        f"`{structure['volume_fraction']:.4f}` (void `{structure['void_fraction']:.4f}`)\n"
        f"- Rod width: `{cell:.2f} mm`; triangles: `{topology['triangles']}`\n"
        f"- Center X/Y/Z slice occupancy: `{center_slices}`\n\n"
        "| Axis | Own r | MAE | Cross-talk margin | Comparison |\n"
        "|---|---:|---:|---:|---|\n" + rows + "\n\n"
        "Opposite faces are mirrored views of the same axis projection, not extra images.\n\n"
        "## Method\n\n" + report["method"] + "\n\n## Honest limitations\n\n"
        + "".join(f"- {x}\n" for x in report["limitations"]))
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit("validation failed")


if __name__ == "__main__":
    main()
