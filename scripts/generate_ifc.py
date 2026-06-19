#!/usr/bin/env python3
"""Generate a minimal but valid IFC file from GH-style profile data.

Produces IFC2X3 (IFC 2x3) STEP file that can be loaded by IFC.js / xeokit.
Walls with window/door openings as proper IfcOpeningElement,
columns as IfcColumn, with correct local placement and extrusions.

Usage:
    python scripts/generate_ifc.py examples/demo_house.json docs/examples/demo_house.ifc
"""

import json
import math
import sys
import os
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from bim_to_print.ifc_reader import ExtrudedProfile, Opening


# ── IFC entity IDs ──────────────────────────────────────────────────────────

_counter = [0]

def new_id() -> int:
    _counter[0] += 1
    return _counter[0]

def ref(id_: int) -> str:
    return f"#{id_}"


# ── IFC geometry helpers ────────────────────────────────────────────────────

def fmt_float(v: float) -> str:
    return f"{v:.6f}"

def fmt_point(x, y, z=0.0) -> str:
    return f"({fmt_float(x)},{fmt_float(y)},{fmt_float(z)})"

def fmt_polyline(points_2d) -> str:
    """Return points for IfcPolyline in 3D (z=0)."""
    pts = ",".join(fmt_point(x, y, 0.0) for x, y in points_2d)
    return f"({pts})"


# ── IFC builder ─────────────────────────────────────────────────────────────

def build_ifc(profiles: list[ExtrudedProfile], output_path: str) -> str:
    lines: list[str] = []
    P = lambda: ref(new_id())  # noqa

    # ── Header ──
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    desc = "demo_house 3DCP"
    lines.extend([
        "ISO-10303-21;",
        f"HEADER;",
        f"FILE_DESCRIPTION(('{desc}'),'2;1');",
        f"FILE_NAME('{os.path.basename(output_path)}','{now}',('bim2print'),('bim2print'),'bim2print','bim2print','');",
        f"FILE_SCHEMA(('IFC2X3'));",
        "ENDSEC;",
        "DATA;",
    ])

    # ── Conversions ──
    # Units: mm
    length_unit = P()
    lines.append(f"{length_unit}=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);")
    conv_unit = P()
    lines.append(f"{conv_unit}=IFCCONVERSIONBASEDUNIT(*,.PLANEANGLEUNIT.,'DEGREE',(1.0,),#0);")
    unit_assign = P()
    lines.append(f"{unit_assign}=IFCUNITASSIGNMENT(({length_unit},{conv_unit}));")

    # Project + site + building
    proj = P()
    site = P()
    bldg = P()
    owner = P()
    lines.append(f"{ref(owner)}=IFCORGANIZATION($,'bim2print',$,$,$);")
    app = P()
    lines.append(f"{app}=IFCAPPLICATION({ref(owner)},'0.2.0','bim-to-print','bim-to-print');")
    person = P()
    lines.append(f"{person}=IFCPERSON($,$,$,$,$,$,$);")
    owner_hist = P()
    lines.append(f"{owner_hist}=IFCOWNERHISTORY({ref(person)},{ref(app)},$,.ADDED.,$,{ref(person)},{ref(app)},{now});")

    # Local placement for project origin
    origin_placement = P()
    lines.append(f"{origin_placement}=IFCLOCALPLACEMENT($,#0);")

    lines.append(f"{proj}=IFCPROJECT('{proj}',{ref(owner_hist)},'Demo House',$,$,$,$,({ref(unit_assign)}),#0);")
    lines.append(f"{site}=IFCSITE('{site}',{ref(owner_hist)},'Site',$,$,{ref(origin_placement)},$,$,.ELEMENT.,($,$,$),$,$);")
    lines.append(f"{bldg}=IFCBUILDING('{bldg}',{ref(owner_hist)},'Demo House',$,$,{ref(origin_placement)},$,$,.ELEMENT.,$,#0);")
    lines.append(f"{ref(P())}=IFCRELAGGREGATES('{P()}',{ref(owner_hist)},$,$,{ref(proj)},({ref(site)}));")
    lines.append(f"{ref(P())}=IFCRELAGGREGATES('{P()}',{ref(owner_hist)},$,$,{ref(site)},({ref(bldg)}));")

    # Standard material: concrete
    mat = P()
    lines.append(f"{mat}=IFCMATERIAL('Concrete');")
    mat_layer_set = P()
    lines.append(f"{mat_layer_set}=IFCMATERIALLAYERSET(({ref(P())}),'Concrete');")
    # We'll associate via IfcRelAssociatesMaterial after each element

    # ── Process each profile ──
    building_elements: list[str] = []
    openings_for_profile: dict[str, list[str]] = {}
    element_ids: list[str] = []

    for prof in profiles:
        name = prof.name
        ifc_type = getattr(prof, 'ifc_type', 'IfcBuildingElementProxy')
        pts = prof.points_2d
        height = prof.height
        base_z = prof.base_elevation

        # Wall type mapping
        if 'wall' in ifc_type.lower():
            ifc_entity = 'IFCWALLSTANDARDCASE'
        elif 'column' in ifc_type.lower():
            ifc_entity = 'IFCCOLUMN'
        else:
            ifc_entity = 'IFCBUILDINGELEMENTPROXY'

        # 1. Local placement for this element
        min_x = min(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        max_x = max(p[0] for p in pts)
        max_y = max(p[1] for p in pts)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2

        # Local placement: origin at base center
        axis_place = P()
        lines.append(
            f"{axis_place}=IFCAXIS2PLACEMENT3D("
            f"{ref(P())},{ref(P())},{ref(P())});"
        )
        # Location point
        loc = P()
        lines.append(f"{loc}=IFCCARTESIANPOINT({fmt_point(cx, cy, base_z)});")
        # Z axis (up)
        z_axis = P()
        lines.append(f"{z_axis}=IFCDIRECTION((0.,0.,1.));")
        # X axis (ref direction)
        x_dir = P()
        lines.append(f"{x_dir}=IFCDIRECTION((1.,0.,0.));")
        # Recreate axis2placement
        lines.append(
            f"{axis_place}=IFCAXIS2PLACEMENT3D({ref(loc)},{ref(z_axis)},{ref(x_dir)});"
        )

        elem_placement = P()
        lines.append(f"{elem_placement}=IFCLOCALPLACEMENT({ref(origin_placement)},{ref(axis_place)});")

        # 2. Extrusion geometry
        # Convert points to relative coordinates (centered on cx, cy)
        rel_pts = [(x - cx, y - cy) for x, y in pts]

        polyline = P()
        # Polyline
        pt_list = ",".join(fmt_point(x, y, 0.0) for x, y in rel_pts)
        # Need to define each point as IfcCartesianPoint
        point_refs = []
        for x, y in rel_pts:
            p_ref = P()
            lines.append(f"{p_ref}=IFCCARTESIANPOINT({fmt_point(x, y, 0.0)});")
            point_refs.append(p_ref)

        polyline_pts = ",".join(str(ref) for ref in point_refs)
        polyline_id = P()
        lines.append(f"{polyline_id}=IFCPOLYLINE(({polyline_pts}));")

        # Closed curve
        closed_curve = P()
        lines.append(f"{closed_curve}=IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,'{name}',{ref(polyline_id)});")

        # Extrusion
        extrusion = P()
        extrude_dir = P()
        lines.append(f"{extrude_dir}=IFCDIRECTION((0.,0.,1.));")
        lines.append(
            f"{extrusion}=IFCEXTRUDEDAREASOLID({ref(closed_curve)},{ref(P())},{ref(extrude_dir)},{fmt_float(height)});"
        )
        # Fix the axis2placement in extruded area solid
        place_2d = P()
        lines.append(f"{place_2d}=IFCAXIS2PLACEMENT3D({ref(P())},#0,#0);")
        loc2d = P()
        lines.append(f"{loc2d}=IFCCARTESIANPOINT((0.,0.,0.));")
        lines.append(f"{place_2d}=IFCAXIS2PLACEMENT3D({ref(loc2d)},#0,#0);")
        lines.append(
            f"{extrusion}=IFCEXTRUDEDAREASOLID({ref(closed_curve)},{ref(place_2d)},{ref(extrude_dir)},{fmt_float(height)});"
        )

        # Product representation
        shape_rep = P()
        lines.append(f"{shape_rep}=IFCSHAPEREPRESENTATION({ref(P())},'Body','SweptSolid',({ref(extrusion)}));")
        rep_context = P()
        lines.append(f"{rep_context}=IFCGEOMETRICREPRESENTATIONSUBCONTEXT('Body','Model',*,*,*,*,*,#0);")
        lines.append(f"{shape_rep}=IFCSHAPEREPRESENTATION({ref(rep_context)},'Body','SweptSolid',({ref(extrusion)}));")

        prod_def = P()
        lines.append(f"{prod_def}=IFCPRODUCTDEFINITIONSHAPE($,$,({ref(shape_rep)}));")

        # Element
        elem = P()
        lines.append(
            f"{elem}={ifc_entity}('{elem}',{ref(owner_hist)},'{name}',$,$,"
            f"{ref(elem_placement)},{ref(prod_def)},$);"
        )
        element_ids.append(elem)

        # Aggregate to building
        building_elements.append(str(elem))

        # Material association
        mat_assoc = P()
        lines.append(
            f"{mat_assoc}=IFCRELASSOCIATESMATERIAL('{mat_assoc}',{ref(owner_hist)},$,$,({ref(elem)}),{ref(mat)});"
        )

        # ── Openings ──
        openings: list[Opening] = getattr(prof, 'openings', [])
        opening_refs = []
        for op in openings:
            op_name = op.name or "Opening"
            op_pts = op.shape
            op_z = op.z_start
            op_h = op.z_end - op.z_start

            # Opening local placement (relative to wall)
            op_min_x = min(p[0] for p in op_pts)
            op_min_y = min(p[1] for p in op_pts)
            op_max_x = max(p[0] for p in op_pts)
            op_max_y = max(p[1] for p in op_pts)
            op_cx = (op_min_x + op_max_x) / 2 - cx
            op_cy = (op_min_y + op_max_y) / 2 - cy
            op_w = op_max_x - op_min_x
            op_d = op_max_y - op_min_y

            # Use a simple box representation for openings
            # IfcOpeningElement with IfcExtrudedAreaSolid
            op_loc = P()
            lines.append(f"{op_loc}=IFCCARTESIANPOINT({fmt_point(op_cx, op_cy, op_z)});")
            op_z_axis = P()
            lines.append(f"{op_z_axis}=IFCDIRECTION((0.,0.,1.));")
            op_x_dir = P()
            lines.append(f"{op_x_dir}=IFCDIRECTION((1.,0.,0.));")
            op_axis = P()
            lines.append(f"{op_axis}=IFCAXIS2PLACEMENT3D({ref(op_loc)},{ref(op_z_axis)},{ref(op_x_dir)});")
            op_place = P()
            lines.append(f"{op_place}=IFCLOCALPLACEMENT({ref(elem_placement)},{ref(op_axis)});")

            # Opening rectangle profile
            rect_pts = [
                (-op_w/2, -op_d/2),
                (op_w/2, -op_d/2),
                (op_w/2, op_d/2),
                (-op_w/2, op_d/2),
                (-op_w/2, -op_d/2),
            ]
            op_poly = P()
            op_pt_refs = []
            for rx, ry in rect_pts:
                rp = P()
                lines.append(f"{rp}=IFCCARTESIANPOINT({fmt_point(rx, ry, 0.0)});")
                op_pt_refs.append(rp)
            op_poly_pts = ",".join(str(r) for r in op_pt_refs)
            lines.append(f"{op_poly}=IFCPOLYLINE(({op_poly_pts}));")

            op_profile = P()
            lines.append(f"{op_profile}=IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,'{op_name}',{ref(op_poly)});")

            op_extrude_dir = P()
            lines.append(f"{op_extrude_dir}=IFCDIRECTION((0.,0.,1.));")
            op_place2d = P()
            op_loc2d = P()
            lines.append(f"{op_loc2d}=IFCCARTESIANPOINT((0.,0.,0.));")
            lines.append(f"{op_place2d}=IFCAXIS2PLACEMENT3D({ref(op_loc2d)},#0,#0);")
            op_extrusion = P()
            lines.append(
                f"{op_extrusion}=IFCEXTRUDEDAREASOLID({ref(op_profile)},{ref(op_place2d)},{ref(op_extrude_dir)},{fmt_float(op_h)});"
            )

            op_shape = P()
            op_rep = P()
            lines.append(f"{op_rep}=IFCSHAPEREPRESENTATION({ref(rep_context)},'Body','SweptSolid',({ref(op_extrusion)}));")
            lines.append(f"{op_shape}=IFCPRODUCTDEFINITIONSHAPE($,$,({ref(op_rep)}));")

            opening_elem = P()
            lines.append(
                f"{opening_elem}=IFCOPENINGELEMENT('{opening_elem}',{ref(owner_hist)},'{op_name}',$,$,"
                f"{ref(op_place)},{ref(op_shape)},$);"
            )

            # Void relation: opening cuts wall
            void_rel = P()
            lines.append(
                f"{void_rel}=IFCRELVOIDSELEMENT('{void_rel}',{ref(owner_hist)},$,$,"
                f"{ref(elem)},({ref(opening_elem)}));"
            )

    # ── Building element aggregation ──
    elem_list = ", ".join(building_elements)
    lines.append(
        f"{ref(P())}=IFCRELCONTAINEDINSPATIALSTRUCTURE("
        f"'#',{ref(owner_hist)},$,$,({elem_list}),{ref(bldg)});"
    )

    lines.append("ENDSEC;")
    lines.append("END-ISO-10303-21;")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/generate_ifc.py <input.json> <output.ifc>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path) as f:
        data = json.load(f)

    profiles = []
    for p in data:
        profiles.append(ExtrudedProfile(
            name=p.get("name", "Element"),
            ifc_type=p.get("ifc_type", "IfcBuildingElementProxy"),
            points_2d=p["points_2d"],
            base_elevation=p.get("base_elevation", 0.0),
            height=p.get("height", 3000.0),
            openings=[
                Opening(
                    shape=op["shape"],
                    z_start=op["z_start"],
                    z_end=op["z_end"],
                    name=op.get("name", "opening"),
                )
                for op in p.get("openings", [])
            ],
        ))

    ifc_content = build_ifc(profiles, output_path)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(ifc_content)

    print(f"✅ Generated IFC file: {output_path}")
    print(f"   Size: {len(ifc_content):,} bytes")
    print(f"   Entities: {len([l for l in ifc_content.split(chr(10)) if l.startswith('#')])}")


if __name__ == "__main__":
    main()
