from pathlib import Path
import sys,json,hashlib,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
P=B/'natural/2016/TS/plans/page05.json';p=json.loads(P.read_text('utf8'));sha=lambda v:hashlib.sha256(v.read_bytes()).hexdigest();history=P.parent/'history'/sha(P);history.mkdir(parents=True,exist_ok=True);(history/P.name).write_bytes(P.read_bytes())
rect=[142,627,273,655.5]
with page_worker():
 with f.open(p['original_english_source'])as doc:gs=[g for g in _traces(doc[4])if g['c'].strip()and f.Rect(rect).contains(f.Point(g['origin']))]
assert len(gs)>20
p.setdefault('reviewed_stationary_expression_groups',[]).append(dict(label='Original2016 page5 separate display equation7, not a script of preceding prose reference(5)',glyphs=gs,reviewed=True,source_rect=rect,reason='Full original source144dpi and actual proof read. Native8.52pt numerator R at183.14,632.38 belongs to the stationary displayed dt=R/(U0-q/C(q))dq=f(q)dq equation7. It is not a superscript of the preceding translated prose reference closing parenthesis at178.376,622.54. Bind the entire original display expression; every glyph and all fraction rules remain at exact original source x/y/font/GID/point/paint. No script exclusion or audit threshold change.'))
P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');print('IZHO2016_PAGE5_ORIGINAL_SEPARATE_DISPLAY_OWNERSHIP_BOUND',len(gs),flush=True)
