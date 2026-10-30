# Reviewed monthly problems and historical publication

`2026-W44.json` preserves the original publication of the three supplied physics problems, complete Korean and English web statements and solutions, and evidence-based partial-credit rubrics. Numbers 4–6 originally appended to the existing week. Each web rubric totals 100 points; the proton-chain statement also preserves the original 15-point allocations.

The monthly transition moves the current six problems to `2026-11`, preserving their database IDs, content, rubrics, submissions and scores. They remain open through November 30, 2026 in Korea; the exclusive cutoff is December 1 00:00 KST (`1796050800`). A separate durable publication marker applies this transition once and preserves later administrator edits. The original JSON stays unchanged so existing and fresh databases follow the same publication history.

The answer-sheet update retires the three introductory problems from public lists, direct reads, submissions and rankings. Their private historical records remain in the database. The supplied problems retain IDs 4, 5 and 6 and display as problems 1, 2 and 3. Their statements, rubrics and month-end deadline are unchanged.

`monthly-problems.mjs` defines the public subquestion forms shared by the Worker and native printable HTML sheets. Every answered part includes both a final answer and working; a part may be left completely blank for partial submission. The Worker validates known part IDs, enforces field limits, stores the complete structured sheet, and sends its labelled text to the existing grader. Unanswered parts receive zero, and awarded points require evidence from the corresponding part's user-entered answer or working.

Each account has at most three accepted submissions per problem, across typed and photo-derived answers and after the monthly deadline. The server atomically saves a pending submission before calling the grader. A request identifier makes network retries idempotent and rejects identifier reuse with different content. Invalid forms, drafts and OCR do not consume attempts. Accepted pending/error submissions do count because the answer is preserved; the existing administrator regrade acts on that same submission. Legacy submissions count toward the same limit.

The photo workflow uses the shared scanner and Upstage OCR, with an explicit target subquestion. The student checks the recognized working and enters/checks the final answer before submission. Printable sheets are HTML at `sim/monthly-answer-sheet.html`, not embedded PDFs. `monthly-figures.js` safely inlines the three reviewed SVGs with inherited theme colors and scoped identifiers; no white image panels are used.

Each printable A4 page has four solid black corner marks for scan alignment. Monthly uploads send the selected OCR scan and a separately encoded capture to `POST /api/monthly/problems/:id/photos`. Successful OCR retains the capture and recognized text in D1; failed OCR does not retain a photo. The account-scoped browser draft keeps deduplicated photo IDs by part and submits `photo_ids` with the answer. The server validates photo ownership, problem and part. Own submission history offers authenticated capture viewing through `GET /api/monthly/photos/:photoId`, with no token in URLs and with object URLs revoked on navigation. Monthly captures and submitted answers persist independently of the exam-mode temporary-image cleanup.

Only the total score is released immediately for native monthly problems. Criterion scores, evidence and corrections remain private in submit responses, idempotent replays and own submission reads until the exact exclusive cutoff. For November this is December 1, 2026 at 00:00 KST. Responses expose `feedback_held` and `feedback_available_at`; the browser also suppresses stale cached details before that time. Exam-mode immediate feedback is unchanged.

Typed work receives a separate conservative review for explicit AI-generation artifacts. Style or LaTeX alone cannot justify withholding a grade; uncertain or failed reviews continue to normal grading. A supported suspicion is saved as `ai_suspected` with no numeric score, consumes one accepted attempt, and can be reviewed/regraded by an administrator without a new attempt. The UI explains false positives and recommends the student's own handwritten solution without claiming a photograph proves authorship. Verified photo OCR exempts a part only when its complete final answer and working match after whitespace/math-delimiter normalization; typed replacements and additions remain eligible for review. Client `via_ocr` flags cannot grant this exemption. Screening plus grading may take about two minutes; transport does not impose a shorter abort and network retries retain the original request ID.

Native monthly public presentation omits the supplied-material/editor provenance labels in headers and statement/solution tails. Private source content and the historical publication JSON remain available for administration and publication verification.

The Worker imports the JSON through `src/weekly-content.js`. Its existing D1 binding publishes the reviewed batch atomically on the first monthly/legacy weekly/problem request. The durable `weekly_publications` marker prevents duplication and preserves subsequent administrator edits. A conflicting occupied week/number aborts the initial batch. This needs no new credential or D1 management permission. Canonical links use `#/monthly`; old `#/weekly` problem links remain valid.

After publication, edit a live problem through the existing administrator problem editor. Changing this JSON does not overwrite published records. A new reviewed batch needs its own explicit publication ID and unused week/number slots.

Statements and models use escaped plain text, `$…$` / `$$…$$` math, `##` / `###` headings, and standalone `![caption](weekly/figures/name.svg)` figures. Only local figure paths render as images; those existing asset URLs remain unchanged. Student answer previews remain plain escaped text. The attached PDFs are not embedded or offered as the problem interface. The API/UI releases worked solutions after the monthly deadline, while continuing to accept practice submissions.

Editorial details:

- Proton chain: retain the periodic displacement cell, infinite neighbour sum, zero-mode exclusion, and finite particle-count qualifications. Web point allocations are integer weights totalling 100; original allocations remain in the source metadata and statement.
- Walls and free targets: retain the exact finite-N geometry, admissible ordered-collision domain, and conditional minimum defining the critical coefficient. The model includes the full proof and numerical appendix; optional checks are not required for full marks. Its 12 tabulated results and small-N missed-target counterexample were independently reproduced during conversion.
- Optical Rutherford scattering: the supplied image states `|dr/ds|=1` despite defining `dl=n ds`. The web statement explicitly corrects this to a question whose answer is `|dr/ds|=n`. Distinguish the Coulomb approximation from the original refractive-index model and its small-angle validity.

Validation:

```sh
node community/weekly/build-seed.mjs --check
node --test community/test-weekly-content.mjs community/test-monthly-period.mjs community/test-monthly-answers.mjs community/test-monthly-policy.mjs community/test-monthly-photos.mjs community/test-monthly-presentation.mjs tests/test-weekly-rendering.cjs tests/test-monthly-*.cjs
```

The deployment workflow validates the content and grading integration before deploying the Worker. Rebuild the site catalogue after changing `arena.js` so its lazy asset hash stays current.
