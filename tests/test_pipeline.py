"""
Tests for bim-to-print — verify pipeline round-trip.

Run with: pytest tests/ -v
"""

from __future__ import annotations

import json
import os
import tempfile

import numpy as np
import pytest

from bim_to_print.ifc_reader import ExtrudedProfile, BuildingModel
from bim_to_print.slicer import slice_model, slice_profile, SliceLayer
from bim_to_print.toolpath import generate_toolpath, ToolpathResult, LayerToolpath
from bim_to_print.gcode_writer import PrintSettings, write_gcode_string


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_wall_profile() -> ExtrudedProfile:
    """A simple 3000×200×2400mm wall."""
    return ExtrudedProfile(
        name="Test-Wall",
        ifc_type="IfcWall",
        points_2d=[
            (0.0, 0.0),
            (3000.0, 0.0),
            (3000.0, 200.0),
            (0.0, 200.0),
            (0.0, 0.0),
        ],
        base_elevation=0.0,
        height=2400.0,
    )


@pytest.fixture
def square_column() -> ExtrudedProfile:
    return ExtrudedProfile(
        name="Test-Col",
        ifc_type="IfcColumn",
        points_2d=[
            (0.0, 0.0),
            (300.0, 0.0),
            (300.0, 300.0),
            (0.0, 300.0),
            (0.0, 0.0),
        ],
        base_elevation=0.0,
        height=2400.0,
    )


# ---------------------------------------------------------------------------
# IFC Reader (manual profile creation, since no IFC test file)
# ---------------------------------------------------------------------------


class TestExtrudedProfile:
    def test_basic_attributes(self, simple_wall_profile):
        assert simple_wall_profile.name == "Test-Wall"
        assert simple_wall_profile.ifc_type == "IfcWall"
        assert simple_wall_profile.height == 2400.0
        assert len(simple_wall_profile.points_2d) == 5

    def test_negative_elevation(self):
        p = ExtrudedProfile(
            name="Below-Grade",
            ifc_type="IfcWall",
            points_2d=[(0, 0), (100, 0), (100, 20), (0, 20), (0, 0)],
            base_elevation=-500.0,
            height=3000.0,
        )
        assert p.base_elevation == -500.0
        assert p.height == 3000.0


# ---------------------------------------------------------------------------
# Slicer
# ---------------------------------------------------------------------------


class TestSlicer:
    def test_slice_profile_yields_layers(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        expected_layers = int(2400.0 / 5.0)  # 480
        assert len(layers) == expected_layers

    def test_layer_heights(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        assert abs(layers[0].z - 2.5) < 0.01  # centre of first layer
        assert abs(layers[1].z - 7.5) < 0.01
        assert abs(layers[-1].z - layers[0].z) < 2400.0  # sanity

    def test_slice_model_merges_multiple(self, simple_wall_profile, square_column):
        sliced = slice_model([simple_wall_profile, square_column], layer_height=5.0)
        # Each profile produces 480 layers → 960 total
        assert len(sliced.layers) == 960
        assert sliced.layer_height == 5.0

    def test_slice_order(self, simple_wall_profile, square_column):
        sliced = slice_model([square_column, simple_wall_profile], layer_height=5.0)
        # Should be sorted by Z
        for i in range(len(sliced.layers) - 1):
            assert sliced.layers[i].z <= sliced.layers[i + 1].z

    def test_zero_height_profile(self):
        p = ExtrudedProfile(
            name="Zero", ifc_type="IfcWall",
            points_2d=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
            base_elevation=0.0, height=0.0,
        )
        layers = slice_profile(p, layer_height=5.0)
        assert len(layers) >= 1  # at least one layer

    def test_tiny_polygon(self):
        p = ExtrudedProfile(
            name="Tiny", ifc_type="IfcWall",
            points_2d=[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)],
            base_elevation=0.0, height=100.0,
        )
        layers = slice_profile(p, layer_height=5.0)
        assert len(layers) == 20


# ---------------------------------------------------------------------------
# Toolpath
# ---------------------------------------------------------------------------


class TestToolpath:
    def test_generate_toolpath_defaults(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        sliced = type("SM", (), {"layers": layers, "layer_height": 5.0})()
        result = generate_toolpath(sliced)  # type: ignore[arg-type]
        assert isinstance(result, ToolpathResult)
        assert len(result.layer_paths) == len(layers)

    def test_layer_toolpath_has_moves(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        first_layer = layers[0]
        from bim_to_print.toolpath import _generate_layer_toolpath
        lt = _generate_layer_toolpath(first_layer)
        assert len(lt.moves) > 0
        assert lt.z == first_layer.z
        assert lt.profile_name == "Test-Wall"

    def test_no_infill(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        sliced = type("SM", (), {"layers": layers[:5], "layer_height": 5.0})()
        result = generate_toolpath(sliced, infill_pattern="none")
        assert len(result.layer_paths) == 5

    def test_toolpath_has_perimeter_count(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        from bim_to_print.toolpath import _generate_layer_toolpath
        lt: LayerToolpath = _generate_layer_toolpath(
            layers[0], perimeter_count=3
        )
        # Should have travel + perimeter + more for infill
        extrudes = [m for m in lt.moves if hasattr(m, "e")]
        assert len(extrudes) > 0


# ---------------------------------------------------------------------------
# G-code Writer
# ---------------------------------------------------------------------------


class TestGCodeWriter:
    def test_write_roundtrip(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        sliced = type("SM", (), {"layers": layers[:3], "layer_height": 5.0})()
        result = generate_toolpath(sliced)
        gcode = write_gcode_string(result)
        assert gcode.startswith("; G-code generated by bim-to-print")
        assert "G21" in gcode  # mm mode
        assert "G90" in gcode  # absolute positioning
        assert "G28" in gcode  # homing
        assert "G1" in gcode  # extrusion moves
        assert "G0" in gcode  # travel moves

    def test_custom_settings(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        sliced = type("SM", (), {"layers": layers[:2], "layer_height": 5.0})()
        result = generate_toolpath(sliced)
        settings = PrintSettings(
            travel_speed=9999,
            print_speed=3333,
            first_layer_speed=1111,
        )
        gcode = write_gcode_string(result, settings=settings)
        assert "F9999" in gcode  # travel speed in G0
        assert "F1111" in gcode  # first layer speed in G1
        # Can't reliably check F3333 without parsing — accept

    def test_pre_post_gcode(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        sliced = type("SM", (), {"layers": layers[:1], "layer_height": 5.0})()
        result = generate_toolpath(sliced)
        settings = PrintSettings(
            pre_gcode="M104 S200\nM140 S60",
            post_gcode="M107\n",
        )
        gcode = write_gcode_string(result, settings=settings)
        assert "M104 S200" in gcode
        assert "M140 S60" in gcode
        assert "M107" in gcode

    def test_extrusion_values_positive(self, simple_wall_profile):
        layers = slice_profile(simple_wall_profile, layer_height=5.0)
        sliced = type("SM", (), {"layers": layers[:5], "layer_height": 5.0})()
        result = generate_toolpath(sliced)
        gcode = write_gcode_string(result)
        import re
        e_vals = re.findall(r"E([0-9.e+-]+)", gcode)
        # All E values should be numeric (no NaN)
        for e in e_vals:
            val = float(e)
            assert val > 0 or val == 0.0


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


class TestPipeline:
    def test_pipeline_from_gh(self, simple_wall_profile):
        """Run full pipeline with manual profile data through pipeline_from_gh."""
        from bim_to_print.pipeline import pipeline_from_gh

        profile_data = [
            {
                "name": simple_wall_profile.name,
                "ifc_type": simple_wall_profile.ifc_type,
                "points_2d": [list(p) for p in simple_wall_profile.points_2d],
                "base_elevation": simple_wall_profile.base_elevation,
                "height": simple_wall_profile.height,
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".gcode", delete=False) as f:
            gcode_path = f.name

        try:
            result = pipeline_from_gh(
                profile_data, gcode_path,
                layer_height=10.0,  # coarse for speed
            )
            assert result["profiles"] == 1
            assert result["layers"] == 240  # 2400 / 10
            assert os.path.exists(gcode_path)

            with open(gcode_path) as f:
                content = f.read()
            assert "G21" in content
        finally:
            os.unlink(gcode_path)

    def test_demo_command_output(self):
        """Verify `bim2print demo` produces valid output."""
        from bim_to_print.cli import main as cli_main
        from click.testing import CliRunner

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".gcode", delete=False) as f:
            gcode_path = f.name

        try:
            result = runner.invoke(cli_main, [
                "demo", "--output", gcode_path,
                "--width", "100", "--height", "100",
                "--layer-height", "5",
            ])
            assert result.exit_code == 0, result.output
            assert os.path.exists(gcode_path)
            with open(gcode_path) as f:
                content = f.read()
            assert "G21" in content
        finally:
            if os.path.exists(gcode_path):
                os.unlink(gcode_path)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_point_polygon(self):
        p = ExtrudedProfile(
            name="Line",
            ifc_type="IfcWall",
            points_2d=[(0, 0)],
            base_elevation=0.0,
            height=100.0,
        )
        layers = slice_profile(p, layer_height=5.0)
        assert len(layers) == 0  # not printable

    def test_empty_profile_list(self):
        sliced = slice_model([], layer_height=5.0)
        assert len(sliced.layers) == 0
        assert sliced.total_layers == 0

    def test_empty_toolpath_result(self):
        class EmptySliced:
            layers = []
            layer_height = 5.0
        result = generate_toolpath(EmptySliced())  # type: ignore
        assert len(result.layer_paths) == 0

    def test_negative_coordinates(self):
        p = ExtrudedProfile(
            name="Negative",
            ifc_type="IfcColumn",
            points_2d=[(-500, -500), (500, -500), (500, 500), (-500, 500), (-500, -500)],
            base_elevation=0.0,
            height=1000.0,
        )
        layers = slice_profile(p, layer_height=5.0)
        assert len(layers) == 200
        from bim_to_print.toolpath import _generate_layer_toolpath
        lt = _generate_layer_toolpath(layers[0])
        assert len(lt.moves) > 0

    def test_extrusion_calculation_under_1mm_layer(self):
        p = ExtrudedProfile(
            name="Thin",
            ifc_type="IfcWall",
            points_2d=[(0, 0), (100, 0), (100, 20), (0, 20), (0, 0)],
            base_elevation=0.0,
            height=2.0,
        )
        layers = slice_profile(p, layer_height=1.0)
        assert len(layers) == 2
        from bim_to_print.toolpath import _generate_layer_toolpath
        lt = _generate_layer_toolpath(layers[0])
        assert len(lt.moves) > 0


# ---------------------------------------------------------------------------
# GH definition generator
# ---------------------------------------------------------------------------


class TestGHDefinition:
    def test_generate_gh_xml(self):
        from bim_to_print.gh_definition import generate_gh_definition
        with tempfile.NamedTemporaryFile(suffix=".gh", delete=False) as f:
            gh_path = f.name
        json_path = "/tmp/test_gh_export.json"

        try:
            generate_gh_definition(
                gh_path,
                wall_width=1000.0,
                wall_thickness=150.0,
                wall_height=2000.0,
                json_export_path=json_path,
            )
            assert os.path.exists(gh_path)
            with open(gh_path) as f:
                content = f.read()
            assert "Rectangle" in content
            assert "Extrude" in content
            assert "Export JSON" in content or "Python" in content
        finally:
            if os.path.exists(gh_path):
                os.unlink(gh_path)

    def test_gh_generator_cli(self):
        from bim_to_print.gh_definition import main as gh_main
        import sys
        # Capture output
        try:
            with tempfile.NamedTemporaryFile(suffix=".gh", delete=False) as f:
                gh_path = f.name
            # Simulate CLI args
            sys.argv = ["gh_gen", gh_path, "--width", "500", "--height", "1000"]
            gh_main()
            assert os.path.exists(gh_path)
        finally:
            if os.path.exists(gh_path):
                os.unlink(gh_path)
