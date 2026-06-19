#!/usr/bin/env python3
"""Quality assessment of generated building plans.

Reads the building geometry from GH JSON, runs structural and architectural
viability checks, and outputs a QA report. Can also ingest rendered plan
images for visual checks if available.

Usage:
    python scripts/qa_assess_plan.py examples/demo_house.json [--renders renders/]
"""

import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QAReport:
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    items: list = field(default_factory=list)

    def add_pass(self, check: str, detail: str = ""):
        self.passed += 1
        self.items.append(("✅", check, detail))

    def add_fail(self, check: str, detail: str = ""):
        self.failed += 1
        self.items.append(("❌", check, detail))

    def add_warn(self, check: str, detail: str = ""):
        self.warnings += 1
        self.items.append(("⚠️", check, detail))

    def print(self):
        print(f"\n{'='*60}")
        print(f"  QA Assessment Report")
        print(f"{'='*60}")
        for status, check, detail in self.items:
            if detail:
                print(f"  {status} {check}: {detail}")
            else:
                print(f"  {status} {check}")
        print(f"{'='*60}")
        print(f"  ✅ {self.passed} passed · ⚠️  {self.warnings} warnings · ❌ {self.failed} failed")
        print(f"{'='*60}")
        return self.failed == 0


def check_profile(profile: dict, report: QAReport):
    """Run all checks on a single building profile."""
    name = profile.get("name", "Unnamed")
    pts = profile.get("points_2d", [])
    height = profile.get("height", 0)
    ifc_type = profile.get("ifc_type", "Unknown")
    openings = profile.get("openings", [])

    # 1. Minimum wall thickness (for 3DCP)
    if ifc_type.lower() in ("ifcwall", "ifcwallstandardcase", "ifcwallstandardcase"):
        p0 = pts[0]
        thicknesses = []
        for p in pts:
            dx = abs(p[0] - p0[0])
            dy = abs(p[1] - p0[1])
            if dx > 1 and dy > 1:  # corner point
                continue
            thickness = max(dx, dy)
            if 10 < thickness < 500:  # plausible wall thickness
                thicknesses.append(thickness)
        if thicknesses:
            min_t = min(thicknesses)
            if min_t < 150:
                report.add_warn(f"{name}: Wall thickness {min_t:.0f}mm < 150mm — may be too thin for 3DCP")
            elif min_t < 100:
                report.add_fail(f"{name}: Wall thickness {min_t:.0f}mm < 100mm — unprintable")
            else:
                report.add_pass(f"{name}: Wall thickness {min_t:.0f}mm OK")
        else:
            report.add_warn(f"{name}: Could not determine wall thickness")

    # 2. Minimum height (printable)
    if height > 0:
        if height < 300:
            report.add_warn(f"{name}: Height {height:.0f}mm < 300mm — very short element")
        elif height > 4000:
            report.add_warn(f"{name}: Height {height:.0f}mm > 4000mm — may need segmented print")
        else:
            report.add_pass(f"{name}: Height {height:.0f}mm OK")
    else:
        report.add_warn(f"{name}: Zero height")

    # 3. Polygon validation
    if len(pts) < 3:
        report.add_fail(f"{name}: <3 points — not a valid polygon")
    else:
        # Check for self-intersection (simple check: no repeated adjacent points)
        for i in range(len(pts)):
            j = (i + 1) % len(pts)
            if pts[i] == pts[j]:
                # Already closed — check if it's the last→first
                if i != len(pts) - 1:
                    report.add_warn(f"{name}: Duplicate adjacent point at index {i}")
                    break
        else:
            report.add_pass(f"{name}: Valid polygon ({len(pts)} points)")

    # 4. Opening checks
    for op in openings:
        op_name = op.get("name", "opening")
        op_z = op.get("z_start", 0)
        op_h = op.get("z_end", 0) - op.get("z_start", 0)
        op_shape = op.get("shape", [])

        if op_h > height:
            report.add_fail(f"{name}/{op_name}: Opening height {op_h:.0f}mm > wall height {height:.0f}mm")
        elif op_h < 100:
            report.add_warn(f"{name}/{op_name}: Opening height {op_h:.0f}mm < 100mm")
        else:
            report.add_pass(f"{name}/{op_name}: Opening height {op_h:.0f}mm OK")

        if len(op_shape) < 3:
            report.add_fail(f"{name}/{op_name}: Opening has <3 points")
        else:
            report.add_pass(f"{name}/{op_name}: Valid opening polygon")

    # 5. Printability checks
    if height > 0:
        layers = max(1, int(height / 10))  # 10mm layers
        if layers > 500:
            report.add_warn(f"{name}: {layers} layers — long print time")
        else:
            report.add_pass(f"{name}: {layers} layers — reasonable print duration")


def check_structural(profiles: list[dict], report: QAReport):
    """Cross-profile structural checks."""
    # Check for enclosure (do walls form a rough rectangle or have gaps?)
    wall_names = [p["name"] for p in profiles if "wall" in p.get("ifc_type", "").lower()]
    column_names = [p["name"] for p in profiles if "column" in p.get("ifc_type", "").lower()]

    if len(wall_names) < 2:
        report.add_warn(f"Only {len(wall_names)} wall(s) — may not form an enclosure")
    else:
        report.add_pass(f"{len(wall_names)} walls defined")

    if len(column_names) == 0:
        report.add_pass("No columns (acceptable for small single-storey)")
    else:
        report.add_pass(f"{len(column_names)} column(s) defined")

    # Check total building footprint
    all_pts = []
    for p in profiles:
        all_pts.extend(p.get("points_2d", []))
    if all_pts:
        xs = [pt[0] for pt in all_pts]
        ys = [pt[1] for pt in all_pts]
        width = max(xs) - min(xs)
        depth = max(ys) - min(ys)
        floor_area = width * depth / 1_000_000  # m²
        report.add_pass(f"Footprint: {width/1000:.1f} × {depth/1000:.1f} m ({floor_area:.1f} m²)")
        if floor_area < 10:
            report.add_warn(f"Floor area {floor_area:.1f} m² < 10 m² — very small")
        elif floor_area > 500:
            report.add_warn(f"Floor area {floor_area:.1f} m² > 500 m² — verify")

    # Check total print volume
    total_concrete = 0
    for p in profiles:
        pts = p.get("points_2d", [])
        h = p.get("height", 0)
        if len(pts) >= 3:
            # Shoelace for area
            area = 0
            for i in range(len(pts)):
                j = (i + 1) % len(pts)
                area += pts[i][0] * pts[j][1]
                area -= pts[j][0] * pts[i][1]
            area = abs(area) / 2 / 1_000_000  # m²
            total_concrete += area * h / 1000  # m³
    report.add_pass(f"Total concrete volume: {total_concrete:.2f} m³")
    if total_concrete > 50:
        report.add_warn(f"High concrete volume ({total_concrete:.2f} m³) — verify supply chain")


def check_design_viability(profiles: list[dict], report: QAReport):
    """High-level design viability checks."""
    for p in profiles:
        name = p.get("name", "?")
        openings = p.get("openings", [])
        for op in openings:
            op_z = op.get("z_start", 0)
            op_h = op.get("z_end", 0) - op.get("z_start", 0)
            # Window sill height check
            if op_h > 500 and op_z < 300:
                report.add_warn(f"{name}/{op.get('name')}: Low sill at Z={op_z:.0f}mm — potential structural weakness")
            # Door height check
            if op_h > 1800:
                report.add_pass(f"{name}/{op.get('name')}: Door height {op_h:.0f}mm OK")
                if op_h < 2000:
                    report.add_warn(f"{name}/{op.get('name')}: Door height {op_h:.0f}mm < 2000mm — check clearance")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/qa_assess_plan.py <input.json> [--renders <dir>]")
        sys.exit(1)

    input_path = sys.argv[1]
    renders_dir = None
    if "--renders" in sys.argv:
        idx = sys.argv.index("--renders")
        renders_dir = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None

    if not os.path.exists(input_path):
        print(f"❌ Input not found: {input_path}")
        sys.exit(1)

    with open(input_path) as f:
        profiles = json.load(f)

    print(f"\n📐 Loading building model: {input_path}")
    print(f"   {len(profiles)} profiles")

    report = QAReport()

    for p in profiles:
        check_profile(p, report)

    check_structural(profiles, report)
    check_design_viability(profiles, report)

    passes = report.print()

    # Check rendered images if available
    if renders_dir and os.path.isdir(renders_dir):
        pngs = [f for f in os.listdir(renders_dir) if f.endswith(".png")]
        if pngs:
            print(f"\n📸 Renderings available ({len(pngs)} views):")
            for f in sorted(pngs):
                sz = os.path.getsize(os.path.join(renders_dir, f))
                print(f"   📷 {f} ({sz:,} bytes)")
        else:
            print(f"\n⚠️  No PNGs in renders directory: {renders_dir}")

    sys.exit(0 if passes else 1)


if __name__ == "__main__":
    main()
