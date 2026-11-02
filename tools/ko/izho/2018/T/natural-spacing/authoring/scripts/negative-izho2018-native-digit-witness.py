from pathlib import Path
import sys,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import reposition_inline
from pdf_memory_gate import page_worker
# Import only the read-only cropped renderer, without running its CLI loop.
source=Path('D:/CodexBuilds/diagnose-izho2018-native-digit-phase.py').read_text('utf8');prefix=source[:source.index('for number in map(int,sys.argv[1:]):')]
namespace={'__name__':'native_digit_crop_helper'};exec(compile(prefix,'native-digit-crop-helper','exec'),namespace)
crop=namespace['crop_rgb'];np=namespace['np'];f=namespace['f']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n in map(int,sys.argv[1:]):
 with page_worker():
  folder=B/f'natural/2018/T';out=folder/f'page{n:02}-native-digit-phase';path=out/'witness.json';w=json.loads(path.read_text('utf8'));target=folder/f'page{n:02}.pdf'
  assert sha(target)==w['proof_sha256'];g=w['checks'][0]['actual_destination']
  raw,q=reposition_inline(target,1,erased_glyphs=[g]);bad=out/'negative-one-actual-native-CID-omitted.pdf';bad.write_bytes(raw)
  assert q['passed']
  tests=[];r=list(f.Rect(g['bbox'])+(-.5,-.5,.5,.5))
  for renderer in ['MuPDF','Poppler']:
   a=crop(out/'original-native-CID-only.pdf',r,4,renderer,out/f'negative-reference-{renderer}')
   b=crop(bad,r,4,renderer,out/f'negative-final-{renderer}')
   missing=int(((a.min(axis=2)<32)&(b.min(axis=2)>=220)).sum());assert missing>0
   tests.append(dict(renderer=renderer,scale=4,omitted_original_source_character=g['c'],omitted_original_source_GID=g['trace_gid'],reference_dark_pixels_missing=missing,rejected=True))
  w['negative_actual_original_CID_omission']=dict(mutant_sha256=sha(bad),native_erasure_qa=q,checks=tests,passed=True)
  w['passed']=w['passed']and all(t['rejected']for t in tests)
  path.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n','utf8');assert sha(target)==w['proof_sha256']
  print('ACTUAL_NATIVE_CID_OMISSION_NEGATIVE_REJECTED',n,tests,'delivered_proof_unmodified',True,flush=True)
