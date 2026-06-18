#!/usr/bin/env python3
"""Parse G-code file and emit a 3D toolpath HTML visualisation via Three.js.

Usage:
    python render_gcode.py <input.gcode> [output.html]
"""

import re
import json
import sys
import os


def parse_gcode(gcode_path: str) -> tuple[list[dict], dict]:
    """Parse G-code file and return moves + stats."""
    moves = []
    current_z = 0.0
    current_e = 0.0
    line_pat = re.compile(r'^(G[01])\s+(.*)')

    with open(gcode_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(';') or not line:
                continue
            m = line_pat.match(line)
            if not m:
                continue
            cmd = m.group(1)
            rest = m.group(2).split(';')[0].strip()
            params = {}
            for part in rest.split():
                if len(part) >= 2 and part[0] in 'XYZEF':
                    try:
                        params[part[0]] = float(part[1:])
                    except ValueError:
                        pass

            x = params.get('X')
            y = params.get('Y')
            z = params.get('Z')
            e = params.get('E')

            if x is not None and y is not None:
                moves.append({
                    'cmd': cmd,
                    'x': x, 'y': y,
                    'z': current_z,
                    'e': e if e is not None else current_e,
                    'extrude': cmd == 'G1' and e is not None and abs(e) > 0.001,
                })
            if z is not None:
                current_z = z
            if e is not None:
                current_e = e

    travel_dist = sum(
        ((m2['x'] - m1['x'])**2 + (m2['y'] - m1['y'])**2)**0.5
        for m1, m2 in zip(moves[:-1], moves[1:])
        if m2.get('extrude') and m1.get('extrude')
    )

    return moves, {'total_moves': len(moves), 'travel_dist_mm': round(travel_dist, 1)}


def build_layer_data(moves: list[dict], max_sample_layers: int = 48) -> list[dict]:
    """Group moves into per-layer print segments, sample for display.

    Only extrusion moves (G1 with E > 0) are rendered. Travel moves (G0)
    are skipped so openings appear as clear gaps.
    Each layer stores multiple independent line segments.
    """
    layers = {}
    for m in moves:
        if not m.get('extrude'):
            continue  # skip travel moves
        z_key = round(m['z'], 2)
        if z_key not in layers:
            layers[z_key] = []
        layers[z_key].append(m)

    z_vals = sorted(layers.keys())
    step = max(1, len(z_vals) // max_sample_layers)
    sampled_z = z_vals[::step]

    all_layers = []
    for z in sampled_z:
        pts = layers[z]
        if len(pts) > 1:
            # Build segments: each contiguous run of extrude moves = one segment
            segments = []
            seg = []
            for p in pts:
                if seg:
                    seg.append(p)
                else:
                    seg = [p]
                # Check if next point connects continuously
            # Simple approach: each point pair is a segment
            # Actually for line rendering, just pack all points but render as grouped segments
            flat = []
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i+1]
                dist = ((b['x'] - a['x'])**2 + (b['y'] - a['y'])**2)**0.5
                if dist > 100:  # large jump = new segment
                    continue  # skip the travel gap
                if not flat:
                    flat.extend([round(a['x'], 1), round(a['y'], 1)])
                flat.extend([round(b['x'], 1), round(b['y'], 1)])
            if flat:
                all_layers.append({'z': round(z, 2), 'pts': flat[:400]})

    return all_layers


def generate_html(layer_data: list[dict], stats: dict, data_json: str) -> str:
    """Generate standalone Three.js HTML visualisation."""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>bim2print — Toolpath Visualisation</title>
<style>
  body {{ margin:0; overflow:hidden; background:#0d1117; font-family:system-ui,sans-serif; }}
  #info {{
    position:fixed; top:12px; left:12px; color:#8b949e; font-size:13px; z-index:10;
    background:#161b22; padding:8px 14px; border-radius:8px; border:1px solid #30363d;
    pointer-events:none;
  }}
  #info h2 {{ margin:0 0 4px; color:#f0f6fc; font-size:16px; }}
  #stats {{
    position:fixed; bottom:12px; left:12px; color:#8b949e; font-size:12px; z-index:10;
    background:#161b22; padding:6px 12px; border-radius:8px; border:1px solid #30363d;
  }}
  .controls {{ position:fixed; bottom:12px; right:12px; z-index:10; display:flex; gap:6px; }}
  .controls button {{
    background:#21262d; border:1px solid #30363d; color:#c9d1d9; font-size:13px;
    padding:6px 14px; border-radius:6px; cursor:pointer;
  }}
  .controls button:hover {{ background:#30363d; }}
</style>
</head>
<body>
<div id="info">
  <h2>🏠 bim2print — Building Toolpath</h2>
  {stats['total_moves']} moves · <span id="layer-label">layer 1</span>
</div>
<div id="stats">{stats['travel_dist_mm']}m total travel</div>
<div class="controls">
  <button id="play-btn">▶ Play</button>
  <button id="reset-btn">⟲ Reset</button>
</div>

<script type="importmap">
{{
  "imports": {{
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }}
}}
</script>

<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

const LAYER_COLORS = [0x58a6ff, 0x3fb950, 0xd29922, 0xf78166, 0xbc8cff, 0x79c0ff, 0x56d364, 0xe3b341, 0xffa657, 0xd2a8ff];
const layerData = {data_json};

// Scene
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d1117);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth/window.innerHeight, 1, 100000);
camera.position.set(4000, 3000, 5000);

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
const gridHelper = new THREE.GridHelper(6000, 20, 0x21262d, 0x21262d);
gridHelper.position.y = 0;
scene.add(gridHelper);

// Lights
scene.add(new THREE.AmbientLight(0x404660));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(2000, 5000, 3000);
scene.add(dirLight);
const backLight = new THREE.DirectionalLight(0x8888ff, 0.3);
backLight.position.set(-2000, 1000, -3000);
scene.add(backLight);

// Build layers
const layerLines = [];
let allPoints = [];

layerData.forEach((ld, idx) => {{
  const pts = ld.pts;
  if (pts.length < 4) return;
  const color = LAYER_COLORS[idx % LAYER_COLORS.length];
  const z = ld.z;

  const positions = [];
  for (let i = 0; i < pts.length; i += 2) {{
    positions.push(pts[i], z, pts[i+1]);
  }}
  if (positions.length < 6) return;

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  const material = new THREE.LineBasicMaterial({{ color, transparent: true, opacity: 0.3 }});
  const line = new THREE.Line(geometry, material);
  line.visible = false;
  scene.add(line);
  layerLines.push({{ line, material, z }});
  allPoints.push(...positions);
}});

// Auto-fit camera to data
if (allPoints.length > 0) {{
  let minX=Infinity,maxX=-Infinity,minZ=Infinity,maxZ=-Infinity;
  for (let i=0; i<allPoints.length; i+=3) {{
    minX=Math.min(minX,allPoints[i]); maxX=Math.max(maxX,allPoints[i]);
    minZ=Math.min(minZ,allPoints[i+2]); maxZ=Math.max(maxZ,allPoints[i+2]);
  }}
  const cx = (minX+maxX)/2, cz = (minZ+maxZ)/2;
  const span = Math.max(maxX-minX, maxZ-minZ, 1000);
  camera.position.set(cx + span*1.2, span*0.8, cz + span*1.5);
  controls.target.set(cx, 0, cz);
}}

layerLines.sort((a,b) => a.z - b.z);

const layerLabel = document.getElementById('layer-label');
let currentLayerIdx = 0;
let isPlaying = false;
let playTimer = null;

function showLayer(idx) {{
  layerLines.forEach((l, i) => {{
    if (i <= idx) {{
      l.line.visible = true;
      l.material.opacity = (i === idx) ? 1.0 : 0.3;
    }} else {{
      l.line.visible = false;
    }}
  }});
  const z = layerLines[idx]?.z ?? 0;
  layerLabel.textContent = `layer ${{idx+1}}/${{layerLines.length}} · Z=${{z.toFixed(1)}}mm`;
  currentLayerIdx = idx;
}}

function resetView() {{
  controls.target.set(2500, 0, 200);
  controls.update();
  showLayer(0);
}}

showLayer(0);

document.getElementById('play-btn').addEventListener('click', () => {{
  if (isPlaying) {{
    isPlaying = false;
    clearInterval(playTimer);
    document.getElementById('play-btn').textContent = '▶ Play';
    return;
  }}
  isPlaying = true;
  document.getElementById('play-btn').textContent = '⏸ Pause';
  showLayer(0);
  let i = 0;
  playTimer = setInterval(() => {{
    i++;
    showLayer(i);
    if (i >= layerLines.length - 1) {{
      clearInterval(playTimer);
      isPlaying = false;
      document.getElementById('play-btn').textContent = '▶ Play';
    }}
  }}, 80);
}});

document.getElementById('reset-btn').addEventListener('click', resetView);

renderer.domElement.addEventListener('wheel', (e) => {{
  e.preventDefault();
  if (isPlaying) return;
  let idx = currentLayerIdx + (e.deltaY > 0 ? 1 : -1);
  idx = Math.max(0, Math.min(layerLines.length-1, idx));
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
</script>
</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python render_gcode.py <input.gcode> [output.html]")
        sys.exit(1)

    gcode_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'toolpath_viz.html'

    if not os.path.exists(gcode_path):
        print(f"Error: {gcode_path} not found")
        sys.exit(1)

    moves, stats = parse_gcode(gcode_path)
    print(f"Parsed {stats['total_moves']} moves from {gcode_path}")

    layer_data = build_layer_data(moves, max_sample_layers=48)
    print(f"Sampled {len(layer_data)} layers for display")

    data_json = json.dumps(layer_data)
    html = generate_html(layer_data, stats, data_json)

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Wrote {output_path} — serve it and open in browser.")


if __name__ == '__main__':
    main()
