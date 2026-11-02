"""Final audits using the frozen builder plus the exact source-stroke QA fix.
Owns a memory gate per check, with fair yields; do not wrap this in another gate.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,time,os,traceback
import pymupdf as fitz
import cpho_early_natural as a
a.install()
import cpho_natural_full_qa as full
full.ROOT=a.BASE/'authoring-root'
import pdf_native_geometry_stroke_motion as stroke
full.geometry_audit=stroke.audit
from pdf_new_prose_native_text_overlap import audit as text_overlap
from cpho_natural_spacing_qa import original_native_glyphs
from cpho_early_heading_qa import audit as heading_audit
from pdf_native_inline_reposition import _traces
from pdf_memory_gate import page_worker

def style_audit(path,journal):
 expected=defaultdict(list)
 for p in journal['new_batang_placements']:
  for c in p['text']:
   if c.strip():expected[c].append((p['style']['size'],p['point'][1],p['style']['render_mode']))
 with fitz.open(path)as d:rows=[g for g in _traces(d[0])if g['font']=='Batang'and g['c'].strip()and g['trace_gid']>=0]
 errors=[];maxsize=maxy=0.
 for g in rows:
  choices=expected.get(g['c'],[])
  if not choices:errors.append(dict(reason='Unexpected new Hangul',glyph=g));continue
  p=min(choices,key=lambda v:abs(v[1]-g['origin'][1])+abs(v[0]-g['size']));choices.remove(p)
  ds,dy=abs(p[0]-g['size']),abs(p[1]-g['origin'][1]);maxsize=max(maxsize,ds);maxy=max(maxy,dy)
  if ds>.0001 or dy>.002 or p[2]!=g['render_mode']:errors.append(dict(reason='Original size/baseline/paint mismatch',glyph=g,expected=p))
 if any(expected.values()):errors.append(dict(reason='Missing requested new Hangul',characters={k:v for k,v in expected.items()if v}))
 return dict(passed=not errors,translation_style_violations=errors,translation_size_max_delta_pt=maxsize,translation_baseline_max_delta_pt=maxy,checked_new_Batang_glyphs=len(rows),native_style_preserved_by_exact_encoded_CID_mover=journal['native_move_qa']['passed'])

def audit(year,language,number):
 with page_worker():report=full.audit(year,language,number)
 time.sleep(.6)
 path=Path(report['output']);j=json.loads(path.with_suffix('.qa.json').read_text('utf8'))
 with page_worker():overlap=text_overlap(path,native_glyphs=original_native_glyphs(year,language,number),shifts=j['native_shifts'])
 time.sleep(.6)
 dest=path.with_suffix('.prose-native-text-overlap.json');dest.write_text(json.dumps(overlap,ensure_ascii=False,indent=2),'utf8')
 heading=heading_audit(year,language,number,path,j)
 if heading['source_numeric_font_resources']!=len(heading['digits'])or not heading['source_numeric_font_resources']:raise ValueError('Actual source numeric font-program witness count is incomplete')
 style=style_audit(path,j)
 report.update(prose_native_text_overlap=dict(path=str(dest),sha256=a.core.sha(dest),dark_pixels=overlap['dark_prose_pixels_over_native_text'],passed=overlap['passed']),
  source_numerical_prose_and_whole_heading_alignment=heading,independent_new_prose_style=style,
  validation_engine=dict(frozen_build_manifest=str(a.BASE/'engine-manifest.json'),frozen_build_manifest_sha256=a.core.sha(a.BASE/'engine-manifest.json'),
   driver=str(Path(__file__)),driver_sha256=a.core.sha(__file__),source_stroke_QA_adapter=str(Path(stroke.__file__)),source_stroke_QA_adapter_sha256=a.core.sha(stroke.__file__),PDF_mutations=False))
 report['passed']=report['passed']and overlap['passed']and heading['passed']and style['passed']
 t=path.with_suffix('.audit.tmp');t.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');os.replace(t,path.with_suffix('.audit.json'))
 print('FINAL_QA',year,language,number,report['passed'],'overprint',overlap['dark_prose_pixels_over_native_text'],'style',style['passed'],flush=True)
 return report

def run():
 log=[]
 for y in(2005,2013):
  for l in('ko','en'):
   for n in(1,2,3):
    print('AUDIT',y,l,n,'PID',os.getpid(),flush=True)
    try:r=audit(y,l,n);log.append(dict(year=y,language=l,page=n,passed=r['passed']))
    except Exception as e:log.append(dict(year=y,language=l,page=n,passed=False,error=str(e),trace=traceback.format_exc()));print('QA_ERROR',y,l,n,str(e),flush=True)
    p=a.BASE/'final-validation-status.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(log,ensure_ascii=False,indent=2),'utf8');os.replace(tmp,p);time.sleep(.6)
 print('VALIDATION DONE',sum(r['passed']for r in log),len(log),flush=True)
 return log
if __name__=='__main__':run()
