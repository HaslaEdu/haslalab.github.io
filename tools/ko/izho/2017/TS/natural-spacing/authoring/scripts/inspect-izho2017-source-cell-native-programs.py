from pathlib import Path
import json,sys
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups
from pdf_original_text_ops import glyph_key
for n in map(int,sys.argv[1:]):
 p=json.loads((B/f'natural/2017/TS/plans/page{n:02}.json').read_text('utf8'))
 with page_worker():inv=inspect_inline_groups(p['source_base'],n,include_text_shows=True)
 out=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions/native-program-inspection');out.mkdir(parents=True,exist_ok=True);(out/f'page{n:02}-initial-full-inventory.json').write_text(json.dumps(inv,ensure_ascii=False),'utf8')
 for index,a in enumerate(p['explicit_native_math_atoms']):
  if not(n==6 and a['rect'][1]>748 and a['rect'][3]<770):continue
  wanted={glyph_key(g)for g in a['source_native_glyphs']};clips=[]
  for c in inv['clip_groups']:
   keys={glyph_key(g)for g in c['glyphs']if g['c'].strip()}
   if keys and keys<=wanted:clips.append(dict(indices=c['operator_indices'],clips=c['clip_rects'],text=''.join(g['c']for g in c['glyphs']if g['c'].strip()),glyphs=len(keys)))
  print(index,a['rect'],'wanted',len(wanted),''.join(g['c']for g in a['source_native_glyphs']), 'clips',clips,flush=True)
