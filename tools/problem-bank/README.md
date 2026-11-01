# Private problem-bank import preparation

These standalone tools register source revisions, question boundaries, private image references and separately reviewed language versions. They have no production Worker routes, no student interface, no Google Drive credentials, and no OCR, translation or other paid API calls. Importing a manifest registers an inventory; it does **not** mean its pages have been extracted or translated.

Use a **separate private D1 database**. Do not use the community database, exam answer tables, or an answer-photo bucket subject to retention cleanup. Keep original PDFs, manifests, question JSON and generated SQL outside this public Git checkout. The CLI refuses SQL output within this checkout, including a resolved directory symlink. Never commit the generated SQL or real book content.

## Input contract

The manifest is JSON with `version: 1` and a `sources` array. Each source needs:

| Field | Meaning |
| --- | --- |
| `drive_id`, `revision` | Verified stable Drive file ID and its exact revision identifier. Modified-time/hash identifiers may be used when the provider has no revision ID; do not invent an unknown revision. |
| `title`, `mime_type` | Title and `application/pdf`. |
| `sha256`, `page_count` | SHA-256 of the complete downloaded PDF and actual positive page count. |
| `subjects`, `level` | Values from the exported `SUBJECTS` and `LEVELS` arrays in `store.mjs`. |
| `source_language` | Lower-case two-letter language code for the actual original. |
| `private_object_key`, `local_path` | Optional private object key and/or private local source path. A key is an opaque bucket key, never a public or authenticated URL. |
| `expected_question_count` | Optional independently checked positive total. |
| `extraction_complete` | Defaults to `false`. `true` requires an expected total, and the database must contain exactly that many question locators. |

Source IDs are deterministic SHA-256 identifiers of Drive ID plus revision. The same revision cannot silently change its PDF hash, page count or original language. Renaming a book does not create another source. Equal file hashes across different Drive IDs remain separate provenance records; a hash index allows duplicate detection without losing attribution.

The optional questions file has `version: 1` and a `questions` array. Each question needs:

- `source: {drive_id, revision}` referencing a manifest source.
- `locator`: stable source-relative locator, such as `chapter-1/problem-2`; `original_number` preserves the printed numbering. `chapter` is optional.
- `kind`: `problem`, `exercise` or `example`. Do not mix an answer/solution into a statement.
- `subjects` and `level`, or inherit these from the source.
- `spans: [{page, bbox: [x0,y0,x1,y1]}, ...]`: **one-based PDF page numbers**, top-left origin, normalized coordinates in `[0,1]`. Multiple page regions retain continued statements, shared conditions and subquestions together. The tool validates page bounds and nonempty rectangles.
- `review_status`: `pending` by default, `verified` only after checking the boundaries and classification, or `rejected`.
- `versions`: zero or more `{language, role, text, review_status}` objects. A source-language version must have `role: "original"`; another language has `role: "translation"`. Text preserves LaTeX verbatim. Only one supplied version per language is accepted in one import.
- `assets`: optional per-question figures/crops described below.

A missing Korean translation remains missing. An unverified translation stays `pending`; copying English into a Korean field is not a completed translation. Current text updates retain their previous text-hash versions, and changed pending text cannot inherit a previous version's verified status.

Question IDs are deterministic by source revision plus locator. Replaying the same input does not duplicate questions, language versions, figures or job entries. The tool does not infer unobserved numbering, solve questions, or mark translations verified automatically.

## Private figures and small image payloads

An asset uses `{asset_id, role, private_object_key, mime_type, sha256, spans}`. `asset_id` is a stable identifier within its question; `role` is `figure` or `question_crop`. Allowed MIME types are PNG, JPEG, WebP, SVG and PDF. Every asset keeps its source page regions, including figures continued on another page.

When no private object bucket is available, a small crop may supply `inline_base64` and optional `byte_length` instead of `private_object_key`. The complete payload is limited to 4 MiB, checked against the declared SHA-256 and split into 32 KiB binary chunks in `bank_asset_chunks`. The schema permits a future prepared-statement chunk size of up to 256 KiB; SQL file exports use smaller chunks. `bank_asset_payloads` records total size, whole-asset hash and chunk count. `readInlineAsset()` verifies chunk order, each size/hash and the assembled image hash before returning bytes. A `d1-inline/...` object key identifies this storage mode; it is not a URL or an assertion that a bucket exists.

This optional crop mechanism is not a bulk original-PDF uploader. Source-PDF byte storage and its integrity/readback are separate from source inventory metadata.

Question-level `source_language` can override a compilation's dominant language. For example, an Estonian booklet included in an otherwise English collection keeps its Estonian original, plus separate English and Korean translations. `context` preserves source authors, topic-index provenance, transcription notes and unresolved source flags. An unresolved source flag prevents the readiness view from treating that question as complete, even if language versions were mistakenly marked verified.

## Source extraction and local OCR

The edition-specific `extract-pns.py`, `extract-puzzling.py` and other extractor adapters keep original page regions and WebP crops. They distinguish statement sections from worked solutions and retain existing subparts and source-provided statement hints. Their output is a draft, not a proofread edition. Private transcription overrides must be supplied as data with the source-PDF SHA-256; book text must never be embedded in public tool source.

`extract-more-puzzling.py` preserves the supplied edition's 200 numbered statements and attaches its twelve footnotes to the corresponding question. `extract-blundell.py` follows each chapter's two-column exercise sections and also records the two unnumbered appendix exercises using stable page locators. It flags missing source context and the edition's damaged embedded math-font programs. These adapters require their checked PDF hash; another edition needs its own boundary review.

`extract-pns-native.py` uses a private edition profile for the printed numbering and reviewed OCR corrections. `extract-schroeder.py` follows the actual standalone problem-label font and preserves externally referenced figures, footnotes and private context overrides. A caption near a statement is not automatically a supplied figure: requested answer sketches must stay outside the statement.

A PNS profile can supply hash-bound local Tesseract checkpoints for pages whose native text layer is empty. Word coordinates use each checkpoint's actual render size; an existing native layer cannot be overwritten. Printed numbering errors retain the observed `original_number`, while the sequence position remains a separate locator. Duplicate scan labels require an explicit, image-checked private exclusion with matching coordinates and a review note. These exceptions never silently repair the source or mark it verified.

For two-column scans, `detect-column-labels.py` reads narrow numeric margins with local Tesseract and saves source-bound candidate coordinates. Candidate sequences require separate review: clipped digits, numbered concept lists and text fragments can resemble problem labels. Page-specific strip bounds belong in the private profile. `extract-column-questions.py` consumes the reviewed header inventory, follows continuations through columns and pages, and keeps original-language OCR text separate from canonical source images. Reviewed auxiliary source diagrams can be supplied through private `question_context_regions`; the main question regions remain separately identified for matching. Crop and bilingual review still remain pending after extraction.

`prepare-extracted.py --private-root PRIVATE` merges schema-aligned extractor output and statement-segment adapters with numbered translation batches. It verifies crop hashes before generating private import JSON, ignores temporary draft files, preserves non-English originals and leaves every version pending independent review. Use `--text-only` only after the corresponding source crops have already been imported.

Directly authored bilingual batches use numbered JSON filenames and an `items` or `questions` array with `original_number`, `text_en`, `text_ko`, `source_image_checked`, `review_notes` and `unresolved_source`. Include `locator` whenever printed numbers repeat in a compilation or for unnumbered exercises. Authors must compare equations, units and figures with the source image; parsing the PDF text alone does not complete that check. `audit-translation-math.mjs PRIVATE_TRANSLATIONS_DIR` checks LaTeX syntax with the repository's KaTeX without contacting a service. Syntax success does not establish scientific correctness.

For image-only source books, `ocr_scanned.py` uses local Tesseract rather than a paid OCR service:

```powershell
python -m pip install --only-binary=:all: tesserocr pymupdf pillow
python tools/problem-bank/ocr_scanned.py --pdf PRIVATE/source.pdf --output-dir PRIVATE/ocr --tessdata-dir C:/local-tessdata
```

Supply English `eng.traineddata` from [Tesseract's official fast-model repository](https://github.com/tesseract-ocr/tessdata_fast). On Windows, some Tesseract builds require an ASCII trained-data directory. Pages are rendered in memory; only atomic text/coordinate checkpoints are saved. Restarting checks the source hash, scale and training hash before skipping a completed page. OCR equations remain unverified until compared with the original image. The OCR script does not download models or contact a provider.

For scans with oversized PDF page boxes, `--max-render-side 3000` caps the longest rendered side in pixels. Each page records its actual render dimensions and scale, and resuming with a different cap is rejected. Use those per-page coordinates rather than assuming the requested DPI. The default zero cap preserves existing OCR settings; another language such as `--language kor` requires its own local trained-data file.

`run-subscription-batches.py` is an optional bounded draft translator using an existing ChatGPT-authenticated Codex CLI. It previews by default; `--run` explicitly consumes that subscription's usage allowance. It refuses API-key environment variables, does not select a different model, and stops on errors without automatic retry loops. It is not an unattended, already-running translation service merely because the script is present.

## Prepare and apply

```powershell
node tools/problem-bank/store.mjs --manifest C:/private-bank/manifest.json --questions C:/private-bank/questions.json --out C:/private-bank/import.sql
```

Omit `--questions` to register only the source inventory. The CLI prints counts and the private output path, never question text; `server_imported` is explicitly `false`. SQL generation is a local preparation step.

Apply the generated file only after verifying the target database is the isolated private question bank:

```powershell
wrangler d1 execute haslalab-problem-bank --remote --file C:/private-bank/import.sql
```

The SQL includes `schema.sql`, fixed identifiers and safely encoded literals; external values cannot become SQL syntax. It omits `BEGIN`/`COMMIT` because [D1 file import supplies its own transaction](https://developers.cloudflare.com/d1/best-practices/import-export-data/). For a Worker-side binding, initialize `schema.sql` separately and call `applyD1Import()`, which uses parameterized prepared statements in one atomic D1 batch. Do not split one logical import into independent nontransactional statements.

After applying an import, `verify-remote-assets.py --database PRIVATE_DB --config PRIVATE_CONFIG --out PRIVATE_REPORT` reads back a bounded sample of the largest inline images from each source using an already authenticated Wrangler CLI. It checks chunk order, chunk hashes, assembled hashes, byte counts, image MIME types and image decoding. The report records that sampling scope; it does not mark statements or translations verified.

For local verification, `applyImport(DatabaseSync, normalized)` applies parameterized statements under an explicit SQLite transaction and rolls back all imported changes on failure. Conflicting source revisions and false complete-extraction totals fail rather than accepting a partial import. Schema creation itself is additive and independent of a data import transaction.

Set a question's `assets_complete: true` only for a complete, hash-checked crop snapshot. That explicit flag removes obsolete crops and payload chunks belonging to that question in the same transaction; unrelated questions are unaffected. Omit the flag for text-only updates so existing source images remain intact. A saved translation draft completes the translation stage; independent review remains a separate pending job and the bilingual readiness view stays false until review succeeds.

## Progress and remaining work

`bank_source_readiness` exposes `stored_questions`, `bilingual_verified_questions` and `ready`. `ready = 1` requires all of:

1. Extraction is explicitly declared complete.
2. Stored question count equals the independently checked total.
3. Every question has verified boundaries/classification.
4. Every question has both a current verified Korean and current verified English version.

The `bank_jobs` table records extraction, translation and review checkpoints, with lease, retry and usage/cost fields for a future runner. Registering jobs does not run them. No background processing or provider credentials are configured by these tools.

Shortest-first order is actual page count, then stable source ID. It is a queue priority, not proof that a shorter book contains fewer questions. Confirm original numbering and totals while reviewing each source.

```powershell
node --test tools/problem-bank/test-store.mjs
```

Tests cover stable identities, replay, missing translations, bilingual readiness, text-version review isolation, page/box validation, rollback, hostile SQL text, private output boundaries and crop integrity.

`python -m unittest discover -s tools/problem-bank -p 'test_*.py'` also checks adapters, repeated-number translation identity, local OCR geometry, printed-number preservation, reviewed duplicate exclusions and the optional runner's mocked failure handling. These tests contain synthetic content and do not run OCR, models or remote imports.
