"""Run original strict page QA and compare the narrow authored-space repair."""
from pathlib import Path
import json,subprocess,sys,time,hashlib
import numpy as np,pymupdf as fitz
from PIL import Image
import build_page11 as cfg
import cpho_2023_natural_qa as qa
from pdf_memory_gate import page_worker
qa.OUT=cfg.build.OUT;qa.ROOT=cfg.ROOT
HERE=cfg.HERE
OLD=cfg.build.BUILD/'natural-layout/pages/CPhO_2023_p11_KO_natural.pdf'
NEW=cfg.build.OUT/'CPhO_2023_p11_KO_natural.pdf'

def render(path,target):
 code='import pymupdf as f,sys;d=f.open(sys.argv[1]);d[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False).save(sys.argv[2])'
 subprocess.run([sys.executable,'-c',code,str(path),str(target)],check=True)
 with Image.open(target)as im:return np.asarray(im.convert('RGB')).copy()
def run():
 with page_worker():strict=qa.audit(11,'ko')
 time.sleep(.6)
 with page_worker():before=render(OLD,HERE/'old-page11-4x.png')
 time.sleep(.6)
 with page_worker():after=render(NEW,HERE/'new-page11-4x.png')
 time.sleep(.6)
 diff=np.any(before!=after,axis=2);yy,xx=np.nonzero(diff);bbox=[float(xx.min()/4),float(yy.min()/4),float((xx.max()+1)/4),float((yy.max()+1)/4)]if len(xx)else None
 band=np.zeros(diff.shape,bool);band[int(332*4):int(349*4),:]=True
 outside=int((diff&~band).sum())
 q=json.loads(NEW.with_suffix('.qa.json').read_text('utf8'))
 row=next(r for r in q['lines']if abs(r['baseline']-342.889984)<.02)
 texts=[p['text']for p in q['new_batang_placements']if abs(p['point'][1]-342.889984)<.02]
 assert all(t in texts for t in('는','고정','다음을','구하라')),texts
 assert not any(t in texts for t in('는고정','다음을구하라')),texts
 report=dict(passed=bool(strict['passed']and not outside),old_sha256=hashlib.sha256(OLD.read_bytes()).hexdigest(),new_sha256=hashlib.sha256(NEW.read_bytes()).hexdigest(),strict_page_audit_passed=strict['passed'],actual_changed_bbox=bbox,changed_pixels=int(diff.sum()),changed_pixels_outside_affected_baseline_band=outside,allowed_band_y=[332,349],expected_new_words_present=True,affected_line=row,recorded_batang_words=texts)
 (HERE/'narrow-change-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
 print(json.dumps(report,ensure_ascii=False),flush=True)
 return report
if __name__=='__main__':run()
