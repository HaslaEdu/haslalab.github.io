from pathlib import Path
import hashlib,json,shutil,sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');n=int(sys.argv[1]);langs=sys.argv[2:]or['ko','en'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
for lang in langs:
 assert 5<=n<=20 and lang in['ko','en']
 groups=[B/f'native-baseline/{lang}',B/f'natural/2007/{lang}',B/f'evidence/{lang}']
 files=[p for folder in groups for p in folder.glob(f'page{n:02}*')if p.is_file()]
 version=hashlib.sha256(''.join(str(p.relative_to(B))+sha(p)for p in sorted(files)).encode()).hexdigest()[:16]
 history=B/'history'/f'page{n:02}-{lang}-{version}';history.mkdir(parents=True,exist_ok=True)
 for p in files:
  target=history/p.relative_to(B);target.parent.mkdir(parents=True,exist_ok=True);assert p.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve())and not target.exists();digest=sha(p);p.rename(target);assert sha(target)==digest;records.append(dict(original_path=str(p),preserved_path=str(target),sha256=digest))
 staging=B/f'initial-fixed-slot-staging/{lang}/page{n:02}'
 if staging.exists():
  target=history/'initial-fixed-slot-staging'/lang/f'page{n:02}';target.parent.mkdir(parents=True,exist_ok=True)
  assert staging.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve())and not target.exists();shutil.move(str(staging),str(target));records.append(dict(preserved_initial_fixed_slot_staging=str(target)))
 receipt=history/'preservation-receipt.json';assert not receipt.exists();receipt.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf8')
print('PRESERVED_OWN_CPHO2007_PAGE_BEFORE_REBUILD',n,langs,len(records),flush=True)
