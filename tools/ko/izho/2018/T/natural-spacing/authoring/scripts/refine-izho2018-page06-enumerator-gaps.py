from pathlib import Path
import sys,json
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path.insert(0,str(B/'engine'))
from pdf_native_inline_reposition import _traces
p=B/'natural/2018/T/plans/page06.json';d=json.loads(p.read_text('utf8'));boundaries=[];groups=[]
with f.open(d['original_english_source'])as doc:
 gs=_traces(doc[5])
 for number,y in [('3.2',309.4599609375),('3.3',375.4599914550781)]:
  enum=[g for g in gs if g['c'].strip()and abs(g['origin'][1]-y)<.001 and 84<g['origin'][0]<101]
  expression=[g for g in gs if g['c'].strip()and g['font']=='Cambria Math'and 127<g['origin'][0]<174 and abs(g['origin'][1]-y)<3]
  assert ''.join(g['c']for g in enum)==number
  assert ''.join(g['c']for g in expression)in ['𝐴1,𝐵1','𝐴2,𝐵2'],expression
  reason='Source-native subquestion enumerator followed by a separate complete mathematical object after the English word Find was translated after that object in Korean. Replace only this inter-object prose gap with3pt; preserve every source glyph, point, baseline and all internal mathematical spacing.'
  boundaries.append(dict(enumerator_glyphs=enum,expression_glyphs=expression,reason=reason))
  groups.append(dict(label='Complete original '+number+' object list: all source A/B glyphs, subscripts and comma share one horizontal translation; the question enumerator is a separate prose object.',glyphs=expression))
d['reviewed_native_enumerator_to_expression_gaps']=boundaries
d['reviewed_native_expression_groups']=groups
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('REVIEWED_SEPARATE_ENUMERATOR_MATH_OBJECT_PROSE_BOUNDARIES',len(boundaries))
