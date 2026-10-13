# Printing

Use **two identical stands** of the selected variant for one case. Each ready-to-print job already contains both stands; do not add another pair.

## Ready-to-print QIDI Q2 jobs

- [v0.3 tall pair: package](../variants/v03-high/printing/ds10_v03_two_stands_QIDI_Q2_PLA.gcode.3mf), [G-code](../variants/v03-high/printing/ds10_v03_two_stands_QIDI_Q2_PLA.gcode).
- [v0.4 short pair: package](../variants/v04-low/printing/ds10_v04_two_stands_QIDI_Q2_PLA.gcode.3mf), [G-code](../variants/v04-low/printing/ds10_v04_two_stands_QIDI_Q2_PLA.gcode).

These are the unchanged files used for the completed prints. They target the QIDI Q2 and its stock start and end commands. They contain no network address or automatic upload action.

| Setting | Value |
|---|---|
| Printer / bed | QIDI Q2 / 270 × 270 mm |
| Nozzle / material | 0.4 mm / 1.75 mm PLA |
| Normal / first layer | 0.28 mm / 0.2 mm |
| Wall loops | 4 |
| Infill | 25% gyroid |
| Profile maximum volumetric flow | 16 mm³/s |
| Nozzle / bed temperature | 230 / 55 °C |
| Chamber heating | 0 °C |
| Supports | Automatic, as configured in the saved profile |
| Adhesion | Outer brim, 2 mm |
| Orientation | Flat base down, Z=0 |
| Layout | Two stands parallel to X, 5 mm gap along Y, no rotation |
| Scale / compensation | 1:1, no shrinkage or XY compensation |

Each `printing/profiles/` directory contains machine, process, and PLA profiles, plus the effective slicing settings. PLA profile temperatures match the actual G-code for both variants, including v0.3.

On the test printer, T0 was mapped to spool 1B. The package uses T0; select the physical spool mapping on the printer before starting.

## Slicing for your printer

Open a single-stand STL or a geometry-only 3MF of the selected variant in your slicer. Keep millimeter units and 100% scale. For a pair, open `ds10_two_stands_v03.3mf` or `ds10_two_stands_v04.3mf`: each contains two instances of the same mesh in the prepared layout. Place the bases on the bed and slice for your printer and material.

The top G-code layers are at Z=99.88 mm for v0.3 and Z=76.92 mm for v0.4. These are the layer positions produced by slicing; the source CAD heights are 100 mm and 76.932515 mm respectively. Model scale is unchanged.

## Time and material for a pair

| Variant | Slicer estimate | Estimated PLA | Recorded total duration |
|---|---:|---:|---:|
| v0.3 | 4 h 34 min 56 s | 193.82 g | 5 h 5 min 21 s |
| v0.4 | 4 h 9 min 20 s | 173.54 g | 4 h 36 min 33 s |

Recorded durations come from completed printer jobs and include printer preparation. These figures apply to the supplied files and profile; other machines and materials depend on their settings.

Unsupported M624 object-label commands were removed from the prepared jobs: 714 in v0.3 and 550 in v0.4. G-code checksums were updated. Geometry and every motion and extrusion line were preserved from the sliced jobs. Both packages were verified again for this release.
