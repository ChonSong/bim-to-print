"""Inner Blender script — runs inside the Docker container via blender --background.
Builds walls with proper openings, slab, roof, renders 6 views."""
import bpy, bmesh, math, os


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


def make_concrete_mat(name="Concrete", base_color=(0.55, 0.55, 0.55, 1.0)):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        nodes.remove(n)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.0
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 80.0
    noise.inputs["Detail"].default_value = 8.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.03
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_wall_with_openings(name, base_pts, z, h, openings, mat):
    """Build a wall mesh with openings cut out, extruded to height h."""
    # Build the base polygon (XY plane at z=0), then extrude upward
    verts_2d = [(x, y) for x, y in base_pts]
    if verts_2d[0] != verts_2d[-1]:
        verts_2d.append(verts_2d[0])

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    # Create outer boundary edge loop
    outer_verts = []
    for x, y in verts_2d[:-1]:  # skip closing point, bmesh handles it
        outer_verts.append(bm.verts.new((x, y, 0)))

    # Create the outer face
    outer_face = bm.faces.new(outer_verts)

    # Create hole for each opening
    for op_idx, op in enumerate(openings):
        ox, oy = op["x"], op["y"]
        ow, od = op["w"], op["d"]
        # Opening is at wall face (y=0 plane for main wall)
        hole_verts = [
            bm.verts.new((ox, oy, 0)),
            bm.verts.new((ox + ow, oy, 0)),
            bm.verts.new((ox + ow, oy + od, 0)),
            bm.verts.new((ox, oy + od, 0)),
        ]
        # Create hole face (will be removed)
        hole_face = bm.faces.new(hole_verts)
        # Cut hole using the outer face's loop
        bmesh.utils.face_flip(hole_face)
        # Dissolve the hole face to create a hole in the outer face
        # Inset the hole
        bmesh.ops.delete(bm, geom=[hole_face], context="FACES_ONLY")

    # Extrude upward
    extruded = bmesh.ops.extrude_face_region(bm, geom=[outer_face])
    extrude_verts = [v for v in extruded["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=extrude_verts, vec=(0, 0, h))

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def make_solid_box(name, x, y, z, sx, sy, sz, mat):
    """Simple cuboid."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    return obj


def render_view(cam_loc, target, name, output_dir):
    """Set camera and render."""
    # Create camera
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    cam.name = f"Cam-{name}"
    bpy.context.scene.camera = cam

    # Track target
    target_obj = bpy.data.objects.new(f"Target-{name}", None)
    bpy.context.collection.objects.link(target_obj)
    target_obj.location = target
    track = cam.constraints.new(type="TRACK_TO")
    track.target = target_obj
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    # Special handling for plan view — make it orthographic
    if name == "plan":
        bpy.context.scene.render.resolution_x = 1920
        bpy.context.scene.render.resolution_y = 1920  # square for plan

    # Render
    path = os.path.join(output_dir, f"{name}.png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {name}")

    # Cleanup
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.objects.remove(target_obj, do_unlink=True)


# ── Main ──
output_dir = "/output"
cycles_samples = __CYCLES_SAMPLES__

clean_scene()

# Materials
conc_wall = make_concrete_mat("WallMat", (0.60, 0.58, 0.55, 1.0))
conc_dark = make_concrete_mat("DarkMat", (0.40, 0.39, 0.37, 1.0))
conc_slab = make_concrete_mat("SlabMat", (0.35, 0.35, 0.35, 1.0))
glass_mat = make_concrete_mat("GlassMat", (0.2, 0.3, 0.4, 0.3))
glass_mat.blend_method = "BLEND"
glass_mat.shadow_method = "NONE"

# ── Build geometry ──
# Main wall with window + door
make_wall_with_openings("Main-Wall", [(0,0),(4000,0),(4000,200),(0,200)], 0, 2400, [
    {"name": "Window", "x": 500, "y": 0, "w": 1000, "d": 200, "z": 800, "h": 1200},
    {"name": "Door", "x": 2500, "y": 0, "w": 1000, "d": 200, "z": 0, "h": 2100},
], conc_wall)

# Side wall with window
make_wall_with_openings("Side-Wall", [(4000,0),(4000,1000),(4200,1000),(4200,0)], 0, 2400, [
    {"name": "SideWindow", "x": 0, "y": 0, "w": 200, "d": 600, "z": 900, "h": 1000},
], conc_dark)

# Column
make_solid_box("Column", 4350, 150, 1200, 150, 150, 1200, conc_dark)

# Slab foundation
make_solid_box("Slab", 2250, 500, -80, 2350, 600, 80, conc_slab)

# Roof
make_solid_box("Roof", 2250, 500, 2480, 2350, 600, 80, conc_slab)

# Ground plane
bpy.ops.mesh.primitive_plane_add(size=15000, location=(2250, 500, -120))
ground = bpy.context.active_object
ground.name = "Ground"
ground_mat = make_concrete_mat("GroundMat", (0.12, 0.12, 0.12, 1.0))
ground.data.materials.append(ground_mat)

# ── Lighting ──
bpy.ops.object.light_add(type="SUN", location=(10000, 8000, 8000))
sun = bpy.context.active_object
sun.data.energy = 6.0
sun.data.angle = 0.01

bpy.ops.object.light_add(type="SUN", location=(-5000, 2000, 6000))
fill_sun = bpy.context.active_object
fill_sun.data.energy = 1.5
fill_sun.data.angle = 0.02

bpy.ops.object.light_add(type="AREA", location=(0, 0, 4000))
amb = bpy.context.active_object
amb.data.energy = 100
amb.data.size = 5000

# ── Scene setup ──
# Compute bounding box
all_objs = [o for o in bpy.data.objects if o.type == "MESH"]
cx = sum(o.location.x for o in all_objs) / len(all_objs)
cy = sum(o.location.y for o in all_objs) / len(all_objs)
cz = 1200  # mid-height

# World background
world = bpy.context.scene.world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Strength"].default_value = 0.3

# Render settings
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.cycles.samples = cycles_samples
bpy.context.scene.cycles.use_adaptive_sampling = True
bpy.context.scene.cycles.adaptive_threshold = 0.01
bpy.context.scene.render.film_transparent = False
bpy.context.scene.cycles.max_bounces = 4
bpy.context.scene.cycles.diffuse_bounces = 4
bpy.context.scene.cycles.glossy_bounces = 4

target = (cx, cy, cz)
dist = max(5000, cx * 1.8)

# ── Render all views ──
views = [
    ("overview", (cx + dist, cy - dist*0.3, cz + dist*0.6)),
    ("plan", (cx, cy + 5000, cz)),
    ("elevation-north", (cx, cy + dist, cz)),
    ("elevation-south", (cx, cy - dist, cz)),
    ("elevation-east", (cx + dist, cy, cz)),
    ("elevation-west", (cx - dist, cy, cz)),
]

for name, loc in views:
    render_view(loc, target, name, output_dir)

print("All 6 renders complete.")
