"""Run the full pipeline on demo_house.json and generate G-code + viz."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bim_to_print.pipeline import pipeline_from_gh

with open(os.path.join(os.path.dirname(__file__), "demo_house.json")) as f:
    profiles = json.load(f)

gcode_path = os.path.join(os.path.dirname(__file__), "demo_house.gcode")

result = pipeline_from_gh(
    profiles, gcode_path,
    layer_height=10.0,
    perimeter_count=2,
    infill_pattern="lines",
    infill_density=0.2,
)

print(f"profiles={result['profiles']}")
print(f"layers={result['layers']}")
print(f"distance={result['total_distance_mm']}mm")
print(f"filament={result['estimated_filament_mm']}mm")
print(f"gcode_file={gcode_path}")
print("OK")
