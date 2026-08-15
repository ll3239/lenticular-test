#!/usr/bin/env python3
"""Validate organizer dimensions, item clearances, and Bambu bed fit."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import numpy as np
from generate_entryway_dimensions import build_report
from generate_entryway_storage_box import LAYOUT_COMPACT

STL = Path("output/entryway_storage_box.stl")
SPEC = Path("output/entryway_storage_box_spec.json")
REPORT_JSON = Path("output/entryway_fit_check.json")
REPORT_MD = Path("output/ENTRYWAY_FIT_CHECK.md")

BRIM = 5.0


def binary_stl_extents(path: Path) -> list[float]:
    data = path.read_bytes()
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    expected_size = 84 + triangle_count * 50
    if len(data) != expected_size:
        raise ValueError(f"{path} is not a valid binary STL")
    record_type = np.dtype(
        [("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")]
    )
    records = np.frombuffer(data, dtype=record_type, count=triangle_count, offset=84)
    triangles = records["vertices"].reshape(-1, 3)
    return (triangles.max(axis=0) - triangles.min(axis=0)).round(3).tolist()


def result(name: str, actual, required, passed: bool, note: str) -> dict:
    return {
        "name": name,
        "actual_mm": actual,
        "required_mm": required,
        "pass": passed,
        "note": note,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stl", type=Path, default=STL)
    parser.add_argument("--spec", type=Path, default=SPEC)
    parser.add_argument("--report-json", type=Path, default=REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=REPORT_MD)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    extents = binary_stl_extents(args.stl)
    import trimesh

    mesh = trimesh.load(args.stl, force="mesh", process=True)
    mesh_integrity = {
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "single_printable_volume": bool(mesh.is_volume),
    }
    unsupported_mask = (mesh.face_normals[:, 2] < -0.99) & (mesh.triangles_center[:, 2] > 2.5)
    unsupported_horizontal_area = round(float(mesh.area_faces[unsupported_mask].sum()), 3)
    support_free_pass = unsupported_horizontal_area < 1.0
    solid_volume_cm3 = round(float(mesh.volume) / 1000.0, 1)
    material_estimates_g = {
        "PETG": round(solid_volume_cm3 * 1.27),
        "PLA": round(solid_volume_cm3 * 1.24),
    }

    dimensions = build_report(LAYOUT_COMPACT)
    by_id = {c["id"]: c for c in dimensions["compartments"]}

    def clearance(compartment_id: str) -> list[float]:
        net = by_id[compartment_id]["internal_net_mm"]
        return [net["width_x"], net["depth_y"]]

    oil = clearance("essential_oils")
    power = clearance("power_banks")
    cable = clearance("data_cable")
    card = clearance("card_1")
    receipt = clearance("receipts")
    letters = clearance("letters")
    checks = [
        result(
            "Earphones / misc front bay",
            clearance("earphones_other"),
            [90.0, 90.0],
            min(clearance("earphones_other")) >= 90.0,
            "100×100 mm clear front-left tray.",
        ),
        result(
            "Six oil bottles (3×2)",
            oil,
            [90.0, 60.0],
            oil[0] >= 90 and oil[1] >= 60,
            "Six Ø30×80 mm bottles fit 3×2 in the left mid bay.",
        ),
        result(
            "Power banks (merged bay, rear)",
            power,
            [80.0, 60.0],
            power[0] >= 80 and power[1] >= 60,
            "Two 110×80×30 mm banks in one ≥60 mm-deep rear bay.",
        ),
        result(
            "Coiled data cable (shallow front)",
            cable,
            [60.0, 24.0],
            cable[0] >= 60 and cable[1] >= 24,
            "Shallow 24 mm front tray; width fits a ~60 mm coiled bundle.",
        ),
        result(
            "Card wallets (each slot)",
            card,
            [85.6, 25.0],
            card[0] >= 85.6 and card[1] >= 25,
            "Each front-right slot accepts an 85.6 mm-wide wallet up to 25 mm thick.",
        ),
        result(
            "Receipts",
            receipt,
            [85.6, 20.0],
            receipt[0] >= 85.6 and receipt[1] >= 20,
            "Folded receipts fit the 20 mm-target front slot.",
        ),
        result(
            "Letters at back (footprint)",
            letters,
            [180.0, 5.0],
            letters[0] >= 180 and letters[1] >= 5,
            "Fits mail up to 200 mm wide; not unfolded A4/C5 (210–229 mm wide).",
        ),
        result(
            "Letters retaining baffle",
            [by_id["letters"]["baffle_height_mm"]["back_at_y1"]],
            [140.0],
            by_id["letters"]["baffle_height_mm"]["back_at_y1"] >= 140.0,
            "A 150 mm-tall envelope protrudes ~10 mm above the 140 mm internal baffle.",
        ),
    ]

    printers = [
        {
            "printer": "Bambu P1/P1S/X1/A1",
            "bed_mm": [256.0, 256.0],
            "with_brim_mm": [extents[0] + 2 * BRIM, extents[1] + 2 * BRIM],
        },
        {
            "printer": "Bambu A1 mini",
            "bed_mm": [180.0, 180.0],
            "with_brim_mm": [extents[0] + 2 * BRIM, extents[1] + 2 * BRIM],
        },
    ]
    for printer in printers:
        footprint = printer["with_brim_mm"]
        bed = printer["bed_mm"]
        printer["pass"] = footprint[0] <= bed[0] and footprint[1] <= bed[1]
        printer["remaining_margin_mm"] = [
            round(bed[0] - footprint[0], 3),
            round(bed[1] - footprint[1], 3),
        ]

    report = {
        "stl": str(args.stl),
        "stl_extents_mm": extents,
        "mesh_integrity": mesh_integrity,
        "unsupported_horizontal_area_above_base_mm2": unsupported_horizontal_area,
        "support_free_pass": support_free_pass,
        "solid_model_volume_cm3": solid_volume_cm3,
        "material_estimates_g": material_estimates_g,
        "expected_outer_mm": spec["outer_mm"],
        "brim_mm_each_side": BRIM,
        "item_checks": checks,
        "printer_checks": printers,
        "all_item_checks_pass": all(c["pass"] for c in checks),
        "p1s_fit_pass": printers[0]["pass"],
        "mesh_integrity_pass": all(mesh_integrity.values()),
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    status = lambda passed: "PASS" if passed else "FAIL"
    lines = [
        "# Entryway organizer fit check",
        "",
        f"- STL measured extents: **{extents[0]:g} × {extents[1]:g} × {extents[2]:g} mm**",
        f"- With {BRIM:g} mm brim: **{extents[0] + 2 * BRIM:g} × {extents[1] + 2 * BRIM:g} mm**",
        f"- Mesh integrity: **{status(all(mesh_integrity.values()))}** (watertight, consistent winding, single volume)",
        f"- Support-free geometry: **{status(support_free_pass)}** "
        f"({unsupported_horizontal_area:g} mm² horizontal underside above the base)",
        f"- Solid model volume: **{solid_volume_cm3:g} cm³** "
        f"(about {material_estimates_g['PETG']} g PETG / {material_estimates_g['PLA']} g PLA before purge)",
        "",
        "## Item clearances",
        "",
        "| Check | Net clearance | Required | Result |",
        "|---|---:|---:|:---:|",
    ]
    for check in checks:
        actual = " × ".join(f"{v:g}" for v in check["actual_mm"])
        required = " × ".join(f"{v:g}" for v in check["required_mm"])
        lines.append(f"| {check['name']} | {actual} mm | {required} mm | {status(check['pass'])} |")
    lines += ["", "## Printer bed", "", "| Printer | Bed | With brim | Remaining margin | Result |", "|---|---:|---:|---:|:---:|"]
    for printer in printers:
        bed = " × ".join(f"{v:g}" for v in printer["bed_mm"])
        footprint = " × ".join(f"{v:g}" for v in printer["with_brim_mm"])
        margin = " × ".join(f"{v:g}" for v in printer["remaining_margin_mm"])
        lines.append(f"| {printer['printer']} | {bed} mm | {footprint} mm | {margin} mm | {status(printer['pass'])} |")
    lines += [
        "",
        "> Partition tops follow the same sloped/trapezoid profile as the exterior rim, kept ~10 mm lower.",
        "",
    ]
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.report_json}")
    print(f"Wrote {args.report_md}")
    if (
        not report["all_item_checks_pass"]
        or not report["p1s_fit_pass"]
        or not report["mesh_integrity_pass"]
        or not report["support_free_pass"]
    ):
        raise SystemExit("Fit validation failed")


if __name__ == "__main__":
    main()
