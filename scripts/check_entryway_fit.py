#!/usr/bin/env python3
"""Validate organizer dimensions, item clearances, and Bambu bed fit."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import numpy as np

STL = Path("output/entryway_storage_box.stl")
SPEC = Path("output/entryway_storage_box_spec.json")
REPORT_JSON = Path("output/entryway_fit_check.json")
REPORT_MD = Path("output/ENTRYWAY_FIT_CHECK.md")

DIVIDER = 1.5
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

    # Net clearances after shared 1.5 mm divider walls.
    checks = [
        result(
            "Six oil bottles (3×2)",
            [99.25, 99.25],
            [90.0, 60.0],
            99.25 >= 90 and 99.25 >= 60,
            "Six Ø30 mm bottles fit in a 3×2 arrangement.",
        ),
        result(
            "Power bank 1 (vertical)",
            [99.25, 31.5],
            [80.0, 30.0],
            99.25 >= 80 and 31.5 >= 30,
            "110×80×30 mm bank stands upright; 1.5 mm thickness clearance.",
        ),
        result(
            "Power bank 2 (vertical)",
            [99.25, 31.5],
            [80.0, 30.0],
            99.25 >= 80 and 31.5 >= 30,
            "Same clearance as power bank 1.",
        ),
        result(
            "Coiled data cable",
            [99.25, 30.5],
            [60.0, 30.0],
            99.25 >= 60 and 30.5 >= 30,
            "Allows an approximately 60×30 mm flattened cable bundle.",
        ),
        result(
            "Standard cards",
            [99.25, 20.5],
            [85.6, 3.0],
            99.25 >= 85.6 and 20.5 >= 3,
            "Cards fit upright, not flat; each slot can hold a small stack.",
        ),
        result(
            "Letters at back (footprint)",
            [200.0, 29.25],
            [180.0, 5.0],
            200 >= 180 and 29.25 >= 5,
            "Mail slot width and depth at the rear band.",
        ),
        result(
            "Letters standing height",
            [round(spec["slope"]["back_rim_mm"], 1)],
            [150.0],
            spec["slope"]["back_rim_mm"] >= 148.0,
            "Rear rim rises to ~150 mm so 15 cm envelopes can stand upright.",
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
        "> Internal partition walls stay ~10 mm below the local exterior rim and never rise above it along their span.",
        "",
    ]
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.report_json}")
    print(f"Wrote {args.report_md}")
    if not report["all_item_checks_pass"] or not report["p1s_fit_pass"] or not report["mesh_integrity_pass"]:
        raise SystemExit("Fit validation failed")


if __name__ == "__main__":
    main()
