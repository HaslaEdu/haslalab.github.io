# 2023 KPhE figure tracing

Verified 2026-10-30.

The build input is the supplied 2023 PDF crop identified by `source`, `page`, `rect` and `sourceSha256` in `kphe_figures/index.json`. Place these source PDFs in `tmp/kphe_archive/originals/`. The renderer consumes the checked SVGZ assets and needs only gzip decompression; Potrace is a build dependency.

`kphe_figures.py` samples each crop at 3 pixels per source point, detects neutral paper from the outside margin, and retains the existing separate RGB-color and grayscale ink masks. Potrace fits each mask independently; it does not cluster colors, change text or infer new geometry. Transparent holes and original object shading are retained.

Larger contours use **Potrace 1.16**, `turdsize=0`, `alphamax=1`, curve optimization enabled, `opttolerance=0.2`, coordinate unit `100`. Tiny independent ink islands with bounding-box area at most 80 source-sampling pixels retain the preceding native contour geometry, preventing antialiasing from making a dot or punctuation mark disappear. Revision 1 assets already passed all original comparisons without this protection; revision 2 adds the protection. Each row records its tracing revision and method.

Candidates must pass the unchanged raw-source checks: ink recall within 1.5 pixels >= 0.97, precision within 2 pixels >= 0.97, local-contrast edge recall within 2 pixels >= 0.97, ink IoU >= 0.70, and a transparent fraction > 0.03. Every isolated source-ink component of up to 80 pixels must also retain nearby vector ink. An unsuccessful candidate retains its preceding verified native contour asset byte-for-byte; `tracing_method`, `potrace_candidate` and `fallback_reason` distinguish these rows. The final visual review compares all source/vector pairs for small dots, thin lines, corners, labels and shades.

Final review accepted 56 curve assets and retained 23 native contour assets. Of the native fallbacks, six passed the global numeric comparisons but were rejected visually: 2023-1 middle Q7/Q11/Q12 and 2023-2 middle Q5/Q16/Q17. Their colored boundaries or label contrast degraded. `VISUAL_NATIVE_FALLBACKS` in the generator preserves these decisions on rebuild, and each affected index row records the specific reason. Global unsigned-edge agreement alone cannot validate label contrast polarity.

Potrace source and documentation: [project](https://potrace.sourceforge.net/), [1.16 options](https://potrace.sourceforge.net/potrace.1.html). Verified Windows build:

- [Official Windows 64-bit archive](https://potrace.sourceforge.net/download/1.16/potrace-1.16.win64.zip), 186345 bytes
- Archive SHA-256: `63699f9885b5ed053977fd94452a7bdbb77ee62b77bf28a3f17b2f14b9b9c65d`
- `potrace.exe` SHA-256: `f1bcde040ae6576dc9c5868be7a72064957c5aea08e1dece240428319fc672a4`
- Runtime path used: `tmp/potrace-prototype/potrace-1.16.win64/potrace.exe`
- The executable and extracted distribution remain in ignored `tmp/`; neither is committed.

Rebuild from the repository root with the original PDFs available:

```powershell
$env:KPHE_POTRACE_BIN = (Resolve-Path 'tmp/potrace-prototype/potrace-1.16.win64/potrace.exe').Path
python -X utf8 tools/kphe_figures.py --jobs=6
```

The executable can instead be on `PATH`, or supplied through `--potrace=ABSOLUTE_PATH`. Its version and SHA are checked and recorded. `--engine=native` builds the retained native contour implementation. `--only=CROP_KEY` selects a crop; `--resume` reuses per-crop checked journals with matching asset hashes after interruption. Changing tracing code or parameters requires a new tracing revision or clearing its old journals under `tmp/kphe_figure_qa/`.

Verified environment: Python 3.14.6, NumPy 2.5.2, OpenCV 5.0.0, PyMuPDF 1.28.2, Pillow 12.2.0. The generator produces deterministic gzip (`level=9`, `mtime=0`). The index records the compressed asset SHA/bytes and the decompressed SVG SHA/bytes separately. Rendering is unchanged by this lossless compression.
