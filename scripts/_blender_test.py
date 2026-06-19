#!/usr/bin/env python3
"""Quick test render to verify lighting fix."""
import subprocess, tempfile, os, json

script = '''
import bpy, json

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Simple test: a cube with concrete material
bpy.ops.mesh.primitive_cube_add(size=2000, location=(0, 0, 0))
bpy.context.active_object.name = "Test"
bpy.ops.object.transform_apply(scale=True)

mat = bpy.data.materials.new(name="Concrete")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
for n in nodes: nodes.remove(n)
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
bsdf.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1.0)
bsdf.inputs["Roughness"].default_value = 0.85
out = nodes.new("ShaderNodeOutputMaterial")
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
bpy.context.active_object.data.materials.append(mat)

# Ground
bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -1000))
ground_mat = bpy.data.materials.new(name="Ground")
ground_mat.use_nodes = True
bgs = ground_mat.node_tree.nodes["Principled BSDF"]
bgs.inputs["Base Color"].default_value = (0.15, 0.15, 0.15, 1.0)
bpy.context.active_object.data.materials.append(ground_mat)

# Bright lighting
bpy.ops.object.light_add(type="SUN", location=(3000, 2000, 4000))
bpy.context.active_object.data.energy = 20.0

# Sky background
world = bpy.context.scene.world
world.use_nodes = True
nw = world.node_tree.nodes
lw = world.node_tree.links
for n in nw: nw.remove(n)
bg = nw.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.5, 0.6, 0.8, 1.0)
bg.inputs["Strength"].default_value = 2.0
out = nw.new("ShaderNodeOutputMaterial")
lw.new(bg.outputs["Background"], out.inputs["Surface"])

# Camera
bpy.ops.object.camera_add(location=(4000, 2000, 3000))
bpy.context.scene.camera = bpy.context.active_object
track = bpy.context.active_object.constraints.new(type="TRACK_TO")
track.target = bpy.data.objects.new("Target", None)
bpy.context.collection.objects.link(track.target)
track.target.location = (0, 0, 0)
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"

# Render
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.render.resolution_x = 640
bpy.context.scene.render.resolution_y = 480
bpy.context.scene.cycles.samples = 32
bpy.context.scene.render.filepath = "/output/test_lighting.png"
bpy.ops.render.render(write_still=True)
print("Test render complete")
'''

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(script)
    spath = f.name

cmd = [
    "docker", "run", "--rm",
    "-v", f"{spath}:/script.py:ro",
    "-v", f"{os.path.abspath('docs/research/renders')}:/output",
    "nytimes/blender:latest",
    "blender", "--background", "--python", "/script.py",
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
for line in result.stdout.split("\n"):
    if "complete" in line or "Saved" in line:
        print(line)
if result.returncode != 0:
    for line in result.stderr.split("\n")[-5:]:
        if line.strip():
            print(f"ERR: {line.strip()}")
os.unlink(spath)

# Check render
from PIL import Image
import collections
img = Image.open("docs/research/renders/test_lighting.png")
print(f"Image: {img.size}")
colors = collections.Counter()
for y in range(0, img.height, 2):
    for x in range(0, img.width, 2):
        c = img.getpixel((x,y))[:3]
        colors[c] += 1
total = sum(colors.values())
bg_c = sum(v for k,v in colors.items() if all(ch < 25 for ch in k))
conc = sum(v for k,v in colors.items() if all(80 <= ch < 170 for ch in k))
lite = sum(v for k,v in colors.items() if any(ch >= 200 for ch in k))
print(f"Background: {bg_c/total*100:.1f}%")
print(f"Mid-range:  {conc/total*100:.1f}%")
print(f"Bright:     {lite/total*100:.1f}%")
