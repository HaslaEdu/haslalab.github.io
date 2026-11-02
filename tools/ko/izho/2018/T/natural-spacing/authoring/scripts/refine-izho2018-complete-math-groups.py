from pathlib import Path
import json,sys,shutil,hashlib
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import _traces
F=B/'natural/2018/T'
source=B/'2018/source/IZhO_2018_T.pdf'
with f.open(source)as d:
 rows3=_traces(d[2]);rows4=_traces(d[3])
def group(rows,rect,label):
 box=f.Rect(rect);glyphs=[g for g in rows if g['c'].strip()and g['font']=='Cambria Math'and box.contains(f.Point(g['origin']))]
 assert glyphs
 return dict(label=label,glyphs=glyphs,reviewed=True,source_original_only=True)
p=F/'plans/page03.json';j=json.loads(p.read_text('utf8'))
j['reviewed_native_expression_groups']=[group(rows3,[461.68,594.64,537.,599.01],'Complete original gravitational-acceleration constant including the exponent on seconds. Its superscript belongs to this expression, not a horizontally closer digit on the preceding prose line. Every member retains one common dx, original point and y.')]
p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
p=F/'plans/page04.json';j=json.loads(p.read_text('utf8'))
negative=F/'negative-partial-integral-movement';negative.mkdir(exist_ok=True)
for name in ['page04.pdf','page04.audit.json','page04.qa.json']:
 target=negative/name
 if not target.exists():shutil.copy2(F/name,target)
j['reviewed_stationary_expression_groups']=[group(rows4,[265.5,385.5,368.05,407.],'Complete original stationary logarithmic saturated-vapor-pressure equation with both fractions and nested scripts. Do not attach its small numerator scripts to digits in the preceding independent temperature-range expression.')]
review=[]
for scope in j['source_line_scopes']:
 if scope['source_at']!=[14,1]:continue
 old=scope['rect'][:];new=[84.73,min(old[1],518.),554.27,max(old[3],539.5)]
 j['allowed_line_rects']=[new[:]if r==old else r for r in j['allowed_line_rects']]
 for other in j['source_line_scopes']+j['centered_lines']+j['right_aligned_lines']:
  if other.get('rect')==old:other['rect']=new[:]
 review.append(dict(source_at=[14,1],previous_rect=old,rect=new,reason='One complete original inline integral occupies several raw-dictionary blocks; include the original entire fraction widget and its original source-column blank area so the explicit native atom cannot be filtered out by the prose-prefix rectangle. All18 original math glyphs and both fraction rules must receive one common dx.'))
assert len(review)==1
j['reviewed_complete_inline_math_source_rows']=review
j.pop('native_ink_witness_profile',None);j.pop('native_ink_witness',None)
p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
print('SOURCE_REVIEWED_EXPRESSION_MEMBERSHIPS_AND_COMPLETE_INTEGRAL_FRAME_DECLARED; NO_SHARED_GUARD_OR_THRESHOLD_CHANGED',flush=True)
