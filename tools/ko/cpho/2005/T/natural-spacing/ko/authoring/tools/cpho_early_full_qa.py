"""Independent actual-ink, source-program and geometry audits for early T PDFs."""
from pathlib import Path
import json,time,os
import cpho_early_natural as a
a.install()
import cpho_natural_full_qa as full
full.ROOT=a.BASE/'authoring-root'
from pdf_new_prose_native_text_overlap import audit as text_overlap
from cpho_natural_spacing_qa import original_native_glyphs
from pdf_memory_gate import page_worker

def audit(year,language,number):
 report=full.audit(year,language,number)
 path=Path(report['output']);j=json.loads(path.with_suffix('.qa.json').read_text('utf8'))
 overlap=text_overlap(path,native_glyphs=original_native_glyphs(year,language,number),shifts=j['native_shifts'])
 dest=path.with_suffix('.prose-native-text-overlap.json');dest.write_text(json.dumps(overlap,ensure_ascii=False,indent=2),'utf8')
 report['prose_native_text_overlap']=dict(path=str(dest),sha256=a.core.sha(dest),dark_pixels=overlap['dark_prose_pixels_over_native_text'],passed=overlap['passed'])
 from cpho_early_heading_qa import audit as heading_audit
 heading=heading_audit(year,language,number,path,j)
 report['source_numerical_prose_and_whole_heading_alignment']=heading
 report['passed']=report['passed']and overlap['passed']and heading['passed']
 t=path.with_suffix('.audit.tmp');t.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');os.replace(t,path.with_suffix('.audit.json'))
 print('FINAL_QA',year,language,number,report['passed'],'overprint',overlap['dark_prose_pixels_over_native_text'],flush=True)
 return report
if __name__=='__main__':
 import sys,traceback
 targets=json.loads(sys.argv[1]);out=[]
 for y,l,n in targets:
  print('QA',y,l,n,flush=True)
  try:
   with page_worker():q=audit(y,l,n)
   out.append(dict(year=y,language=l,page=n,passed=q['passed']))
  except Exception as e:out.append(dict(year=y,language=l,page=n,passed=False,error=str(e),trace=traceback.format_exc()));print('QA_ERROR',y,l,n,str(e),flush=True)
  d=a.BASE/'full-qa-batch-status.json';t=d.with_suffix('.tmp');t.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8');os.replace(t,d);time.sleep(.6)
