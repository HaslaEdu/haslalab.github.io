"""Use actual display-math bounds without intersecting the following prose line."""
from pathlib import Path
import json,sys
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original')
sys.path.insert(0,str(B/'engine'))
from pdf_native_inline_reposition import _traces
p=B/'natural/2018/T/plans/page05.json';d=json.loads(p.read_text('utf8'))
old=[154.,231.5,491.,255.8];new=[154.,231.5,491.,254.5]
for key in ['excluded_figure_rects','frozen_display_math_rects']:
 assert old in d[key] or new in d[key]
 d[key]=[new[:] if r==old else r for r in d[key]]
with f.open(d['original_english_source'])as doc:
 gs=_traces(doc[4])
 display=[g for g in gs if g['c'].strip()and f.Rect(new).contains(f.Point(g['origin']))]
 inline=[g for g in gs if g['c'].strip()and g['font']=='Cambria Math'and abs(g['origin'][1]-265.02996826171875)<.001]
assert display and ''.join(g['c']for g in inline)=='𝑐=2.9979m/s'
d['reviewed_stationary_expression_groups']=[dict(label='Complete original displayed Lorentz transformations, including their original fraction scripts, punctuation and rules. This source display ends before the next prose line; all physical glyphs retain zero dx.',glyphs=display)]
d['reviewed_native_expression_groups']=[g for g in d['reviewed_native_expression_groups']if not g['label'].startswith('Complete original printed light-speed')]+[dict(label='Complete original printed light-speed constant c=2.9979m/s. Every original source glyph retains its font, point, baseline and one common horizontal displacement; no partial exclusion by the preceding display rectangle.',glyphs=inline)]
d['reviewed_display_boundary']=dict(rect=new,following_prose_baseline=265.02996826171875,following_native_bbox_top=min(g['bbox'][1]for g in inline),reason='The earlier255.8pt rectangle intersected the next line glyph boxes and split the constant. Actual display glyph boxes end at253.213pt.254.5pt fully protects the display while leaving the following whole constant eligible.')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
q=Path('D:/CodexBuilds/prepare-izho2018-theory-natural.py');s=q.read_text('utf8');s=s.replace('display=[154.,231.5,491.,255.8]','display=[154.,231.5,491.,254.5]');q.write_text(s,'utf8')
print('REVIEWED_DISPLAY_AND_FOLLOWING_COMPLETE_CONSTANT',len(display),len(inline))
