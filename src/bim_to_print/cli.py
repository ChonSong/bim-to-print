"""
cli.py — Command-line interface for bim-to-print.

Usage:
    bim2print ifc input.ifc output.gcode --layer-height 5
    bim2print gh input.json output.gcode
"""

from __future__ import annotations

import json
import sys

import click

from . import __version__


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------
_shared_opts = [
    click.option("--layer-height", default=5.0, help="Layer height in mm", show_default=True),
    click.option("--nozzle-diameter", default=6.0, help="Nozzle diameter in mm", show_default=True),
    click.option("--extrusion-width", default=8.0, help="Bead width in mm", show_default=True),
    click.option("--perimeter-count", default=2, help="Number of perimeter contours", show_default=True),
    click.option("--infill-pattern", default="lines", type=click.Choice(["lines", "grid", "none"]), show_default=True),
    click.option("--infill-density", default=0.3, type=float, help="Infill fraction 0–1", show_default=True),
    click.option("--verbose", "-v", is_flag=True, help="Print detailed output"),
]


def _add_opts(func):
    for opt in reversed(_shared_opts):
        func = opt(func)
    return func


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__version__)
def main():
    """bim-to-print — BIM file to 3D concrete printing G-code."""


@main.command()
@click.argument("ifc_path", type=click.Path(exists=True))
@click.argument("gcode_path", type=click.Path())
@_add_opts
def ifc(ifc_path: str, gcode_path: str, **kwargs):
    """Convert an IFC file directly to printable G-code."""
    try:
        from .pipeline import pipeline

        result = pipeline(ifc_path, gcode_path, **kwargs)
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"✅ Pipeline complete")
    click.echo(f"   Profiles : {result['profiles']}")
    click.echo(f"   Layers   : {result['layers']}")
    click.echo(f"   Distance : {result['total_distance_mm']:.1f} mm")
    click.echo(f"   Filament : {result['estimated_filament_mm']:.1f} mm")
    click.echo(f"   Output   : {result['gcode_file']}")


@main.command()
@click.argument("gh_json", type=click.Path(exists=True))
@click.argument("gcode_path", type=click.Path())
@_add_opts
def gh(gh_json: str, gcode_path: str, **kwargs):
    """Generate G-code from a Grasshopper-derived JSON geometry file.

    The JSON must be a list of profile objects:
      [{"name":"Wall-1", "points_2d": [[x,y], ...], "base_elevation": 0, "height": 3000}]
    """
    with open(gh_json) as f:
        data = json.load(f)

    from .pipeline import pipeline_from_gh

    result = pipeline_from_gh(data, gcode_path, **kwargs)

    click.echo(f"✅ GH pipeline complete")
    click.echo(f"   Profiles : {result['profiles']}")
    click.echo(f"   Layers   : {result['layers']}")
    click.echo(f"   Output   : {result['gcode_file']}")


@main.command()
@click.option("--output", "-o", default="-", help="Output G-code path (default: stdout)")
@click.option("--width", default=100, type=float, help="Wall width in mm")
@click.option("--height", default=200, type=float, help="Wall height in mm")
@_add_opts
def demo(output: str, width: float, height: float, **kwargs):
    """Run the full pipeline on a demo rectangular wall.

    Useful for testing without an IFC file.
    """
    demo_profiles = [
        {
            "name": "Demo-Wall",
            "ifc_type": "IfcWall",
            "points_2d": [
                [0.0, 0.0],
                [width, 0.0],
                [width, 25.0],
                [0.0, 25.0],
                [0.0, 0.0],
            ],
            "base_elevation": 0.0,
            "height": height,
        }
    ]

    from .pipeline import pipeline_from_gh

    gcode_path = output if output != "-" else "/tmp/demo_output.gcode"
    result = pipeline_from_gh(demo_profiles, gcode_path, **kwargs)

    click.echo(f"✅ Demo pipeline complete")
    click.echo(f"   Wall     : {width}×25×{height} mm")
    click.echo(f"   Layers   : {result['layers']}")
    click.echo(f"   Distance : {result['total_distance_mm']:.1f} mm")
    click.echo(f"   Filament : {result['estimated_filament_mm']:.1f} mm")
    click.echo(f"   Output   : {gcode_path}")

    if output == "-":
        with open(gcode_path) as f:
            click.echo("\n" + f.read())


if __name__ == "__main__":
    main()
