"""Validate researched score records and build lazy per-competition public data.

    python tools/build-result-comparisons.py [--check]

Only anonymous score distributions and published award thresholds are served.
Source URLs, completeness and scoring scopes remain attached to every record.
"""
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUESTED = ('ipho', 'apho', 'eupho', 'ispho', 'nbpho', 'opho', 'izho',
             'physcup', 'plancks', 'ortvay', 'gpho', 'imo', 'icho', 'ieso',
             'ioaa', 'ioaajr', 'ibo')


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate(record):
    identity = record.get('id', '(missing id)')
    def require(condition, message):
        if not condition:
            raise ValueError(f'{identity}: {message}')
    require(isinstance(identity, str) and identity != '(missing id)', 'id is required')
    require(str(record.get('year', '')).isdigit(), 'year must identify one edition')
    require(record.get('scope') in ('theory', 'experiment', 'total', 'round'), 'unknown scoring scope')
    require('manualOnly' not in record or type(record['manualOnly']) is bool, 'manual-only must be a boolean')
    maximum = record.get('max')
    manual_unknown = record.get('manualOnly') is True and maximum is None
    require(manual_unknown or number(maximum) and maximum > 0, 'verified positive scoring maximum is required for automatic comparison')
    if manual_unknown:
        require(not record.get('taskSets') and not record.get('components'), 'an unknown score scale cannot match graded paper scores')
    ceiling = float('inf') if manual_unknown else maximum
    scores = record.get('scores', [])
    require(isinstance(scores, list) and all(number(s) and 0 <= s <= ceiling + 1e-6 for s in scores), 'scores must fit the published maximum')
    count = record.get('participants')
    require(count is None or type(count) is int and count >= len(scores), 'participant count cannot be less than the published score count')
    require(type(record.get('complete')) is bool, 'completeness must be explicit')
    require(not record['complete'] or bool(scores) and count == len(scores), 'complete distributions need every participant score')
    require(record.get('population') in ('individual', 'team'), 'individual/team population must be explicit')
    if record.get('rankFloor') is not None:
        require(record['scope'] == 'total' and number(record['rankFloor']) and 0 <= record['rankFloor'] <= ceiling and (count is None or type(count) is int) and bool(scores), 'rank coverage floor requires a sourced total distribution')
        require(any(s >= record['rankFloor'] - 1e-9 for s in scores), 'the coverage floor must lie within the published scores')
    for tasks in record.get('taskSets', []):
        require(isinstance(tasks, list) and bool(tasks) and len(set(tasks)) == len(tasks) and all(isinstance(t, str) and t for t in tasks), 'invalid full-paper task set')
    cuts = record.get('medalCutoffs', {})
    require(isinstance(cuts, dict), 'medal cutoffs must be a mapping')
    previous = ceiling
    for tier in ('gold', 'silver', 'bronze', 'hm'):
        if tier in cuts:
            require(number(cuts[tier]) and 0 <= cuts[tier] <= previous, 'award thresholds must descend within the scoring scale')
            previous = cuts[tier]
    require(not set(cuts) - {'gold', 'silver', 'bronze', 'hm'}, 'unknown award category')
    if cuts:
        require(record.get('awardScope') is True, 'partial component scores cannot award overall medals')
        require(record.get('cutoffKind') in ('published', 'observed'), 'cutoff provenance must be explicit')
    reference = record.get('medalReference')
    if reference is not None:
        require(record['scope'] in ('theory', 'experiment') and not record.get('awardScope') and not record.get('manualOnly'), 'reference medal bands apply only to a known component scale')
        require(reference.get('basis') == 'round_rank', 'unknown component reference method')
        require(reference.get('population') == ('complete' if record['complete'] else 'published'), 'reference population must match score coverage')
        counts, ref_cuts = reference.get('counts', {}), reference.get('cuts', {})
        tiers = ('gold', 'silver', 'bronze')
        require(set(counts) == set(tiers) and all(type(counts[k]) is int and counts[k] >= 0 for k in tiers), 'verified G/S/B award counts required')
        require(0 < sum(counts.values()) <= len(scores), 'award reference ranks must be covered by the published component scores')
        ranked, boundary, expected = sorted(scores, reverse=True), 0, {}
        for tier in tiers:
            boundary += counts[tier]
            if counts[tier]:
                expected[tier] = ranked[boundary - 1]
        require(set(ref_cuts) == set(expected) and all(number(ref_cuts[k]) and abs(ref_cuts[k] - value) < 1e-7 for k, value in expected.items()), 'reference cuts must use cumulative award counts on this component, preserving ties')
        proof = reference.get('sources', [])
        require(bool(proof) and all(isinstance(s.get('url'), str) and s['url'].startswith(('https://', 'http://')) and type(s.get('official')) is bool for s in proof), 'award-count sources required for component reference')
    components = record.get('components', [])
    require(isinstance(components, list), 'components must be a list')
    component_ids = set()
    for component in components:
        require(number(component.get('max')) and component['max'] > 0 and component.get('id'), 'invalid component')
        require(component['id'] not in component_ids, 'component identifiers must be unique')
        component_ids.add(component['id'])
        for tasks in component.get('taskSets', []):
            require(isinstance(tasks, list) and bool(tasks) and len(set(tasks)) == len(tasks) and all(isinstance(t, str) and t for t in tasks), 'invalid full-component task set')
    if components:
        require(number(maximum) and abs(sum(c['max'] for c in components) - maximum) < 1e-6, 'additive component maxima must equal the published total')
    sources = record.get('sources', [])
    require(bool(sources) and all(isinstance(s.get('url'), str) and s['url'].startswith(('https://', 'http://')) and type(s.get('official')) is bool for s in sources), 'verifiable sources and official/unofficial attribution required')
    record['scores'] = sorted(scores, reverse=True)
    return record


def build(check=False):
    datasets = {comp: {'schema': 1, 'comp': comp, 'records': []} for comp in REQUESTED}
    identities = set()
    for path in sorted((ROOT / 'tools/results').glob('*.json')):
        source = json.loads(path.read_text(encoding='utf-8-sig'))
        if source.get('schema') != 1 or 'competitions' not in source:
            continue
        for comp, data in source['competitions'].items():
            if not comp.isalpha() or not comp.islower():
                raise ValueError(f'{path}: invalid competition key {comp}')
            target = datasets.setdefault(comp, {'schema': 1, 'comp': comp, 'records': []})
            if data.get('coverage'):
                target['coverage'] = data['coverage']
            for record in data.get('records', []):
                validate(record)
                if record['id'] in identities:
                    raise ValueError(f'duplicate record: {record["id"]}')
                identities.add(record['id'])
                target['records'].append(record)
    stale = []
    for comp, data in datasets.items():
        data['records'].sort(key=lambda r: (-int(r['year']), r['id']))
        target = ROOT / 'sim/results' / f'{comp}.json'
        content = json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n'
        if check:
            if not target.is_file() or target.read_text(encoding='utf-8') != content:
                stale.append(str(target.relative_to(ROOT)))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8', newline='\n')
    if stale:
        raise ValueError('Generated result comparisons are stale: ' + ', '.join(stale))
    print(f'{"Checked" if check else "Built"} {len(datasets)} comparison datasets, {len(identities)} scoring records.')


if __name__ == '__main__':
    build('--check' in sys.argv)
