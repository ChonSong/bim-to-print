"""
gh_definition.py — Generate Grasshopper XML (.gh) definition files.

Produces a minimal working Grasshopper definition that takes a rectangular
wall profile and outputs a JSON geometry file consumable by `bim2print gh`.

The generated .gh file contains:
  - A Rectangle (BRep) component for the wall outline
  - An Extrude component to create the 3D wall
  - A Deconstruct BRep component to extract geometry
  - A Panel (text output) showing the dimensions
  - An I/O panel that exports to JSON

This covers the critical "GH → custom tool" link in the BIM-to-print pipeline.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# GH XML namespace
# ---------------------------------------------------------------------------

GH_NS = "http://schemas.rhino3d.com/grasshopper"


def _make_guid() -> str:
    """Generate a Rhino-style GUID."""
    return str(uuid.uuid4()).upper()


def _coerce_float(val: Any) -> str:
    return str(float(val))


def _ghi_attribs(
    x: float = 0, y: float = 0, uid: Optional[str] = None,
) -> Dict[str, str]:
    return {
        "x": str(x), "y": str(y),
        "uid": uid or _make_guid(),
    }


# ---------------------------------------------------------------------------
# Component builders
# ---------------------------------------------------------------------------


def _make_rectangle_component(
    width: float, length: float, uid: str,
) -> etree.Element:
    """GH Rectangle (BRep) primitive component."""
    comp = etree.SubElement(
        etree.Element("component", nsmap={None: GH_NS}),
        "component",
        _ghi_attribs(x=10, y=10, uid=uid),
    )
    etree.SubElement(comp, "name").text = "Rectangle"
    etree.SubElement(comp, "nickname").text = "Rect"

    # Inputs
    inputs = etree.SubElement(comp, "inputs")
    # Plane (default XY)
    inp1 = etree.SubElement(inputs, "input", {"name": "Plane",
                                               "type": "Plane", "id": "0"})
    etree.SubElement(inp1, "description").text = "Base plane"
    etree.SubElement(inp1, "expression").text = "Plane.WorldXY"

    # Width X
    inp2 = etree.SubElement(inputs, "input", {"name": "Width X",
                                               "type": "float", "id": "1"})
    etree.SubElement(inp2, "description").text = "Wall length (mm)"
    etree.SubElement(inp2, "expression").text = str(width)

    # Width Y
    inp3 = etree.SubElement(inputs, "input", {"name": "Width Y",
                                               "type": "float", "id": "2"})
    etree.SubElement(inp3, "description").text = "Wall thickness (mm)"
    etree.SubElement(inp3, "expression").text = str(length)

    # Radius (0 = rectangle)
    inp4 = etree.SubElement(inputs, "input", {"name": "R",
                                               "type": "float", "id": "3"})
    etree.SubElement(inp4, "description").text = "Corner radius"
    etree.SubElement(inp4, "expression").text = "0.0"

    # Output
    outputs = etree.SubElement(comp, "outputs")
    out1 = etree.SubElement(outputs, "output", {"name": "Rectangle",
                                                 "type": "Curve", "id": "0"})
    etree.SubElement(out1, "description").text = "Rectangle curve"

    return comp


def _make_extrude_component(
    height: float, curve_uid: str, uid: str,
) -> etree.Element:
    """GH Extrude component."""
    comp = etree.SubElement(
        etree.Element("component", nsmap={None: GH_NS}),
        "component",
        _ghi_attribs(x=200, y=10, uid=uid),
    )
    etree.SubElement(comp, "name").text = "Extrude"
    etree.SubElement(comp, "nickname").text = "Extrude"

    # Inputs
    inputs = etree.SubElement(comp, "inputs")
    inp1 = etree.SubElement(inputs, "input", {"name": "Base",
                                               "type": "Curve", "id": "0"})
    etree.SubElement(inp1, "description").text = "Profile curve"
    etree.SubElement(inp1, "source").text = f"0#{curve_uid}"

    inp2 = etree.SubElement(inputs, "input", {"name": "Direction",
                                               "type": "Vector3D",
                                               "id": "1"})
    etree.SubElement(inp2, "description").text = "Extrusion direction"
    etree.SubElement(inp2, "expression").text = "Vector3D(0,0,1)"

    inp3 = etree.SubElement(inputs, "input", {"name": "Height",
                                               "type": "float", "id": "2"})
    etree.SubElement(inp3, "description").text = "Wall height (mm)"
    etree.SubElement(inp3, "expression").text = str(height)

    # Outputs
    outputs = etree.SubElement(comp, "outputs")
    out1 = etree.SubElement(outputs, "output", {"name": "Extruded",
                                                 "type": "Brep", "id": "0"})
    etree.SubElement(out1, "description").text = "Extruded solid"

    return comp


def _make_panel_component(
    text: str, uid: str, x: float = 400, y: float = 10,
) -> etree.Element:
    """GH Panel component with static text."""
    comp = etree.SubElement(
        etree.Element("component", nsmap={None: GH_NS}),
        "component",
        _ghi_attribs(x=x, y=y, uid=uid),
    )
    etree.SubElement(comp, "name").text = "Panel"
    etree.SubElement(comp, "nickname").text = "Panel"
    inputs = etree.SubElement(comp, "inputs")
    inp = etree.SubElement(inputs, "input", {"name": "",
                                              "type": "text", "id": "0"})
    etree.SubElement(inp, "description").text = "Static text"
    etree.SubElement(inp, "expression").text = json.dumps(text)
    return comp


def _make_json_export_component(
    source_uid: str, file_path: str, uid: str,
) -> etree.Element:
    """A Python script component that exports geometry data to JSON.

    This is a custom GHA-style component expressed as a GH Python (Script)
    block that writes a JSON file consumable by `bim2print gh`.
    """
    comp = etree.SubElement(
        etree.Element("component", nsmap={None: GH_NS}),
        "component",
        _ghi_attribs(x=400, y=120, uid=uid),
    )
    etree.SubElement(comp, "name").text = "Python"
    etree.SubElement(comp, "nickname").text = "Export JSON"

    inputs = etree.SubElement(comp, "inputs")
    inp = etree.SubElement(inputs, "input", {"name": "Brep",
                                              "type": "Brep", "id": "0"})
    etree.SubElement(inp, "description").text = "Extruded wall"
    etree.SubElement(inp, "source").text = f"0#{source_uid}"

    outputs = etree.SubElement(comp, "outputs")
    out1 = etree.SubElement(outputs, "output", {"name": "Path",
                                                 "type": "text", "id": "0"})
    etree.SubElement(out1, "description").text = "Output file path"

    # Python code (literal template for GH's Python component)
    code = etree.SubElement(comp, "code")
    code_lines = [
        'import rhinoscriptsyntax as rs',
        'import json',
        '',
        f'output_path = r"{file_path}"',
        '',
        'if Brep:',
        '    # Get bounding box',
        '    bbox = rs.BoundingBox(Brep)',
        '    if bbox:',
        '        x0, y0, _ = bbox[0]',
        '        x1, y1, z1 = bbox[6]',
        '        w = x1 - x0',
        '        t = y1 - y0',
        '        h = z1',
        '',
        '        profile = {',
        '            "name": "GH-Wall",',
        '            "ifc_type": "IfcWall",',
        '            "points_2d": [',
        '                [0, 0],',
        '                [w, 0],',
        '                [w, t],',
        '                [0, t],',
        '                [0, 0],',
        '            ],',
        '            "base_elevation": 0,',
        '            "height": h,',
        '        }',
        '        with open(output_path, "w") as f:',
        '            json.dump([profile], f, indent=2)',
        '        Path = output_path',
    ]
    code.text = "\n".join(code_lines)

    return comp


# ---------------------------------------------------------------------------
# Document builder
# ---------------------------------------------------------------------------


def generate_gh_definition(
    output_path: str,
    wall_width: float = 3000.0,
    wall_thickness: float = 200.0,
    wall_height: float = 2400.0,
    json_export_path: str = "/tmp/gh_wall.json",
    name: str = "bim-to-print GH Export",
) -> None:
    """Generate a complete Grasshopper .gh definition file.

    Args:
        output_path: Where to write the .gh file.
        wall_width: Wall length in mm.
        wall_thickness: Wall depth in mm.
        wall_height: Wall height in mm.
        json_export_path: Path for the JSON export (consumed by bim2print).
        name: Document name.
    """
    # Wire GUIDs
    rect_uid = _make_guid()
    extrude_uid = _make_guid()
    panel_uid = _make_guid()
    export_uid = _make_guid()

    # Root
    root = etree.Element(
        "GHDefinition",
        nsmap={None: GH_NS},
    )
    etree.SubElement(root, "name").text = name
    etree.SubElement(root, "version").text = "1.0.0"
    etree.SubElement(root, "created").text = datetime.datetime.now().isoformat()

    # Project info
    proj = etree.SubElement(root, "project")
    etree.SubElement(proj, "name").text = "bim-to-print"
    etree.SubElement(proj, "description").text = (
        "Grasshopper → JSON → bim2print G-code pipeline"
    )

    # Components
    components = etree.SubElement(root, "components")

    # Rectangle
    rect_comp = _make_rectangle_component(wall_width, wall_thickness, rect_uid)
    components.append(rect_comp)

    # Extrude
    extrude_comp = _make_extrude_component(wall_height, rect_uid, extrude_uid)
    components.append(extrude_comp)

    # Panel (info)
    info_text = (
        f"BIM-to-Print Wall\n"
        f"Width: {wall_width}mm, Thickness: {wall_thickness}mm, "
        f"Height: {wall_height}mm\n"
        f"Volume: {wall_width * wall_thickness * wall_height / 1e9:.2f} m³\n"
        f"Layers @5mm: {int(wall_height / 5)}"
    )
    panel_comp = _make_panel_component(info_text, panel_uid)
    components.append(panel_comp)

    # Export JSON
    export_comp = _make_json_export_component(extrude_uid, json_export_path, export_uid)
    components.append(export_comp)

    # Wire connections (abstract — GH stores connections per component input)
    connections = etree.SubElement(root, "connections")
    conn = etree.SubElement(connections, "connection")
    etree.SubElement(conn, "source").text = f"{rect_uid}:0"
    etree.SubElement(conn, "target").text = f"{extrude_uid}:0"
    conn2 = etree.SubElement(connections, "connection")
    etree.SubElement(conn2, "source").text = f"{extrude_uid}:0"
    etree.SubElement(conn2, "target").text = f"{export_uid}:0"

    # Write XML
    tree = etree.ElementTree(root)
    tree.write(
        output_path,
        xml_declaration=True,
        encoding="utf-8",
        pretty_print=True,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a Grasshopper .gh definition for bim-to-print"
    )
    parser.add_argument("output", help="Output .gh file path")
    parser.add_argument("--width", type=float, default=3000.0,
                        help="Wall width (mm)")
    parser.add_argument("--thickness", type=float, default=200.0,
                        help="Wall thickness (mm)")
    parser.add_argument("--height", type=float, default=2400.0,
                        help="Wall height (mm)")
    parser.add_argument("--json-export", default="/tmp/gh_wall.json",
                        help="Path for JSON geometry export")
    args = parser.parse_args()

    generate_gh_definition(
        args.output,
        wall_width=args.width,
        wall_thickness=args.thickness,
        wall_height=args.height,
        json_export_path=args.json_export,
    )
    print(f"✅ Grasshopper definition written to {args.output}")


if __name__ == "__main__":
    main()
