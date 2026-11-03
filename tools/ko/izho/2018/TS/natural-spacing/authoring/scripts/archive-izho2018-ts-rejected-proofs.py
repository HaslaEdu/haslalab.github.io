from pathlib import Path
import hashlib,sys,json
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');F=B/'natural/2018/TS';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in map(int,sys.argv[1:]):
 files=sorted(p for p in F.glob(f'page{n:02}*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];target=F/'history'/f'rejected-{n:02}-{version}';target.mkdir(parents=True,exist_ok=True)
 plan=F/f'plans/page{n:02}.json';(target/'current-plan-at-archive.json').write_bytes(plan.read_bytes())
 for p in files:
  q=target/p.name;assert p.resolve().is_relative_to(B.resolve())and q.resolve().is_relative_to(B.resolve());assert not q.exists();pin=sha(p);p.rename(q);assert sha(q)==pin
 print('PRESERVED_SOURCE2018_REJECTED_PROOF_ATTEMPT',n,target,flush=True)
