"""Generate a filled-polygon 3D visualization from compas_slicer layer data."""
import json
import os

from compas.geometry import Box, Frame, Point, Vector, boolean_difference_mesh_mesh, boolean_union_mesh_mesh
from compas.datastructures import Mesh
from compas_slicer.slicers import PlanarSlicer
from compas_slicer.config import SlicerConfig

OUT = os.path.join(os.path.dirname(__file__))


def get_vf(mesh):
    keys = list(mesh.vertices())
    V = [mesh.vertex_attributes(k, "xyz") for k in keys]
    F = [mesh.face_vertices(fk) for fk in mesh.faces()]
    return (V, F)


def make_box(xsize, ysize, zsize, cx, cy, cz):
    return Box(xsize=xsize, ysize=ysize, zsize=zsize,
               frame=Frame(Point(cx, cy, cz), Vector(1, 0, 0), Vector(0, 1, 0)))


def mesh_from_box(box):
    m = Mesh.from_shape(box)
    m.quads_to_triangles()
    return m


def subtract_openings(wall_box, opening_boxes):
    wall_mesh = mesh_from_box(wall_box)
    vf = get_vf(wall_mesh)
    for obox in opening_boxes:
        om = mesh_from_box(obox)
        vf = boolean_difference_mesh_mesh(vf, get_vf(om))
    V, F = vf
    m = Mesh.from_vertices_and_faces(V.tolist(), F.tolist())
    m.quads_to_triangles()
    return m


def build_house_mesh():
    meshes = []
    # Main wall: 4000x200x2400
    main_wall = make_box(4000, 200, 2400, 2000, 100, 1200)
    main_openings = [
        make_box(1000, 200, 1200, 1000, 100, 1400),  # window
        make_box(1000, 200, 2100, 3000, 100, 1050),  # door
    ]
    meshes.append(subtract_openings(main_wall, main_openings))

    # Side wall: 200x1000x2400
    side_wall = make_box(200, 1000, 2400, 4100, 500, 1200)
    side_openings = [
        make_box(200, 600, 1000, 4100, 600, 1400),  # window
    ]
    meshes.append(subtract_openings(side_wall, side_openings))

    # Column
    meshes.append(mesh_from_box(make_box(300, 300, 2400, 4350, 150, 1200)))

    combined_vf = get_vf(meshes[0])
    for m in meshes[1:]:
        try:
            combined_vf = boolean_union_mesh_mesh(combined_vf, get_vf(m))
        except Exception:
            V1, F1 = combined_vf
            V2, F2 = get_vf(m)
            offset = len(V1)
            combined_vf = (V1 + V2, F1 + [[i + offset for i in f] for f in F2])

    V, F = combined_vf
    m = Mesh.from_vertices_and_faces(V, F)
    m.quads_to_triangles()
    return m


def layer_data_to_json(slicer, max_sample=64):
    """Convert slicer layers to JSON for Three.js filled-polygon rendering.

    Each layer's paths: the first closed path is the outer contour,
    subsequent closed paths are holes.
    Renders each layer as a filled polygon with holes subtracted.
    """
    # Sample evenly
    total = len(slicer.layers)
    step = max(1, total // max_sample)
    sampled_indices = list(range(0, total, step))[:max_sample]

    layers_json = []
    for idx in sampled_indices:
        layer = slicer.layers[idx]
        if not layer.paths:
            continue

        z = round(layer.paths[0].points[0].z, 1) if layer.paths[0].points else 0

        outer = []
        holes = []
        for path in layer.paths:
            pts = [(round(p.x, 1), round(p.y, 1)) for p in path.points if p is not None]
            if len(pts) < 3:
                continue
            # First closed path = outer, rest closed = holes
            if not outer and path.is_closed:
                outer = pts
            elif path.is_closed:
                holes.append(pts)

        if outer:
            layers_json.append({
                "z": z,
                "outer": outer,
                "holes": holes,
            })

    return layers_json


def generate_html(layers_json):
    data = json.dumps(layers_json)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>bim2print — compas Pipeline Visualization</title>
<style>
  body {{ margin:0; overflow:hidden; background:#0d1117; font-family:system-ui,sans-serif; }}
  #info {{ position:fixed; top:12px; left:12px; color:#8b949e; font-size:13px; z-index:10; background:#161b22; padding:8px 14px; border-radius:8px; border:1px solid #30363d; }}
  #info h2 {{ margin:0 0 4px; color:#f0f6fc; font-size:16px; }}
  #stats {{ position:fixed; bottom:12px; left:12px; color:#8b949e; font-size:12px; z-index:10; background:#161b22; padding:6px 12px; border-radius:8px; border:1px solid #30363d; }}
  .controls {{ position:fixed; bottom:12px; right:12px; z-index:10; display:flex; gap:6px; }}
  .controls button {{ background:#21262d; border:1px solid #30363d; color:#c9d1d9; font-size:13px; padding:6px 14px; border-radius:6px; cursor:pointer; }}
  .controls button:hover {{ background:#30363d; }}
</style></head><body>
<div id="info"><h2>🏠 compas — Building Toolpath</h2><span id="layer-label">layer 1</span></div>
<div id="stats">{len(layers_json)} layers displayed</div>
<div class="controls">
  <button id="play-btn">▶ Play</button>
  <button id="reset-btn">⟲ Reset</button>
</div>

<script type="importmap">{{
  "imports": {{
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }}
}}</script>

<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

const LAYER_COLORS = [0x3fb950, 0x58a6ff, 0xd29922, 0xf78166, 0xbc8cff, 0x79c0ff, 0x56d364, 0xe3b341, 0xffa657, 0xd2a8ff];
const data = {data};

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d1117);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth/window.innerHeight, 1, 100000);
camera.position.set(5000, 3500, 6000);

const renderer = new THREE.WebGLRenderer({{ antialias: true }});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(2500, 0, 200);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI / 2.1;

// Grid
const grid = new THREE.GridHelper(8000, 20, 0x21262d, 0x21262d);
grid.position.y = 0;
scene.add(grid);

// Lights
scene.add(new THREE.AmbientLight(0x404660, 1.0));
const dl = new THREE.DirectionalLight(0xffffff, 1.0);
dl.position.set(2000, 5000, 3000);
scene.add(dl);
scene.add(new THREE.DirectionalLight(0x8888ff, 0.4).position.set(-2000, 1000, -3000));

// Build layer meshes (filled polygons)
const layerMeshes = [];
const allPos = [];

function makeLayerShape(outerPts, holePtsList, z) {{
  const shape = new THREE.Shape();
  shape.moveTo(outerPts[0][0], outerPts[0][1]);
  for (let i = 1; i < outerPts.length; i++) {{
    shape.lineTo(outerPts[i][0], outerPts[i][1]);
  }}
  shape.closePath();

  for (const hole of holePtsList) {{
    const holeShape = new THREE.Path();
    holeShape.moveTo(hole[0][0], hole[0][1]);
    for (let i = 1; i < hole.length; i++) {{
      holeShape.lineTo(hole[i][0], hole[i][1]);
    }}
    holeShape.closePath();
    shape.holes.push(holeShape);
  }}

  const geom = new THREE.ShapeGeometry(shape);
  geom.rotateX(-Math.PI / 2);
  geom.translate(0, z, 0);
  return geom;
}}

data.forEach((ld, idx) => {{
  const color = LAYER_COLORS[idx % LAYER_COLORS.length];
  const geom = makeLayerShape(ld.outer, ld.holes, ld.z);
  const mat = new THREE.MeshBasicMaterial({{
    color, side: THREE.DoubleSide, transparent: true, opacity: 0.6,
  }});
  const mesh = new THREE.Mesh(geom, mat);
  mesh.visible = false;

  // Also add edge lines
  const edges = new THREE.EdgesGeometry(geom);
  const edgeMat = new THREE.LineBasicMaterial({{ color, transparent: true, opacity: 0.8 }});
  const wireframe = new THREE.LineSegments(edges, edgeMat);
  wireframe.visible = false;

  scene.add(mesh);
  scene.add(wireframe);
  layerMeshes.push({{ mesh, wireframe, z: ld.z }});

  const pos = geom.attributes.position;
  for (let i = 0; i < pos.count; i++) {{
    allPos.push(pos.getX(i), pos.getY(i), pos.getZ(i));
  }}
}});

// Auto-fit
if (allPos.length > 0) {{
  let minX=Infinity,maxX=-Infinity,minZ=Infinity,maxZ=-Infinity;
  for (let i=0; i<allPos.length; i+=3) {{
    minX=Math.min(minX,allPos[i]); maxX=Math.max(maxX,allPos[i]);
    minZ=Math.min(minZ,allPos[i+2]); maxZ=Math.max(maxZ,allPos[i+2]);
  }}
  const cx=(minX+maxX)/2, cz=(minZ+maxZ)/2;
  const span = Math.max(maxX-minX, maxZ-minZ, 1000);
  camera.position.set(cx + span*1.2, span*0.8, cz + span*1.5);
  controls.target.set(cx, 0, cz);
}}

layerMeshes.sort((a,b) => a.z - b.z);

const label = document.getElementById('layer-label');
let currentIdx = 0;
let isPlaying = false;
let playTimer = null;

function showLayer(idx) {{
  layerMeshes.forEach((l, i) => {{
    const show = i <= idx;
    l.mesh.visible = show;
    l.wireframe.visible = show;
  }});
  const z = layerMeshes[idx]?.z ?? 0;
  label.textContent = `layer ${{idx+1}}/${{layerMeshes.length}} · Z=${{z.toFixed(1)}}mm`;
  currentIdx = idx;
}}

function resetView() {{
  controls.target.set(2500, 0, 200);
  controls.update();
  showLayer(0);
}}

showLayer(0);

document.getElementById('play-btn').addEventListener('click', () => {{
  if (isPlaying) {{
    isPlaying = false; clearInterval(playTimer);
    document.getElementById('play-btn').textContent = '▶ Play'; return;
  }}
  isPlaying = true;
  document.getElementById('play-btn').textContent = '⏸ Pause';
  showLayer(0);
  let i = 0;
  playTimer = setInterval(() => {{
    i++; showLayer(i);
    if (i >= layerMeshes.length-1) {{
      clearInterval(playTimer); isPlaying = false;
      document.getElementById('play-btn').textContent = '▶ Play';
    }}
  }}, 80);
}});

document.getElementById('reset-btn').addEventListener('click', resetView);

renderer.domElement.addEventListener('wheel', (e) => {{
  e.preventDefault();
  if (isPlaying) return;
  let idx = currentIdx + (e.deltaY > 0 ? 1 : -1);
  idx = Math.max(0, Math.min(layerMeshes.length-1, idx));
  showLayer(idx);
}}, {{ passive: false }});

window.addEventListener('resize', () => {{
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}});

function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}}
animate();
</script></body></html>"""


def main():
    print("Building mesh...")
    mesh = build_house_mesh()

    print("Slicing...")
    config = SlicerConfig()
    slicer = PlanarSlicer(mesh, layer_height=10.0)
    slicer.slice_model()
    print(f"  {slicer.number_of_layers} layers, {slicer.number_of_paths} paths")

    print("Converting to JSON...")
    layers_json = layer_data_to_json(slicer, max_sample=64)
    print(f"  {len(layers_json)} sampled layers")

    print("Generating HTML...")
    html = generate_html(layers_json)
    path = os.path.join(OUT, "compas_house_viz.html")
    with open(path, "w") as f:
        f.write(html)
    print(f"  Written to {path}")
    print("Done!")


if __name__ == "__main__":
    main()
