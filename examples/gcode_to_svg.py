#!/usr/bin/env python3
"""Generate static SVG plan-view and cross-section from G-code toolpaths.

Produces two SVGs:
  1. Plan view — top-down, perimeters + infill, all layers overlaid
  2. Layer stack — isometric-ish stacked layers showing the build

Usage:
    python gcode_to_svg.py <input.gcode> [--plan plan.svg] [--stack stack.svg]
"""

import math
import re
import sys
import os
import argparse
from collections import defaultdict


def parse_gcode(gcode_path: str) -> list[dict]:
    """Parse G-code into a list of moves."""
    moves = []
    current_z = 0.0
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
                    'e': e if e is not None else 0,
                    'extrude': cmd == 'G1' and e is not None and abs(float(e)) > 0.001,
                })
            if z is not None:
                current_z = z

    return moves


def get_bounds(moves: list[dict]) -> tuple:
    """Get bounding box of all moves."""
    xs = [m['x'] for m in moves]
    ys = [m['y'] for m in moves]
    zs = [m['z'] for m in moves]
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def group_by_layer(moves: list[dict], max_layers: int = 32) -> list[dict]:
    """Group extrusion moves by layer, sample for display."""
    layers = defaultdict(list)
    for m in moves:
        if not m.get('extrude'):
            continue
        z_key = round(m['z'], 1)
        layers[z_key].append(m)

    z_vals = sorted(layers.keys())
    step = max(1, len(z_vals) // max_layers)
    sampled = z_vals[::step]

    result = []
    for z in sampled:
        pts = layers[z]
        if len(pts) < 2:
            continue
        result.append({'z': z, 'moves': pts})
    return result


def build_segments(layer_moves: list[dict]) -> list[list[tuple]]:
    """Build continuous line segments from extrusion moves."""
    max_gap = 100.0
    segments = []
    current = []
    for m in layer_moves:
        if not current:
            current.append((m['x'], m['y']))
            continue
        last = current[-1]
        dist = math.hypot(m['x'] - last[0], m['y'] - last[1])
        if dist > max_gap or not m.get('extrude'):
            if len(current) >= 2:
                segments.append(current)
            current = [(m['x'], m['y'])]
        else:
            current.append((m['x'], m['y']))
    if len(current) >= 2:
        segments.append(current)
    return segments


def generate_plan_svg(
    layers: list[dict],
    bounds: tuple,
    width: int = 800,
    padding: int = 60,
) -> str:
    """Generate plan view SVG showing perimeters and infill."""
    x_min, y_min, z_min, x_max, y_max, z_max = bounds

    # Extend bounds slightly
    x_min -= 200
    y_min -= 200
    x_max += 200
    y_max += 200
    range_x = x_max - x_min
    range_y = y_max - y_min
    max_range = max(range_x, range_y)

    scale = (width - 2 * padding) / max_range
    height = int((width - 2 * padding) * (range_y / range_x) + 2 * padding)

    def tx(x):
        return padding + (x - x_min) * scale

    def ty(y):
        return height - padding - (y - y_min) * scale

    lines_svg = []
    # Process each layer — later layers drawn on top
    for layer_idx, layer in enumerate(reversed(layers)):
        segments = build_segments(layer['moves'])
        # Determine if this looks like perimeter or infill based on segment length
        for seg in segments:
            if len(seg) < 2:
                continue
            # Estimate: perimeters are closed loops (start ~= end), infill is back-and-forth
            start = seg[0]
            end = seg[-1]
            closed = math.hypot(end[0] - start[0], end[1] - start[1]) < 20.0
            seg_len = sum(math.hypot(seg[i+1][0]-seg[i][0], seg[i+1][1]-seg[i][1]) for i in range(len(seg)-1))
            is_perimeter = closed and seg_len > 50

            if is_perimeter:
                color = '#58a6ff'
                stroke_w = 2.5
                opacity = 0.6 + (layer_idx / len(layers)) * 0.3
            else:
                color = '#3fb950'
                stroke_w = 1.0
                opacity = 0.15 + (layer_idx / len(layers)) * 0.15

            pts_str = ' '.join(f'{tx(p[0])},{ty(p[1])}' for p in seg)
            lines_svg.append(
                f'    <polyline points="{pts_str}" fill="none" '
                f'stroke="{color}" stroke-width="{stroke_w}" '
                f'opacity="{min(opacity, 1.0)}" />'
            )

    # Build layer height bar
    layer_count = len(layers)
    bar_x = width - 40
    bar_y = padding
    bar_h = height - 2 * padding
    bar_colors = []
    for i in range(min(layer_count, 10)):
        c = ['#58a6ff', '#3fb950', '#d29922', '#f78166', '#bc8cff',
             '#79c0ff', '#56d364', '#e3b341', '#ffa657', '#d2a8ff'][i % 10]
        seg_h = bar_h / min(layer_count, 48)
        y_pos = bar_y + (i * seg_h / (layer_count / min(layer_count, 48)))
        bar_colors.append(f'    <rect x="{bar_x}" y="{y_pos}" width="12" height="{max(seg_h, 4)}" '
                          f'fill="{c}" opacity="0.7" rx="1" />')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     style="background:#0f1117; border-radius:8px; font-family:system-ui,sans-serif;">
  <defs>
    <linearGradient id="bg-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0f1117"/>
      <stop offset="100%" stop-color="#1a1d27"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg-grad)" rx="8"/>
  
  <!-- Title -->
  <text x="{padding}" y="28" fill="#e2e4ed" font-size="15" font-weight="700">Plan view — demo house toolpath</text>
  <text x="{padding}" y="46" fill="#8b92ab" font-size="11">Top-down view · {len(layers)} sampled layers · {sum(1 for l in layers for _ in build_segments(l['moves']))} toolpath segments</text>
  
  <!-- Grid -->
  <line x1="{tx(x_min)}" y1="{ty(0)}" x2="{tx(x_max)}" y2="{ty(0)}" stroke="#2d3348" stroke-width="0.5" stroke-dasharray="4,4"/>
  <line x1="{tx(4000)}" y1="{ty(y_min)}" x2="{tx(4000)}" y2="{ty(y_max)}" stroke="#2d3348" stroke-width="0.5" stroke-dasharray="4,4"/>

  <!-- Toolpath lines -->
{chr(10).join(lines_svg)}

  <!-- Dimension annotations -->
  <line x1="{tx(0)}" y1="{ty(-50)}" x2="{tx(4500)}" y2="{ty(-50)}" stroke="#8b92ab" stroke-width="1"/>
  <polygon points="{tx(0)},{ty(-45)} {tx(0)},{ty(-55)}" fill="#8b92ab"/>
  <polygon points="{tx(4500)},{ty(-45)} {tx(4500)},{ty(-55)}" fill="#8b92ab"/>
  <text x="{tx(2250)}" y="{ty(-35)}" fill="#8b92ab" font-size="10" text-anchor="middle">4,500 mm</text>

  <line x1="{tx(-80)}" y1="{ty(0)}" x2="{tx(-80)}" y2="{ty(1000)}" stroke="#8b92ab" stroke-width="1"/>
  <polygon points="{tx(-75)},{ty(0)} {tx(-85)},{ty(0)}" fill="#8b92ab"/>
  <polygon points="{tx(-75)},{ty(1000)} {tx(-85)},{ty(1000)}" fill="#8b92ab"/>
  <text x="{tx(-55)}" y="{ty(500)}" fill="#8b92ab" font-size="10" text-anchor="middle" transform="rotate(-90,{tx(-55)},{ty(500)})">1,000 mm</text>

  <!-- Opening labels -->
  <text x="{tx(1000)}" y="{ty(120)}" fill="#f78166" font-size="9" text-anchor="middle">Window</text>
  <text x="{tx(3000)}" y="{ty(120)}" fill="#d29922" font-size="9" text-anchor="middle">Door</text>
  <text x="{tx(4100)}" y="{ty(650)}" fill="#f78166" font-size="9" text-anchor="middle">Window</text>
  <text x="{tx(4350)}" y="{ty(50)}" fill="#bc8cff" font-size="9" text-anchor="middle">Column</text>
  
  <!-- Layer count bar (only show a subset) -->
  <text x="{bar_x + 6}" y="{bar_y - 8}" fill="#8b92ab" font-size="9" text-anchor="middle">Layers</text>
{chr(10).join(bar_colors)}
  <text x="{bar_x + 6}" y="{bar_y + bar_h + 14}" fill="#8b92ab" font-size="9" text-anchor="middle">↓</text>

  <!-- Legend -->
  <rect x="{padding}" y="{height - padding - 50}" width="200" height="40" rx="6" fill="#1a1d27" opacity="0.9"/>
  <line x1="{padding + 10}" y1="{height - padding - 35}" x2="{padding + 40}" y2="{height - padding - 35}" stroke="#58a6ff" stroke-width="2.5"/>
  <text x="{padding + 48}" y="{height - padding - 31}" fill="#8b92ab" font-size="10">Perimeter (contour)</text>
  <line x1="{padding + 10}" y1="{height - padding - 18}" x2="{padding + 40}" y2="{height - padding - 18}" stroke="#3fb950" stroke-width="1"/>
  <text x="{padding + 48}" y="{height - padding - 14}" fill="#8b92ab" font-size="10">Infill (lines, 20%)</text>

  <!-- Stats -->
  <text x="{width - padding}" y="{height - 16}" fill="#8b92ab" font-size="10" text-anchor="end">Main wall 4m · Side wall 1m · Column · 2 windows · 1 door</text>
</svg>"""
    return svg


def generate_stack_svg(
    layers: list[dict],
    bounds: tuple,
    width: int = 800,
    padding: int = 60,
) -> str:
    """Generate isometric-ish layer stack SVG — side-angle view of printed layers."""
    x_min, y_min, z_min, x_max, y_max, z_max = bounds
    range_x = x_max - x_min + 400
    range_z = z_max - z_min + 100
    if range_z < 100:
        range_z = 100

    # Isometric projection: x→x, y→(x+y)/2, z→z (pseudo-3D looking from NE at ~30°)
    scale = (width - 2 * padding) / max(range_x, range_z * 3)

    cx, cy = x_min + (x_max - x_min) / 2, y_min + (y_max - y_min) / 2
    center_x = width / 2
    base_y = width - padding

    def project(x, y, z):
        dx = (x - cx) * scale
        dy = (y - cy) * scale * 0.5
        px = center_x + dx - dy
        py = base_y - z * scale * 2.5 + (dx + dy) * 0.3
        return px, py

    # Build extrude segments per layer
    layer_polylines = []
    for idx, layer in enumerate(layers[:40]):
        segments = build_segments(layer['moves'])
        color_idx = idx % 10
        colors = ['#58a6ff', '#3fb950', '#d29922', '#f78166',
                  '#bc8cff', '#79c0ff', '#56d364', '#e3b341',
                  '#ffa657', '#d2a8ff']
        color = colors[color_idx]
        opacity = 0.15 + (idx / len(layers)) * 0.5

        for seg in segments:
            if len(seg) < 2:
                continue
            pts_str = ' '.join(f'{project(p[0], p[1], layer["z"] - 2.5)[0]:.1f},{project(p[0], p[1], layer["z"] - 2.5)[1]:.1f}' for p in seg)
            layer_polylines.append(
                f'    <polyline points="{pts_str}" fill="none" '
                f'stroke="{color}" stroke-width="1.5" opacity="{min(opacity, 0.8)}" />'
            )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {width}"
     style="background:#0f1117; border-radius:8px; font-family:system-ui,sans-serif;">
  <rect width="{width}" height="{width}" fill="#0f1117" rx="8"/>

  <text x="{width/2}" y="28" fill="#e2e4ed" font-size="15" font-weight="700" text-anchor="middle">Layer stack — isometric view</text>
  <text x="{width/2}" y="46" fill="#8b92ab" font-size="11" text-anchor="middle">
    {len(layers)} layers stacked · 2.4 m total height · 10 mm per layer</text>

{chr(10).join(layer_polylines)}

  <!-- Base plane -->
  <rect x="{padding}" y="{width - padding - 10}" width="{width - 2*padding}" height="10" rx="2" fill="#1a1d27" stroke="#2d3348" stroke-width="0.5"/>
  <text x="{width/2}" y="{width - padding - 2}" fill="#8b92ab" font-size="10" text-anchor="middle">Print bed</text>

  <!-- Height indicator -->
  <line x1="{width - padding + 40}" y1="{base_y}" x2="{width - padding + 40}" y2="{base_y - 2400 * scale * 2.5}" stroke="#8b92ab" stroke-width="1"/>
  <polygon points="{width - padding + 35},{base_y} {width - padding + 45},{base_y}" fill="#8b92ab"/>
  <polygon points="{width - padding + 35},{base_y - 2400 * scale * 2.5} {width - padding + 45},{base_y - 2400 * scale * 2.5}" fill="#8b92ab"/>
  <text x="{width - padding + 48}" y="{base_y - 1200 * scale * 2.5}" fill="#8b92ab" font-size="10">2,400 mm</text>

  <text x="{width/2}" y="{width - 10}" fill="#8b92ab" font-size="10" text-anchor="middle">
    Each colour band = sampled layer · interactivity at bim2print.codeovertcp.com</text>
</svg>"""
    return svg


def main():
    parser = argparse.ArgumentParser(description='Generate SVG visualisations from G-code')
    parser.add_argument('input', help='Input .gcode file')
    parser.add_argument('--plan', default='plan_view.svg', help='Output plan SVG path')
    parser.add_argument('--stack', default='layer_stack.svg', help='Output stack SVG path')
    args = parser.parse_args()

    print(f"Parsing {args.input}...")
    moves = parse_gcode(args.input)
    print(f"  {len(moves)} moves parsed")

    bounds = get_bounds(moves)
    print(f"  Bounds: X=[{bounds[0]:.0f},{bounds[3]:.0f}] Y=[{bounds[1]:.0f},{bounds[4]:.0f}] Z=[{bounds[2]:.0f},{bounds[5]:.0f}]")

    layers = group_by_layer(moves, max_layers=32)
    print(f"  {len(layers)} sampled layers")

    plan_svg = generate_plan_svg(layers, bounds)
    with open(args.plan, 'w') as f:
        f.write(plan_svg)
    print(f"  Plan view → {args.plan}")

    stack_svg = generate_stack_svg(layers, bounds)
    with open(args.stack, 'w') as f:
        f.write(stack_svg)
    print(f"  Stack view → {args.stack}")

    print("Done!")


if __name__ == '__main__':
    main()
