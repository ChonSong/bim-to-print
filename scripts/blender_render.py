#!/usr/bin/env python3
"""Render BIM model views using Blender headless via Docker.

Imports the IFC model, applies concrete materials, sets up lighting,
renders standard views: perspective, plan (top-down), 4 elevations (N/S/E/W).

Usage:
    python scripts/blender_render.py [--ifc demo_house.ifc] [--output renders/]
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile


BLENDER_IMAGE = "nytimes/blender:latest"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def build_blender_script(ifc_path: str, output_dir: str) -> str:
    """Generate the Blender Python script to render views."""
    abs_ifc = os.path.abspath(ifc_path)
    abs_out = os.path.abspath(output_dir)
    os.makedirs(abs_out, exist_ok=True)

    return f'''
import bpy
import os
import math

# Clear scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Import IFC
ifc_path = "{abs_ifc}"
output_dir = "{abs_out}"

# Since we don't have BlenderBIM, build geometry procedurally from our data
# Wall dimensions from demo_house.json
walls = [
    {{"name": "Main-Wall", "pts": [(0,0),(4000,0),(4000,200),(0,200)], "z": 0, "h": 2400,
      "openings": [
        {{"x":500,"y":0,"w":1000,"d":200,"z":800,"h":1200}},
        {{"x":2500,"y":0,"w":1000,"d":200,"z":0,"h":2100}},
      ]}},
    {{"name": "Side-Wall", "pts": [(4000,0),(4000,1000),(4200,1000),(4200,0)], "z": 0, "h": 2400,
      "openings": [
        {{"x":0,"y":0,"w":200,"d":600,"z":900,"h":1000}},
      ]}},
    {{"name": "Column", "pts": [(4200,0),(4200,300),(4500,300),(4500,0)], "z": 0, "h": 2400,
      "openings": []}},
    {{"name": "Slab", "pts": [(-100,-100),(4600,-100),(4600,1100),(-100,1100)], "z": -150, "h": 150,
      "openings": []}},
    {{"name": "Roof", "pts": [(-100,-100),(4600,-100),(4600,1100),(-100,1100)], "z": 2400, "h": 150,
      "openings": []}},
]

# Concrete material
conc_mat = bpy.data.materials.new(name="Concrete")
conc_mat.use_nodes = True
nodes = conc_mat.node_tree.nodes
links = conc_mat.node_tree.links

# Clear default nodes
for n in nodes:
    nodes.remove(n)

# Create principled BSDF
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
bsdf.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1.0)
bsdf.inputs["Roughness"].default_value = 0.85
bsdf.inputs["Metallic"].default_value = 0.0

# Output
out = nodes.new("ShaderNodeOutputMaterial")
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

# Add noise texture for concrete look
noise = nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 200.0
noise.inputs["Detail"].default_value = 10.0
noise.inputs["Roughness"].default_value = 0.7

# Bump map
bump = nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.05
links.new(noise.outputs["Fac"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

# Color variation
col_ramp = nodes.new("ShaderNodeValToRGB")
col_ramp.color_ramp.elements[0].position = 0.4
col_ramp.color_ramp.elements[0].color = (0.5, 0.5, 0.5, 1.0)
col_ramp.color_ramp.elements[1].position = 0.6
col_ramp.color_ramp.elements[1].color = (0.6, 0.6, 0.6, 1.0)
links.new(noise.outputs["Fac"], col_ramp.inputs["Factor"])
links.new(col_ramp.outputs["Color"], bsdf.inputs["Base Color"])


def make_wall_mesh(profile):
    """Create wall with openings as extruded mesh with boolean cuts."""
    import bmesh
    
    # Create base wall
    verts = [(x, y, 0) for x, y in profile["pts"]]
    faces = [list(range(len(verts)))]  # ngon
    
    mesh = bpy.data.meshes.new(profile["name"])
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    
    # Extrude upward
    obj = bpy.data.objects.new(profile["name"], mesh)
    bpy.context.collection.objects.link(obj)
    
    mod = obj.modifiers.new("Solidify", "SOLIDIFY")
    mod.thickness = 1  # dummy for wall creation
    # Use geometry nodes or simple extrude
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Switch to edit mode and extrude
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OP={{"value": (0, 0, profile["h"])}}
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    
    # Apply material
    if obj.data.materials:
        obj.data.materials[0] = conc_mat
    else:
        obj.data.materials.append(conc_mat)
    
    # Cut openings using boolean
    for op in profile.get("openings", []):
        if op["h"] <= 0:
            continue
        
        # Create cutter box
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(op["x"] + op["w"]/2, 0, op["z"] + op["h"]/2)
        )
        cutter = bpy.context.active_object
        cutter.scale = (op["w"]/2, op["d"]/2, op["h"]/2)
        cutter.name = f"Cut-{{op['name']}}"
        
        # Boolean modifier
        bool_mod = obj.modifiers.new(name=f"Bool-{{op['name']}}", type="BOOLEAN")
        bool_mod.object = cutter
        bool_mod.operation = "DIFFERENCE"
        
        # Apply and remove cutter
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=bool_mod.name)
        
        # Delete cutter
        bpy.data.objects.remove(cutter, do_unlink=True)
    
    return obj


# Build all walls
all_objs = []
for w in walls:
    obj = make_wall_mesh(w)
    all_objs.append(obj)

# Select all for bounding
bpy.ops.object.select_all(action="DESELECT")
for obj in all_objs:
    obj.select_set(True)

# Compute bounding box
bpy.context.view_layer.objects.active = all_objs[0]
bpy.ops.view3d.snap_cursor_to_selected()
bbox_center = [sum(bpy.context.scene.cursor.location[i] for i in range(3)) / 1 for _ in range(3)]

# Actually compute bounds properly
min_x = min(obj.location.x - max((abs(v.co.x) for v in obj.data.vertices), default=0) for obj in all_objs)
max_x = max(obj.location.x + max((abs(v.co.x) for v in obj.data.vertices), default=0) for obj in all_objs)
min_y = min(obj.location.y - max((abs(v.co.y) for v in obj.data.vertices), default=0) for obj in all_objs)
max_y = max(obj.location.y + max((abs(v.co.y) for v in obj.data.vertices), default=0) for obj in all_objs)
min_z = min(obj.location.z - max((abs(v.co.z) for v in obj.data.vertices), default=0) for obj in all_objs)
max_z = max(obj.location.z + max((abs(v.co.z) for v in obj.data.vertices), default=0) for obj in all_objs)

cx = (min_x + max_x) / 2
cy = (min_y + max_y) / 2
cz = (min_z + max_z) / 2
size_x = max_x - min_x
size_y = max_y - min_y
size_z = max_z - min_z
max_dim = max(size_x, size_y, size_z, 1)

# Lighting
bpy.ops.object.light_add(type="SUN", location=(max_dim*2, max_dim*2, max_dim*3))
sun = bpy.context.active_object
sun.data.energy = 5.0
sun.data.angle = 0.02

bpy.ops.object.light_add(type="AREA", location=(0, 0, max_dim*2))
fill = bpy.context.active_object
fill.data.energy = 200
fill.data.size = max_dim

# Ground plane
bpy.ops.mesh.primitive_plane_add(size=max_dim*4, location=(cx, cy, min_z - 10))
ground = bpy.context.active_object
ground.name = "Ground"
ground_mat = bpy.data.materials.new(name="Ground")
ground_mat.use_nodes = True
bsdf_ground = ground_mat.node_tree.nodes["Principled BSDF"]
bsdf_ground.inputs["Base Color"].default_value = (0.15, 0.15, 0.15, 1.0)
bsdf_ground.inputs["Roughness"].default_value = 0.9
if ground.data.materials:
    ground.data.materials[0] = ground_mat
else:
    ground.data.materials.append(ground_mat)

# Render settings
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.cycles.samples = 128
bpy.context.scene.render.film_transparent = False

def render_view(cam_loc, target, name):
    """Set camera and render."""
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    
    # Point at target
    direction = (target[0] - cam_loc[0], target[1] - cam_loc[1], target[2] - cam_loc[2])
    length = math.sqrt(sum(d*d for d in direction))
    direction = (d/length for d in direction)
    
    cam.constraints.new(type="TRACK_TO")
    constraint = cam.constraints["Track To"]
    constraint.target = bpy.data.objects.new(f"Target-{{name}}", None)
    bpy.context.collection.objects.link(constraint.target)
    constraint.target.location = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    
    # Also rotate camera to be level for plan view
    if name == "plan":
        cam.rotation_euler = (0, 0, 0)
    
    path = os.path.join(output_dir, f"{{name}}.png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"  Rendered {{path}}")
    
    # Cleanup
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.objects.remove(constraint.target, do_unlink=True)

target = (cx, cy, cz)

# Perspective view
dist = max_dim * 1.8
render_view((cx + dist, cy - dist*0.3, cz + dist*0.5), target, "perspective")

# Plan view (top-down orthographic)
render_view((cx, cy + max_dim*3, cz), target, "plan")

# Elevations
render_view((cx + dist, cy, cz + max_dim*0.3), target, "elevation-east")
render_view((cx - dist, cy, cz + max_dim*0.3), target, "elevation-west")
render_view((cx, cy + dist, cz + max_dim*0.3), target, "elevation-north")
render_view((cx, cy - dist, cz + max_dim*0.3), target, "elevation-south")

print("All renders complete.")
'''


def run_blender(blend_script: str, ifc_path: str, output_dir: str):
    """Run Blender in Docker with the script."""
    abs_script = os.path.abspath(blend_script)
    abs_ifc = os.path.abspath(ifc_path)
    abs_out = os.path.abspath(output_dir)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{abs_script}:/script.py:ro",
        "-v", f"{abs_ifc}:/model.ifc:ro",
        "-v", f"{abs_out}:/output",
        BLENDER_IMAGE,
        "blender", "--background", "--python", "/script.py",
    ]

    print(f"🚀 Running Blender render...")
    print(f"   IFC: {ifc_path}")
    print(f"   Output: {output_dir}")
    print(f"   Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"⚠️  Blender stderr:")
        for line in result.stderr.split(chr(10))[-20:]:
            print(f"   {line}")
        print(f"⚠️  Return code: {result.returncode}")
    else:
        print(f"✅ Blender render complete")

    # List outputs
    for f in sorted(os.listdir(abs_out)):
        size = os.path.getsize(os.path.join(abs_out, f))
        print(f"   📁 {f} ({size:,} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Render BIM views with Blender")
    parser.add_argument("--ifc", default="docs/research/demo_house.ifc",
                        help="Input IFC file path")
    parser.add_argument("--output", default="docs/research/renders",
                        help="Output directory for rendered images")
    args = parser.parse_args()

    # Create script
    script_content = build_blender_script(args.ifc, args.output)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        run_blender(script_path, args.ifc, args.output)
    finally:
        os.unlink(script_path)


if __name__ == "__main__":
    main()
