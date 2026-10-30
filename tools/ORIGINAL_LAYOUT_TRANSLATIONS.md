# Original-layout translations

`original_style_publication.json` lists the reviewed files served by the PDF
release. Each entry points to the audit of the final joined PDF, rather than
only the temporary page proofs. The PDFs are stored in the `pdf-izho` and
`pdf-cpho` releases.

The replacement engine removes selected prose text-show operands while keeping
all original text advances and the other PDF tokens intact. Original font
programs, mathematical glyphs, figures, paths, point sizes, baselines and page
order remain in the source page. New prose uses the corresponding serif/sans
family and regular/bold master. Korean is absent from the original Latin fonts,
so Korean glyphs use the pinned static Noto CJK fonts; original Latin resources
are reused where possible. Original italic angles and rendering strokes are
handled explicitly. No automatic shrinking, paragraph merging, mathematical
image conversion, extra edition titles or translator footnotes are used.

For the first restored edition, place the original at
`tmp/source-audit/IZhO_2015_T_EN.pdf`, downloaded from
<https://izho.kz/wp-content/uploads/2018/01/IZhO-2015-Theory_eng.pdf>.
Its SHA-256 is
`f44e9ad512d9dee30b76feffa626be6448630f59627ba462fe58030937dfc84c`.

With PyMuPDF, pikepdf, fontTools, NumPy, OpenCV and Pillow installed, run:

```text
python tools/izho_early_fixed_rebuild.py --year 2015 --kind T
```

The reviewed page plans are in `tools/ko/izho/2015/T/original_style/`.
New font programs are subset with retained CIDs/GIDs; source fonts are never
subset. Complete pages are joined with pikepdf, followed by another audit of
every page in the actual output. Native glyph outlines and the image outside
the translated prose must have zero changed pixels at 4× resolution. A separate
Hangul-outline audit checks for hidden or missing translated text.

`tests/test-original-layout-translations.cjs` checks the publication manifest,
approved hashes, final-file audit coverage, font provenance and release sizes.
It also checks that archive links carry the approved file revision, so an older
PDF in the browser cache is not reused after an in-place replacement. Refresh
the inline revision map with `python tools/update_original_layout_versions.py`.

The newer-year engine is rebuilt with
`python tools/izho_original_style_rebuild.py 2026 T`. It automatically retrieves
the source archive asset and checks its recorded SHA-256. Its audits additionally
compare a prose-suppressed control with the original native ink, avoiding false
positives from neighbouring English glyph overhangs or unused font-metric boxes.
The reviewed final page must still render identically to its individual proof.

The 2025 edition uses `python tools/izho_legacy_style_rebuild.py 2025 T`,
which reuses the original legacy font aliases, encodings and actual PDF widths.
Its final report contains every original-page preservation audit and a zero-pixel
comparison between each joined page and its reviewed proof. The separate
Hangul-outline report checks all seven final pages for missing translated ink.

`python tools/test_pdf_original_text_ops.py` covers CID advances, filled/stroked
text, untouched native Forms and CMap decoding. Native-only Unicode clusters
are consumed only when the original font/GID, zero-width continuation and
position checks agree; those clusters cannot be selected as translated prose.
The font regression tests are
`python tests/test_pdf_original_style_fonts.py`; unsupported Unicode whitespace
must fail validation rather than becoming a visible missing-glyph box.

New Latin glyphs reused from an original font must also have a positive advance
in that PDF's actual `/Widths` or `/W` array. Having the glyph in the embedded
font program alone is insufficient. The 2026 audit records this separately in
`native-ascii-audit.json`.

The 2021–2022 editions use `python tools/izho_2021_2022_style_ready.py YEAR T`
(or `TS`). Finalization with `--ready` verifies the external visual-review
record against every page-proof hash and the joined-page pixel comparison.
Publication checks that record independently. Native Identity CIDs missing
from ToUnicode remain read-only and require a matching embedded font and GID.
Compressed and uncompressed image/soft-mask streams retain their original
bytes and filters; saving does not recompress original streams.

Only explicitly selected actual prose spaces can use the opt-in whitespace
journal. The audit validates their character, font, size, original position and
prose frame, and rejects fabricated or protected math/Form spaces. Run
`python tools/test_pdf_original_style_prose_whitespace.py` for those regressions.
The core also supports explicit one-byte ToUnicode/Widths maps in embedded
Symbolic TrueType fonts and read-only original quote text-show operators.

For CPhO 2007, download the unchanged Chinese original
`CPhO_2007_T_ZH.pdf` from the `pdf-cpho` release into `tmp/source-audit/`.
Its SHA-256 is
`2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9`.
Run `python tools/cpho_2007_original_build.py extract`, then
`python tools/cpho_2007_original_build.py build --pages 1 2 3 4`.
Only the four problem pages are reviewed; the solution-page drafts are excluded
from publication and cannot be composed without an explicit draft option.
The English primary filename is `CPhO_2007_T_EN.pdf`; the old BAUPC-named URL
is a byte-identical compatibility alias. Both languages retain the original
seven figures, mathematical glyphs and source font programs. The final files
pass both MuPDF and Poppler checks outside translated prose, and each joined
page must render identically to its reviewed proof.

CPhO 2006 uses the corresponding `cpho_2006_original_build.py` commands and all
four reviewed pages. Its source SHA-256 is
`4ca77258299918a44f26320027466b81cc70c97e7e467ee190282be0f4516042`.
The original page-2 image covers part of the footer. The translated footer
retains that source stacking order; the visibility audit records those same
occluded components separately and requires zero unexpected hidden components.
Only the raster Chinese caption character is overlaid; the original numeric
caption glyphs and all diagram geometry remain unchanged. The inferred raster
font size and baseline are documented in `raster-caption-provenance.json`.

CPhO 2022 uses `cpho_2022_original_build.py extract` and
`cpho_2022_original_build.py build --pages 1 2 3 4`. Its Chinese source SHA-256 is
`89d1718db8a92afebb741b755beadd4476ac11654b50a5b79d4eaa2d13b91e04`.
`cpho_2022_original_inventory.json` records both reviewed editions and all
authoring/QA files. The original six diagrams and mathematical subscripts are
retained; only 15 diagram-language labels are overlaid. Raster-label font
measurements are inferred and recorded separately from native PDF typography.
Body baselines are checked to 0.0001pt; rotated raster labels use a 0.005pt
rounding limit. MuPDF and Poppler verify native ink and non-language geometry.
The English primary is `CPhO_2022_T_EN.pdf`, with the old BAUPC URL retained as
a byte-identical alias. Rebuild the site catalogue only after Release uploads
finish, since its version includes the final PDF manifest.

The 2023 solution source contains 62 pages. The reviewed Korean edition selects
English physical pages 25–43, keeping their original printed page numbers. Its
explicit control-stem mapping audits those source-page controls against all
19 final pages; the shared default mapping is unchanged.
