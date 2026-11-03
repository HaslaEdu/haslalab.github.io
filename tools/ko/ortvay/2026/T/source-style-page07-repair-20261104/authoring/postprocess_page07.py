"""DRAFT. Exact four-stream postprocessor; production requires a future root GO.

No original compositor, reference, profile, QA or output is ever rewritten.
Only a new directory may receive the copied-and-incrementally-updated PDF.
"""
from pathlib import Path
from decimal import Decimal
import argparse, copy, hashlib, json, re, shutil, sys
sys.dont_write_bytecode = True
R4 = Path(__file__).resolve().parents[2]
HOME = R4 / 'page-repairs/2026-page07-postprocess-v1-20261104'
MIXED = R4 / 'mixed-year-bridges/2026-postprocess-v1-20261104'
QA = R4 / 'qa-amendments/full-ctm-rotation-v1-20261103'
SPEC = R4 / 'experiments/final-failures/root-2026p7-review-20261104/NUMERIC-REPAIR-SPEC.json'
SPEC_SHA = 'b552b2f0cc95c1f0e8aae8bfdfc34fddae4037ce88703eca33f7fe61c914b24c'
NAMES = ('postprocess_page07.py', 'audit_page07_repair.py', 'continue_and_bridge_2026.py')
GO_STATUS = 'ROOT_GO_2026_PAGE07_EXACT_ROW_POSTPROCESS'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def read(path):
    return json.loads(Path(path).read_bytes().decode('utf-8-sig'))


def checked(value):
    path = Path(value['path']).resolve()
    assert path.is_file() and sha(path) == value['sha256'], ('Stale pinned input', path)
    return path


def write_new(path, value):
    path = Path(path).resolve()
    assert path.is_relative_to(HOME) or path.is_relative_to(MIXED)
    assert not path.exists(), ('No existing artifact may be overwritten', path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def preserved(freeze):
    ledger = read(checked(freeze['preserved_input_ledger']))
    assert ledger['production_authorized'] is False  # historical preparation, never a GO
    for value in ledger['preserved_inputs']: checked(value)


def authorization():
    assert Path(__file__).resolve() == HOME / NAMES[0], 'Run only a future frozen copy, never this proposal'
    freeze_path, go_path = HOME/'REPAIR-CODE-INPUT-FROZEN.json', HOME/'ROOT-GO.json'
    freeze, go = read(freeze_path), read(go_path)
    assert freeze['schema'] == 'ortvay-2026-page07-repair-code-input-freeze-v1'
    assert freeze['status'] == 'PAGE07_REPAIR_CODE_INPUT_FROZEN_FOR_ROOT_REVIEW'
    assert go['status'] == GO_STATUS and go['repair_code_input_freeze'] == pin(freeze_path)
    assert go['production_repair_authorized'] is True
    assert go['existing_source_or_runtime_programs_may_change'] is False
    assert go['original_proofs_or_global_lifecycle_may_change'] is False
    assert go['year'] == 2026 and go['page'] == 7
    assert go['permitted_output_directory'] == str(HOME/'page07')
    assert freeze['numeric_spec'] == go['numeric_spec'] == dict(path=str(SPEC), sha256=SPEC_SHA)
    assert sha(SPEC) == SPEC_SHA
    programs = freeze['additional_runtime_files']
    assert len(programs) == 3 and {Path(p['path']).resolve() for p in programs} == {HOME/n for n in NAMES}
    for value in programs: checked(value)
    preserved(freeze)
    return freeze, go, read(SPEC)


def expected_body(previous, spec):
    assert previous['page'] == spec['page'] == 7 and spec['year'] == 2026
    assert spec['dx'] == 3.3125 and spec['production_repair_authorized'] is False
    result = copy.deepcopy(previous)
    rows = [p for p in result['placements'] if abs(p['baseline']-spec['selected_baseline']) < .001]
    assert rows == [spec['old_logical_placement']]
    row = rows[0]
    for field in ('point', 'draw_point'):
        if field in row: row[field][0] += spec['dx']
    lines = [v for v in result['line_reports'] if abs(v['baseline']-spec['selected_baseline']) < .001]
    assert len(lines) == 1 and all(t['kind'] == 'prose' for t in lines[0]['tokens'])
    line = lines[0]; line['left'] += spec['dx']; line['right'] += spec['dx']
    for token in line['tokens']: token['new_x'] += spec['dx']
    assert spec['source_column'][0] <= row['point'][0]
    assert row['point'][0]+row['advance'] <= spec['source_column'][1]
    return result


def translated_stream(data, record, dx):
    assert dx == 3.3125 and hashlib.sha256(data).hexdigest() == record['raw_sha256']
    assert record['font_alias'] == 'KO_Natural_serif' and record['horizontal']
    assert record['cm'] == [1., 0., 0., 1., 0., 0.]
    assert record['text_matrix'][:4] == [1., 0., 0., 1.]
    number = rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
    pattern = re.compile(rb'(?<!\S)' + rb'\s+'.join([b'('+number+b')']*6) + rb'\s+Tm\b')
    found = list(pattern.finditer(data)); assert len(found) == 1
    match = found[0]
    assert max(abs(float(match.group(i))-record['text_matrix'][i-1]) for i in range(1,7)) <= 1e-9
    # Only the fifth numeric operand (e) is rewritten. Every other byte stays.
    start, end = match.span(5)
    replacement = format(Decimal(match.group(5).decode())+Decimal('3.3125'), '.12f').encode()
    return data[:start]+replacement+data[end:]


def produce():
    freeze, go, spec = authorization()
    source, body_path = checked(spec['precontact_proof']), checked(spec['precontact_layout'])
    original_body = read(body_path); body = expected_body(original_body, spec)
    output = HOME/'page07'; assert not output.exists(); output.mkdir()
    # Snapshot the new three programs separately from the old failed runtime.
    files = {}
    for value in freeze['additional_runtime_files']:
        path = checked(value); retained = output/'runtime-sources/additional'/path.name
        retained.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, retained)
        assert sha(retained) == value['sha256']
        files[str(path)] = dict(sha256=value['sha256'], retained_copy=str(retained))
    runtime = output/'repair-runtime-snapshot.json'
    write_new(runtime, dict(schema='ortvay-page07-additional-runtime-snapshot-v1', files=files,
        numeric_spec=pin(SPEC), repair_code_input_freeze=pin(HOME/'REPAIR-CODE-INPUT-FROZEN.json'),
        root_GO=pin(HOME/'ROOT-GO.json'), base_profile=freeze['base_profile'], additional_runtime_count=3,
        base_original_runtime_count=46, base46_is_provenance_not_a_claim_of_old_only_execution=True))
    sys.path.insert(0, str(QA))
    import pymupdf as fitz
    from amended_actual_paint import streams, glyphs
    with fitz.open(source) as old:
        records = streams(old[0]); actual = glyphs(old[0], True, include_spaces=True)
        lower = [g for g in actual if abs(g['origin'][1]-spec['selected_baseline']) < .001]
        assert ''.join(chr(g['cp']) for g in lower) == '논하라.' and [g['gid'] for g in lower] == [9170,18350,10706,85]
        assert all(g['size']==spec['source_size_pt'] and g['opacity']==1. for g in lower)
        chosen = [s for s in records if abs(s['actual_baseline']-spec['selected_baseline']) < .001]
        assert len(chosen) == len(lower) == 4
        assert sorted(s['xref']for s in chosen)==[317,318,319,320]
        assert sorted(s['actual_first_origin'][0] for s in chosen) == sorted(g['origin'][0] for g in lower)
        for record in chosen:
            # Parsed Tf operand is 11.9552; actual MuPDF size is
            # 11.9552001953125. Source stream bytes/Tf stay unchanged.
            assert sum(len(t)//2 for t in record['tj_tokens'] if isinstance(t,bytes)) == 1
        changes = {s['xref']: translated_stream(s['data'],s,spec['dx']) for s in chosen}
    target = output/'page07.pdf'; shutil.copyfile(source, target)
    with fitz.open(target) as new:
        for xref, data in changes.items(): new.update_stream(xref, data, compress=False)
        assert new.can_save_incrementally(); new.saveIncr()
    assert target.read_bytes().startswith(source.read_bytes()), 'Old complete file bytes must remain an exact prefix'
    body['output_sha256'] = sha(target)
    body['r4_page07_exact_row_postprocess'] = dict(schema='ortvay-page07-exact-row-postprocess-v1',
        numeric_spec=pin(SPEC), repair_code_input_freeze=pin(HOME/'REPAIR-CODE-INPUT-FROZEN.json'),
        root_GO=pin(HOME/'ROOT-GO.json'), postprocessor=pin(__file__), repair_runtime_snapshot=pin(runtime),
        base_failed_proof=pin(source), base_failed_layout=pin(body_path),
        slot_id=spec['selected_slot_id'], baseline=spec['selected_baseline'], point_size=spec['source_size_pt'],
        dx=spec['dx'], selected_stream_xrefs=sorted(changes), original_composer_is_base_provenance=True,
        inherited_QA_claims_require_fresh_independent_revalidation=True)
    write_new(output/'page07.authoring-draft.json', body)
    write_new(output/'postprocess-receipt.json', dict(schema='ortvay-page07-postprocess-receipt-v1',
        status='PDF_CREATED_IN_NEW_DIRECTORY_INDEPENDENT_AUDIT_PENDING', base_failed_proof=pin(source),
        base_failed_layout=pin(body_path), proof=pin(target), draft_layout=pin(output/'page07.authoring-draft.json'),
        numeric_spec=pin(SPEC), changed_streams=[dict(xref=s['xref'],before_sha256=s['raw_sha256'],
            after_sha256=hashlib.sha256(changes[s['xref']]).hexdigest(), before_text_matrix=s['text_matrix'], original_Tf_operand=s['size']) for s in chosen],
        original_file_prefix_exact=True, repair_runtime_snapshot=pin(runtime)))
    preserved(freeze)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['produce'])
    parser.parse_args();produce()
