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

A PDF obtained from an official course website can instead provide `origin: {kind: "url", url, attribution, license_identifier, license_url, terms_url?}` and omit `drive_id`. Its `revision` must be `sha256:` followed by the actual PDF hash. URLs use HTTPS without credentials, query strings or custom ports; page fragments are removed from their identity. Questions refer to `{origin: {kind: "url", url}, revision}`. This registers provenance from an already downloaded and checked PDF; the import tools do not fetch it or infer permission from public availability.

For a PDF inside an archive, keep the real container URL and add `origin.archive_member: {container_sha256, member_path, member_sha256}`. The member hash must equal the source PDF hash; its revision identifies those member bytes. The member path is a relative archive path without traversal. Separate member PDFs retain distinct content revisions under the same container URL, and the stored origin preserves the container hash and member path for later verification. Verify both the archive and extracted member before importing; do not invent a direct PDF URL.

URL source IDs have a separate namespace and preserve every existing Drive source/question ID. Normalized URL sources have `drive_id: null` and explicit origin metadata. For compatibility with existing databases, the legacy SQL `book_sources.drive_id` column stores the **actual URL** as its identity key; no fictitious Drive ID is created. `bank_source_origins` stores typed attribution and license metadata, and copy fingerprints verify it. Consumers must use this origin URL instead of constructing a Drive link. License conditions and third-party exceptions still need source review before any publication; storing a license identifier is not evidence that every component has reuse permission.

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

For column scans, `detect-column-labels.py` reads narrow numeric margins with local Tesseract and saves source-bound candidate coordinates. Candidate sequences require separate review: clipped digits, numbered concept lists and text fragments can resemble problem labels. Page-specific strip bounds belong in the private profile. `extract-column-questions.py` consumes the reviewed header inventory, follows continuations through one or more columns and pages, and keeps original-language OCR text separate from canonical source images. A profile may instead select `source_text_method: native` for an existing PDF text layer. Numeric chapters and appendix letters have distinct locators; headers may preserve a printed chapter-qualified `original_number` independently of their sequence position. A section can retain its source unit system and provenance. An explicit `last_body_bottom` or image-checked `question_end_overrides` can shorten an interval to exclude unrelated notes or the next section heading. Reviewed auxiliary source diagrams can be supplied through private `question_context_regions`; the main question regions remain separately identified for matching. Crop and bilingual review still remain pending after extraction.

An image-checked `question_region_overrides` entry can shorten individual primary rectangles while retaining a continuation on a later page. This handles a different exercise's floating figure between two pieces of statement prose. Replacement rectangles must stay inside the original source cells and reading order; supplementary material belongs in auxiliary regions instead.

For scans mixing ordinary and oversized physical page boxes, profile `page_body_top` and `page_body_bottom` boundaries in each page's source coordinates. `--max-render-side 2000` limits crop render dimensions without changing their normalized source regions. The crop cache records this cap and refuses to reuse images from a different render setting. The default zero retains the requested DPI.

`prepare-extracted.py --private-root PRIVATE` merges schema-aligned extractor output and statement-segment adapters with numbered translation batches. It verifies crop hashes before generating private import JSON, ignores temporary draft files, preserves non-English originals and leaves every version pending independent review. Use `--text-only` only after the corresponding source crops have already been imported.

When verified private context additions exist, pass `--context-text-overlays PRIVATE/context-text-overlays.json` to **every subsequent bulk preparation or import**. This explicit option is supported by `prepare-extracted.py`, `store.mjs` and the normal `route-import.mjs` export command. No overlay file is discovered automatically or read from this checkout. Python preparation calls the same JS validator through captured stdio, sending only identity, versions and context rather than image payloads.

The private overlay format is `{version:1, items:[{question_id,source_id,source_sha256,locator,language,base_text_sha256,text_sha256,text,review_status:"pending",context_overlay?}]}`. Every entry binds its canonical question ID to the source ID and locator, checks the registered PDF SHA and actual new-text SHA, and accepts an input body only when its actual SHA equals the declared base or already-applied new body. Duplicate question/language entries, conflicting context metadata, missing language versions and stale bodies fail before output replacement. Global overlay inventories may include questions outside a scoped import. Optional `context_overlay` is a bounded complete replacement of that question's context object and must agree across languages.

The option changes only the prepared current language versions and optional context; it keeps source identities, roles, other original-language versions and assets. It does not rewrite frozen extractor/translation files or promote review status. Normal SQL import retains previous text-hash versions as inactive history. A new correction based on an intermediate body needs an explicitly checked overlay base matching the frozen input used for preparation; an unrelated stale draft is rejected rather than guessed.

Moved inputs can retain their historical paths in frozen manifests. An optional private-root `runtime-path-map.json` with `{version: 1, prefixes: [{from: "OLD_ABSOLUTE_ROOT", to: "CURRENT_ABSOLUTE_ROOT"}]}` maps PDF and crop paths when reading. Prefixes respect directory boundaries and cannot escape the configured destination. This mapping leaves the original manifest unchanged.

`solutions.mjs` stores solutions in separate `bank_solution_*` tables. `normalizeSolutions(input, questionIndex)` requires exact question source revisions, PDF hashes and locators from the canonical question index. Every solution supplies `kind` (`worked_solution`, `answer_only`, or `hint`), `authorship` (`source_transcription` or `haslalab_original_draft`), source regions, both English and Korean bodies, and the actual original-language body. A mixed-language book may specify the original language per solution. Original drafts identify Codex as author and their PDF regions as problem inputs.

`applySolutions` writes a local SQLite transaction; `writeSolutionSql` streams an import only outside the public checkout. IDs keep source transcriptions and original drafts separate. Revised language snapshots preserve inactive text and role history. Crop payloads use verified 32 KiB chunks. Authoring imports remain private and pending independent review, and do not change question statements. Before activating a private solution route, the orchestration must verify the canonical question source against the server, check reviewed staging hashes, and read back every active solution body, role and image payload.

A column-extraction profile for a URL PDF uses `source: {origin: {kind: "url", url}, revision}` instead of the legacy `drive_id`. The exact reference and PDF hash must identify one registered revision. The extractor and preparer retain this URL reference, while attribution and license details remain in the manifest. Source lookups include the revision for both Drive and URL records. The preparer maps the extractor alias `waves` to the storage subject `oscillations_waves`.

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

The exporter writes a private temporary file, closes it, then atomically replaces the requested SQL file. Always wait for an export's successful process exit before uploading its output. A returned background-session identifier means the export is still running.

When several authors share one machine, serialize memory-heavy extraction, complete image/math audits and SQL exports with the same private resource lock:

```powershell
python tools/problem-bank/with-resource-lock.py --lock-file D:/private-bank/heavy.lock --label source-audit -- python D:/private-bank/audit.py
```

Wrap only the outer command; nested wrappers using the same lock would wait on themselves. Lightweight drafting can continue in parallel. The lock propagates the child exit status and does not retry failures. The operating system releases it on process exit; retain the lock file so waiting processes continue to use the same file identity.

After applying an import, `verify-remote-assets.py --database PRIVATE_DB --config PRIVATE_CONFIG --out PRIVATE_REPORT` reads back a bounded sample of the largest inline images from each source using an already authenticated Wrangler CLI. It checks chunk order, chunk hashes, assembled hashes, byte counts, image MIME types and image decoding. The report records that sampling scope; it does not mark statements or translations verified.

## Routing books across private databases

`route-import.mjs` splits a prepared full snapshot using a private version-1 routing file. The file supplies `registry_database`, `databases: [{name,id}]` and `source_routes: [{source_id,database,question_count}]`. Each registered source needs exactly one route and its checked original question count. Database names must use the private question-bank namespace. The tool neither creates databases nor changes plans or billing.

```powershell
node tools/problem-bank/route-import.mjs --manifest D:/private-bank/import-manifest.json --questions D:/private-bank/import-questions.json --routes D:/private-bank/routes.json --out-dir D:/private-bank/copy-checkpoint
```

Each selected database receives a SQL import containing only its selected source inventory, an expected fingerprint file and a verification query. Run that verification query against the same remote database after its successful import; save Wrangler's JSON response privately. Verify it with `--verify-expected EXPECTED_JSON --observed REMOTE_JSON --out RECEIPT_JSON`. It checks every current question, context, language hash, asset identity and chunk metadata against the copied snapshot. Partial text-only updates cannot generate copy receipts.

Before activating routes, also run `verify-remote-assets.py` for each new database. Build arrays of the copy receipts and crop-readback reports, then export registry SQL with `--registry-manifest MANIFEST --routes ROUTES --receipts RECEIPTS_ARRAY --samples REPORTS_ARRAY --out REGISTRY_SQL`. A route away from the registry database requires a verified full copy with the declared question count and a successful remote crop readback. Apply this registry SQL only after those checks pass. Existing copies remain available; activation deletes no old questions or history.

The registry's `bank_source_routes` table identifies the canonical database for each source revision. Resolve a question's source route before reading its crops, including `d1-inline/...` keys. Generated `*.progress.sql` queries restrict counts to each database's assigned sources: summing raw database totals would double-count retained legacy copies. Local route plans, receipts, SQL and all book content stay outside Git. Wait for each export process to exit successfully before uploading or replacing its input snapshot.

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
