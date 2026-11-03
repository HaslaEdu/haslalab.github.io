from pathlib import Path
import sys,json,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];n=int(sys.argv[1]);F=B/'natural/2015/TS'
import pdf_korean_natural_composer as c
from izho_natural_spacing_rebuild import page_build
from pdf_native_inline_reposition import inspect_inline_groups
from pdf_original_text_ops import glyph_key
original=c.reposition_inline
def debug(source,page,*,erased_glyphs,shifts,**options):
 inv=inspect_inline_groups(source,page);problems=[]
 for index,s in enumerate(shifts):
  keys={glyph_key(g)for g in s['glyphs']if g['c'].strip()};dx=s['dx']
  for clip in inv['clip_groups']:
   nonspace={glyph_key(g)for g in clip['glyphs']if g['c'].strip()}
   if not nonspace or not nonspace<=keys:continue
   for g in clip['glyphs']:
    if not g['c'].strip():continue
    r=f.Rect(g['bbox']);visible=f.Rect(r)
    for own in clip['clip_rects']:
     if own is not None:visible&=f.Rect(own)
    for parent in clip['ancestor_clip_rects']:
     if parent is None or(not f.Rect(parent).contains(r+(dx,0,dx,0))and(not clip['clip_rects']or(not visible.is_empty and not f.Rect(parent).contains(visible+(dx,0,dx,0))))):problems.append(dict(shift=index,dx=dx,glyph=g,clip=clip))
 (F/f'page{n:02}-failed-native-motion-diagnostic.json').write_text(json.dumps(dict(source=str(source),shifts=shifts,options=options,problems=problems),ensure_ascii=False,indent=2)+'\n','utf8')
 return original(source,page,erased_glyphs=erased_glyphs,shifts=shifts,**options)
c.reposition_inline=debug
page_build(F/f'plans/page{n:02}.json')
