"""
ifc_reader.py — Extract wall/column geometries from IFC files.

Uses IfcOpenShell (optional dependency, install via `pip install bim-to-print[ifc]`).
Returns simplified 2D polygonal outlines suitable for slicing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Data model — geometry slices extracted from BIM
# ---------------------------------------------------------------------------


@dataclass
class ExtrudedProfile:
    """A 2D polygonal profile extruded vertically through a height."""

    name: str
    ifc_type: str  # e.g. "IfcWall", "IfcColumn", "IfcSlab"
    points_2d: List[Tuple[float, float]]  # clockwise outer boundary
    base_elevation: float  # Z of bottom
    height: float  # extrusion height above base
    material: str = "unknown"


@dataclass
class BuildingModel:
    """All printable elements from a BIM file."""

    profiles: List[ExtrudedProfile] = field(default_factory=list)
    units: str = "mm"  # all coordinates in mm
    model_name: str = ""


# ---------------------------------------------------------------------------
# IfcOpenShell reader
# ---------------------------------------------------------------------------


def _to_mm(value: float, unit: str) -> float:
    """Convert IFC length to millimetres."""
    if unit == "mm":
        return value
    elif unit == "m":
        return value * 1000.0
    elif unit == "cm":
        return value * 10.0
    elif unit == "ft":
        return value * 304.8
    else:
        return value  # assume mm


def _get_unit_name(ifc_file) -> str:
    """Return the project length unit name."""
    try:
        proj = ifc_file.by_type("IfcProject")[0]
        units = proj.UnitsInContext
        for assign in units:
            if hasattr(assign, "Units"):
                for u in assign.Units or []:
                    if hasattr(u, "UnitType") and u.UnitType == "LENGTHUNIT":
                        return getattr(u, "Name", "mm") or "mm"
    except Exception:
        pass
    return "mm"


def _polygon_from_ifc(representation, unit: str) -> List[Tuple[float, float]]:
    """Extract the first 2D polygon from a SweptSolid representation.

    Handles IfcExtrudedAreaSolid with IfcPolyline, IfcArbitraryClosedProfileDef,
    IfcRectangleProfileDef, and IfcCircleProfileDef (approximated as polygon).
    """
    items = representation.Items or []
    for solid in items:
        if not hasattr(solid, "SweptSolid") and solid.is_a(
            "IfcExtrudedAreaSolid"
        ):
            profile = getattr(solid, "SweptArea", None)
            if profile is None:
                continue
            # Curve on the profile
            outer_curve = getattr(profile, "OuterCurve", None)
            if outer_curve is None:
                continue

            # IfcPolyline
            if outer_curve.is_a("IfcPolyline"):
                pts = outer_curve.Points
                return [
                    (_to_mm(p.Coordinates[0], unit), _to_mm(p.Coordinates[1], unit))
                    for p in pts
                ]

            # IfcArbitraryClosedProfileDef – same path
            if outer_curve.is_a("IfcArbitraryClosedProfileDef"):
                # climb into curve again
                sub = getattr(outer_curve, "OuterCurve", None) or outer_curve
                if sub.is_a("IfcPolyline"):
                    pts = sub.Points
                    return [
                        (_to_mm(p.Coordinates[0], unit), _to_mm(p.Coordinates[1], unit))
                        for p in pts
                    ]

            # IfcRectangleProfileDef
            if profile.is_a("IfcRectangleProfileDef"):
                xdim = _to_mm(profile.XDim, unit)
                ydim = _to_mm(profile.YDim, unit)
                return [
                    (-xdim / 2, -ydim / 2),
                    (xdim / 2, -ydim / 2),
                    (xdim / 2, ydim / 2),
                    (-xdim / 2, ydim / 2),
                    (-xdim / 2, -ydim / 2),
                ]

            # IfcCircleProfileDef → approximate as octagon
            if profile.is_a("IfcCircleProfileDef"):
                radius = _to_mm(profile.Radius, unit)
                n = 8
                pts = []
                for i in range(n + 1):
                    theta = 2 * math.pi * i / n
                    pts.append(
                        (radius * math.cos(theta), radius * math.sin(theta))
                    )
                return pts

    return []


def read_ifc(filepath: str) -> BuildingModel:
    """Parse an IFC file and return printable profiles.

    Returns a full BuildingModel on success.
    Raises ImportError if IfcOpenShell is not installed.
    Raises ValueError if the file cannot be parsed.
    """
    try:
        import ifcopenshell  # noqa: F401
    except ImportError:
        raise ImportError(
            "IfcOpenShell is required. Install with: pip install bim-to-print[ifc]"
        )

    import ifcopenshell

    ifc_file = ifcopenshell.open(filepath)
    unit = _get_unit_name(ifc_file)
    model = BuildingModel(model_name=filepath, units="mm")

    # Supported element types
    target_types = {"IfcWall", "IfcColumn", "IfcSlab", "IfcBeam", "IfcBuildingElementProxy"}

    for element in ifc_file.by_type("IfcBuildingElement"):
        elem_type = element.is_a()
        if elem_type not in target_types:
            continue

        rep = getattr(element, "Representation", None)
        if rep is None:
            continue

        # Get name
        name = getattr(element, "Name", None) or element.GlobalId

        # Get elevation / height from ObjectPlacement and representations
        elevation = 0.0
        height = 3000.0  # fallback

        # Try to extract height from ExtrudedAreaSolid
        for rep in (rep.Representations or []):
            polygon = _polygon_from_ifc(rep, unit)
            if polygon:
                extrusion_dir = None
                for solid in (rep.Items or []):
                    if solid.is_a("IfcExtrudedAreaSolid"):
                        extruded = solid.Depth if hasattr(solid, "Depth") else 3000.0
                        height = _to_mm(extruded, unit)
                        break
                break
        else:
            continue  # no polygon found

        # Simple placement extraction
        placement = getattr(element, "ObjectPlacement", None)
        if placement:
            rel = getattr(placement, "RelativePlacement", None)
            if rel:
                loc = getattr(rel, "Location", None)
                if loc:
                    coords = loc.Coordinates
                    if len(coords) >= 3:
                        elevation = _to_mm(coords[2], unit)

        model.profiles.append(
            ExtrudedProfile(
                name=name,
                ifc_type=elem_type,
                points_2d=polygon,
                base_elevation=elevation,
                height=height,
                material=getattr(element, "Material", "unknown"),
            )
        )

    if not model.profiles:
        raise ValueError(
            f"No printable elements found in {filepath}. "
            f"Supported types: {', '.join(sorted(target_types))}"
        )

    return model
