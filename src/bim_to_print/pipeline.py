"""
pipeline.py — Top-level orchestration: IFC → slices → toolpath → G-code.
"""

from __future__ import annotations

from typing import Optional

from .gcode_writer import PrintSettings, write_gcode, write_gcode_string
from .ifc_reader import BuildingModel, read_ifc
from .slicer import slice_model
from .toolpath import generate_toolpath


def pipeline(
    ifc_path: str,
    gcode_path: str,
    layer_height: float = 5.0,
    nozzle_diameter: float = 6.0,
    extrusion_width: float = 8.0,
    perimeter_count: int = 2,
    infill_pattern: str = "lines",
    infill_density: float = 0.3,
    settings: Optional[PrintSettings] = None,
    verbose: bool = False,
) -> dict:
    """Run the full bim-to-print pipeline.

    Args:
        ifc_path: Path to input .ifc file.
        gcode_path: Output .gcode file path.
        layer_height: Layer height in mm.
        nozzle_diameter: Nozzle diameter in mm.
        extrusion_width: Extrusion bead width in mm.
        perimeter_count: Number of perimeter contours.
        infill_pattern: 'lines', 'grid', or 'none'.
        infill_density: Fraction (0–1).
        settings: Optional PrintSettings override.

    Returns:
        Dict with summary stats.
    """
    # 1. Read IFC
    model: BuildingModel = read_ifc(ifc_path)

    # 2. Slice
    sliced = slice_model(model.profiles, layer_height=layer_height)

    # 3. Toolpath
    tp_result = generate_toolpath(
        sliced,
        nozzle_diameter=nozzle_diameter,
        extrusion_width=extrusion_width,
        perimeter_count=perimeter_count,
        infill_pattern=infill_pattern,
        infill_density=infill_density,
    )

    # 4. G-code
    write_gcode(tp_result, gcode_path, settings=settings)

    return {
        "profiles": len(model.profiles),
        "layers": len(sliced.layers),
        "total_distance_mm": tp_result.total_distance_mm,
        "estimated_filament_mm": tp_result.estimated_filament_mm,
        "gcode_file": gcode_path,
    }


def pipeline_from_gh(
    profile_data: list,
    gcode_path: str,
    layer_height: float = 5.0,
    nozzle_diameter: float = 6.0,
    extrusion_width: float = 8.0,
    perimeter_count: int = 2,
    infill_pattern: str = "lines",
    infill_density: float = 0.3,
    settings: Optional[PrintSettings] = None,
    verbose: bool = False,
) -> dict:
    """Run pipeline with manual profile data (e.g. from GH output).

    Args:
        profile_data: List of dicts with keys name, ifc_type,
                      points_2d, base_elevation, height.
        gcode_path: Output .gcode path.
        See pipeline() for other args.

    Returns:
        Summary dict.
    """
    from .ifc_reader import BuildingModel, ExtrudedProfile

    profiles = [
        ExtrudedProfile(
            name=p["name"],
            ifc_type=p.get("ifc_type", "IfcBuildingElementProxy"),
            points_2d=p["points_2d"],
            base_elevation=p.get("base_elevation", 0.0),
            height=p.get("height", 3000.0),
        )
        for p in profile_data
    ]
    model = BuildingModel(profiles=profiles)

    sliced = slice_model(model.profiles, layer_height=layer_height)
    tp_result = generate_toolpath(
        sliced,
        nozzle_diameter=nozzle_diameter,
        extrusion_width=extrusion_width,
        perimeter_count=perimeter_count,
        infill_pattern=infill_pattern,
        infill_density=infill_density,
    )
    write_gcode(tp_result, gcode_path, settings=settings)

    return {
        "profiles": len(profiles),
        "layers": len(sliced.layers),
        "total_distance_mm": tp_result.total_distance_mm,
        "estimated_filament_mm": tp_result.estimated_filament_mm,
        "gcode_file": gcode_path,
    }
