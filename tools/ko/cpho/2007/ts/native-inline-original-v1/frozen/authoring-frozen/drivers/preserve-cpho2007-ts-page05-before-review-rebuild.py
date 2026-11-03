from pathlib import Path
import hashlib,json,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
for lang in['ko','en']:
 groups=[(B/f'native-baseline/{lang}',list((B/f'native-baseline/{lang}').glob('page05*'))),(B/f'natural/2007/{lang}',list((B/f'natural/2007/{lang}').glob('page05*'))),(B/f'evidence/{lang}',list((B/f'evidence/{lang}').glob('page05*')))]
 files=[p for _,paths in groups for p in paths if p.is_file()];version=hashlib.sha256(''.join(str(p.relative_to(B))+sha(p)for p in sorted(files)).encode()).hexdigest()[:16];history=B/'history'/f'page05-before-native-punctuation-review-{lang}-{version}';history.mkdir(parents=True,exist_ok=True)
 for p in files:
  target=history/p.relative_to(B);target.parent.mkdir(parents=True,exist_ok=True);assert p.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(p);p.rename(target);assert sha(target)==digest;records.append(dict(original_path=str(p),preserved_path=str(target),sha256=digest))
 staging=B/f'initial-fixed-slot-staging/{lang}/page05'
 if staging.exists():
  target=history/'initial-fixed-slot-staging'/lang/'page05';target.parent.mkdir(parents=True,exist_ok=True)
  assert staging.resolve()==(B/f'initial-fixed-slot-staging/{lang}/page05').resolve()and staging.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();shutil.move(str(staging),str(target));records.append(dict(preserved_initial_fixed_slot_staging=str(target)))
(B/'history/page05-native-punctuation-review-preservation.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf8');print('PRESERVED_ALL_OWN_PAGE05_PROOFS_BASELINES_AND_EVIDENCE_BEFORE_SOURCE_FAITHFUL_REBUILD',len(records),flush=True)
