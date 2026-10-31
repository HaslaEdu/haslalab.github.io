# Historical score comparisons

Research/import scripts in this directory produce version-1 source datasets with
`competitions.<key>.records`. Build the anonymous public data with:

```
python tools/build-result-comparisons.py
python tools/build-result-comparisons.py --check
```

Each record has a globally unique `id`, edition `year`, scoring `scope`, verified
`max`, bilingual `label`, anonymous `scores`, `participants`, `complete`,
`population` (individual/team), and attributed `sources` (URL, title, official).
`taskSets` contains only verified alternatives for the **entire** scored paper.
Omit it when the source scale or paper coverage cannot be matched automatically.
When a published total distribution has an unknown maximum or a weighted scale
that cannot match grading, use `manualOnly: true`, `max: null`, and no task sets.
The UI then accepts only an explicitly entered total in the source's own units;
it never automatically converts a graded score to that scale.
All individual marks, including ties and zeroes, are retained; no participant
names, countries, or personal information are needed by the comparison UI.

`rankFloor` can identify a source-verified overall-score boundary above which all
contestants' totals are published. It is set from a published lowest award (IPhO
minutes), from the lowest listed total when the statutes award every prize and
honourable mention by total thresholds and the table provably lists every awardee
(IPhO 2018 minutes' prize count; APhO 2025/2026 ranks 1..n, each labelled), or,
for EuPhO 2020, above the trailing all-zero rows that are the only rows in doubt.
The entrant count may stay unknown: ranks are then exact, but no percentile. It permits an exact hypothetical rank only
above that boundary, even when lower totals are private. Set
`participantCountUncertain` to suppress population percentages when published
participant counts conflict. A theory/experiment score cannot exceed its own
total, so the client derives an exact full-field **round** rank from the same
edition's total floor, only when the round's published scores come from exactly
the same published contestants (equal counts and population) and the round score
is at or above that floor. Below it the round stays a published-only comparison.
A round-reference band is labelled full-field only when that rank is exact or the
band's own cut is at or above the floor; unpublished scores can only raise a cut.

`topScore` records a declared best score for an edition without a score table (the
UI otherwise shows the highest published score, which is always an awardee's). APhO
2000–2026 thresholds and best scores come from the official minutes (2000–2017, all
thresholds cross-checked against Wikipedia; the minutes win for best scores) and a
pinned Wikipedia revision; a table year's thresholds must classify every official
row as it was awarded.

`medalCutoffs` is allowed only with `awardScope: true`: these scores determine
that competition's overall awards. `cutoffKind: published` means the organiser
declared a threshold; `observed` means a lowest published award-winning score,
which the UI explicitly distinguishes. `medalCutoffRule: gt` marks a strict
threshold; the default is inclusive. Do not invent total-score thresholds for
awards defined by a complete individual problem, quotas, or other criteria.

Where a table shows awards only by row colour (EuPhO 2021/2022), the collector reads
each row's filled band and requires the bands to follow the total-threshold order.
EuPhO 2025 rows carrying only a special prize at or above the lowest gold total are
counted as gold under the published threshold rule.

`medalReference` is separate from an official medal cutoff. For a complete
theory or experimental paper it records the actual edition's gold/silver/bronze
counts, their sources, and the same-round score at each cumulative award count.
The client labels this a **theory/experiment reference medal range**. Ties share
the highest matching band. A winner-only component distribution stays marked
`published`; it gains a full-field rank only through the total-floor bound above. No honourable
mention is inferred from rank counts. Both the builder and client recompute the
reference boundaries and reject inconsistent counts, cuts, or coverage.

When a signed-in student has both complete rounds graded, selected report APIs
include private `related_results` metadata. The client anchors the current
report, matches exact component tasks and maxima, then adds the latest valid
complement from the same competition/edition/exam namespace. It prefers the
same mode and explicitly labels any mixed timed/untimed fallback. Each chosen
record is linked; duplicate sessions, overlapping tasks, partial or qualitative
work and unknown/weighted scales cannot be silently added. This changes only
the historical comparison, never the recorded grade, token balance, or current
round's HaslaLab sample standing.

The UI never extrapolates a partial paper, normalises a raw mark to a different
official scale, or calls an incomplete winner-only distribution the full field.
Combined competitions can provide additive `components` with their maxima and
full-paper task sets. Other-round scores entered in the report are a local
reference calculation and never change the server grade or sample standings.
Standardised totals such as IBO T-scores must not be computed by adding raw
theory/practical marks.

Every imported edition retains its source and coverage notes. Unavailable
editions display an explicit absence of verified comparison data. The old
`sim/labmedals.json`/`sim/labmedal.js` experiment-only medal projection is retained
as a historical asset but is no longer used in receipts or score reports.
