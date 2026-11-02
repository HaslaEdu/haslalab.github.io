from pathlib import Path
import sys,json,pymupdf as f,hashlib
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');sys.path.insert(0,str(B/'engine'))
from pdf_native_inline_reposition import _traces
P=B/'natural/2019/T/plans/page07.json';d=json.loads(P.read_text('utf8'))
with f.open(d['original_english_source'])as source:gs=[g for g in _traces(source[6])if g['c'].strip()and f.Rect(306.,219.,401.,230.).contains(f.Point(g['origin']))]
assert len(gs)==16,[(g['c'],g['origin'])for g in gs]
d['reviewed_native_expression_groups']=[dict(label='Complete original absorption cross-section sigma_A=3,90*10^-16cm^2. Original exponent16 is paired within its own source Form, not with the unrelated preceding prose6G identifier. All16 original glyphs retain source fonts/GIDs/fractional points/y and one common horizontal dx.',glyphs=gs)]
digest=hashlib.sha256((P.parents[1]/'page07.pdf').read_bytes()).hexdigest();P.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('EXACT_SOURCE_EXPRESSION_MEMBERSHIP',len(gs),'proof_unmodified',digest)
