from pathlib import Path
import json,hashlib,sys,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import _traces
from pdf_memory_gate import page_worker
P=B/'natural/2016/TS/plans/page02.json';p=json.loads(P.read_text('utf8'));sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest();history=P.parent/'history'/sha(P);history.mkdir(parents=True,exist_ok=True);(history/P.name).write_bytes(P.read_bytes())
rect=[142,706,235,726]
with page_worker():
 with f.open(p['original_english_source'])as doc:gs=[g for g in _traces(doc[1])if g['c'].strip()and f.Rect(rect).contains(f.Point(g['origin']))]
assert len(gs)>=12
p.setdefault('reviewed_stationary_expression_groups',[]).append(dict(label='Original2016 page2 separate display5 DeltaUG=pi R2 Delta h rho g h',glyphs=gs,reviewed=True,source_rect=rect,reason='Full source144dpi and strict output reviewed. Native7.073508pt superscript2 at196.01965,714.42096 belongs to the stationary R squared of displayed equation5, not preceding prose inline Delta h at192.25441,704.06354. Bind the full original display expression as stationary: all native fonts/GIDs/fractional points/Y/paint and source relative geometry still independently audited. No script exclusion or threshold change.'))
P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');print('IZHO2016_PAGE2_ORIGINAL_SEPARATE_DISPLAY5_OWNERSHIP_BOUND',len(gs),flush=True)
