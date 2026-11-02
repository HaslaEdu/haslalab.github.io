# Private HaslaLab problem library

This separate Worker serves the administrator UI and API. It uses the existing community service only for session authentication and the authorized Upstage OCR endpoint. The source corpus, bilingual statements, solution variants, classification and private image chunks remain in the three canonical problem-bank D1 databases. A separate D1 database holds the derived bilingual FTS index, and a dedicated private R2 bucket holds hash-addressed original PDFs.

The static UI contains code and vendor assets only. No textbook statement, generated SQL, source PDF, production token or private manifest belongs in this directory. The UI uses the existing HaslaLab account; session tokens are held in session storage. All library, source PDF and OCR operations require the server-confirmed administrator role. Source drafts, translations, source solutions and authored solution drafts retain their review status.

## API

- `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`: existing community authentication through a service binding.
- `GET /api/problem-bank/status`, `/sources`, `/search`: private corpus status, canonical sources and bounded keyword/formula searches.
- `GET /api/problem-bank/questions/:id`: current bilingual statement versions and authenticated source images.
- `GET /api/problem-bank/questions/:id/context`: bounded canonical referenced-question traversal, with cycle and truncation flags.
- `GET /api/problem-bank/questions/:id/solutions`: separately attributed stored source solutions and original drafts.
- `GET /api/problem-bank/questions/:id/recommendations`: subject and text similarity; this is not a trained personalization model.
- `POST /api/problem-bank/identify`: supplied JSON text without OCR, or one raster photo through the existing authorized OCR service. Returns candidates and recognized text for correction; it does not certify an exact match or save the photo.
- `GET /api/problem-bank/assets/:id`, `/sources/:source_id/pdf`: authenticated exact source bytes with integrity metadata.

## Data preparation

Export the current canonical routed statement bodies privately, verifying actual UTF-8 body hashes. `tools/problem-bank/build-search-index.mjs PRIVATE/input.jsonl PRIVATE/output` validates source/question identity and emits compressed, private SQL batches. It shares the exact normalization helper and schema with the runtime, retaining source titles and printed numbers in the search index. Verify every current body, normalized search text and metadata against the expected hashes after import. The index is derived data; it does not replace canonical versions or their history. Apply any verified context-text overlays when preparing future source imports, so a frozen original draft cannot revert a later source-context recovery.

R2 object keys use `sources/<sha256>.pdf`. Register a source-object mapping only after full remote PDF bytes have been read and matched to the original SHA-256. Keep the bucket's public development URL disabled. This bucket is separate from temporary student answer scans.

## Validation and deployment

```powershell
node --test community/test-problem-bank.mjs problem-bank/test-worker.mjs tools/problem-bank/test-search-index.mjs
wrangler deploy --dry-run --config problem-bank/wrangler.toml
wrangler deploy --config problem-bank/wrangler.toml
```

Use an isolated checkout for this deployment so unrelated community/frontend changes are preserved. `run_worker_first = true` makes CSP and response policy apply to the static UI as well as private routes. No OpenAI API key or generation/embedding provider is required for this initial FTS-based service. OCR authorization is controlled by `BANK_OCR_ENABLED`; credentials remain in the existing community Worker.
