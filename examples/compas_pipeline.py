"""Full compas-based pipeline: mesh → boolean subtract openings → slice → print organize → G-code → viz."""
import json
import os
import sys

import numpy as np
from compas.datastructures import Mesh
from compas.geometry import Box, Frame, Point, Vector, boolean_difference_mesh_mesh, boolean_union_mesh_mesh
from compas_slicer.slicers import PlanarSlicer
from compas_slicer.print_organization import PlanarPrintOrganizer
from compas_slicer.print_organization.print_organization_utilities.gcode import create_gcode_text
from compas_slicer.config import GcodeConfig

OUT = os.path.join(os.path.dirname(__file__))


def get_vf(mesh):
    keys = list(mesh.vertices())
    V = [mesh.vertex_attributes(k, "xyz") for k in keys]
    F = [mesh.face_vertices(fk) for fk in mesh.faces()]
    return (V, F)


def make_box(xsize, ysize, zsize, cx, cy, cz):
    """Box with center at (cx, cy, cz) for boolean operations."""
    return Box(
        xsize=xsize, ysize=ysize, zsize=zsize,
        frame=Frame(Point(cx, cy, cz), Vector(1, 0, 0), Vector(0, 1, 0)),
    )


def mesh_from_box(box):
    m = Mesh.from_shape(box)
    m.quads_to_triangles()
    return m


def subtract_openings(wall_box, opening_boxes):
    """Boolean subtract all openings from wall box. Returns a single Mesh."""
    wall_mesh = mesh_from_box(wall_box)
    vf = get_vf(wall_mesh)
    
    for obox in opening_boxes:
        om = mesh_from_box(obox)
        result = boolean_difference_mesh_mesh(vf, get_vf(om))
        vf = result  # result is (V, F) tuple
    
    # Reconstruct Mesh
    V, F = vf
    mesh = Mesh.from_vertices_and_faces(V.tolist(), F.tolist())
    mesh.quads_to_triangles()
    return mesh


def build_house_mesh():
    """Build the complete house mesh with all openings subtracted."""
    meshes = []
    
    # Main wall: 4000x200x2400, center at (2000, 100, 1200)
    main_wall = make_box(4000, 200, 2400, 2000, 100, 1200)
    main_openings = [
        # Window: 1000x200x1200, from (500,0,800) to (1500,200,2000) → center (1000, 100, 1400)
        make_box(1000, 200, 1200, 1000, 100, 1400),
        # Door: 1000x200x2100, from (2500,0,0) to (3500,200,2100) → center (3000, 100, 1050)
        make_box(1000, 200, 2100, 3000, 100, 1050),
    ]
    meshes.append(subtract_openings(main_wall, main_openings))
    
    # Side wall: 200x1000x2400, from (4000,0,0) to (4200,1000,2400) → center (4100, 500, 1200)
    side_wall = make_box(200, 1000, 2400, 4100, 500, 1200)
    side_openings = [
        # Window: 200x600x1000, from (4000,300,900) to (4200,900,1900) → center (4100, 600, 1400)
        make_box(200, 600, 1000, 4100, 600, 1400),
    ]
    meshes.append(subtract_openings(side_wall, side_openings))
    
    # Column: 300x300x2400, from (4200,0,0) to (4500,300,2400) → center (4350, 150, 1200)
    col1 = make_box(300, 300, 2400, 4350, 150, 1200)
    meshes.append(mesh_from_box(col1))
    
    # Merge all meshes via boolean union
    print("Merging meshes...")
    combined_vf = get_vf(meshes[0])
    for m in meshes[1:]:
        print(f"  Union with mesh ({len(list(m.vertices()))} verts)...")
        try:
            combined_vf = boolean_union_mesh_mesh(combined_vf, get_vf(m))
        except Exception as e:
            print(f"  Union failed ({e}), merging vertices directly")
            # Fallback: just combine vertex/face lists
            V1, F1 = combined_vf
            V2, F2 = get_vf(m)
            offset = len(V1)
            combined_vf = (V1 + V2, F1 + [[i + offset for i in f] for f in F2])
    
    V, F = combined_vf
    mesh = Mesh.from_vertices_and_faces(V, F)
    mesh.quads_to_triangles()
    from compas_slicer.utilities import utils
    utils.check_triangular_mesh(mesh)
    print(f"Final mesh: {len(list(mesh.vertices()))} verts, {len(list(mesh.faces()))} faces")
    return mesh


def main():
    print("=" * 60)
    print("Building house mesh with openings...")
    mesh = build_house_mesh()
    
    print("\nSlicing...")
    slicer = PlanarSlicer(mesh, layer_height=10.0)
    slicer.slice_model()
    print(f"  Layers: {slicer.number_of_layers}")
    t, c, o = slicer.number_of_paths
    print(f"  Paths: total={t}, closed={c}, open={o}")
    
    # Show layer structure
    for layer in slicer.layers:
        z_avg = sum(p.z for p in layer.paths[0].points) / len(layer.paths[0].points) if layer.paths else 0
        if 0 < z_avg < 20 or 800 < z_avg < 1500:
            print(f"  Layer z~{z_avg:.0f}: {len(layer.paths)} paths" + 
                  (f" (has hole)" if len(layer.paths) > 1 else ""))
    
    print("\nOrganizing print points...")
    organizer = PlanarPrintOrganizer(slicer)
    organizer.create_printpoints(generate_mesh_normals=False)
    print(f"  Print layers: {len(organizer.printpoints.layers)}")
    
    print("\nGenerating G-code...")
    config = GcodeConfig()
    config.layer_width = 8.0
    config.feedrate = 1800
    config.feedrate_travel = 3600
    config.filament_diameter = 1.75
    gcode = create_gcode_text(organizer, config)
    
    gcode_path = os.path.join(OUT, "compas_house.gcode")
    with open(gcode_path, "w") as f:
        f.write(gcode)
    print(f"  G-code written to {gcode_path}")
    print(f"  Size: {len(gcode.split(chr(10)))} lines")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
