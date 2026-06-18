# Architecture

## Design goals

1. **No vendor lock-in** — each stage is a standalone pass-through function
2. **Configurable** — layer height, nozzle, speeds all tuneable without code changes
3. **Two input paths** — IFC files for BIM professionals, JSON for Grasshopper users

## Data flow

```
┌──────────┐   ┌─────────┐   ┌──────────┐   ┌────────────┐
│ IFC File │──→│ Reader  │──→│  Slicer  │──→│ Toolpath   │
│ (.ifc)   │   │ ifc_    │   │ slice_   │   │ Generator  │
└──────────┘   │ reader  │   │ model()  │   │ generate_  │
               └─────────┘   └──────────┘   │ toolpath() │
┌──────────┐   ┌─────────┐                  └─────┬──────┘
│ GH JSON  │──→│ JSON    │                        │
│ (.json)  │   │ import  │                        ▼
└──────────┘   └─────────┘                  ┌────────────┐
                                             │ G-code     │
                                             │ Writer     │
                                             │ write_     │
                                             │ gcode()    │
                                             └─────┬──────┘
                                                   ▼
                                            ┌────────────┐
                                            │  output     │
                                            │  .gcode     │
                                            └────────────┘
```

## Key abstractions

### ExtrudedProfile (ifc_reader.py)
A 2D polygon + extrusion height — the basic printable element.
- `points_2d`: outer boundary in XY (clockwise, closed)
- `base_elevation`: Z of bottom face
- `height`: extrusion height

### SliceLayer (slicer.py)
A single horizontal cross-section at a given Z.
- `outer_contour`: N×2 numpy array of boundary points
- `z`: absolute Z coordinate
- `layer_index`: ordinal within the parent profile

### Move types (toolpath.py)
- `ExtrusionSegment`: printing move with E value
- `TravelMove`: repositioning move (no extrusion)

### PrintSettings (gcode_writer.py)
Printer-specific parameters separate from geometry logic.

## Extension points

| Point | What to change |
|-------|----------------|
| New input format | Add a reader that produces `ExtrudedProfile` list |
| Custom infill | Modify `_generate_infill()` in toolpath.py |
| Different G-code dialect | Subclass or replace `write_gcode` |
| Multiple nozzles | Add `nozzle_index` to `ExtrusionSegment` |
| Support material | Add a `support_contour` field to `SliceLayer` |
