"""Read-only, exact six-override contract for the final IChO 2019 handoff.

No PDF parsing, rendering, producer execution, staging or filesystem writes occur
here.  prepare() also binds the joined publication to the exact 60 proof pages.
"""
from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import json

BASE = Path(__file__).resolve().parents[1]
B = (BASE / 'historical/icho/composer-2019').resolve()
P = (BASE / 'proofs/icho/2019-final').resolve()
PUBLICATION_ROOT = Path('C:/Users/andre/CodexWork/HaslaLab/haslalab-poi-style-publication').resolve()
SOURCE = '5821bab3b65b216cc74df99d7ec643389d212c15b4d88c95a7da22de8baf97d8'
READY_SHA = 'e7ac28136d66573a9674322876b08458ef0165dcf0e3aab2a682cf48665b6737'
FREEZE_SHA = '81156ebe66c0872dd0301e5a22d0b72f8e29dd8ba56ed3eae60b87d3422ba49a'
PINS = {
    'READY-for-root-assembly-r2.json': READY_SHA,
    'final-code-freeze-r2.json': FREEZE_SHA,
    'final-r2-page53-semantics-amendment.json': '95f51bb3527ea0f83202c4c071e01b884a09369c615b7de5cd628896b3083f39',
    'final-r2-source-checkbox-columns-amendment.json': '22eebd85186fae16a0c31ad8d3b23e8e67d5f015e2efd7eddbf730a0694faee7',
    'final-r2-page51-second-answer-row-amendment.json': 'cd50b0b21e8fba85c47bc79923453aab684d379676830d61c2ae98aa7e45a9f2',
    'final-r2-page54-starting-compound-amendment.json': 'fc26e9089730d02d6c03c7f052b194c6c5366548267ead8a2faba220250b8475',
}
CHANGED_PAGES = [13, 45, 46, 51, 53, 54]
TEXT53 = {'p53:b3:l0:s3-3': '',
          'p53:b3:l0:s5-5': '-이노시톨에서 유래한 우세 화합물의 분자식을. 이 시료에서',
          'p53:b3:l1:s0-0': '관찰된 양성자 수와 일치해야 하며, 측정 자료는'}
TEXT51 = {'p51:b6:l0:s8-8:c0-22': '덜 안정함. 비교:', 'p51:b6:l0:s12-12': '착물.'}
TEXT54 = {'p54:b7:l0:s2-2': '는 화합물', 'p54:b7:l0:s4-4:c0-4': '에서'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def checked(pin):
    path = Path(pin['path']).resolve()
    assert path.is_file() and sha(path) == pin['sha256'], ('Stale final IChO2019 evidence', path)
    if 'bytes' in pin:
        assert path.stat().st_size == pin['bytes'], ('Evidence size changed', path)
    return path


def timestamp(value):
    return datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def _assert_override(page, expected, actual):
    assert actual == expected, ('Unapproved override change', page)


def _validate_handoff(engine_dir=None):
    engine = Path(engine_dir or B / 'engine').resolve()
    assert engine == B / 'engine', ('Unexpected 2019 engine directory', engine)
    docs = {}
    for name, digest in PINS.items():
        assert sha(B / name) == digest, ('Unapproved final handoff document', name)
        docs[name] = read(B / name)
    ready = docs['READY-for-root-assembly-r2.json']
    freeze = docs['final-code-freeze-r2.json']
    a53 = docs['final-r2-page53-semantics-amendment.json']
    choices = docs['final-r2-source-checkbox-columns-amendment.json']
    a51 = docs['final-r2-page51-second-answer-row-amendment.json']
    a54 = docs['final-r2-page54-starting-compound-amendment.json']
    assert ready['status'] == 'READY_FOR_ROOT_ASSEMBLY' and ready['year'] == 2019 and ready['pages'] == 60
    assert Path(ready['proof_root']).resolve() == P and ready['contains_solutions'] is False
    assert ready['intro_pages'] == list(range(1, 8)) and ready['body_pages'] == list(range(8, 61))
    assert freeze['year'] == 2019 and freeze['pages'] == 60 and freeze['source_sha256'] == SOURCE
    assert ready['source']['sha256'] == SOURCE and checked(ready['source']) == Path(freeze['source']).resolve()
    frozen = {Path(pin['path']).resolve(): pin for pin in freeze['files']}
    assert len(freeze['files']) == len(frozen) == 197
    programs = [path for path in frozen if path.suffix == '.py']
    assert len(programs) == 69
    expected, after, regenerated_after = {}, {}, {}

    def original(amend, page):
        assert amend['year'] == 2019 and amend['page'] == page
        assert amend['source_sha256'] == SOURCE and amend['base_freeze_sha256'] == FREEZE_SHA
        path = Path(amend['changed_input']).resolve()
        assert path == B / f'page{page:02}.overrides.json'
        assert sha(amend['before_copy']) == amend['before_sha256'] == frozen[path]['sha256']
        regenerated_after[page] = timestamp(amend['created_utc'])
        return copy.deepcopy(read(amend['before_copy']))

    e53 = original(a53, 53)
    assert a53['slot_edits'] == TEXT53
    for slot, text in TEXT53.items():
        e53['__slot_edits__'].setdefault(slot, {})['text'] = text
    expected[53], after[53] = e53, a53['after_sha256']
    assert choices['year'] == 2019 and choices['source_sha256'] == SOURCE and choices['base_freeze_sha256'] == FREEZE_SHA
    assert [row['page'] for row in choices['pages']] == [13, 45, 46, 51]
    baselines = {13: [609.4299926757812], 45: [735.219970703125, 759.0960083007812],
                 46: [83.15997314453125], 51: [144.8599853515625, 186.3800048828125]}
    for row in choices['pages']:
        page = row['page']
        path = Path(row['changed_input']).resolve()
        assert path == B / f'page{page:02}.overrides.json'
        assert sha(row['before_copy']) == row['before_sha256'] == frozen[path]['sha256']
        value = copy.deepcopy(read(row['before_copy']))
        assert '__layout_scope__' in value
        assert set(row['scope_edits']) == {'fixed_prose_baselines', 'source_two_column_choice_review' if page == 45 else 'source_checkbox_columns_review'}
        assert row['scope_edits']['fixed_prose_baselines'] == baselines[page]
        assert row['text_edits'] == (TEXT51 if page == 51 else {})
        value['__layout_scope__'].update(row['scope_edits'])
        for slot, text in row['text_edits'].items():
            value['__slot_edits__'].setdefault(slot, {})['text'] = text
        represented = Path(a51['before_copy']) if page == 51 else path
        assert sha(represented) == row['after_sha256']
        _assert_override(page, value, read(represented))
        expected[page], after[page] = value, row['after_sha256']
        regenerated_after[page] = timestamp(row['created_utc'])
    assert a51['year'] == 2019 and a51['page'] == 51 and a51['source_sha256'] == SOURCE
    assert a51['base_freeze_sha256'] == FREEZE_SHA and a51['parent_checkbox_amendment_sha256'] == PINS['final-r2-source-checkbox-columns-amendment.json']
    assert Path(a51['changed_input']).resolve() == B / 'page51.overrides.json'
    assert sha(a51['before_copy']) == a51['before_sha256'] == after[51]
    assert a51['only_inserted_source_baseline'] == 165.6199951171875
    assert a51['fixed_prose_baselines_before'] == expected[51]['__layout_scope__']['fixed_prose_baselines']
    final_baselines = [144.8599853515625, 165.6199951171875, 186.3800048828125]
    assert a51['fixed_prose_baselines_after'] == final_baselines
    expected[51]['__layout_scope__']['fixed_prose_baselines'] = final_baselines
    after[51], regenerated_after[51] = a51['after_sha256'], timestamp(a51['created_utc'])
    e54 = original(a54, 54)
    assert a54['slot_edits'] == TEXT54
    for slot, text in TEXT54.items():
        e54['__slot_edits__'].setdefault(slot, {})['text'] = text
    expected[54], after[54] = e54, a54['after_sha256']
    assert sorted(expected) == CHANGED_PAGES
    for page in CHANGED_PAGES:
        path = B / f'page{page:02}.overrides.json'
        assert sha(path) == after[page]
        _assert_override(page, expected[page], read(path))
    actual_changes = []
    for path, pin in frozen.items():
        digest = sha(path)
        if digest != pin['sha256']:
            actual_changes.append(dict(path=str(path), before_sha256=pin['sha256'], after_sha256=digest))
        else:
            assert path.stat().st_size == pin['bytes']
        if path.name in {f'page{page:02}.overrides.json' for page in CHANGED_PAGES} and path.parent == B:
            assert digest == after[int(path.name[4:6])]
        else:
            assert digest == pin['sha256'], ('Changed frozen input', path)
    assert {Path(row['path']).resolve() for row in actual_changes} == {B / f'page{page:02}.overrides.json' for page in CHANGED_PAGES}
    assert len(actual_changes) == 6 and len(frozen) - len(actual_changes) == 191
    assert all(sha(path) == frozen[path]['sha256'] for path in programs)
    # The immutable bootstrap ledger protects the original frozen 2024 tree.
    for pin in read(B / 'bootstrap-provenance.json')['entries']:
        assert sha(pin['source']) == pin['source_sha256'], ('Protected frozen 2024 input changed', pin['source'])

    evidence = [B / name for name in PINS]
    ready_writer = None
    for pin in ready['evidence']:
        path = checked(pin)
        if path.suffix == '.json':
            evidence.append(path)
        else:
            assert path == B / 'final-r2-code-review/create_ready_manifest.py'
            ready_writer = path
    assert ready_writer is not None
    bindings = []
    assert [row['page'] for row in ready['page_artifacts']] == list(range(1, 61))
    for row in ready['page_artifacts']:
        page = row['page']
        assert row['passed'] is True
        pins = {Path(pin['path']).name: pin for pin in row['artifacts']}
        assert len(pins) == len(row['artifacts'])
        for pin in row['artifacts']:
            path = checked(pin)
            assert path.parent == (B if path.name == f'page{page:02}.diagnostic.json' else P)
            if path.suffix == '.json' and not path.name.endswith(('.layout.json', '.effective-plan.json')):
                evidence.append(path)
        def artifact(suffix):
            return pins[f'page{page:02}{suffix}']
        q = read(artifact('.layout.json')['path'])
        diagnostic_pin = artifact('.diagnostic.json')
        diagnostic_path = Path(diagnostic_pin['path'])
        diagnostic = read(diagnostic_path)
        assert diagnostic_path.stat().st_mtime >= max(timestamp(freeze['created_utc']), regenerated_after.get(page, 0))
        proof_sha = artifact('.pdf')['sha256']
        assert diagnostic['passed'] is True and diagnostic['output_sha256'] == q['output_sha256'] == proof_sha
        assert q['page'] == page and q['source_sha256'] == SOURCE
        assert q['composer_sha256'] == frozen[B / 'natural_plan_compose_icho2019.py']['sha256']
        assert q['vector_language_helper_sha256'] == frozen[B / 'vector_language_icho2019.py']['sha256']
        assert q['actual_native_vector_coordinate_audit']['audit_code_sha256'] == frozen[B / 'verify_native_vectors_icho2019.py']['sha256']
        assert q['overrides_sha256'] == sha(B / f'page{page:02}.overrides.json')
        assert q['plan_sha256'] == sha(B.parent / '2019' / f'page{page:02}.ko.json')
        assert q['effective_plan_sha256'] == artifact('.effective-plan.json')['sha256']
        render = read(artifact('.render.json')['path'])
        assert render['proof_sha256'] == proof_sha and render['png_sha256'] == artifact('.png')['sha256']
        assert render['layout_sha256'] == artifact('.layout.json')['sha256']
        for suffix in ['.inter-row-audit.json', '.underline-style-audit.json']:
            audit = read(artifact(suffix)['path'])
            assert audit['passed'] is True and audit['proof_sha256'] == proof_sha
        for suffix in ['.graphic-label-geometry.json', '.caption-center-audit.json', '.template-geometry.json']:
            name = f'page{page:02}{suffix}'
            if name in pins:
                audit = read(pins[name]['path'])
                assert audit['passed'] is True and audit['proof_sha256'] == proof_sha
        bindings.append(dict(page=page, proof_path=str(P / f'page{page:02}.pdf'), proof_sha256=proof_sha,
                             qa_sha256=artifact('.layout.json')['sha256'], effective_plan_sha256=artifact('.effective-plan.json')['sha256'],
                             plan_sha256=q['plan_sha256'], overrides_sha256=q['overrides_sha256'], composer_sha256=q['composer_sha256'],
                             png_sha256=artifact('.png')['sha256'], render_sha256=artifact('.render.json')['sha256'], diagnostic_sha256=diagnostic_pin['sha256']))
    verification = read(B / 'final-60-page-proof-verification.json')
    assert verification['passed'] is True and verification['verified_pages'] == 60 and verification['failures'] == []
    assert verification['freeze_sha256'] == FREEZE_SHA and verification['rows'] == ready['page_artifacts']
    assert {Path(row['path']).resolve(): (row['before_sha256'], row['after_sha256']) for row in verification['actual_changed_R2_inputs']} == {Path(row['path']).resolve(): (row['before_sha256'], row['after_sha256']) for row in actual_changes}
    assert verification['other_R2_frozen_inputs_unchanged'] == 191 and verification['all69_frozen_Python_programs_unchanged'] is True
    visual = read(B / 'final-r2-visual-review.json')
    assert visual['passed'] is True and visual['reviewed_pages'] == 60 and visual['remaining_pages'] == []
    assert visual['source_sha256'] == SOURCE and visual['freeze_sha256'] == FREEZE_SHA
    assert [row['page'] for row in visual['pages']] == list(range(1, 61))
    for row, binding in zip(visual['pages'], bindings):
        for key, field in [('pdf_sha256', 'proof_sha256'), ('layout_sha256', 'qa_sha256'), ('png_sha256', 'png_sha256'), ('render_sha256', 'render_sha256'), ('diagnostic_sha256', 'diagnostic_sha256')]:
            assert row[key] == binding[field]
        assert row['passed'] is True
    programs.append(ready_writer)
    for relative, audit_path, key in [
        ('verify_r2_final.py', B / 'final-60-page-proof-verification.json', 'final_revision_verifier_sha256'),
        ('verify_all_source_checkboxes.py', B / 'final-r2-code-review/all-source-checkbox-coordinate-audit.json', 'audit_code_sha256'),
        ('verify_answer_columns45.py', P / 'page45.answer-columns-audit.json', 'audit_code_sha256'),
    ]:
        path = B / 'final-r2-code-review' / relative
        assert sha(path) == read(audit_path)[key]
        programs.append(path)
    programs.append(Path(__file__).resolve())
    manifest = dict(schema='icho2019-final-handoff-publication-v1', year=2019, source_sha256=SOURCE,
                    ready_source=str(B / 'READY-for-root-assembly-r2.json'), ready_sha256=READY_SHA,
                    freeze_source=str(B / 'final-code-freeze-r2.json'), freeze_sha256=FREEZE_SHA,
                    amendment_manifests=[dict(source=str(B / name), sha256=digest) for name, digest in PINS.items() if name not in ['READY-for-root-assembly-r2.json', 'final-code-freeze-r2.json']],
                    amended_inputs=actual_changes, original_input_files=197, unchanged_input_files=191,
                    frozen_Python_programs=69,
                    pages=[dict(page=row['page'], proof_sha256=row['proof_sha256'], layout_sha256=row['qa_sha256'], effective_plan_sha256=row['effective_plan_sha256'], overrides_sha256=row['overrides_sha256'], diagnostic_sha256=row['diagnostic_sha256']) for row in bindings])
    return dict(programs=list(dict.fromkeys(programs)), evidence=list(dict.fromkeys(evidence)), manifest=manifest,
                bindings=bindings, actual_changed_inputs=actual_changes, frozen_inputs=197,
                unchanged_inputs=191, frozen_Python_programs=69, ready_sha256=READY_SHA,
                _expected_overrides=expected)


def validate_handoff(engine_dir=None):
    """Validate the source handoff only; this does not approve a joined PDF."""
    result = _validate_handoff(engine_dir)
    result.pop('_expected_overrides')
    return result


def prepare(engine_dir, qa, *, pdf, root):
    """Validate exact live source evidence and the prospective public join."""
    root = Path(root).resolve()
    assert root == PUBLICATION_ROOT, ('2019 staging must use the isolated mutable publication worktree', root)
    result = validate_handoff(engine_dir)
    pdf = Path(pdf).resolve()
    assert pdf.name == 'IChO_2019_T_KO.pdf' and sha(pdf) == qa['sha256']
    assert qa.get('file', pdf.name) == pdf.name
    assert qa['schema'] == 'natural-source-native-joined-v1' and qa['status'] == 'READY'
    assert qa['source_sha256'] == SOURCE and qa['pages'] == 60 and qa['visual_review_required'] is False
    assert len(qa['page_audits']) == 60
    for page, binding in zip(qa['page_audits'], result['bindings']):
        for key in ['page', 'proof_sha256', 'qa_sha256', 'effective_plan_sha256', 'plan_sha256', 'overrides_sha256']:
            assert page[key] == binding[key], ('Join is not bound to the final 2019 handoff', binding['page'], key)
        if 'composer_sha256' in page:
            assert page['composer_sha256'] == binding['composer_sha256']
        for field, digest in [('proof_path', binding['proof_sha256']), ('qa_path', binding['qa_sha256']), ('effective_plan_path', binding['effective_plan_sha256']), ('plan_path', binding['plan_sha256']), ('overrides_path', binding['overrides_sha256'])]:
            path = Path(page[field])
            if not path.is_absolute():
                path = (root / path).resolve()
                assert path.is_relative_to(root)
            assert sha(path) == digest
            if field == 'qa_path':
                assert read(path)['composer_sha256'] == binding['composer_sha256']
    return result


def self_test():
    result = _validate_handoff()
    rejected = []
    for page in CHANGED_PAGES:
        bad = copy.deepcopy(read(B / f'page{page:02}.overrides.json'))
        bad['__unapproved_negative_probe__'] = 'source scope/formula/text may not change outside the exact amendment'
        try:
            _assert_override(page, result['_expected_overrides'][page], bad)
        except AssertionError:
            rejected.append(page)
        else:
            raise AssertionError(('Accepted a modified final override', page))
    assert rejected == CHANGED_PAGES
    return dict(status='PASS', scope='Actual final handoff/file hashes and six in-memory override reconstruction negatives; no joined publication was approved by this CLI.', pages=60,
                frozen_inputs=197, changed_override_pages=CHANGED_PAGES, unchanged_inputs=191,
                frozen_Python_programs=69, rejected_in_memory_override_mutations=rejected,
                programs=len(result['programs']), JSON_evidence=len(result['evidence']), program_sha256=sha(__file__))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--qa', type=Path)
    parser.add_argument('--pdf', type=Path)
    parser.add_argument('--root', type=Path, default=PUBLICATION_ROOT)
    args = parser.parse_args()
    assert bool(args.qa) == bool(args.pdf), '--qa and --pdf must be supplied together'
    if args.self_test:
        report = self_test()
    else:
        result = validate_handoff()
        report = dict(status='PASS', pages=len(result['bindings']), unchanged_inputs=result['unchanged_inputs'], changed_override_pages=CHANGED_PAGES, program_sha256=sha(__file__))
    if args.qa:
        joined = prepare(B / 'engine', read(args.qa), pdf=args.pdf, root=args.root)
        report.update(joined_publication_bound=True, joined_pdf_sha256=sha(args.pdf), joined_qa_sha256=sha(args.qa), programs=len(joined['programs']), JSON_evidence=len(joined['evidence']))
    print(json.dumps(report))
