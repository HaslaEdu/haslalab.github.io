import copy
import hashlib
import json
from pathlib import Path
from prose_decoration_publication import validate_contact

BASE = Path(__file__).resolve().parents[1]
folder = BASE / 'proofs/icho/2019-final'
engine = BASE / 'historical/icho/composer-2019'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
ready_path=engine/'READY-for-root-assembly-r2.json'
assert sha(ready_path)=='e7ac28136d66573a9674322876b08458ef0165dcf0e3aab2a682cf48665b6737'
ready=json.loads(ready_path.read_text('utf8'))
assert ready['status']=='READY_FOR_ROOT_ASSEMBLY' and len(ready['page_artifacts'])==60
for page in ready['page_artifacts']:
    for pin in page['artifacts']:
        assert sha(pin['path'])==pin['sha256'] and Path(pin['path']).stat().st_size==pin['bytes']
count = 0
pages = []
for path in sorted(folder.glob('page*.layout.json')):
    diagnostic = engine/(path.name[:6]+'.diagnostic.json')
    assert diagnostic.exists()
    q = json.loads(path.read_text(encoding='utf-8-sig'))
    d = json.loads(diagnostic.read_text(encoding='utf-8-sig'))
    assert d['passed'] and d['output_sha256'] == q['output_sha256'] == sha(path.with_suffix('').with_suffix('.pdf'))
    for c in q.get('intentional_prose_decoration_contacts', []):
        validate_contact(q, c)
        count += 1
    pages.append(dict(page=q['page'], layout_sha256=sha(path)))
q0 = json.loads((folder/'page08.layout.json').read_text(encoding='utf-8-sig'))
def reject(name, mutate):
    q = copy.deepcopy(q0)
    c = q['intentional_prose_decoration_contacts'][0]
    mutate(q, c)
    try:
        validate_contact(q, c)
    except (AssertionError, KeyError, TypeError):
        return dict(name=name, rejected=True)
    raise AssertionError('Accepted invalid underline: '+name)

cases = [
    ('affine flag downgrade', lambda q,c: c.update(x_translation_only=True)),
    ('affine flag downgrade with protected ink contact', lambda q,c: (c.update(x_translation_only=True),q.update(actual_prose_underline_protected_native_ink_contact_pixels=1),q['actual_prose_underline_coverage_and_style_audit'].update(protected_native_ink_contact_pixels=1))),
    ('unreviewed source', lambda q,c: q.update(source_sha256='0'*64)),
    ('stale proof binding', lambda q,c: q.update(output_sha256='0'*64)),
    ('unbound source path', lambda q,c: c.update(source_path_index=-1)),
    ('changed source paint', lambda q,c: q['reviewed_moving_prose_decoration_paths'][0]['vector_path'].update(paint_operator='S')),
    ('moved underline baseline', lambda q,c: q['prose_vector_decorations'][0]['target_rect'].__setitem__(1,q['prose_vector_decorations'][0]['target_rect'][1]+.01)),
    ('actual underline thickness changed', lambda q,c: q['actual_prose_underline_coverage_and_style_audit']['underline_rows'][0]['actual_underline_bbox'].__setitem__(3,q['actual_prose_underline_coverage_and_style_audit']['underline_rows'][0]['actual_underline_bbox'][3]+.01)),
    ('partial-word underline despite reported PASS', lambda q,c: q['actual_prose_underline_coverage_and_style_audit']['underline_rows'][0]['actual_emphasized_glyph_curve_union_bbox'].__setitem__(0,200)),
    ('protected native ink contact', lambda q,c: q.update(actual_prose_underline_protected_native_ink_contact_pixels=1)),
    ('full font identity not verified', lambda q,c: q['actual_prose_underline_coverage_and_style_audit']['underline_rows'][0].update(all_Korean_used_glyph_GIDs_outlines_and_hmtx_match_pinned_full_font=False)),
    ('invalid nonpositive scale', lambda q,c: c.update(prose_decoration_x_scale=0)),
    ('missing actual curve measurements', lambda q,c: q.pop('actual_prose_underline_coverage_and_style_audit')),
    ('widened coverage tolerance', lambda q,c: q['actual_prose_underline_coverage_and_style_audit'].update(underline_coverage_tolerance_pt=.1)),
]
negative = [reject(name, mutate) for name, mutate in cases]
report = dict(status='PASS', validator_sha256=sha(Path(__file__).with_name('prose_decoration_publication.py')),
              ready_sha256=sha(ready_path),
              assembler_sha256=sha(Path(__file__).with_name('assemble_natural.py')),
              checked_contacts=count, current_pages=pages, negative_cases=negative,
              scope='Static publication validator regression against actual final layout evidence; does not replace PDF-based production geometry audits.')
out=BASE/'engine/publication-transition/prose-decoration-validator-regression.json'
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='PASS', contacts=count, pages=len(pages), rejected=len(negative), report=str(out), sha256=sha(out))))
