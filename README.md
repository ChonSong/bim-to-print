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

## Research module — Sydney 3D-printed housing

The [`docs/research/`](docs/research/) directory contains a comprehensive mid-2025 analysis of the 3D concrete printing landscape for residential construction in Sydney, covering:

| Document | What it covers |
|----------|---------------|
| [Vendor database](docs/research/vendor-database.md) | Contour3D, Luyten, CyBe, PaCompatible — specs, pricing, contacts |
| [Decision matrix](docs/research/decision-matrix.md) | Weighted comparison (cost × speed × envelope × maturity) |
| [Lab & certification directory](docs/research/lab-certification-directory.md) | ULTRA Labs, RMIT, UTS, certifiers, NCC clause map |
| [Software stack](docs/research/software-stack.md) | Rhino+GH, Fusion 360, COMPAS, `bim2print` integration |
| [Market landscape](docs/research/sydney-market-landscape.md) | Housing demand, council interest, cost drivers, strategic positioning |
| [Regulatory pathway](docs/research/regulatory-pathway.md) | NCC Performance Solution path, EoS dossier, certifier engagement |
| [Pilot roadmap](docs/research/pilot-roadmap.md) | 18-month phased plan with budgets and risk log |
| [Grant proposal template](docs/research/grant-proposal-template.md) | 1-page brief for councils and grant bodies |
| [EoS dossier template](docs/research/evidence-of-suitability-dossier.md) | Full evidence package structure for certifier submission |
| [Financial model](docs/research/financial-model-template.md) | CAPEX/OPEX, break-even analysis, per-print cost estimator |
| [Master index](docs/research/INDEX.md) | Quick navigation of all research artifacts |

## Architecture

### Data flow [![Pipeline](https://img.shields.io/badge/pipeline-IFC%2FGH%E2%86%92G--code-blue)](docs/ARCHITECTURE.md)

```
IFC / GH JSON → Reader → Slicer → Toolpath → G-code → Printer
                                                      ↓
                                              Research module
                                              (vendors, compliance,
                                               markets, roadmap)
```

## License

MIT — see `LICENSE`
