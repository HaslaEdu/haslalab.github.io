"""Positive source motion and negative prose-vs-math guard regressions."""
from pathlib import Path
import copy,hashlib,json
import natural_plan_compose_icho2019 as c
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;layout=json.loads((g.PROOFS/'page43.layout.json').read_text('utf8'));assert layout['source_sha256']==g.SOURCE_SHA
refs=layout['reviewed_moving_prose_decoration_paths'];shifts=layout['native_shifts'];results=[]
def call(changed):return c.motion.reposition_inline(g.SOURCE,43,shifts=shifts,reviewed_moving_prose_decoration_paths=changed,reviewed_stationary_vector_paths=layout['reviewed_stationary_vector_paths'])
raw,qa=call(refs);assert qa['passed']and qa['native_vector_path_bytes_preserved'];results.append(dict(case='exact-source-positive-motion',passed=True,original_native_GID_font_size_y_and_path_bytes_preserved=True))
def reject(name,mutate,expected):
 changed=copy.deepcopy(refs);mutate(changed)
 try:call(changed)
 except ValueError as e:
  assert expected in str(e),(name,str(e));results.append(dict(case=name,passed=True,rejection=str(e)))
 else:raise AssertionError('Source guard accepted invalid '+name)
reject('wrong-original-source-SHA',lambda r:r[0].update(source_sha256='0'*64),'exact source hash')
reject('wrong-original-English-GID',lambda r:r[0]['source_prose_glyphs'][0].update(gid=r[0]['source_prose_glyphs'][0]['gid']+1),'exact source prose GID')
reject('wrong-original-path-bounds',lambda r:r[0]['vector_path']['rect'].__setitem__(2,r[0]['vector_path']['rect'][2]+.01),'exact native path')
reject('wrong-original-English-baseline',lambda r:r[0].update(source_baseline=r[0]['source_baseline']+.5),'geometry/baseline')
native=[v for s in shifts for v in s['glyphs']if v['c']in'Ve'and 500<v['origin'][1]<510];assert native
reject('mathematical-glyphs-cannot-authorize-prose-decoration',lambda r:r[0].update(source_prose_glyphs=native),'actual English prose')
try:c.motion.reposition_inline(g.SOURCE,43,_outline_reader=object())
except ValueError as e:assert 'read-only'in str(e);results.append(dict(case='custom-outline-reader-cannot-mutate-output',passed=True,rejection=str(e)))
else:raise AssertionError('Read-only inspector was accepted in native write mode')
report=dict(source_sha256=g.SOURCE_SHA,layout_proof_sha256=layout['output_sha256'],program_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),native_motion_sha256=hashlib.sha256(Path(c.motion.__file__).read_bytes()).hexdigest(),tests=results,all_passed=True,writes='Only this JSON report; original source/frozen/other-year PDFs unchanged.')
(B/'source-prose-transform-guard-regressions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(report,ensure_ascii=False),flush=True)
