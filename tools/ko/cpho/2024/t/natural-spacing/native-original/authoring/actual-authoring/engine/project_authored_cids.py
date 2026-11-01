"""Project only the approved authored-space glyph positions onto the old PDF.
The corrected shadow composer is a layout oracle. All original Batang CIDs,
GIDs, programs, paint and baselines are retained; no fonts/text are reinserted.
"""
from pathlib import Path
import json,shutil,hashlib
import pymupdf as fitz
import build_page11 as cfg
from pdf_native_inline_reposition import _traces,reposition_inline
from pdf_memory_gate import page_worker
HERE=cfg.HERE;OLD=cfg.build.BUILD/'natural-layout/pages/CPhO_2023_p11_KO_natural.pdf';TARGET=cfg.build.OUT/'CPhO_2023_p11_KO_natural.pdf'
def run():
 candidate=HERE/'full-page-shadow-candidate.pdf';shutil.copy2(TARGET,candidate)
 cq=json.loads(TARGET.with_suffix('.qa.json').read_text('utf8'));(HERE/'full-page-shadow-candidate.qa.json').write_text(json.dumps(cq,ensure_ascii=False,indent=2),'utf8')
 def glyphs(path):
  with fitz.open(path)as d:return sorted([g for g in _traces(d[0])if g['font']=='Batang'and g['c'].strip()and abs(g['origin'][1]-342.889984)<.02 and g['origin'][0]>350],key=lambda g:g['origin'][0])
 old,new=glyphs(OLD),glyphs(candidate);assert ''.join(g['c']for g in old)==''.join(g['c']for g in new)=='는고정다음을구하라'
 shifts=[];witness=[]
 for a,b in zip(old,new):
  assert all(a[k]==b[k]for k in('c','font','trace_gid','size','render_mode','color'))and a['origin'][1]==b['origin'][1]
  dx=b['origin'][0]-a['origin'][0]
  if abs(dx)>.001:shifts.append(dict(glyphs=[{k:a[k]for k in('c','font','size','origin')}],dx=dx))
  witness.append(dict(c=a['c'],font=a['font'],gid=a['trace_gid'],size=a['size'],old=a['origin'],expected=b['origin'],dx=dx))
 raw,proof=reposition_inline(OLD,1,shifts=shifts);TARGET.write_bytes(raw)
 report=json.loads(OLD.with_suffix('.qa.json').read_text('utf8'))
 report['new_batang_placements']=[p for p in report['new_batang_placements']if not(abs(p['point'][1]-342.889984)<.02 and p['point'][0]>350)]+[p for p in cq['new_batang_placements']if abs(p['point'][1]-342.889984)<.02 and p['point'][0]>350]
 report['new_batang_runs']=len(report['new_batang_placements'])
 report['lines']=[next(r for r in cq['lines']if abs(r['baseline']-342.889984)<.02)if abs(r['baseline']-342.889984)<.02 else r for r in report['lines']]
 report.update(output_sha256=hashlib.sha256(raw).hexdigest(),authored_spacing_projection=dict(source=str(OLD),source_sha256=hashlib.sha256(OLD.read_bytes()).hexdigest(),oracle=str(candidate),oracle_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),glyphs=witness,original_encoded_CID_move_qa=proof,no_new_font_or_glyphs=True,all_other_prose_and_math_positions_preserved=True))
 TARGET.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
 (HERE/'projection-qa.json').write_text(json.dumps(report['authored_spacing_projection'],ensure_ascii=False,indent=2),'utf8')
 print(json.dumps(dict(sha256=report['output_sha256'],moved_native_Batang_CIDs=len(shifts),passed=proof['passed'])),flush=True)
 return TARGET
if __name__=='__main__':
 with page_worker():run()
