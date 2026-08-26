#!/usr/bin/env python3
"""Validate topology and reproducibly preview the connected depth-line cube."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

from generate_connected_depth_lines import (
    FACE_NAMES,
    build_cube,
    load_gray,
)


def correlation(a, b):
    a, b = np.asarray(a).ravel(), np.asarray(b).ravel()
    a, b = a - a.mean(), b - b.mean()
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denominator) if denominator else 0.0


def exposure_aligned_mae(rendered, target):
    """MAE after one global linear exposure/black-level calibration."""
    x, y = np.asarray(rendered).ravel(), np.asarray(target).ravel()
    matrix = np.column_stack((x, np.ones_like(x)))
    scale, offset = np.linalg.lstsq(matrix, y, rcond=None)[0]
    fitted = np.clip(scale * x + offset, 0.0, 1.0)
    return float(np.mean(np.abs(fitted - y))), float(scale), float(offset)


def line_decode(field, lines):
    """Remove the line carrier by averaging each physical channel."""
    decoded = np.empty_like(field)
    width = field.shape[1]
    for index in range(lines):
        c0, c1 = index * width // lines, (index + 1) * width // lines
        decoded[:, c0:c1] = field[:, c0:c1].mean(axis=1)[:, None]
    return decoded


def directional_shadow_preview(field, size, ray_slope=0.75, ambient=0.15):
    """Lambert render with deterministic horizon-ray self-shadowing.

    The light travels from local -u toward the face.  For each surface sample,
    the horizon scan tests whether an earlier point intersects that light ray.
    """
    spacing = size / (field.shape[0] - 1)
    height = -field
    visible = np.ones_like(height, dtype=bool)
    for row in range(height.shape[0]):
        horizon = -np.inf
        for column in range(height.shape[1]):
            if column:
                visible[row, column] = horizon <= height[row, column] + 1e-10
            horizon = max(horizon - ray_slope * spacing, height[row, column])

    dv, du = np.gradient(height, spacing, spacing)
    normals = np.dstack((-du, -dv, np.ones_like(field)))
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    light = np.asarray((-1.0, 0.0, ray_slope), dtype=float)
    light /= np.linalg.norm(light)
    intensity = ambient + (1.0 - ambient) * visible * np.clip(normals @ light, 0.0, 1.0)
    return intensity


def panel(source, field, shade, out_path, face):
    dimension = 420
    source_image = Image.fromarray(
        np.uint8(np.clip(source, 0, 1) * 255), "L"
    ).resize((dimension, dimension), Image.Resampling.NEAREST).convert("RGB")
    depth_image = Image.fromarray(
        np.uint8((1.0 - field / max(field.max(), 1e-9)) * 255), "L"
    ).resize((dimension, dimension), Image.Resampling.NEAREST).convert("RGB")
    shade_image = Image.fromarray(
        np.uint8(np.clip(shade, 0, 1) * 255), "L"
    ).resize((dimension, dimension), Image.Resampling.NEAREST).convert("RGB")
    canvas = Image.new("RGB", (dimension * 3, dimension + 34), "#202124")
    for index, image in enumerate((source_image, depth_image, shade_image)):
        canvas.paste(image, (index * dimension, 34))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 9), f"{face}: preprocessed source", fill="white")
    draw.text((dimension + 8, 9), "orthographic depth", fill="white")
    draw.text((dimension * 2 + 8, 9), "fixed directional light", fill="white")
    canvas.save(out_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--images", type=Path, nargs=6, required=True)
    parser.add_argument("--preview-dir", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path, required=True)
    parser.add_argument("--size", type=float, default=50.0)
    parser.add_argument("--lines", type=int, default=50)
    parser.add_argument("--resolution", type=int, default=251)
    parser.add_argument("--max-depth", type=float, default=0.45)
    args = parser.parse_args()

    mesh = trimesh.load_mesh(args.mesh, process=True)
    components = mesh.split(only_watertight=False)
    bounds_error = float(np.max(np.abs(mesh.extents - args.size)))
    topology = {
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        # Avoid trimesh.body_count: it unnecessarily requires optional scipy.
        "body_count": len(components),
        "connected_components": len(components),
        "bounds_mm": mesh.bounds.tolist(),
        "extents_mm": mesh.extents.tolist(),
        "bounds_max_error_mm": bounds_error,
        "volume_mm3": float(mesh.volume),
        "triangles": len(mesh.faces),
    }
    pitch = args.size / args.lines
    feature_constraints = {
        "line_pitch_mm": pitch,
        "separator_width_mm": 0.4,
        "groove_width_mm": pitch - 0.4,
        "grid_spacing_mm": args.size / (args.resolution - 1),
        "nozzle_diameter_mm": 0.4,
        "passes_0_4mm_xy_feature_rule": bool(
            pitch - 0.4 >= 0.4 and args.resolution >= args.lines * 5 + 1
        ),
    }

    # Regeneration supplies the exact deterministic physical face samples used by
    # the STL; topology and dimensions above are independently read from the STL.
    expected_mesh, fields = build_cube(
        args.images, args.size, args.lines, args.resolution, args.max_depth
    )
    actual_bytes = args.mesh.read_bytes()
    expected_bytes = expected_mesh.export(file_type="stl")
    mesh_matches_encoding = actual_bytes == expected_bytes
    topology["sha256"] = hashlib.sha256(actual_bytes).hexdigest()
    topology["matches_deterministic_encoded_mesh"] = mesh_matches_encoding

    args.preview_dir.mkdir(parents=True, exist_ok=True)
    face_results = []
    for face, image_path in zip(FACE_NAMES, args.images):
        source = load_gray(image_path, args.resolution)
        target_dark = 1.0 - source
        decoded = line_decode(fields[face], args.lines)
        decoded /= max(decoded.max(), 1e-9)
        target_lines = line_decode(target_dark, args.lines)
        target_lines /= max(target_lines.max(), 1e-9)
        shade = directional_shadow_preview(fields[face], args.size)
        rendered_dark = line_decode(1.0 - shade, args.lines)
        rendered_dark /= max(rendered_dark.max(), 1e-9)
        render_mae, exposure_scale, black_offset = exposure_aligned_mae(
            rendered_dark[1:-1, 1:-1], target_lines[1:-1, 1:-1]
        )
        preview_path = args.preview_dir / f"{face}.png"
        panel(source, fields[face], shade, preview_path, face)
        face_results.append({
            "face": face,
            "source": str(image_path),
            "preview": str(preview_path),
            "depth_pearson": correlation(decoded[1:-1, 1:-1], target_lines[1:-1, 1:-1]),
            "depth_normalized_mae": float(
                np.mean(np.abs(decoded[1:-1, 1:-1] - target_lines[1:-1, 1:-1]))
            ),
            "rendered_light_pearson": correlation(
                rendered_dark[1:-1, 1:-1], target_lines[1:-1, 1:-1]
            ),
            "rendered_light_exposure_aligned_mae": render_mae,
            "render_exposure_fit": {
                "scale": exposure_scale, "black_offset": black_offset
            },
            "depth_range_mm": [
                float(fields[face].min()), float(fields[face].max())
            ],
        })

    passed = (
        topology["watertight"]
        and topology["winding_consistent"]
        and topology["connected_components"] == 1
        and topology["body_count"] == 1
        and mesh_matches_encoding
        and bounds_error < 1e-4
        and feature_constraints["passes_0_4mm_xy_feature_rule"]
        and all(item["depth_pearson"] >= 0.90 for item in face_results)
        and all(item["depth_normalized_mae"] <= 0.15 for item in face_results)
        and all(item["rendered_light_pearson"] >= 0.85 for item in face_results)
        and all(item["rendered_light_exposure_aligned_mae"] <= 0.10 for item in face_results)
    )
    report = {
        "passed": passed,
        "mesh": str(args.mesh),
        "settings": {
            "size_mm": args.size, "lines_per_face": args.lines,
            "grid_resolution": args.resolution, "max_depth_mm": args.max_depth,
            "lighting": {
                "projection": "orthographic", "local_direction": [-1.0, 0.0, 0.75],
                "ambient": 0.15, "self_shadow": "heightfield horizon rays",
            },
            "thresholds": {
                "depth_pearson_min": 0.90, "depth_normalized_mae_max": 0.15,
                "rendered_light_pearson_min": 0.85,
                "rendered_light_exposure_aligned_mae_max": 0.10,
            },
        },
        "topology": topology,
        "feature_constraints": feature_constraints,
        "faces": face_results,
        "print_note": (
            "The bottom face retains its image mapping, but it is against the print "
            "bed in the default orientation; bed texture and first-layer limits reduce visibility."
        ),
        "limitations": [
            "Lighting direction is fixed in each face's local coordinates; one world-space "
            "lamp cannot illuminate all six differently oriented faces at this same angle.",
            "The renderer models directional Lambert light, ambient fill, and heightfield "
            "occlusion, but not printer-layer stair stepping, scattering, gloss, or interreflection.",
            "The 0.4 mm separator is exactly one nominal 0.4 mm nozzle width; slicer line-width "
            "policy, XY compensation, and printer calibration can materially change it.",
        ],
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2) + "\n")
    rows = "\n".join(
        f"| {x['face']} | {x['depth_pearson']:.4f} | "
        f"{x['depth_normalized_mae']:.4f} | `{x['preview']}` |"
        for x in face_results
    )
    args.report_md.write_text(
        "# Connected depth-line cube validation\n\n"
        f"**Result: {'PASS' if passed else 'FAIL'}**\n\n"
        f"- Watertight: `{topology['watertight']}`\n"
        f"- Connected components / bodies: `{topology['connected_components']}` / "
        f"`{topology['body_count']}`\n"
        f"- Matches deterministic encoded mesh: "
        f"`{topology['matches_deterministic_encoded_mesh']}`\n"
        f"- Extents: `{topology['extents_mm']}` mm\n"
        f"- Triangles: `{topology['triangles']}`\n\n"
        f"- Pitch / separator / groove: `{pitch:.2f}` / `0.40` / "
        f"`{pitch - 0.4:.2f}` mm\n\n"
        "| Face | Depth r | Depth MAE | Render r | Render MAE | Preview |\n"
        "|---|---:|---:|---:|---:|---|\n" + "\n".join(
            f"| {x['face']} | {x['depth_pearson']:.4f} | "
            f"{x['depth_normalized_mae']:.4f} | {x['rendered_light_pearson']:.4f} | "
            f"{x['rendered_light_exposure_aligned_mae']:.4f} | `{x['preview']}` |"
            for x in face_results
        ) + "\n\n"
        "Acceptance requires depth r >= 0.90, depth MAE <= 0.15, rendered-light "
        "r >= 0.85, and rendered-light exposure-aligned MAE <= 0.10 on every face. "
        "The single global linear exposure/black-level fit does not alter spatial "
        "content. Render metrics compare the line-decoded self-shadow render with "
        "the source at the same bandwidth. Rays use fixed local direction "
        "`[-1, 0, 0.75]`; Lambert response, ambient light, and channel occlusion "
        "are included.\n\n"
        f"Print caveat: {report['print_note']}\n\n"
        "Limitations:\n" + "".join(f"- {item}\n" for item in report["limitations"])
    )
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit("validation failed")


if __name__ == "__main__":
    main()
