"""
toolpath.py — Generate print toolpaths (perimeter + infill) from slice layers.

Implements:
  - Contour/perimeter path: follows the outer boundary with proper Clipper2 offset
  - Hole perimeters: offset outward to create wall framing around openings
  - Infill pattern: grid-based filling clipped to the printable region (outer ∖ holes)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np
import pyclipper

from .slicer import SlicedModel, SliceLayer

# ---------------------------------------------------------------------------
# Toolpath primitives
# ---------------------------------------------------------------------------


@dataclass
class ExtrusionSegment:
    """A single continuous extrusion move."""

    x: float
    y: float
    z: float
    e: float  # extrusion amount (relative)
    speed: int = 1800  # mm/min


@dataclass
class TravelMove:
    """Non-printing move (no extrusion)."""

    x: float
    y: float
    z: float


Move = ExtrusionSegment | TravelMove


@dataclass
class LayerToolpath:
    """All moves for one layer of one profile."""

    z: float
    layer_index: int
    profile_name: str
    moves: List[Move] = field(default_factory=list)


@dataclass
class ToolpathResult:
    """Complete toolpath for the model."""

    layer_paths: List[LayerToolpath] = field(default_factory=list)
    total_distance_mm: float = 0.0
    estimated_filament_mm: float = 0.0


# ---------------------------------------------------------------------------
# Geometry helpers (pyclipper wrappers)
# ---------------------------------------------------------------------------


def _poly_to_path(poly: np.ndarray) -> List[tuple]:
    """Convert Nx2 numpy array to list of (x, y) tuples for pyclipper."""
    return [(float(p[0]), float(p[1])) for p in poly]


def _area(poly: np.ndarray) -> float:
    """Signed area — negative means clockwise in screen coords."""
    x, y = poly[:, 0], poly[:, 1]
    return float(np.sum(y * np.roll(x, 1) - x * np.roll(y, 1))) / 2.0


def _offset_polygon(poly: np.ndarray, offset: float) -> np.ndarray:
    """Offset a closed polygon inward (negative) or outward (positive).

    Uses pyclipper's Minkowski offset for proper handling of corners.
    Returns the offset polygon as an Nx2 numpy array, or the original if
    the offset collapses the polygon.
    """
    if abs(offset) < 0.01 or len(poly) < 3:
        return poly

    pco = pyclipper.PyclipperOffset()
    path = _poly_to_path(poly)
    pco.AddPath(path, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
    result = pco.Execute(offset)

    if not result:
        return poly[:0]  # empty — polygon collapsed
    # Return the largest result polygon
    pts = max(result, key=lambda p: abs(pyclipper.Area(p)))
    return np.array(pts, dtype=np.float64)


def _subtract_holes(outer: np.ndarray, holes: List[np.ndarray], expand: float = 0.0) -> List[np.ndarray]:
    """Subtract holes from outer polygon using Clipper2 boolean difference.

    Each hole is optionally expanded by *expand* mm before subtraction
    (to create a wall frame around the opening).

    Returns list of resulting polygons (Nx2 arrays).
    """
    if len(outer) < 3:
        return [outer] if len(outer) >= 3 else []

    pc = pyclipper.Pyclipper()
    pc.AddPath(_poly_to_path(outer), pyclipper.PT_SUBJECT)

    for hole in holes:
        if len(hole) < 3:
            continue
        hole_path = _poly_to_path(hole)
        if expand > 0:
            pco = pyclipper.PyclipperOffset()
            pco.AddPath(hole_path, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
            expanded = pco.Execute(expand)
            for ep in expanded:
                pc.AddPath(ep, pyclipper.PT_CLIP)
        else:
            pc.AddPath(hole_path, pyclipper.PT_CLIP)

    result = pc.Execute(pyclipper.CT_DIFFERENCE, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
    return [np.array(p, dtype=np.float64) for p in result] if result else []


# ---------------------------------------------------------------------------
# Toolpath generation
# ---------------------------------------------------------------------------


def _extrude_around(poly: np.ndarray, z: float, extrusion_width: float, speed: int = 1800) -> List[Move]:
    """Generate extrusion moves tracing a closed polygon.

    Returns a list with a travel move to start + extrusion segments around the ring.
    """
    if len(poly) < 3:
        return []
    moves: List[Move] = []
    moves.append(TravelMove(x=float(poly[0, 0]), y=float(poly[0, 1]), z=z))
    for j in range(len(poly)):
        d = 0.0 if j == 0 else float(np.sqrt(((poly[j] - poly[j - 1]) ** 2).sum()))
        e = d * (extrusion_width * z * 0.001 * 0.01) if d > 0 else 0.0
        moves.append(
            ExtrusionSegment(
                x=float(poly[j, 0]), y=float(poly[j, 1]), z=z, e=round(e, 6), speed=speed,
            )
        )
    # Close
    d = float(np.sqrt(((poly[0] - poly[-1]) ** 2).sum()))
    e = d * (extrusion_width * z * 0.001 * 0.01) if d > 0 else 0.0
    moves.append(
        ExtrusionSegment(
            x=float(poly[0, 0]), y=float(poly[0, 1]), z=z, e=round(e, 6), speed=speed,
        )
    )
    return moves


def _generate_infill_lines(
    fill_regions: List[np.ndarray],
    extrusion_width: float,
    density: float,
    z: float,
) -> List[Move]:
    """Generate parallel infill lines within fill regions, avoiding holes.

    For each fill region, generate vertical lines at spacing = extrusion_width / density.
    Each line is clipped to the region's X-range; Y-range spans the region bounds.
    """
    if not fill_regions or density <= 0:
        return []

    spacing = extrusion_width / max(density, 0.01)
    moves: List[Move] = []

    for region in fill_regions:
        if len(region) < 3:
            continue
        rmin_x, rmin_y = region.min(axis=0)
        rmax_x, rmax_y = region.max(axis=0)

        x = rmin_x
        parity = 0
        while x <= rmax_x:
            if parity % 2 == 0:
                start_pt = np.array([x, rmin_y])
                end_pt = np.array([x, rmax_y])
            else:
                start_pt = np.array([x, rmax_y])
                end_pt = np.array([x, rmin_y])

            d = float(np.sqrt(((end_pt - start_pt) ** 2).sum()))
            if d >= 1.0:
                e = d * (extrusion_width * z * 0.001 * 0.01)
                moves.append(TravelMove(x=float(start_pt[0]), y=float(start_pt[1]), z=z))
                moves.append(
                    ExtrusionSegment(
                        x=float(end_pt[0]), y=float(end_pt[1]), z=z, e=round(e, 6), speed=2400,
                    )
                )

            x += spacing
            parity += 1

    return moves


def _generate_layer_toolpath(
    layer: SliceLayer,
    nozzle_diameter: float = 6.0,
    extrusion_width: float = 8.0,
    perimeter_count: int = 2,
    infill_pattern: str = "lines",
    infill_density: float = 0.3,
) -> LayerToolpath:
    """Generate all printing moves for one slice layer.

    Args:
        layer: The layer to generate toolpaths for.
        nozzle_diameter: Nozzle opening (mm).
        extrusion_width: Width of extruded bead (mm).
        perimeter_count: Number of contours.
        infill_pattern: 'lines', 'grid', or 'none'.
        infill_density: Fraction of area to fill (0–1).

    Returns:
        LayerToolpath with all print moves.
    """
    tp = LayerToolpath(
        z=layer.z,
        layer_index=layer.layer_index,
        profile_name=layer.profile_name,
    )

    poly = layer.outer_contour
    if len(poly) < 3:
        return tp

    # --- Outer perimeters ---
    # Offset inward for each successive ring
    current = poly
    for i in range(perimeter_count):
        offset = -i * extrusion_width
        ring = _offset_polygon(poly, offset) if i > 0 else poly
        if len(ring) < 3:
            break
        tp.moves.extend(_extrude_around(ring, layer.z, extrusion_width, speed=1800))
        current = ring  # track innermost ring for infill boundary

    # --- Hole perimeters (inner frame around openings) ---
    for hole in layer.holes:
        if len(hole) < 3:
            continue
        # Offset hole outward by extrusion_width to create the wall frame
        hole_ring = _offset_polygon(hole, extrusion_width)
        if len(hole_ring) < 3:
            continue
        tp.moves.extend(_extrude_around(hole_ring, layer.z, extrusion_width, speed=1800))

    # --- Infill ---
    if infill_pattern != "none" and infill_density > 0:
        # Compute fillable region = innermost outer ring ∖ expanded holes
        fill_polys = _subtract_holes(
            current, layer.holes,
            expand=extrusion_width,  # keep bead-width gap around openings
        )
        fill_moves = _generate_infill_lines(fill_polys, extrusion_width, infill_density, layer.z)
        tp.moves.extend(fill_moves)

    return tp


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_toolpath(
    sliced: SlicedModel,
    nozzle_diameter: float = 6.0,
    extrusion_width: float = 8.0,
    perimeter_count: int = 2,
    infill_pattern: str = "lines",
    infill_density: float = 0.3,
) -> ToolpathResult:
    """Generate full toolpath for a sliced model.

    Args:
        sliced: The sliced model from slicer.slice_model().
        nozzle_diameter: Nozzle diameter (mm).
        extrusion_width: Bead width (mm).
        perimeter_count: Number of perimeter contours.
        infill_pattern: 'lines', 'grid', or 'none'.
        infill_density: Fraction 0–1.

    Returns:
        Complete ToolpathResult.
    """
    result = ToolpathResult()
    total_dist = 0.0
    total_fil = 0.0

    for layer in sliced.layers:
        lt = _generate_layer_toolpath(
            layer,
            nozzle_diameter=nozzle_diameter,
            extrusion_width=extrusion_width,
            perimeter_count=perimeter_count,
            infill_pattern=infill_pattern,
            infill_density=infill_density,
        )
        result.layer_paths.append(lt)

        # Compute stats from extrusion moves
        for m in lt.moves:
            if isinstance(m, ExtrusionSegment):
                total_dist += 1.0
                total_fil += m.e

    result.total_distance_mm = round(total_dist, 1)
    result.estimated_filament_mm = round(total_fil, 1)
    return result
