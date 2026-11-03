from pathlib import Path
import json,sys,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory')
sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from pdf_native_inline_reposition import _traces
for n,box in [(4,[250,302,350,332]),(5,[245,475,560,504])]:
 p=json.loads((B/f'natural/2017/T/plans/page{n:02}.json').read_text('utf8'))
 with f.open(p['original_english_source'])as d:
  g=[x for x in _traces(d[n-1])if f.Rect(box).contains(f.Point(x['origin']))and x['c'].strip()]
  print(n,[(x['c'],x['font'],round(x['size'],2),[round(v,3)for v in x['origin']],[round(v,3)for v in x['bbox']])for x in g])
  print('drawings',[(list(x['rect']),x['fill'],x['color'])for x in d[n-1].get_drawings()if f.Rect(box).intersects(x['rect'])])
