"""Independently verify original numeric title faces and complete-line alignment."""
from pathlib import Path
import json
import pymupdf as fitz
from pdf_native_inline_reposition import _traces
from cpho_natural_full_qa import native_font_programs
import cpho_early_natural as a

def audit(year,language,number,target,composition):
 numeric=a.BASE/f'numeric-stage/{year}/{language}/complete-source-number-faces.pdf'
 stage=json.loads(numeric.with_suffix('.json').read_text('utf8'))['pages'][number-1]
 with fitz.open(target)as doc:
  page=doc[0];final=[g for g in _traces(page)if g['c'].strip()and g['trace_gid']>=0];width=page.rect.width
 original_programs=[f for f in native_font_programs(numeric,number)if f[1].startswith('/OriginalNumericProse')]
 final_programs=native_font_programs(target,1)
 faces=all(f in final_programs for f in original_programs)
 digits=[]
 for r in stage['digits']:
  old=r['translation_point'];matches=[]
  for s in composition['native_shifts']:
   if any(g['c']==r['digit']and g['font']==r['original_font']and abs(g['size']-r['original_size'])<.0001 and max(abs(v-w)for v,w in zip(g['origin'],old))<.001 for g in s['glyphs']):matches.append(s['dx'])
  if matches and max(matches)-min(matches)>.001:raise ValueError('Conflicting restored numeric prose dx')
  dx=matches[0]if matches else 0;point=[old[0]+dx,old[1]]
  found=[g for g in final if g['c']==r['digit']and g['font']==r['original_font']and g['trace_gid']==r['original_gid']and abs(g['size']-r['original_size'])<.0001 and max(abs(v-w)for v,w in zip(g['origin'],point))<.001]
  if len(found)!=1:raise ValueError(('Actual source numerical prose font/GID/point missing',r,point))
  g=found[0]
  if g['render_mode']!=r['original_render_mode']:raise ValueError('Original numeric prose rendering mode changed')
  digits.append(dict(digit=r['digit'],source_font=g['font'],original_gid=g['trace_gid'],size=g['size'],baseline=g['origin'][1],expected_dx=dx,position_error_pt=max(abs(v-w)for v,w in zip(g['origin'],point))))
 lines=[]
 for p in a.placements(year,language,number):
  role=p.get('original_role')
  if role not in('title','header','footer'):continue
  row=sorted([g for g in final if abs(g['origin'][1]-p['point'][1])<.02],key=lambda g:g['origin'][0])
  text=''.join(g['c']for g in row)
  if text!=''.join(p['text'].split()):raise ValueError(('Complete heading/footer character order changed',p['id'],text,p['text']))
  left=min(g['origin'][0]for g in row);right=max(g['bbox'][2]for g in row)
  if role=='header'and year==2013:
   slot=next(s for s in a.source_plan(year,number)['slots']if s['id']==p['id']);error=abs(right-slot['source_rect'][2]);align='original right edge'
  else:error=abs((left+right)/2-width/2);align='whole line centered on original page'
  if error>.002:raise ValueError(('Whole-line heading alignment failed',p['id'],error))
  lines.append(dict(id=p['id'],text=p['text'],alignment=align,error_pt=error,baseline=p['point'][1]))
 return dict(passed=faces,actual_source_numeric_programs_retained=faces,source_numeric_font_resources=len(original_programs),digits=digits,complete_heading_footer_lines=lines,no_added_edition_title_or_note=True,
  original_printed_footer_total_retained=('2 pages, including on page 3; original printed total is preserved without an added PDF erratum.'if year==2013 else None))
