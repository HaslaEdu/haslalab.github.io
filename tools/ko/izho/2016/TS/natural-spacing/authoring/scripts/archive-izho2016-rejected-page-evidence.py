from pathlib import Path
import sys,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');F=B/'natural/2016/TS';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in map(int,sys.argv[1:]):
 files=sorted(p for p in F.glob(f'page{n:02}*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest();target=F/'history'/f'page{n:02}-rejected-{version}';target.mkdir(parents=True,exist_ok=True)
 for p in files:
  dst=target/p.name;assert p.resolve().is_relative_to(B.resolve())and dst.resolve().is_relative_to(B.resolve());assert not dst.exists();digest=sha(p);p.rename(dst);assert sha(dst)==digest
 print('IZHO2016_REJECTED_EVIDENCE_ARCHIVED',n,version,flush=True)
