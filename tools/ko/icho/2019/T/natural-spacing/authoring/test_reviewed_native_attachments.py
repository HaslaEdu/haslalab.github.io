"""Fail-closed source-bound regressions for original highlight/underline scopes."""
from pathlib import Path
import copy,hashlib,json,time
import natural_plan_compose_icho2019 as c
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;rows=[]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def config(n):return json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'))
def layout(n,q):return c.prepare_layout(g.PLANS/f'page{n:02}.ko.json',q)
def rejects(n,q,label,expected):
    try:layout(n,q)
    except ValueError as exc:
        assert expected in str(exc),(label,str(exc));rows.append(dict(case=label,passed=True,rejection=str(exc)));return
    raise AssertionError('Unsafe source scope unexpectedly accepted: '+label)
q=config(2);out=layout(2,q);assert len(out['reviewed_native_vector_attachments'])==1;rows.append(dict(case='original-yellow-highlight-positive',passed=True))
v=copy.deepcopy(q);v['__layout_scope__']['reviewed_native_vector_attachments'][0]['glyphs'][0]['gid']+=1;rejects(2,v,'wrong-source-GID','exact source glyph')
v=copy.deepcopy(q);v['__layout_scope__']['reviewed_native_vector_attachments'][0]['fill']=[0.,1.,0.];rejects(2,v,'wrong-source-colour','exact path/fill')
v=copy.deepcopy(q);v['__layout_scope__']['reviewed_native_vector_attachments'][0]['affects_typographic_bounds']=False;rejects(2,v,'highlight-cannot-hide-width','Only a source-reviewed prose underline')
q=config(13);out=layout(13,q);ref=q['__layout_scope__']['reviewed_native_vector_attachments'][0];line=next(v for v in out['line_reports']if abs(v['baseline']-ref['source_baseline'])<.001);native=next(v for v in line['tokens']if v['kind']=='native'and v['text']=='1')
source_width=ref['glyphs'][0]['bbox'][2]-ref['glyphs'][0]['bbox'][0];assert abs(native['width']-source_width)<.001
assert native['width']<10 and ref['vector_path']['rect'][2]-ref['vector_path']['rect'][0]>100
assert any(v.get('original_underline_covers_full_korean_phrase')for v in out['prose_vector_decorations'])
assert all(0<=v['new_gap']<=v['ordinary_space']+.001 for v in line['gaps'])
rows.append(dict(case='native-numeral-underline-positive-no-English-width-reservation',passed=True,native_glyph_width_pt=native['width'],original_underline_width_pt=ref['vector_path']['rect'][2]-ref['vector_path']['rect'][0],normal_gaps=line['gaps']))
v=copy.deepcopy(q);v['__layout_scope__']['reviewed_native_vector_attachments'][0]['source_baseline']+=1;rejects(13,v,'wrong-original-baseline','geometry/style guard')
v=copy.deepcopy(q);v['__layout_scope__']['reviewed_native_vector_attachments'][0]['target_prose_slot_ids']=['missing-source-bound-slot'];rejects(13,v,'missing-target-phrase','exact source baseline')
v=copy.deepcopy(q);v['__layout_scope__']['reviewed_native_vector_attachments'][0]['vector_path']['rect'][0]-=1;rejects(13,v,'changed-source-path','exact path/fill')
g.assert_protected_2024()
report=dict(passed=True,source_sha256=g.SOURCE_SHA,composer_sha256=sha(B/'natural_plan_compose_icho2019.py'),test_code_sha256=sha(__file__),cases=rows,source_and_frozen_2024_unchanged=True,tests_write_no_PDF=True)
(B/'reviewed-native-attachments-regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(report,ensure_ascii=False),flush=True)
