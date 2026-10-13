# Source and verification

Each variant includes a standalone parametric CadQuery model. Dimensions are stored in `data/parameters.json`; dimension definitions are in `data/dimension_registry.json`. The source requires no other project.

## Environment

Python 3.12 was used. Dependency versions are pinned in each variant's `source/requirements.txt`.

From the repository root:

`python3 -m venv .venv`

`.venv/bin/python -m pip install -r variants/v04-low/source/requirements.txt`

## Rebuilding

The commands below update the selected variant's files. Supplied STEP and STL files are byte-identical to the printed revisions. Geometry-only 3MF language metadata was changed to English without changing mesh coordinates, triangles, or instance transforms. Ready-to-print packages are unchanged.

`.venv/bin/python variants/v03-high/source/build_model.py`

`.venv/bin/python variants/v03-high/source/make_drawings.py`

`.venv/bin/python variants/v04-low/source/build_model.py`

`.venv/bin/python variants/v04-low/source/make_drawings.py`

Drawings use hidden-line removal on the current STEP model. PNG and SVG files contain the same three views and dimension IDs. All documentation, source comments, labels, and metadata use English.

Ready-to-print files in `printing/` retain the printed geometry. Changing CAD parameters requires slicing a new job; the existing G-code is not updated automatically.

## Package verification

`.venv/bin/python tools/verify_package.py`

Checks cover BREP validity, one connected solid, a watertight STL mesh, dimensions, actual inner retaining-wall faces, agreement between the parametric source and the supplied STEP, millimeter units, and 1:1 scale in 3MF files. For each print package, every vertex and triangle of both instances, their layout, the G-code MD5 checksum, and the absence of M624 are verified. Text files and embedded metadata are also checked for non-English Cyrillic text.

Results are saved in `VALIDATION.json`. To verify files against this release's checksums:

`sha256sum -c SHA256SUMS.txt`

Rebuilding models, drawings, or reports changes the release checksums. Verification covers digital geometry; print and fit results are documented separately in README and `printing/print_settings.json`.
