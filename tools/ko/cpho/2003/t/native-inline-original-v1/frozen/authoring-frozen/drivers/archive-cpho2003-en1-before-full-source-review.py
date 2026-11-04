from pathlib import Path
import json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native').resolve();out=B/'proof-history/en-page01-before-source-completeness-v5';assert not out.exists();out.mkdir(parents=True);rows=[]
paths=list((B/'natural/2003/en').glob('page01*'))+list((B/'native-baseline/en').glob('page01*'))+[B/'initial-fixed-slot-staging/en/page01']
for p in paths:
 p=p.resolve();target=(out/p.relative_to(B)).resolve();assert p.is_relative_to(B)and target.is_relative_to(out.resolve())and not target.exists()
 if p.is_file():rows.append(dict(path=p.relative_to(B).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
 target.parent.mkdir(parents=True,exist_ok=True);p.rename(target)
(out/'archive-manifest.json').write_text(json.dumps(dict(reason='First English visual/source review restores explicit G definition, metal flywheel wording, full y-axis wording and sentence punctuation at unchanged source points. Earlier passing proof is retained as history, not current review.',files=rows),ensure_ascii=False,indent=2)+'\n','utf8')
