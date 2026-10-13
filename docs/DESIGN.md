# Dimensions and design

The external case thickness between the two walls entering the stand was measured as **130.5 mm**. This includes both case walls and is identified as M00.01. Axes: X is across the case along the stand's long axis, Y is along the case, and Z is upward from the bed.

Both variants have a 200 × 50 mm base, 6 mm thick, with R25 semicircular ends. Each stand is one solid with two retaining walls and three external gussets per side. Front and rear gussets are 4 mm thick; middle gussets are 6 mm thick. One case uses two identical stands.

## v0.3

Overall height is 100 mm, with 6 mm retaining walls. Inner faces at X=34.45 and X=165.55 mm create a 131.1 mm slot. For a 130.5 mm case, nominal clearance is 0.3 mm per side. This variant was printed successfully; the next revision reduced slot width and height.

## v0.4

Inner faces at X=34.75 and X=165.25 mm create a slot exactly 130.5 mm wide. Outer faces remain at X=28.45 and X=171.55 mm, giving a wall thickness of 6.3 mm.

Original gusset profiles are preserved. The model is trimmed by a horizontal plane through the junction of the middle gusset and the outer retaining-wall face:

`H = 6 + (100 − 6) × (28.45 − 10) / (34.45 − 10) = 76.9325153374 mm`.

Dimension M01.05 is rounded to 76.93 mm on the drawing; CAD and parameters retain full precision. v0.4 was printed successfully; fit feedback for this revision is still pending.

## Main dimension IDs

| ID | Definition |
|---|---|
| M00.01 | External case thickness |
| M01.01 | Overall base width |
| M01.02 | Depth of one stand |
| M01.03 | Base thickness |
| M01.04 | Semicircular end radius |
| M01.05 | Overall height above the bed |
| M02.01 / M03.01 | Left / right retaining-wall thickness |
| M02-03.01 | Clear slot between retaining walls |
| M00-02.01 / M00-03.01 | Nominal left / right case clearance |

IDs remain consistent between variants. Changing a dimension's value preserves its ID. The case measurement is kept separate from design clearance. No scaling, shrinkage, or XY compensation was applied.

## Design background

The general structural reference was the [SGI Indigo2 stand](https://www.printables.com/model/1427425-sgi-indigo-2-stand): a broad base, retaining walls, and external gussets. DS10 uses a separate parametric BREP model; the original SGI mesh is not included in this package.

The DS10 fit dimension is based on the direct 130.5 mm measurement. Manufacturer reference dimensions were considered separately and did not replace this measurement.
