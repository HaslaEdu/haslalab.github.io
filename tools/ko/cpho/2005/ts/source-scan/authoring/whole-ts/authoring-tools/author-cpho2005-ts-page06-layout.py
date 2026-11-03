"""Explicit source-line erase geometry and protected source display equations."""
from pathlib import Path
import json,sys,re
import pymupdf as f,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import new_font,font_path,row_layout
language=json.loads((B/'authoring/page06-language-row-proposals.json').read_text('utf8'))
types=json.loads((B/'page06-per-row-source-type-proposals.json').read_text('utf8'))
weights=json.loads((B/'page06-row-weight-calibration.json').read_text('utf8'))
assert types['complete'] and weights['complete']
types={r['id']:r for r in types['rows']};weights={r['id']:r for r in weights['rows']}
atoms={r['id']:r for r in json.loads((B/'authoring/page06-native-math-proposals.json').read_text('utf8'))['atoms']}
assert not any(r['search_boundary_touched']for r in atoms.values())
geometry={
 'comparison':(66.5,[64,63,94,82]),'final-rest':(67,[65,98,271,117]),'total-distance-first':(92,[90,118,399,136]),'total-distance-second':(67,[65,138,132,156]),
 'friction-work':(68,[66,174,179,191]),'substitution':(69,[67,212,156,232]),'total-time':(93,[91,249,266,268]),'section-three':(97,[95,298,119,315]),'cooling-B':(98.5,[96,314,408.5,332.47]),
 'volume-alpha':(63.5,[61.5,345.6,407.5,364]),'alpha-one':(64,[63,364.5,108,382]),'same-gas':(89,[87,383,407,401]),'same-energy':(63,[61,401,407,419]),
 'first-law-heat':(63,[61,420,407,439]),'first-law-work':(63,[61,439,334,458]),'B-piston':(88,[86,478,407,496]),'B-displacement':(63.5,[61,497,407,515.5]),'B-pressure':(62.5,[60,515.5,154,533.396]),
 'B-volume':(440,[438,84,782,102.5]),'piston-distance':(440,[438,103,532,121]),'forces':(439,[437,151,782,170.9]),'force-distance':(439,[437,170.9,673.5,188.5]),
 'B-initial':(440,[438,218,701,236]),'equations':(440,[438,269,550,286]),'A-pressure':(465,[463,333,733,351.9]),'A-work-first':(440,[438,380,778,402.5]),'A-work-second':(441,[439,402.5,711,421]),
 'because':(442,[440,442,457,459]),'final-temperature':(442,[440,478,566,497.7]),'continuation':(468,[466,514.8,780,534.5])}
rows=[];used=[];edge_errors=[]
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as source:
 for r in language['rows']:
  id=r['id'];left,erase=geometry[id];t=types[id];w=weights[id]
  ids=re.findall(r'\[\[([^\]]+)\]\]',r['ko'])
  assert sorted(ids)==sorted(re.findall(r'\[\[([^\]]+)\]\]',r['en'])),id
  native=[]
  for name in ids:
   a=atoms[name]
   p=source[5].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(a['rect']),colorspace=f.csGRAY,alpha=False)
   ar=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<150
   sides={n:int(v.sum())for n,v in [('top',ar[:2,:]),('bottom',ar[-2:,:]),('left',ar[:,:2]),('right',ar[:,-2:])]}
   if any(sides.values()):edge_errors.append(dict(id=name,sides=sides))
   native.append(dict(id=name,rect=a['rect'],image_path=a['image_path'],reviewed=True,reason='Manual atlas review: complete original bitmap mathematical object; no neighbouring Chinese/punctuation. Source native image/font shape and original y/1x scale retained; dark crop borders independently zero at8x.'))
  en=w['English_source_SimSun_stroke']['stroke_points'];ko=w['Korean_source_role_Batang_stroke']['stroke_points']
  row=dict(id=id,source_ocr_hint=r['source_ocr_hint'],reviewed=False,source_prose_face='SimSun',size=t['best']['source_point_size'],baseline=t['best']['source_baseline'],left=left,right=409.95 if left<420 else 784.85,ko=r['ko'],en=r['en'],source_atom_ids=ids,atoms=native,erase_rects=[erase],printed_regular_stroke=en,printed_bold_stroke=en,printed_stroke_by_language=dict(en=dict(regular=en,bold=en),ko=dict(regular=ko,bold=ko)),source_CJK_type_evidence=t,source_print_weight_evidence_id=id,math_after_gaps_by_language={'en':{m[0]:.55 for m in re.findall(r"\[\[([^\]]+)\]\]([,:;.])",r['en'])}})
  if id=='B-volume':row['math_after_gaps_by_language']['ko']={'alphaVB':.5}
  rows.append(row);used+=ids
assert not edge_errors,edge_errors
assert sorted(used)==sorted(atoms),(set(used)^set(atoms))
plan=dict(source_page=6,source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',manual_rois_reviewed=False,publication_ready=False,source_only_type_calibration=str(B/'page06-per-row-source-type-proposals.json'),source_only_weight_calibration=str(B/'page06-row-weight-calibration.json'),rows=rows,
 protected_source_display_and_figure_rects=[[175,80.5,398,98.5],[115,153,398,173],[177,192,398,211],[178,232.1,398,248],[166,268.1,398,285],[187,458.2,404,477.7],[551,57.9,779,82.5],[575,123,780,150],[525,189,780,216],[550,236.2,780,268.5],[474,289,780,331],[575,357.071,779,379.5],[559,421.5,780,440.5],[576,459.5,780,477.9],[577,497.8,780,514.7]],
 source_split_formula_preserved=dict(parts=['alpha','one'],reason='Original prose says alpha less than1 across two source lines. Both original mathematical objects retain their source y; no native math retyped.'))
(B/'authoring/page06-layout-proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
errors=[]
for lang in ['ko','en']:
 _,metric,_=new_font(font_path(lang),' '.join(re.sub(r'\[\[[^\]]+\]\]','',r[lang])for r in rows))
 for row in rows:
  try:row_layout(row,lang,metric)
  except ValueError as e:errors.append((lang,row['id'],str(e)));print(*errors[-1],flush=True)
print('PAGE06_LAYOUT_PROPOSAL',len(rows),len(used),'FONT_SIZE_UNCHANGED_OVERFLOWS',len(errors),flush=True)
