from pathlib import Path
import json,hashlib,sys,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');F=B/'natural/2016/TS';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();P=F/'plans/page02.json';p=json.loads(P.read_text('utf8'));history=P.parent/'history'/sha(P);history.mkdir(parents=True,exist_ok=True);(history/P.name).write_bytes(P.read_bytes())
with page_worker():
 with f.open(p['source_base'])as doc:gs=[g for g in _traces(doc[1])if g['c']=='액'and abs(g['origin'][1]-456.43)<.001]
assert len(gs)==1 and 'Bold'in gs[0]['font']
p.setdefault('reviewed_native_hangul_word_joins',[]).append(dict(reviewed=True,native_source_glyphs=gs,following_source_at=[15,1,2],following_text='체·고체 경계면의 표면 에너지 변화는 다음과 같다',reason='Original source boldT and regularhe form a single unspaced word The. Korean translation bold initial액 and regular체 form the single word 액체. Preserve the exact source12pt bold/regular roles and Y; join the same Korean word with zero boundary gap rather than introduce a3pt space.'))
P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');files=sorted(v for v in F.glob('page02*')if v.is_file());version=hashlib.sha256(''.join(v.name+sha(v)for v in files).encode()).hexdigest();archive=F/'history'/('page02-QA-positive-before-original-word-join-'+version);archive.mkdir(parents=True,exist_ok=True)
for v in files:
 target=archive/v.name;assert v.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(v);v.rename(target);assert sha(target)==digest
print('IZHO2016_SOURCE_SINGLE_WORD_BOLD_INITIAL_JOIN_BOUND',flush=True)
