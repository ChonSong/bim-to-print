#!/usr/bin/env python3
"""Render BIM model views using Blender headless via Docker.

Builds walls, columns, slab, roof with proper openings using bmesh
(no boolean modifiers — direct mesh construction). Renders 6 standard
architectural views + generates QA reference images.

Usage:
    python scripts/blender_render.py [--output renders/] [--samples 128]
"""

import argparse
import math
import os
import subprocess
import sys
import tempfile

BLENDER_IMAGE = "nytimes/blender:latest"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def build_wall_mesh_script() -> str:
    """Return Blender Python code. Read as file, not as heredoc."""
    path = os.path.join(SCRIPT_DIR, "_blender_render_inner.py")
    with open(path) as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(description="Render BIM views with Blender")
    parser.add_argument("--output", default="docs/research/renders",
                        help="Output directory for rendered images")
    parser.add_argument("--samples", type=int, default=128,
                        help="Cycles render samples (default: 128)")
    args = parser.parse_args()

    abs_out = os.path.abspath(args.output)
    os.makedirs(abs_out, exist_ok=True)

    # Write inner script
    inner_path = os.path.join(SCRIPT_DIR, "_blender_render_inner.py")
    with open(inner_path) as f:
        inner_code = f.read()

    # Inject parameters
    inner_code = inner_code.replace("__CYCLES_SAMPLES__", str(args.samples))

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(inner_code)
        script_path = f.name

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{script_path}:/script.py:ro",
        "-v", f"{abs_out}:/output",
        BLENDER_IMAGE,
        "blender", "--background", "--python", "/script.py",
    ]

    print(f"🚀 Blender render: {args.samples} samples")
    print(f"   Output: {abs_out}")
    print(f"   {' '.join(cmd[:4])} ...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

    # Show progress (filter noise)
    for line in result.stdout.split("\n"):
        if any(kw in line for kw in ["Rendered", "complete", "Error", "Saved", "Time:", "Fra:"]) and \
           "Sample" not in line:
            print(f"   {line.strip()}")

    if result.returncode != 0:
        for line in result.stderr.split("\n")[-10:]:
            if line.strip():
                sys.stderr.write(f"  ⚠️  {line.strip()}\n")

    os.unlink(script_path)

    # Report output files
    pngs = sorted(f for f in os.listdir(abs_out) if f.endswith(".png"))
    print(f"\n📁 {len(pngs)} renders:")
    for f in pngs:
        sz = os.path.getsize(os.path.join(abs_out, f))
        print(f"   📷 {f} ({sz:,} bytes)")


if __name__ == "__main__":
    main()
