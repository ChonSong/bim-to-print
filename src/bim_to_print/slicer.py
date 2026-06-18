"""
slicer.py — Slice extruded profiles into horizontal print layers.

Produces a stack of 2D contours (one per layer) with a configurable
layer height. Each layer references the parent profile and its Z‑height.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from .ifc_reader import ExtrudedProfile


@dataclass
class SliceLayer:
    """A single horizontal print layer."""

    z: float  # absolute Z of this layer
    layer_index: int
    outer_contour: np.ndarray  # N×2 array of outer boundary points (clockwise)
    profile_name: str  # parent profile name
    profile_type: str


@dataclass
class SlicedModel:
    """All layers for a building model."""

    layers: List[SliceLayer] = field(default_factory=list)
    layer_height: float = 5.0
    total_layers: int = 0


def _make_polygon_clockwise(points: np.ndarray) -> np.ndarray:
    """Ensure polygon vertices are clockwise (needed for contour offset)."""
    if len(points) < 3:
        return points
    # Shoelace signed area
    x, y = points[:, 0], points[:, 1]
    area = 0.5 * np.sum(y * np.roll(x, 1) - x * np.roll(y, 1))
    if area > 0:  # counter-clockwise → reverse
        return points[::-1]
    return points


def slice_profile(
    profile: ExtrudedProfile,
    layer_height: float,
    z_base: float = 0.0,
) -> List[SliceLayer]:
    """Slice a single extruded profile into layers.

    Args:
        profile: The extruded geometry to slice.
        layer_height: Thickness of each printed layer (mm).
        z_base: Global Z offset to add.

    Returns:
        List of SliceLayer, one per layer.
    """
    bottom = profile.base_elevation + z_base
    top = bottom + profile.height

    points = np.array(profile.points_2d, dtype=np.float64)
    if len(points) < 3:
        return []

    points = _make_polygon_clockwise(points)

    # Number of layers
    num_layers = max(1, int(round(profile.height / layer_height)))
    actual_lh = profile.height / num_layers  # distribute evenly

    layers: List[SliceLayer] = []
    for i in range(num_layers):
        z = bottom + i * actual_lh + actual_lh / 2  # centre of layer
        layers.append(
            SliceLayer(
                z=z,
                layer_index=i,
                outer_contour=points.copy(),
                profile_name=profile.name,
                profile_type=profile.ifc_type,
            )
        )

    return layers


def slice_model(
    profiles: List[ExtrudedProfile],
    layer_height: float = 5.0,
) -> SlicedModel:
    """Slice all profiles into a unified SlicedModel sorted by Z.

    Profiles that overlap in XY are *not* booleaned together — each
    profile remains independent so the toolpath generator can handle
    walls, columns, etc. separately.
    """
    all_layers: List[SliceLayer] = []
    for prof in profiles:
        all_layers.extend(slice_profile(prof, layer_height))

    # Sort by Z then by name for deterministic order
    all_layers.sort(key=lambda l: (l.z, l.profile_name))

    return SlicedModel(
        layers=all_layers,
        layer_height=layer_height,
        total_layers=len(all_layers),
    )
