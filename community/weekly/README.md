# Reviewed monthly problems and historical publication

`2026-W44.json` preserves the original publication of the three supplied physics problems, complete Korean and English web statements and solutions, and evidence-based partial-credit rubrics. Numbers 4–6 originally appended to the existing week. Each web rubric totals 100 points; the proton-chain statement also preserves the original 15-point allocations.

The monthly transition moves the current six problems to `2026-11`, preserving their database IDs, content, rubrics, submissions and scores. They remain open through November 30, 2026 in Korea; the exclusive cutoff is December 1 00:00 KST (`1796050800`). A separate durable publication marker applies this transition once and preserves later administrator edits. The original JSON stays unchanged so existing and fresh databases follow the same publication history.

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
node --test community/test-weekly-content.mjs tests/test-weekly-rendering.cjs
```

The deployment workflow validates the content and grading integration before deploying the Worker. Rebuild the site catalogue after changing `arena.js` so its lazy asset hash stays current.
