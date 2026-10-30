# 2023 intermediate-course native figures

37 manually authored native PDF assets use the existing crop keys. The PDFs
contain PDF paths and embedded Gulim / KPS HyhwpEQ font text, with no raster
images, pixel contour extraction, automatic tracing or scan backgrounds.

Rebuild the visually reviewed drawing specification:

```powershell
python tools/kphe_redraw_ab.py --reviewed
```

`--math-base-size` controls the authoring math size. Label sizes are explicit
and relative to the source drawing. There is no global minimum font size or
automatic coordinate clamping. `width_pt` and `height_pt` in `manifest.json`
are the actual final print dimensions; use them instead of forcing every
figure to232pt or restoring the old scan crop aspect ratio.

All36 ordinary figures are at most155pt high. The single narrow spring is
60x80pt, the A/B stacked blocks are170x48pt, and the circuit/meter panels are
232x116pt. T2b5 uses the original two-by-two panel grid; T2b11 uses the original
side-by-side circuit and meter. The two T2b20 native tables retain their9pt
cell text and their source order in a232x189.47pt table exception. Their cells
and answer placeholders are also supplied in `T2b20-table.json`.

Original crops, source/native comparisons at equal point scale, individual
Poppler renders and one-to-one point-size A4 proof PDFs are review files under
`tmp/kphe_redraw_ab_qa/`, outside the distributable directory. `audit.json`
records all37 final PDF hashes, sizes, native text and line checks. The actual
67 math form rectangles and all plaintext runs fit inside their canvases.
Production question and solution page assembly is checked separately.
