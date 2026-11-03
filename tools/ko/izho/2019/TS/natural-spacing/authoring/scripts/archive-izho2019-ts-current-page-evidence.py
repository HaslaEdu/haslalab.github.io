from pathlib import Path
import sys,hashlib,json,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');F=B/'natural/2019/TS';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in map(int,sys.argv[1:]):
 proof=F/f'page{n:02}.pdf';digest=sha(proof);folder=F/'history'/('rejected-'+digest);folder.mkdir(parents=True,exist_ok=True);pins={}
 for p in F.glob(f'page{n:02}*'):
  if not p.is_file():continue
  assert p.resolve().is_relative_to(F.resolve());dest=folder/p.name;assert dest.resolve().is_relative_to(B.resolve());pins[p.name]=sha(p)
  if dest.exists():assert dest.read_bytes()==p.read_bytes();p.unlink()
  else:shutil.move(str(p),str(dest))
 plan=F/f'plans/page{n:02}.json';target=folder/('current-plan-at-archive-'+sha(plan)+'.json');target.write_bytes(plan.read_bytes());(folder/'preserved-evidence.json').write_text(json.dumps(dict(page=n,proof_sha256=digest,files=pins,reason='Full source/final visual rejected disconnected literal-space vector heads or ordinary final QA detected outside text ink; preserve unchanged evidence before source-specific repair.'),indent=2)+'\n','utf8');print('PRESERVED_2019_REJECTED_PAGE_EVIDENCE',n,digest,flush=True)
