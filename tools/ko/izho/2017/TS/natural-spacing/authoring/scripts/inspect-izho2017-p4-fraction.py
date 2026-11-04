from pathlib import Path
import sys,json,pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from izho_native_atomic_tokens import _inventory
from pdf_native_inline_reposition import _traces
p=json.loads((B/'natural/2017/T/plans/page04.json').read_text('utf8'));source=Path(p['source_base']);st=source.stat();inv=_inventory(str(source),4,st.st_mtime_ns,st.st_size);rect=fitz.Rect(264,300,305,326)
with fitz.open(source)as d:g=[v for v in _traces(d[3])if rect.contains(fitz.Point(v['origin']))and 'Cambria'in v['font']and v['c'].strip()]
q=dict(rect=list(rect),glyphs=g,paths=[v for v in inv['vector_paths']if rect.contains(fitz.Rect(v['rect']))],clips=[v for v in inv['clip_groups']if any(rect.contains(fitz.Point(vg['origin']))for vg in v['glyphs'])])
dest=B/'2017/source-native-witness-regressions/p4-complete-vinf-fraction.json';dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('GLYPHS',[(v['c'],v['origin'])for v in g]);print('PATHS',[(v['rect'],v['operator_indices'])for v in q['paths']]);print('CLIPS',[(v['operator_indices'],v.get('known_rectangular_clips'),len(v['glyphs']))for v in q['clips']])
