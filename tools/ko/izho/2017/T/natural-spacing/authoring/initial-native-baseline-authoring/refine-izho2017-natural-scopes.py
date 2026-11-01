from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');f=B/'natural/2017/T/plans'
p=f/'page03.json';q=json.loads(p.read_text('utf8'));old=[225,544,262,566];new=[225,545,262,562.75]
def replace(v):
 if isinstance(v,list):return new if v==old else[replace(x)for x in v]
 if isinstance(v,dict):return{k:replace(x)for k,x in v.items()}
 return v
q=replace(q);q['display_roi_review']='Complete original Omega=S/R^2 physical ink and native R baseline562.010 retained. Old coarse ROI included preceding prose at544.0-545.0 and following prose from562.75. Source formula and every original glyph/point/x/y remain independently protected.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
p=f/'page04.json';q=json.loads(p.read_text('utf8'))
q['hangul_word_revisions']=[dict(source_at=[7,3,0],old='우주선의',new='우주선',reason='Equivalent Korean noun phrase 우주선 속력, at the original12pt and baseline; no physical information removed.')]
q.pop('reviewed_multiline_native_math_bindings',None)
q['explicit_native_math_atoms']=[dict(reviewed=True,rect=[514,69,521,92],baseline=83.29998779296875,font_regex='Cambria',reason='Original top paragraph height a/2 is a complete 8.4pt numerator, 8.4pt denominator and native vector fraction rule. Pack this full fraction beside the translated height clause on the original83.300 baseline by one horizontal shift; keep both source font/GIDs/point sizes and all original y coordinates, including the bar.')]
import pymupdf as fitz,sys
sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from pdf_native_inline_reposition import _traces
with fitz.open(q['source_base'])as doc:
 exponent=[g for g in _traces(doc[3])if g['c'].strip()and 'Cambria'in g['font']and fitz.Rect(274,313,294,328).contains(fitz.Point(g['origin']))]
assert ''.join(g['c']for g in exponent)=='108'
q['reviewed_script_exclusions']=[dict(origin=[289.0799865722656,320.260009765625],reason='Visually checked original English page4: this is the superscript8 of 10^8 in impact parameter b=1.50x10^8km. The automatic nearest-x candidate incorrectly selects the equals sign of the preceding, separate v_infinity=100km/s line. Its true native 10^8 base and exponent are explicitly checked as a complete rigid source group below.')]
q['reviewed_native_expression_groups']=[dict(label='Source impact-parameter 10^8: original native 1,0 and superscript8 retain their exact mutual x/y, font/GID/point/paint.',glyphs=exponent)]
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
p=f/'page05.json';q=json.loads(p.read_text('utf8'));old=[255,481,558,501];new=[255,483.5,558,501]
q=replace(q)
q['display_roi_review']='Equation3 full native ink, including x subscripts and original (3), is retained: highest source native bbox starts483.961 and lowest ends498.729. Old coarse top481 included the preceding prose descender through481.521. All native glyph metadata and full original formula pixels independently protected.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
p=f/'page06.json';q=json.loads(p.read_text('utf8'));runs=json.loads((B/'2017/page06.runs.json').read_text('utf8'))
for li,limits in [(0,[84.734,294]),(1,[319,559.6])]:
 run=runs[f'4,{li},0'];y=run['origin'][1];rect=[limits[0],y-10.2,limits[1],y+5.76]
 if not any(s['source_at']==[4,li]for s in q['source_line_scopes']):q['source_line_scopes'].append(dict(source_at=[4,li],source_text=run['text'],rect=rect,baseline=y,original_grid_cell_bounds=None,original_grid_cell_rect=None))
 if rect not in q['allowed_line_rects']:q['allowed_line_rects'].append(rect)
 q['centered_lines']=[c for c in q['centered_lines']if not(c.get('rect')==rect and abs(c.get('baseline',0)-y)<.01)]
 q['centered_lines'].append(dict(baseline=y,center=(run['bbox'][0]+run['bbox'][2])/2,rect=rect))
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('Reviewed exact formula ROI and both separately centered figure captions.')
