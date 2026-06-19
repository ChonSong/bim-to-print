#!/usr/bin/env python3
"""Generate a realistic 2-bedroom house floor plan for 3DCP.

Outputs a GH-style JSON file compatible with bim2print pipeline.
Overall footprint: ~10m × 8m (80m²), ~70m² internal area.

Usage:
    python scripts/generate_floorplan.py [--output examples/house_floorplan.json]
"""

import argparse
import json
import math
import os


def generate_floorplan() -> list[dict]:
    """Generate a 2-bedroom house plan with openings."""
    
    # All coordinates in mm
    # House footprint: 10000 × 8000 mm
    
    profiles = []
    
    # ── External walls (200mm thick, 2400mm high) ──
    
    # Front wall (south) — with front door + living room window
    profiles.append({
        "name": "Front-Wall",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[0, 0], [10000, 0], [10000, 200], [0, 200], [0, 0]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [
            {
                "shape": [[4200, 0], [5200, 0], [5200, 200], [4200, 200], [4200, 0]],
                "z_start": 0.0, "z_end": 2100.0,
                "name": "Front-Door",
            },
            {
                "shape": [[6500, 0], [8500, 0], [8500, 200], [6500, 200], [6500, 0]],
                "z_start": 600.0, "z_end": 2100.0,
                "name": "Living-Window",
            },
        ],
    })
    
    # Right wall (east) — with kitchen window + bathroom window
    profiles.append({
        "name": "Right-Wall",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[10000, 0], [10000, 8000], [10200, 8000], [10200, 0], [10000, 0]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [
            {
                "shape": [[10000, 3500], [10000, 4700], [10200, 4700], [10200, 3500], [10000, 3500]],
                "z_start": 600.0, "z_end": 2100.0,
                "name": "Kitchen-Window",
            },
            {
                "shape": [[10000, 500], [10000, 1100], [10200, 1100], [10200, 500], [10000, 500]],
                "z_start": 1400.0, "z_end": 2100.0,
                "name": "Bathroom-Window",
            },
        ],
    })
    
    # Back wall (north) — with bedroom windows
    profiles.append({
        "name": "Back-Wall",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[0, 8000], [10000, 8000], [10000, 8200], [0, 8200], [0, 8000]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [
            {
                "shape": [[500, 8000], [2000, 8000], [2000, 8200], [500, 8200], [500, 8000]],
                "z_start": 600.0, "z_end": 1800.0,
                "name": "Bedroom2-Window",
            },
            {
                "shape": [[3500, 8000], [5000, 8000], [5000, 8200], [3500, 8200], [3500, 8000]],
                "z_start": 600.0, "z_end": 1800.0,
                "name": "Bedroom1-Window",
            },
        ],
    })
    
    # Left wall (west) — no openings (party wall)
    profiles.append({
        "name": "Left-Wall",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[0, 0], [0, 8000], [200, 8000], [200, 0], [0, 0]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [],
    })
    
    # ── Internal walls (150mm thick for 3DCP) ──
    
    # Living/Bedrooms partition wall (runs east-west at y=4500)
    # Living room on south side, bedrooms on north side
    profiles.append({
        "name": "Partition-Wall-1",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[200, 4500], [10000, 4500], [10000, 4650], [200, 4650], [200, 4500]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [
            {
                "shape": [[5500, 4500], [6400, 4500], [6400, 4650], [5500, 4650], [5500, 4500]],
                "z_start": 0.0, "z_end": 2100.0,
                "name": "Hallway-Door",
            },
        ],
    })
    
    # Bedroom divider (north-south at x=5600)
    # Bedroom 1 (west) and Bedroom 2 (east)
    profiles.append({
        "name": "Bedroom-Divider",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[5600, 4500], [5600, 8000], [5750, 8000], [5750, 4500], [5600, 4500]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [
            {
                "shape": [[5600, 5800], [5600, 6700], [5750, 6700], [5750, 5800], [5600, 5800]],
                "z_start": 0.0, "z_end": 2100.0,
                "name": "Bedroom-Door",
            },
        ],
    })
    
    # Bathroom enclosure (south-east corner, 2500×2500)
    profiles.append({
        "name": "Bathroom-Wall-1",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[7500, 0], [7500, 2500], [7650, 2500], [7650, 0], [7500, 0]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [
            {
                "shape": [[7500, 800], [7500, 1600], [7650, 1600], [7650, 800], [7500, 800]],
                "z_start": 0.0, "z_end": 2100.0,
                "name": "Bathroom-Door",
            },
        ],
    })
    
    # Bathroom north wall (connects to partition wall)
    profiles.append({
        "name": "Bathroom-Wall-2",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[7500, 2500], [10000, 2500], [10000, 2650], [7500, 2650], [7500, 2500]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [],
    })
    
    # Hallway south wall (forms entrance corridor)
    profiles.append({
        "name": "Hallway-Wall",
        "ifc_type": "IfcWallStandardCase",
        "points_2d": [[5200, 0], [5200, 2500], [5350, 2500], [5350, 0], [5200, 0]],
        "base_elevation": 0.0,
        "height": 2400.0,
        "openings": [],
    })
    
    # ── Structure ──
    
    # Foundation slab (extend 100mm past exterior walls)
    profiles.append({
        "name": "Slab",
        "ifc_type": "IfcSlab",
        "points_2d": [[-100, -100], [10300, -100], [10300, 8300], [-100, 8300], [-100, -100]],
        "base_elevation": -150.0,
        "height": 150.0,
        "openings": [],
    })
    
    # Flat roof slab
    profiles.append({
        "name": "Roof",
        "ifc_type": "IfcSlab",
        "points_2d": [[-100, -100], [10300, -100], [10300, 8300], [-100, 8300], [-100, -100]],
        "base_elevation": 2400.0,
        "height": 150.0,
        "openings": [],
    })
    
    return profiles


def main():
    parser = argparse.ArgumentParser(description="Generate realistic 2-bedroom house floor plan")
    parser.add_argument("--output", default="examples/house_floorplan.json",
                        help="Output JSON path")
    args = parser.parse_args()
    
    profiles = generate_floorplan()
    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(profiles, f, indent=2)
    
    # Stats
    total_openings = sum(len(p["openings"]) for p in profiles)
    print(f"✅ Generated floor plan: {output_path}")
    print(f"   Profiles: {len(profiles)}")
    print(f"   Openings: {total_openings}")
    
    # Calculate floor area
    xs = [p["points_2d"][i][0] for p in profiles if "Wall" in p["ifc_type"] for i in range(len(p["points_2d"]))]
    ys = [p["points_2d"][i][1] for p in profiles if "Wall" in p["ifc_type"] for i in range(len(p["points_2d"]))]
    if xs and ys:
        footprint = (max(xs) - min(xs)) * (max(ys) - min(ys)) / 1_000_000
        print(f"   Footprint: {footprint:.0f} m²")
    
    print(f"   Rooms: Living/Dining, Kitchen, Bathroom, Hallway, Bedroom 1, Bedroom 2")
    print(f"\nRun QA:  python scripts/qa_assess_plan.py {output_path}")
    print(f"Render:  python scripts/blender_render.py --samples 128")


if __name__ == "__main__":
    main()
