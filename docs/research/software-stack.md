# Software stack — 3D concrete printing design-to-print pipeline

Complete reference of CAD, CAM, slicer, scripting, and simulation tools for the 3DCP workflow, connecting to the `bim2print` pipeline.

---

## Design tools

### Autodesk Fusion 360

| Field | Detail |
|-------|--------|
| **Type** | Full CAD/CAM/CAE suite |
| **3DCP use** | Solid modelling → STL export → slicer |
| **Price** | Free trial; ~$70/mo subscription |
| **Pros** | All-in-one; generative design; CAM built-in |
| **Cons** | Cloud-dependent; not parametric-native like Rhino |
| **Export pipeline** | `.f3d` / `.step` → STL → mesh repair → slicer |

### Rhino 3D + Grasshopper

| Field | Detail |
|-------|--------|
| **Type** | Parametric NURBS modelling + visual programming |
| **3DCP use** | Complex facade geometry; print-path scripting via plugins |
| **Price** | $995 USD (Rhino 8); Grasshopper included |
| **Pros** | Parametric; huge plugin ecosystem; direct print-path control |
| **Cons** | Steeper learning curve; no built-in CAM for concrete |
| **Plugins** | COMPAS (compas-dev.github.io) for fabrication |
| **Export pipeline** | `.gh` definition → JSON geometry → `bim2print gh` |

### Dassault Systèmes 3DEXPERIENCE

| Field | Detail |
|-------|--------|
| **Type** | BIM-centric platform |
| **3DCP use** | Full BIM model → slicer integration |
| **Price** | Enterprise licensing |
| **Best for** | Large projects requiring full BIM lifecycle |
| **Export pipeline** | IFC → `bim2print ifc` |

---

## Slicer & toolpath tools

### COMPAS + COMPAS Slicer (Python)

| Field | Detail |
|-------|--------|
| **Type** | Open-source fabrication library |
| **Already in** | `bim2print` dependencies (`compas`, `compas-slicer`) |
| **Capabilities** | Layer slicing, contour offset, infill generation |
| **Docs** | <https://compas.dev/compas-slicer/> |

### Python libraries

| Library | Use case | Status |
|---------|----------|--------|
| `numpy` | Point cloud / contour geometry | Already in `bim2print` |
| `networkx` | Print-path sequencing (TSP solver) | Already in `bim2print` |
| `pyclipper` | Polygon offset / boolean operations | Already in `bim2print` |
| `trimesh` | Mesh repair, STL import/export | Add if importing STL geometry |
| `shapely` | 2D geometry operations | Alternative to pyclipper |
| `mesh-calculator` | Stress analysis of printed geometry | Evaluation |

### Grasshopper plugins (design-time)

| Plugin | Purpose | 
|--------|---------|
| **COMPAS for GH** | Fabrication-aware modelling; `bim2print` generates `.gh` files |
| **Kangaroo** | Physics simulation (print path sag, material behaviour) |
| **Ladybug Tools** | Environmental analysis (thermal, daylight) |
| **Karamba 3D** | Structural analysis of printed walls |

---

## Simulation & verification

| Tool | What it verifies | When in pipeline |
|------|-----------------|------------------|
| **Karamba 3D** (GH) | Structural adequacy of printed wall | Before slicing |
| **COMPAS Slicer preview** | Inter-layer bonding, contour overlap | Slicing stage |
| **G-code simulators** | Print path collisions, overhangs | After G-code gen |
| **molecular-dynamics (LAMMPS)** | Cement hydration modelling (research) | Novel mix development |

---

## End-to-end workflow

```
┌────────────────────────────────────────────────────────────┐
│ DESIGN PHASE                                                │
│ Fusion 360 / Rhino+GH / 3DEXPERIENCE → IFC or GH JSON      │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ SLICING PHASE                                               │
│ bim2print ifc/gh → layer slices (COMPAS Slicer backend)     │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ TOOLPATH PHASE                                              │
│ bim2print → perimeters + infill (pyclipper + networkx)      │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ G-CODE GENERATION                                           │
│ bim2print → Marlin-compatible G-code                        │
│ Post-processing: Cura / Simplify3D / custom scripts         │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ SIMULATION                                                  │
│ G-code simulator (collision, overhang, material usage)      │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ PRINT                                                       │
│ CyBe / Luyten / Contour3D / PaCompatible                    │
└────────────────────────────────────────────────────────────┘
```

---

## Recommended toolchain for Sydney pilot

| Role | Tool | Why |
|------|------|-----|
| BIM model | **3DEXPERIENCE** or **Revit** (export IFC) | Industry standard — certifier expectations |
| Parametric geometry | **Rhino 7+Grasshopper** | COMPAS integration; print-path control |
| Slicing + toolpath | **bim2print** (this repo) | Already handles both IFC and GH paths |
| Structural analysis | **Karamba 3D** | Integrated in GH workflow |
| Lab testing | **ULTRA Labs** | NATA reports for EoS dossier |
