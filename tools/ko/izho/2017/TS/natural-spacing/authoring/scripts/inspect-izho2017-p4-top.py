from pathlib import Path
import sys,json,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from pdf_native_inline_reposition import _traces
from izho_native_atomic_tokens import _inventory
p=json.loads((B/'natural/2017/T/plans/page04.json').read_text('utf8'));q=json.loads((B/'natural/2017/T/page04.qa.json').read_text('utf8'));source=Path(p['source_base']);st=source.stat();inv=_inventory(str(source),4,st.st_mtime_ns,st.st_size)
with f.open(source)as d:g=[v for v in _traces(d[3])if v['origin'][1]<95 and v['origin'][0]>450 and v['c'].strip()]
print('glyphs',g)
for k in ['excluded_figure_rects','allowed_line_rects','native_atomic_tokens']:print(k,p.get(k))
for k in ['forms','images','vector_paths','clip_groups']:
 print(k,[v for v in inv.get(k,[])if (v.get('bbox',v.get('rect',[0,1000,0,1000]))[1]<100 and v.get('bbox',v.get('rect',[0,1000,0,1000]))[0]>450)])
print('lines',[r for r in q.get('lines',[])if r.get('baseline',1000)<95])
print('qkeys',list(q))
