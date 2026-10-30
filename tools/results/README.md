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
contestants' totals are published. It permits an exact hypothetical rank only
above that boundary, even when lower totals are private. Set
`participantCountUncertain` to suppress population percentages when published
participant counts conflict. Neither inference applies to component scores.

`medalCutoffs` is allowed only with `awardScope: true`: these scores determine
that competition's overall awards. `cutoffKind: published` means the organiser
declared a threshold; `observed` means a lowest published award-winning score,
which the UI explicitly distinguishes. `medalCutoffRule: gt` marks a strict
threshold; the default is inclusive. Do not invent total-score thresholds for
awards defined by a complete individual problem, quotas, or other criteria.

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
