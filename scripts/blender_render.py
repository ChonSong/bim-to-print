#!/usr/bin/env python3
"""Render BIM model views using Blender headless via Docker.

Reads a GH-style JSON floor plan, builds walls with proper openings using bmesh,
renders 6 standard architectural views (overview, plan, N/S/E/W elevations).

Usage:
    python scripts/blender_render.py [--model examples/house_floorplan.json]
                                     [--output docs/research/renders] [--samples 128]
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile


BLENDER_IMAGE = "nytimes/blender:latest"
INNER_SCRIPT = os.path.join(os.path.dirname(__file__), "_blender_render_inner.py")


def make_render_script(profiles: list[dict], samples: int) -> str:
    """Generate Blender Python script from floor plan data."""
    walls_json = json.dumps(profiles)

    inner = open(INNER_SCRIPT).read()
    inner = inner.replace("__FLOORPLAN_JSON__", walls_json)
    inner = inner.replace("__CYCLES_SAMPLES__", str(samples))
    return inner


def main():
    parser = argparse.ArgumentParser(description="Render BIM views with Blender")
    parser.add_argument("--model", default="examples/house_floorplan.json",
                        help="GH-style JSON floor plan")
    parser.add_argument("--output", default="docs/research/renders",
                        help="Output directory for rendered images")
    parser.add_argument("--samples", type=int, default=64,
                        help="Cycles render samples")
    args = parser.parse_args()

    abs_model = os.path.abspath(args.model)
    abs_out = os.path.abspath(args.output)
    os.makedirs(abs_out, exist_ok=True)

    # Read model
    with open(abs_model) as f:
        profiles = json.load(f)

    # Generate script with embedded data
    script = make_render_script(profiles, args.samples)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{script_path}:/script.py:ro",
        "-v", f"{abs_out}:/output",
        BLENDER_IMAGE,
        "blender", "--background", "--python", "/script.py",
    ]

    print(f"🚀 Blender render: {args.samples} samples")
    print(f"   Model: {args.model} ({len(profiles)} profiles)")
    print(f"   Output: {abs_out}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

    for line in result.stdout.split("\n"):
        if any(kw in line for kw in ["Rendered", "complete", "Error", "Saved"]) and \
           "Sample" not in line and "Fra:" not in line:
            print(f"   {line.strip()}")

    if result.returncode != 0:
        for line in result.stderr.split("\n")[-10:]:
            if line.strip():
                sys.stderr.write(f"  ⚠️  {line.strip()}\n")
        sys.exit(1)

    os.unlink(script_path)

    pngs = sorted(f for f in os.listdir(abs_out) if f.endswith(".png"))
    print(f"\n📁 {len(pngs)} renders:")
    for f in pngs:
        sz = os.path.getsize(os.path.join(abs_out, f))
        print(f"   📷 {f} ({sz:,} bytes)")


if __name__ == "__main__":
    main()
