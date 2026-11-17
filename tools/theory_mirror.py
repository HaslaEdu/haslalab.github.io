"""Publish only manifest/hash-verified PDFs from an ephemeral staging branch."""
from pathlib import Path, PurePosixPath
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess,hashlib,json,csv,io,tempfile,zipfile,re,sys,time,threading,os
REPO='HaslaEdu/haslalab.github.io'
ROOT=Path.cwd();M=json.loads((ROOT/'_translation_staging/manifest.json').read_text())
assert sys.argv[1:]==['--publish-staged-translations'];assert M['repository']==REPO

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def gh(args):return subprocess.run(['gh',*args],check=True,capture_output=True,text=True).stdout
files=[]
with tempfile.TemporaryDirectory()as td:
 work=Path(td)
 for row in M.get('files',[]):
  p=ROOT/row['path'];assert p.is_file()and sha(p)==row['sha256'];files.append(dict(row,file=p))
 for archive in M.get('archives',[]):
  out=work/archive['name']
  with out.open('wb')as dest:
   for chunk in archive['chunks']:
    p=ROOT/chunk['path'];assert p.stat().st_size==chunk['bytes']and sha(p)==chunk['sha256'];dest.write(p.read_bytes())
  assert sha(out)==archive['sha256']
  with zipfile.ZipFile(out)as z:
   rows=list(csv.DictReader(io.StringIO(z.read('coverage.csv').decode('utf-8-sig'))))
   selected=[r for r in rows if r['competition']==archive['competition']and r['language']==archive['language']]
   assert len(selected)==archive['pdfs']
   for r in selected:
    name=PurePosixPath(r['translation']).name;assert re.fullmatch(r'(OIbF|BPO|USAPhO|OPhO)_[A-Za-z0-9_]+_(EN|KO)\.pdf',name)
    p=work/name
    with z.open(r['translation'])as src,p.open('wb')as dst:
     for b in iter(lambda:src.read(1024*1024),b''):dst.write(b)
    assert sha(p)==r['translation_sha256'];files.append(dict(file=p,name=name,tag='pdf-'+r['competition'].lower(),sha256=r['translation_sha256']))
 assert len(files)==M['expected_pdfs'];assert len({x['name']for x in files})==len(files)
 remote={}
 for tag in sorted({x['tag']for x in files}):
  d=json.loads(gh(['api',f'repos/{REPO}/releases/tags/{tag}']));remote[tag]={a['name']:a for a in d['assets']}
 lock=threading.Lock();last=[0.]
 def upload(x):
  old=remote[x['tag']].get(x['name'])
  if old:
   digest=old.get('digest')
   if digest:assert digest=='sha256:'+x['sha256'],f'Existing different asset: {x["name"]}'
   else:
    dest=work/('existing-'+x['name'])
    with dest.open('wb')as f:subprocess.run(['gh','api',f'repos/{REPO}/releases/assets/{old["id"]}','-H','Accept: application/octet-stream'],check=True,stdout=f)
    assert sha(dest)==x['sha256'],f'Existing different asset: {x["name"]}'
   return dict(name=x['name'],tag=x['tag'],sha256=x['sha256'],status='VERIFIED_EXISTING')
  with lock:
   delay=max(0,last[0]+1.1-time.monotonic())
   if delay:time.sleep(delay)
   last[0]=time.monotonic()
  gh(['release','upload',x['tag'],str(x['file']),'--repo',REPO])
  return dict(name=x['name'],tag=x['tag'],sha256=x['sha256'],status='UPLOADED')
 results=[]
 with ThreadPoolExecutor(max_workers=3)as pool:
  for task in as_completed([pool.submit(upload,x)for x in files]):
   r=task.result();results.append(r);print(json.dumps({'done':len(results),'total':len(files),**r}),flush=True)
 for tag in sorted(remote):
  d=json.loads(gh(['api',f'repos/{REPO}/releases/tags/{tag}']));byname={x['name']:x for x in d['assets']}
  for item in [x for x in files if x['tag']==tag]:
   assert item['name']in byname
   digest=byname[item['name']].get('digest')
   assert digest=='sha256:'+item['sha256'],f'Uploaded asset digest unavailable/different: {item["name"]}'
 print(json.dumps({'status':'PASS','verified_pdfs':len(files),'repository':REPO}),flush=True)
 summary=os.environ.get('GITHUB_STEP_SUMMARY')
 if summary:Path(summary).write_text(f'Published and verified {len(files)} approved PDF assets. No existing different assets were replaced.\n')
