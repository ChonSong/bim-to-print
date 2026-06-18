# Grasshopper Node Map — `bim2print generate-gh`

The generated `.gh` file connects four components to produce a JSON geometry file
consumable by `bim2print gh`.

## Node diagram

```
  ┌──────────────────────┐
  │   Rectangle (Rect)   │  ←  Plane=XY, Width=X, Width Y=Y, R=0
  └──────────┬───────────┘
             │ curve
             ▼
  ┌──────────────────────┐
  │   Extrude            │  ←  Direction=(0,0,1), Height=Z
  └──────────┬───────────┘
             │ brep
        ┌────┴────┐
        ▼         ▼
  ┌──────────┐ ┌──────────────┐
  │  Panel   │ │  Python      │
  │  info    │ │  Export JSON │  →  writes .json file
  └──────────┘ └──────────────┘
```

## Component reference

### 1. Rectangle (BRep)
- **Name**: Rectangle
- **Inputs**:
  - `Plane`: `Plane.WorldXY` (fixed)
  - `Width X`: wall length (mm)
  - `Width Y`: wall thickness (mm)
  - `R`: corner radius (0 = sharp)
- **Output**: Closed curve

### 2. Extrude
- **Name**: Extrude
- **Inputs**:
  - `Base`: curve from Rectangle
  - `Direction`: `Vector3D(0,0,1)` (fixed)
  - `Height`: wall height (mm)
- **Output**: Solid Brep

### 3. Panel
- **Name**: Panel
- **Display text**: wall dimensions, volume, layer count

### 4. Python Export
- **Name**: Python (Export JSON)
- **Input**: Brep from Extrude
- **Output**: file path string
- **Code**: extracts bounding box → writes `[{name, points_2d, height}]` JSON

## Usage

```bash
# Generate the .gh file
python -m bim_to_print.gh_definition wall.gh \
    --width 3000 --thickness 200 --height 2400

# Open wall.gh in Grasshopper, run it → JSON exported to /tmp/gh_wall.json

# Convert to G-code
bim2print gh /tmp/gh_wall.json wall.gcode
```

## Output JSON format

```json
[
  {
    "name": "GH-Wall",
    "ifc_type": "IfcWall",
    "points_2d": [[0, 0], [3000, 0], [3000, 200], [0, 200], [0, 0]],
    "base_elevation": 0,
    "height": 2400
  }
]
```
