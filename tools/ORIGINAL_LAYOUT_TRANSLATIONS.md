# Original-layout translations

`original_style_publication.json` lists the reviewed files served by the PDF
release. Each entry points to the audit of the final joined PDF, rather than
only the temporary page proofs. The PDFs are stored in the `pdf-izho` release.

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
