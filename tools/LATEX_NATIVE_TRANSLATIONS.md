# Native LaTeX translations

The PLANCKS/Ortvay renderer keeps all original source font programs, figures,
mathematical glyphs, page geometry and text advances. Korean uses the corresponding
static Noto CJK serif/sans and regular/bold master in `tools/ko/fonts/`, at the
original source point size, baseline, color and italic angle. No text is shrunk.

Selected source codes remain in invisible `3 Tr` runs with empty `/ActualText`,
then the original rendering mode is restored. This preserves each renderer's
actual Type1 glyph advance: using nominal `/Widths` numbers instead caused
rounding differences in the rejected prototype. Empty ActualText prevents hidden
English from appearing in extracted text. Other source text remains native.
The encoding profile requires an embedded Type1 font, explicit Widths and an
explicit single-byte ToUnicode map, and matches every code against source glyph
traces. Ligatures may be hidden only as complete verified logical clusters.

Install PyMuPDF, pikepdf, fontTools, NumPy and Pillow. Place unchanged official
originals at `tmp/source-audit/PLANCKS_2026_T_EN.pdf` and
`tmp/source-audit/Ortvay_2026_T_EN.pdf`. Their official source URLs are recorded
in the competition manifests in `tools/theory/`. The approved plans retain their
original absolute authoring paths; when rebuilding elsewhere, change only each
plan's `source` path to the downloaded original. Keep `source_sha256` unchanged.

```text
python tools/latex_native_proof.py PAGE_PLAN.json PAGE_PROOF.pdf --check
python tools/latex_native_proof.py PAGE_PLAN.json PAGE_PROOF.pdf
python tools/test_pdf_latex_text_ops.py
python tools/latex_native_assemble.py plancks PLANCKS 18 --work-root WORK_DIRECTORY
```

Plans use one-based `page`, inclusive rawdict span indices in
`at: [block,line,first_span,last_span]`, an exact `source` substring, and Korean
`text`. Optional `char_start`/`char_end` slice the flattened span characters.
`skip: true` retains a source slot. `extend_to` explicitly reviews extra horizontal
room. An overflow fails. Subset fonts are cached only under ignored
`tmp/latex-native/`.

Optional `raster_labels` paint exact old-language ink rectangles and add Korean
without modifying the embedded image or soft-mask streams. Raster fonts/sizes
are explicitly recorded as source-only estimates. The audit checks the overlay
against separately recorded allowed language bounds, and detects Korean intrusion
on retained native ink. Original images, equations and diagram geometry remain
in their original source objects.

The integration tests use the unchanged official sources. Alternate local paths
can be supplied through `LATEX_NATIVE_PLANCKS_SOURCE` and
`LATEX_NATIVE_ORTVAY_SOURCE`. They verify every unselected source glyph and native
font/image/drawing object across the 18-page PLANCKS and 10-page Ortvay papers,
and reject partial ligatures, malformed font maps and stale source selections.

Assembly reads `proofs/COMPETITION/2026/pageNN.pdf` and current proof QA records,
requires hash-matched `visual-review*.json` coverage, and writes the final PDF to
`staged/COMPETITION/`. It compares the actual joined pages with all reviewed
proofs and independently checks original font programs and encoded image bytes.
Every proof page must be visually inspected before its review hash is recorded.
