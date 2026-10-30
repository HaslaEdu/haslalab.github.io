# 2023 intermediate-course native figures

37 native PDF assets replace the old scan contours by the existing crop keys.
Each asset contains authored PDF lines, curves, geometric objects and native
Gulim / KPS HyhwpEQ font text. There are no raster image XObjects, image
embeddings, pixel contour extraction or automatic tracing operations.

Rebuild the reviewed drawing specification:

```powershell
python tools/kphe_redraw_ab.py --reviewed
```

`--math-base-size` controls the authoring math size. The final plaintext and
ordinary math label floor is 8.5 pt (normal mathematical subscripts retain
their proper smaller size). Assets have their own final point dimensions;
they must be placed using `width_pt` / `height_pt` from `manifest.json` rather
than the old scan crop ratio.

Four small plots in T2b 5, the circuit/meter panels in T2b 11, and the two
tables in T2b 20 are stacked in their original reading order to keep labels
legible. T2b 20 is additionally supplied as structured rows and columns in
`T2b20-table.json`; its cell text is 9 pt and its four answer placeholders are
unchanged.

The original crops and final Poppler comparison sheets are temporary review
files under `tmp/kphe_redraw_ab_qa/`, outside the distributable asset directory.
`audit.json` records the source/native checks. All source PDF hashes and final
native PDF hashes are recorded per figure in `manifest.json`.
