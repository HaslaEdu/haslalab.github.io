from pathlib import Path
import json,sys,os
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
import izho_natural_spacing_rebuild as rebuild,pdf_korean_natural_composer as composer
from pdf_native_inline_reposition import inspect_inline_groups
from pdf_original_text_ops import glyph_key
original=composer.reposition_inline
def diagnose(source,page_number,**options):
 inv=inspect_inline_groups(source,page_number);rows=[]
 for s in options.get('shifts',[]):
  keys={glyph_key(g)for g in s['glyphs']};forms=[]
  for v in inv['forms']:
   native={glyph_key(g)for g in v['glyphs']if g['c'].strip()};overlap=native&keys
   if overlap:forms.append(dict(path=v['path'],original_glyphs=len(native),selected_members=len(overlap),fully_selected=native<=keys,selected_glyphs=[g for g in v['glyphs']if glyph_key(g)in overlap]))
  rows.append(dict(dx=s['dx'],form_path=s.get('form_path'),glyphs=s['glyphs'],Forms=forms))
 out=B/'natural/2018/TS/page15-native-selection-diagnostic.json';out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8');print('EXACT_NATIVE_GROUP_SELECTION_RECORDED',str(out),flush=True)
 return original(source,page_number,**options)
composer.reposition_inline=diagnose
with page_worker():rebuild._page_build(B/'natural/2018/TS/plans/page15.json')
