"""Replace one reviewed page; preserve all other proofs and the EN edition."""
from pathlib import Path
import json,hashlib,subprocess,sys,time,os,copy,shutil
import pikepdf,pymupdf as fitz
import numpy as np
from PIL import Image
import build_page11 as cfg
from pdf_memory_gate import page_worker
HERE=cfg.HERE;OLDROOT=cfg.build.BUILD/'natural-layout';OLD=OLDROOT/'editions/CPhO_2023_Combined_KO.pdf';NEW=HERE/'pages/CPhO_2023_p11_KO_natural.pdf'
TARGET=HERE/'editions/CPhO_2023_Combined_KO.pdf'
POPPLER='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def proof(number):return NEW if number==11 else OLDROOT/f'pages/CPhO_2023_p{number}_KO_natural.pdf'
def fresh_hash(path,page):
 code='import pymupdf as f,sys,hashlib,json;d=f.open(sys.argv[1]);p=d[int(sys.argv[2])-1].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);print(json.dumps(dict(width=p.width,height=p.height,sha256=hashlib.sha256(p.samples).hexdigest())))'
 return json.loads(subprocess.check_output([sys.executable,'-c',code,str(path),str(page)],encoding='utf8'))
def pp(path,page,prefix):
 subprocess.run([POPPLER,'-f',str(page),'-l',str(page),'-r','144','-singlefile','-png',str(path),str(prefix)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
 with Image.open(str(prefix)+'.png')as im:return np.asarray(im.convert('RGB')).copy()
def run():
 narrow=json.loads((HERE/'narrow-change-qa.json').read_text('utf8'));assert narrow['passed']
 ready=json.loads((HERE/'CPhO_2023_Combined_KO.ready.json').read_text('utf8'));en=json.loads((HERE/'CPhO_2023_Combined_EN.ready.json').read_text('utf8'))
 assert sha(OLD)==ready['sha256']and sha(en['output'])==en['sha256']
 for row in ready['page_proofs']:
  if row['page']!=11:assert sha(proof(row['page']))==row['proof_sha256']
 TARGET.parent.mkdir(exist_ok=True)
 with page_worker(),pikepdf.open(OLD)as joined,pikepdf.open(NEW)as single:
  joined.pages[10]=single.pages[0];joined.save(TARGET,compress_streams=False)
 time.sleep(.6)
 digest=sha(TARGET);checks=[];renders=HERE/'assembly-renders';renders.mkdir(exist_ok=True)
 for n in range(1,37):
  expected=ready['page_proofs'][n-1]['rendered_pixel_sha256_4x']
  if n==11:
   with page_worker():expected=fresh_hash(NEW,1)['sha256']
   time.sleep(.6)
  with page_worker():actual=fresh_hash(TARGET,n)
  time.sleep(.6)
  assert actual['sha256']==expected,('Combined render differs from reviewed proof',n)
  with page_worker():a=pp(OLD if n!=11 else NEW,n if n!=11 else 1,renders/f'old-{n:02}');b=pp(TARGET,n,renders/f'new-{n:02}');count=int(np.any(a!=b,axis=2).sum())
  time.sleep(.6)
  assert not count,('Poppler comparison failed',n,count)
  row=dict(page=n,proof_sha256=sha(proof(n)),combined_sha256=digest,rendered_pixel_sha256_4x=actual['sha256'],MuPDF_changed_pixels=0,Poppler_144dpi_changed_pixels=0,other_proof_byte_preserved=n!=11)
  checks.append(row);(HERE/'assembly-progress.json').write_text(json.dumps(checks,indent=2),'utf8');print('JOIN',n,'0/0',flush=True)
 result=copy.deepcopy(ready);result.update(output=str(TARGET),sha256=digest,bytes=TARGET.stat().st_size,private_authored_space_revision=dict(original_KO_sha256=ready['sha256'],affected_page=11,restored_words='는 고정. 다음을 구하라',missing_spaces_restored=3,other_35_proof_bytes_preserved=True,complete_EN_edition_unchanged=dict(path=en['output'],sha256=en['sha256']),narrow_change_qa=str(HERE/'narrow-change-qa.json'),narrow_change_qa_sha256=sha(HERE/'narrow-change-qa.json'),projected_original_CID_witness=str(HERE/'projection-qa.json'),projected_original_CID_witness_sha256=sha(HERE/'projection-qa.json'),assembly_checks=checks))
 q=json.loads(NEW.with_suffix('.qa.json').read_text('utf8'));ind=json.loads(NEW.with_suffix('.independent.json').read_text('utf8'))
 for row in result['page_proofs']:
  n=row['page'];row['final_sha256']=digest;row['rendered_pixel_sha256_4x']=checks[n-1]['rendered_pixel_sha256_4x']
  if n==11:row.update(proof_sha256=sha(NEW),native_move_qa=q['native_move_qa'],actual_native_math_visible_ink=ind['native_ink'],authored_spacing_original_CID_projection=q['authored_spacing_projection'])
 for row in result['page_audits']:
  if row['page']==11:row.update(path=str(NEW.with_suffix('.independent.json')),sha256=sha(NEW.with_suffix('.independent.json')))
 snapshot=HERE/'engine'
 hashes={str(p.relative_to(snapshot)).replace('\\','/'):sha(p)for p in(snapshot/'tools').glob('*.py')}
 for name in('build_page11.py','qa_page11.py','project_authored_cids.py','assemble_private.py'):
  dest=snapshot/name;shutil.copy2(HERE/name,dest);hashes[name]=sha(dest)
 result.update(authoring_snapshotroot=str(snapshot),authoring_snapshot_sha256=hashes)
 path=TARGET.with_suffix('.ready.json');path.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
 print('FINAL_READY',str(path),digest,flush=True);return result
if __name__=='__main__':run()
