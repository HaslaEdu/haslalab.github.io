from pathlib import Path
import json,sys,pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_moved_native_ink import _key
f=B/'natural/2017/T';q=json.loads((f/'page01.qa.json').read_text('utf8'));p=json.loads((f/'plans/page01.json').read_text('utf8'))
with fitz.open(p['original_english_source'])as o,fitz.open(f/'page01.old-source.pdf')as d:
 keys={(glyph_key(g),g['trace_gid'],g['render_mode'])for g in _traces(o[0])if g['c'].strip()and g['trace_gid']>=0 and g['render_mode']!=3}
 old=[g for g in _traces(d[0])if(glyph_key(g),g['trace_gid'],g['render_mode'])in keys and g['c'].strip()]
 moves={_key(g):s['dx']for s in q['native_shifts']for g in s['glyphs']}
 for g in old:
  dx=moves.get(_key(g),0);r=fitz.Rect(g['bbox'])+ (dx,0,dx,0)
  if r.intersects(fitz.Rect(285,380,369,390)):print(g['c'],g['font'],g['size'],g['origin'],'dx',dx,'gid',g['trace_gid'],'target_bbox',list(r))
