#!/usr/bin/env python3
"""Generate annotated SVG visualisations from G-code toolpaths.

Produces two SVGs:
  1. Plan view — top-down with callout labels, dimensions, scale bar, compass
  2. Layer stack — isometric stacked layers with height annotations

Usage:
    python gcode_to_svg.py <input.gcode> [--plan plan.svg] [--stack stack.svg]
"""

import math
import re
import os
import argparse
from collections import defaultdict


# ── G-code parser ──────────────────────────────────────────────────────────

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
            e_val = params.get('E')
            if x is not None and y is not None:
                moves.append({
                    'cmd': cmd,
                    'x': x, 'y': y,
                    'z': current_z,
                    'e': e_val if e_val is not None else 0,
                    'extrude': cmd == 'G1' and e_val is not None and abs(float(e_val)) > 0.001,
                })
            if z is not None:
                current_z = z
    return moves


def get_bounds(moves):
    xs = [m['x'] for m in moves]
    ys = [m['y'] for m in moves]
    zs = [m['z'] for m in moves]
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def group_by_layer(moves, max_layers=32):
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


def build_segments(layer_moves, max_gap=100.0):
    segments = []
    cur = []
    for m in layer_moves:
        if not cur:
            cur.append((m['x'], m['y']))
            continue
        last = cur[-1]
        dist = math.hypot(m['x'] - last[0], m['y'] - last[1])
        if dist > max_gap:
            if len(cur) >= 2:
                segments.append(cur)
            cur = [(m['x'], m['y'])]
        else:
            cur.append((m['x'], m['y']))
    if len(cur) >= 2:
        segments.append(cur)
    return segments


# ── SVG builders ────────────────────────────────────────────────────────────

def _rect_around_label(tx, ty, w=110, h=18, padding=4):
    """Return x,y,w,h for a bg rect that fits around a label."""
    x = tx - w//2
    y = ty - h//2
    return x, y, w, h


def generate_plan_svg(layers, bounds, width=800, pad=60):
    x_min, y_min, z_min, x_max, y_max, z_max = bounds
    x_min -= 200
    y_min -= 200
    x_max += 200
    y_max += 200
    rx = x_max - x_min
    ry = y_max - y_min
    mr = max(rx, ry)
    s = (width - 2 * pad) / mr
    h = int((width - 2 * pad) * (ry / rx) + 2 * pad)

    def tx(x): return pad + (x - x_min) * s
    def ty(y): return h - pad - (y - y_min) * s

    # ── Build toolpath lines ──
    all_lines = []
    for li, layer in enumerate(reversed(layers)):
        segs = build_segments(layer['moves'])
        for seg in segs:
            if len(seg) < 2:
                continue
            start, end = seg[0], seg[-1]
            closed = math.hypot(end[0]-start[0], end[1]-start[1]) < 20
            seg_len = sum(math.hypot(seg[i+1][0]-seg[i][0], seg[i+1][1]-seg[i][1]) for i in range(len(seg)-1))
            is_perim = closed and seg_len > 50
            color = '#58a6ff' if is_perim else '#3fb950'
            sw = 2.5 if is_perim else 1.0
            op = min(0.55 + (li/len(layers))*0.3, 0.85) if is_perim else min(0.12 + (li/len(layers))*0.12, 0.24)
            pts = ' '.join(f'{tx(p[0]):.1f},{ty(p[1]):.1f}' for p in seg)
            all_lines.append(
                f'    <polyline points="{pts}" fill="none" '
                f'stroke="{color}" stroke-width="{sw}" opacity="{op:.3f}"/>'
            )

    # ── Building element descriptors (known from demo_house.json) ──
    # These are the known building element positions; we use them for annotation
    # labels even though the G-code itself doesn't carry semantic names.
    elements = [
        # (label, x_center, y_center, color, w, h, is_opening)
        ("Main Wall\n4,000 × 200 mm", 2000, 100, '#58a6ff', 140, 36, False),
        ("Side Wall\n1,000 × 200 mm", 4100, 500, '#58a6ff', 120, 36, False),
        ("Column\n300 × 300 mm", 4350, 150, '#bc8cff', 100, 36, False),
        ("Window 1\n1,000 × 1,200 mm", 1000, 100, '#f78166', 110, 36, True),
        ("Door\n1,000 × 2,100 mm", 3000, 100, '#d29922', 100, 36, True),
        ("Window 2\n600 × 1,000 mm", 4100, 600, '#f78166', 110, 36, True),
    ]

    # ── Layer count bar ──
    bar_x, bar_y, bar_h = width - 40, pad + 40, h - 2 * pad - 80
    bar_colors = []
    layer_count = min(len(layers), 48)
    for i in range(layer_count):
        c = ['#58a6ff','#3fb950','#d29922','#f78166','#bc8cff',
             '#79c0ff','#56d364','#e3b341','#ffa657','#d2a8ff'][i % 10]
        seg_h = max(bar_h / layer_count, 3)
        yp = bar_y + i * seg_h
        bar_colors.append(
            f'    <rect x="{bar_x}" y="{yp:.1f}" width="12" height="{seg_h:.1f}" '
            f'fill="{c}" opacity="0.7" rx="1"/>'
        )

    # ── Compass ──
    cx, cy = pad + 25, pad + 20
    compass = (
        f'  <!-- Compass -->\n'
        f'  <circle cx="{cx}" cy="{cy}" r="16" fill="none" stroke="#8b92ab" stroke-width="1"/>\n'
        f'  <polygon points="{cx},{cy-14} {cx-4},{cy+2} {cx},{cy-4} {cx+4},{cy+2}" fill="#e05a5a"/>\n'
        f'  <text x="{cx}" y="{cy-20}" fill="#8b92ab" font-size="9" text-anchor="middle">N</text>\n'
    )

    # ── Scale bar ──
    scale_1000 = pad + 8
    scale_bar_w = 1000 * s
    scale_y = h - pad + 30
    scale_bar = (
        f'  <!-- Scale bar -->\n'
        f'  <line x1="{scale_1000}" y1="{scale_y}" x2="{scale_1000 + scale_bar_w}" y2="{scale_y}" '
        f'stroke="#8b92ab" stroke-width="2"/>\n'
        f'  <line x1="{scale_1000}" y1="{scale_y-5}" x2="{scale_1000}" y2="{scale_y+3}" stroke="#8b92ab" stroke-width="1.5"/>\n'
        f'  <line x1="{scale_1000 + scale_bar_w}" y1="{scale_y-5}" x2="{scale_1000 + scale_bar_w}" y2="{scale_y+3}" stroke="#8b92ab" stroke-width="1.5"/>\n'
        f'  <text x="{scale_1000 + scale_bar_w/2}" y="{scale_y+14}" fill="#8b92ab" font-size="10" text-anchor="middle">1,000 mm</text>\n'
    )

    # ── Callout boxes for each element ──
    callout_svg = []
    seen_y = {}  # avoid label overlap
    for label, ex, ey, color, bw, bh, is_opening in elements:
        px = tx(ex)
        py = ty(ey)

        # Leader line from annotation to element
        label_x = px + (-1 if px > width/2 else 1) * 160
        label_x = max(pad + 10, min(width - pad - 10, label_x))

        # Push label downward if another label at same x-range
        label_y = py - 60 if py > h/2 else py + 60
        for k in seen_y:
            if abs(label_x - k) < 180:
                label_y = max(label_y, seen_y[k] + 45)
        seen_y[label_x] = label_y

        line_color = color if not is_opening else '#8b92ab'

        # Line from element to callout box
        lx = label_x
        ly = label_y
        cx_tr = 6  # corner radius
        bw_use = max(bw, len(label.split('\n')[0]) * 7 + 10)
        bh_use = bh

        callout_svg.append(
            f'  <!-- {label.replace(chr(10)," ")} -->\n'
            f'  <line x1="{px:.1f}" y1="{py:.1f}" x2="{lx:.1f}" y2="{ly:.1f}" '
            f'stroke="{line_color}" stroke-width="1" stroke-dasharray="4,3"/>'
        )
        # Box background
        callout_svg.append(
            f'  <rect x="{lx-bw_use//2}" y="{ly-bh_use//2}" width="{bw_use}" height="{bh_use}" '
            f'rx="{cx_tr}" fill="#1a1d27" stroke="{line_color}" stroke-width="1" opacity="0.95"/>'
        )
        # Label text (multiline)
        lines = label.split('\n')
        for li2, line_txt in enumerate(lines):
            ty2 = ly - 6 + li2 * 16
            fc = color if not is_opening else '#f0c040'
            fw = '600' if li2 == 0 else '400'
            fs = '10' if li2 == 1 else '11'
            callout_svg.append(
                f'  <text x="{lx}" y="{ty2}" fill="{fc}" font-size="{fs}" '
                f'font-weight="{fw}" text-anchor="middle">{line_txt}</text>'
            )

    # ─── Assemble SVG ───
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h+50}"
     style="background:#0f1117; border-radius:8px; font-family:system-ui,sans-serif;">
  <defs>
    <linearGradient id="bg-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0f1117"/>
      <stop offset="100%" stop-color="#1a1d27"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{h+50}" fill="url(#bg-grad)" rx="8"/>

  <!-- Title -->
  <text x="{pad}" y="26" fill="#e2e4ed" font-size="15" font-weight="700">Plan view — demo house toolpath</text>
  <text x="{pad}" y="43" fill="#8b92ab" font-size="11">56,260 moves · {len(layers)} sampled layers · Perimeters (blue) · Infill (green) · Openings visible as gaps</text>

  <!-- Grid -->
  <line x1="{tx(x_min)}" y1="{ty(0)}" x2="{tx(x_max)}" y2="{ty(0)}" stroke="#2d3348" stroke-width="0.5" stroke-dasharray="4,4"/>
  <line x1="{tx(4000)}" y1="{ty(y_min)}" x2="{tx(4000)}" y2="{ty(y_max)}" stroke="#2d3348" stroke-width="0.5" stroke-dasharray="4,4"/>

  <!-- Toolpath lines -->
{chr(10).join(all_lines)}

  <!-- Callout annotations -->
{chr(10).join(callout_svg)}

  <!-- Dimension: overall width -->
  <line x1="{tx(0)}" y1="{ty(-30)}" x2="{tx(4500)}" y2="{ty(-30)}" stroke="#8b92ab" stroke-width="1"/>
  <polygon points="{tx(0)},{ty(-26)} {tx(0)},{ty(-34)}" fill="#8b92ab"/>
  <polygon points="{tx(4500)},{ty(-26)} {tx(4500)},{ty(-34)}" fill="#8b92ab"/>
  <text x="{tx(2250)}" y="{ty(-18)}" fill="#8b92ab" font-size="10" text-anchor="middle">4,500 mm overall width</text>

  <!-- Dimension: main wall length -->
  <line x1="{tx(100)}" y1="{ty(-55)}" x2="{tx(3900)}" y2="{ty(-55)}" stroke="#2d3348" stroke-width="0.5"/>
  <text x="{tx(2000)}" y="{ty(-42)}" fill="#8b92ab" font-size="9" text-anchor="middle">Main wall 4,000 mm</text>

  <!-- Layer count bar -->
  <text x="{bar_x+6}" y="{bar_y-6}" fill="#8b92ab" font-size="9" text-anchor="middle">Layers</text>
{chr(10).join(bar_colors)}
  <text x="{bar_x+6}" y="{bar_y+bar_h+10}" fill="#8b92ab" font-size="9" text-anchor="middle">↑</text>

  {compass}

  {scale_bar}

  <!-- Legend -->
  <rect x="{width//2-100}" y="{h-30}" width="200" height="22" rx="4" fill="#1a1d27" opacity="0.9"/>
  <line x1="{width//2-90}" y1="{h-19}" x2="{width//2-60}" y2="{h-19}" stroke="#58a6ff" stroke-width="2.5"/>
  <text x="{width//2-52}" y="{h-16}" fill="#8b92ab" font-size="9">Perimeter</text>
  <line x1="{width//2+5}" y1="{h-19}" x2="{width//2+30}" y2="{h-19}" stroke="#3fb950" stroke-width="1"/>
  <text x="{width//2+38}" y="{h-16}" fill="#8b92ab" font-size="9">Infill (20%)</text>
</svg>"""
    return svg


def generate_stack_svg(layers, bounds, width=800, pad=60):
    x_min, y_min, z_min, x_max, y_max, z_max = bounds
    rx = x_max - x_min + 400
    rz = z_max - z_min + 100
    if rz < 100:
        rz = 100
    s = (width - 2 * pad) / max(rx, rz * 3)
    cx, cy = x_min + rx/2 - 200, y_min + (y_max - y_min) / 2
    ctr_x = width / 2
    base_y = width - pad

    def proj(x, y, z):
        dx = (x - cx) * s
        dy = (y - cy) * s * 0.5
        px = ctr_x + dx - dy
        py = base_y - z * s * 2.5 + (dx + dy) * 0.3
        return px, py

    # ── Toolpath polylines ──
    colors = ['#58a6ff','#3fb950','#d29922','#f78166','#bc8cff',
              '#79c0ff','#56d364','#e3b341','#ffa657','#d2a8ff']
    all_polys = []
    for li, layer in enumerate(layers[:40]):
        segs = build_segments(layer['moves'])
        c = colors[li % 10]
        op = min(0.15 + (li / len(layers)) * 0.5, 0.8)
        z_off = layer['z'] - 2.5
        for seg in segs:
            if len(seg) < 2:
                continue
            pts = ' '.join(f'{proj(p[0],p[1],z_off)[0]:.1f},{proj(p[0],p[1],z_off)[1]:.1f}' for p in seg)
            all_polys.append(
                f'    <polyline points="{pts}" fill="none" '
                f'stroke="{c}" stroke-width="1.5" opacity="{op:.3f}"/>'
            )

    # ── Annotations ──
    ann = []
    # Height labels
    total_z = z_max - z_min
    for h_mark in range(0, int(total_z) + 100, 600):
        if h_mark == 0:
            continue
        px1, py1 = proj(0, 0, h_mark)
        ann.append(
            f'  <line x1="{width-pad+40}" y1="{py1}" x2="{width-pad+65}" y2="{py1}" '
            f'stroke="#2d3348" stroke-width="0.5" stroke-dasharray="3,2"/>'
        )
        ann.append(
            f'  <text x="{width-pad+70}" y="{py1+4}" fill="#8b92ab" font-size="9">{h_mark} mm</text>'
        )

    # Layer number callouts (every ~5 layers)
    step = max(1, len(layers) // 7)
    for li in range(0, len(layers), step):
        layer = layers[li]
        segs = build_segments(layer['moves'])
        if not segs:
            continue
        mid = segs[len(segs)//2][len(segs[len(segs)//2])//2]
        px1, py1 = proj(mid[0], mid[1], layer['z'])
        c = colors[li % 10]
        ann.append(
            f'  <text x="{px1-20}" y="{py1+2}" fill="{c}" font-size="8" '
            f'font-weight="600" text-anchor="end" opacity="0.8">L{li+1}</text>'
        )

    # Bottom / top labels
    px_b, py_b = proj(0, 0, z_min)
    px_t, py_t = proj(0, 0, z_max)
    ann.append(
        f'  <text x="{pad+10}" y="{py_b+30}" fill="#8b92ab" font-size="10">'
        f'Bottom: Z={z_min:.0f} mm</text>'
    )
    ann.append(
        f'  <text x="{pad+10}" y="{py_t-10}" fill="#8b92ab" font-size="10">'
        f'Top: Z={z_max:.0f} mm</text>'
    )

    # Profile labels
    ann.append(
        f'  <text x="{proj(2000,100,1200)[0]}" y="{proj(2000,100,1200)[1]+10}" '
        f'fill="#58a6ff" font-size="9" text-anchor="middle">Main Wall</text>'
    )
    ann.append(
        f'  <text x="{proj(4100,500,1200)[0]}" y="{proj(4100,500,1200)[1]+10}" '
        f'fill="#58a6ff" font-size="9" text-anchor="middle">Side Wall</text>'
    )
    ann.append(
        f'  <text x="{proj(4350,150,1200)[0]}" y="{proj(4350,150,1200)[1]+10}" '
        f'fill="#bc8cff" font-size="9" text-anchor="middle">Column</text>'
    )

    # ── Height dimension bar ──
    px_b2, py_b2 = proj(0, 0, z_min)
    px_t2, py_t2 = proj(0, 0, z_max)
    dim_x = width - pad + 40
    dim_bar = (
        f'  <line x1="{dim_x}" y1="{py_b2}" x2="{dim_x}" y2="{py_t2}" '
        f'stroke="#8b92ab" stroke-width="1.5"/>\n'
        f'  <polygon points="{dim_x-4},{py_b2+8} {dim_x},{py_b2} {dim_x+4},{py_b2+8}" fill="#8b92ab"/>\n'
        f'  <polygon points="{dim_x-4},{py_t2-8} {dim_x},{py_t2} {dim_x+4},{py_t2-8}" fill="#8b92ab"/>\n'
        f'  <text x="{dim_x+12}" y="{(py_b2+py_t2)/2+4}" fill="#8b92ab" font-size="10" '
        f'transform="rotate(-90,{dim_x+12},{(py_b2+py_t2)/2})">2,400 mm</text>\n'
    )

    # ── Legend ──
    legend_y = width - 16
    legend = (
        f'  <text x="{width/2}" y="{legend_y}" fill="#8b92ab" font-size="10" text-anchor="middle">'
        f'Each colour band = one sampled layer · {len(layers)} of 720 total · '
        f'<tspan fill="#58a6ff">perimeter</tspan> · '
        f'<tspan fill="#3fb950">infill</tspan></text>\n'
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {width}"
     style="background:#0f1117; border-radius:8px; font-family:system-ui,sans-serif;">
  <rect width="{width}" height="{width}" fill="#0f1117" rx="8"/>

  <text x="{width/2}" y="28" fill="#e2e4ed" font-size="15" font-weight="700" text-anchor="middle">Layer stack — isometric view</text>
  <text x="{width/2}" y="46" fill="#8b92ab" font-size="11" text-anchor="middle">
    {len(layers)} sampled layers · 2,400 mm total height · ~10 mm per layer</text>

  <!-- Print bed -->
  <rect x="{pad-10}" y="{base_y}" width="{width-2*pad+20}" height="10" rx="3" fill="#1a1d27" stroke="#2d3348" stroke-width="0.5"/>
  <text x="{width/2}" y="{base_y+24}" fill="#8b92ab" font-size="10" text-anchor="middle">Print bed</text>

  <!-- Toolpath lines -->
{chr(10).join(all_polys)}

  <!-- Height dimension -->
{dim_bar}

  <!-- Annotations -->
{chr(10).join(ann)}

  <!-- Legend -->
{legend}
</svg>"""
    return svg


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Generate annotated SVG visualisations from G-code')
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
