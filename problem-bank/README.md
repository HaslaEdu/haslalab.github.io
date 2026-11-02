# HaslaLab problem library

The problem library is available to visitors inside HaslaLab Learn → Physics and Learn → Astronomy. Its same-origin embedded UI follows the site's language and theme and reuses an existing HaslaLab session for optional member features. The fixed API Worker uses the community service for session authentication and the existing authorized Upstage OCR endpoint. Canonical statements and solutions remain in the three D1 shards. A separate D1 database holds derived bilingual FTS documents and difficulty/classification facets; a private R2 bucket holds originals and approved figure variants.

The static UI contains code and vendor assets only. No textbook statement, generated SQL, source PDF, production token or private manifest belongs in this directory. Embedded mode reads `hlCmTok` only under an admitted same-origin parent, sends it only to the fixed API, and never deletes or revokes the parent site's session on denial. Parent messages carry theme, language and height only. Public reads work without an account and survive an unavailable authentication service. Original whole PDFs/crops and paid OCR require the server-confirmed administrator role. Member difficulty feedback requires a verified session. Source drafts, translations and solutions retain their review status. Selecting a problem never fetches a solution; only the explicit solution action does.

## API

- `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`: existing community authentication through a service binding.
- `GET /api/problem-bank/status`, `/sources`, `/search`: public status, published source titles and keyword/formula searches. Empty-query browsing uses a canonical cursor with no offset300 ceiling; text search remains bounded and reports truncation. Filters include collection, source, subject and stars1–5.
- `GET /api/problem-bank/questions/:id`: current bilingual statement versions and admitted figures; no solution body.
- `GET /api/problem-bank/questions/:id/context`: bounded canonical referenced-question traversal, with cycle and truncation flags.
- `GET /api/problem-bank/questions/:id/solutions`: separately attributed stored source solutions and original drafts.
- `GET /api/problem-bank/questions/:id/recommendations`: initial subject, difficulty, novelty and source-diversity recommendations; this is not a trained personalization model.
- `POST /api/problem-bank/identify`: supplied JSON text without OCR, or one raster photo through the existing authorized OCR service. Returns candidates and recognized text for correction; it does not certify an exact match or save the photo.
- `GET /api/problem-bank/assets/:id`, `/figures/:id`: hash-verified admitted figures. Known answer annotations are blocked from public problem display; unreviewed reference figures remain collapsed. Source PDFs/crops remain administrator-only.
- `GET|POST /api/problem-bank/questions/:id/feedback`: aggregate self-reported difficulty and the member's own rating. One current record per member/question, bounded input and daily write limit. This cannot submit a verified grade or change ability/item ratings.
- `POST /api/problem-bank/questions/:id/difficulty-review`: administrator rubric review, requiring the current English canonical text SHA and explicit confirmation that required context was read.

## Difficulty and recommendations

`rubric-v1` scores prerequisites, concept integration, mathematical tools and reasoning from0–4, with weights30%,20%,20%,30%. Thresholds0.65/1.35/2.1/2.85 produce1–5stars. Automatic estimates use English statements and source-level evidence and remain **provisional, low-confidence**. Length, printed problem numbers and missing/OCR context do not increase difficulty. Missing references reduce confidence. A later expert review replaces the estimate; self-reported user feedback stays separately identified. These thresholds are an initial design, not a validated scale.

Initial anchors are1star for a direct single-concept task,2 for a basic calculus task,3 for differential-equation/eigenmode work,4 for a standalone advanced mathematical tool, and5 for advanced tools combined with nontrivial reasoning/approximation. The same book may span the full scale; its source-level label does not force every item into one difficulty band. Integration uses concepts in the statement, not the number of source/topic tags. These anchors help inspect estimates; they do not certify individual questions without review.

The initial recommender ranks candidate topic matches near a chosen star level, excludes the current question, reported-solved items, exact statement copies and unresolved-source candidates, and caps each published work at three items (two scans of the same work share that cap). It may return fewer items when the candidate pool is insufficient. A subsequent version can use per-topic ability and item difficulty updated by verified grading outcomes, then evaluate held-out prediction calibration and recommendation diversity. `eloUpdate` rejects self-reported outcomes; no browser-supplied correctness value is accepted as verified evidence. The current service does not claim to reproduce PhysLeague's unavailable implementation.

The separation between problem characteristics and mere calculation burden follows [University of Minnesota Physics Education Research](https://groups.spa.umn.edu/physed/Research/CRP/crjudge.html). The proposed future verified-outcome update follows the adaptive assessment approach discussed by [Pelánek (2016)](https://www.fi.muni.cz/~xpelanek/publications/CAE-elo.pdf); no trained rating model is claimed for this release.

## Data preparation

Export the current canonical routed statement bodies privately, verifying actual UTF-8 body hashes. `tools/problem-bank/build-search-index.mjs PRIVATE/input.jsonl PRIVATE/output` validates source/question identity and emits compressed, private SQL batches. It shares the exact normalization helper and schema with the runtime, retaining source titles and printed numbers in the search index. Verify every current body, normalized search text and metadata against the expected hashes after import. The index is derived data; it does not replace canonical versions or their history. Apply any verified context-text overlays when preparing future source imports, so a frozen original draft cannot revert a later source-context recovery.

R2 object keys use `sources/<sha256>.pdf` or `figures/<sha256>.png|svg`. Admit a figure only after source/question/parent-asset identity, exact crop bounds, givens-only visual approval and full remote SHA readback. Raster crops retain original labels; they are not falsely described as vector redraws. SVG extraction must reject scripts, events, external references and off-crop hidden text. Keep the bucket's public development URL disabled. This bucket is separate from temporary student answer scans.

## Validation and deployment

```powershell
node --test community/test-problem-bank.mjs community/test-problem-bank-model.mjs problem-bank/test-worker.mjs tools/problem-bank/test-search-index.mjs tests/test-problem-library-learning.cjs
wrangler deploy --dry-run --config problem-bank/wrangler.toml
wrangler deploy --config problem-bank/wrangler.toml
```

Use an isolated checkout for this deployment so unrelated community/frontend changes are preserved. `run_worker_first = true` makes CSP and response policy apply to the static UI as well as private routes. No OpenAI API key or generation/embedding provider is required for this initial FTS-based service. OCR authorization is controlled by `BANK_OCR_ENABLED`; credentials remain in the existing community Worker.
