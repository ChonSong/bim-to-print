# bim-to-print

**BIM-to-G-code pipeline for 3D concrete printing.**

Reads building geometry from IFC files (or Grasshopper), slices it into print layers, generates toolpaths with configurable perimeters and infill, and outputs Marlin-compatible G-code.

---

## Quick start

```bash
# Install
pip install -e ".[dev]"

# Run demo wall (no IFC file needed)
bim2print demo --width 3000 --height 2400 -o wall.gcode

# From Grasshopper JSON export
bim2print gh examples/demo_wall.json output.gcode --layer-height 5

# From IFC file
bim2print ifc model.ifc output.gcode
```

## Pipeline

```
IFC / GH JSON
    ↓
IFC Reader (ifc_reader.py)   ← IfcOpenShell for IFC, manual JSON for GH
    ↓
Slicer (slicer.py)           ← horizontal layers at configured height
    ↓
Toolpath (toolpath.py)       ← contours + infill per layer
    ↓
G-code (gcode_writer.py)     ← Marlin/RepRap G-code
    ↓
.gcode file → printer
```

## Configuration

### Per-command options

| Option | Default | Description |
|--------|---------|-------------|
| `--layer-height` | 5.0 mm | Height of each printed layer |
| `--nozzle-diameter` | 6.0 mm | Nozzle opening |
| `--extrusion-width` | 8.0 mm | Extruded bead width |
| `--perimeter-count` | 2 | Number of contour passes |
| `--infill-pattern` | `lines` | `lines`, `grid`, or `none` |
| `--infill-density` | 0.3 (30%) | Fraction of area to infill |

### Print settings (programmatic API)

```python
from bim_to_print.gcode_writer import PrintSettings

settings = PrintSettings(
    travel_speed=6000,          # mm/min
    print_speed=1800,           # mm/min
    first_layer_speed=1200,     # mm/min
    extrusion_multiplier=1.0,   # flow rate tweak
    pre_gcode="M104 S200",      # run before print
    post_gcode="M84",           # run after print
)
```

## Commands

| Command | Purpose |
|---------|---------|
| `bim2print ifc <input> <output>` | Convert IFC file to G-code |
| `bim2print gh <input.json> <output>` | Convert GH JSON export to G-code |
| `bim2print demo [opts]` | Run demo on a rectangular wall |
| `bim2print generate-gh <output.gh>` | Generate a Grasshopper definition |

## Project structure

```
bim-to-print/
├── src/
│   └── bim_to_print/
│       ├── __init__.py         # version
│       ├── cli.py              # click CLI
│       ├── ifc_reader.py       # IFC file parsing
│       ├── slicer.py           # layer slicing
│       ├── toolpath.py         # perimeter + infill generation
│       ├── gcode_writer.py     # G-code output
│       ├── pipeline.py         # orchestration
│       └── gh_definition.py    # Grasshopper .gh generator
├── grasshopper/                 # generated .gh files
├── examples/
│   ├── demo_wall.json          # example JSON input
│   └── demo_wall.gcode         # example output
├── tests/
│   └── test_pipeline.py        # 25+ tests
├── docs/
│   ├── ARCHITECTURE.md
│   └── GH_NODE_MAP.md
└── pyproject.toml
```

## Dependencies

- **Runtime**: `click`, `numpy`
- **Optional (IFC)**: `ifcopenshell` (`pip install bim-to-print[ifc]`)
- **Optional (GH gen)**: `lxml` (built-in XML support)
- **Dev**: `pytest`, `pytest-cov`

## License

MIT — see `LICENSE`
