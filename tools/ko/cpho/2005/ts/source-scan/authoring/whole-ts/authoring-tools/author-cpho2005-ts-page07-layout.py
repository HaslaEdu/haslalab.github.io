"""Explicit source-line erase geometry and protected source display equations."""
from pathlib import Path
import json,sys,re
import pymupdf as f,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import new_font,font_path,row_layout
language=json.loads((B/'authoring/page07-language-row-proposals.json').read_text('utf8'))
types=json.loads((B/'page07-per-row-source-type-proposals.json').read_text('utf8'))
weights=json.loads((B/'page07-row-weight-calibration.json').read_text('utf8'))
assert types['complete'] and weights['complete']
types={r['id']:r for r in types['rows']};weights={r['id']:r for r in weights['rows']}
atoms={r['id']:r for r in json.loads((B/'authoring/page07-native-math-proposals.json').read_text('utf8'))['atoms']}
assert not any(r['search_boundary_touched']for r in atoms.values())
geometry={'same-moles': (68, [66, 64.5, 150, 83]), 'B-final': (68.5, [66.5, 100, 404, 120]), 'state-equation': (68, [66, 121, 83, 139]), 'equation-range': (69, [67, 170, 173, 190]), 'substitution': (70, [68, 233.5, 216, 252]), 'section-four': (94, [92, 285.5, 117, 304]), 'compression-first': (94, [92, 302.5, 407, 321.5]), 'compression-second': (70, [68, 321.5, 408, 341]), 'contact-forces': (70, [68, 339.5, 408, 359.5]), 'friction-forces': (70, [68, 358.2, 408, 377.25]), 'extra-compression': (64, [62, 387.371, 407, 408]), 'before-impact': (64, [62, 407, 248, 426]), 'caption': (601, [599, 219, 627, 238]), 'massless': (440, [438, 237.5, 783, 256]), 'resultant': (440, [438, 257, 782, 275]), 'components': (440, [438, 275, 582, 293]), 'combine': (441, [439, 335.5, 532, 353.02]), 'recovery-first': (461, [459, 438.146, 783, 458]), 'recovery-second': (436, [434, 458, 674, 477])}
rows=[];used=[];edge_errors=[]
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as source:
 for r in language['rows']:
  id=r['id'];left,erase=geometry[id];t=types[id];w=weights[id]
  ids=re.findall(r'\[\[([^\]]+)\]\]',r['ko'])
  assert sorted(ids)==sorted(re.findall(r'\[\[([^\]]+)\]\]',r['en'])),id
  native=[]
  for name in ids:
   a=atoms[name]
   p=source[6].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(a['rect']),colorspace=f.csGRAY,alpha=False)
   ar=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<150
   sides={n:int(v.sum())for n,v in [('top',ar[:2,:]),('bottom',ar[-2:,:]),('left',ar[:,:2]),('right',ar[:,-2:])]}
   if any(sides.values()):edge_errors.append(dict(id=name,sides=sides))
   native.append(dict(id=name,rect=a['rect'],image_path=a['image_path'],reviewed=True,reason='Manual atlas review: complete original bitmap mathematical object; no neighbouring Chinese; original list punctuation before fP/fQ is intentionally retained and not duplicated. Source native image/font shape and original y/1x scale retained; dark crop borders independently zero at8x.'))
  en=w['English_source_SimSun_stroke']['stroke_points'];ko=w['Korean_source_role_Batang_stroke']['stroke_points']
  row=dict(id=id,source_ocr_hint=r['source_ocr_hint'],reviewed=False,source_prose_face='SimSun',size=t['best']['source_point_size'],baseline=t['best']['source_baseline'],left=left,right=409.95 if left<420 else 784.85,ko=r['ko'],en=r['en'],source_atom_ids=ids,atoms=native,erase_rects=[erase],printed_regular_stroke=en,printed_bold_stroke=en,printed_stroke_by_language=dict(en=dict(regular=en,bold=en),ko=dict(regular=ko,bold=ko)),source_CJK_type_evidence=t,source_print_weight_evidence_id=id,math_after_gaps_by_language={'en':{m[0]:.55 for m in re.findall(r"\[\[([^\]]+)\]\]([,:;.])",r['en'])}})
  if id=='friction-forces':
   for language_key in ['ko','en']:row['math_after_gaps_by_language'].setdefault(language_key,{}).update({'fN':1.125,'fP':.5})
   row['source_math_list_spacing_evidence']='Native fN crop right101.25; fP crop left102.375 right118.375; fQ crop left118.875. Keep their original1.125pt/0.5pt inter-crop gaps so all3 native objects retain one common source-to-target horizontal translation.'
  if id=='compression-first':row['math_after_gaps_by_language'].setdefault('ko',{}).update({'F-external':.5})
  rows.append(row);used+=ids
assert not edge_errors,edge_errors
assert sorted(used)==sorted(atoms),(set(used)^set(atoms))
plan=dict(source_page=7,source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',manual_rois_reviewed=False,publication_ready=False,source_only_type_calibration=str(B/'page07-per-row-source-type-proposals.json'),source_only_weight_calibration=str(B/'page07-row-weight-calibration.json'),rows=rows,
 protected_source_display_and_figure_rects=[[210, 81, 405, 100], [153, 140, 405, 170.5], [93, 190.2, 405, 233], [117, 252.2, 406, 285.4], [163, 427, 405, 445], [163, 446, 405, 474], [185, 474.5, 405, 502], [184, 502.2, 405, 521.621], [559, 56.77, 784, 129], [476, 145, 748, 215], [502, 294, 785, 314], [490, 315, 785, 334.5], [478, 357.97, 784, 426.22], [496, 477.2, 784, 495], [482, 496, 784, 517.646]],
 original_math_list_separators_retained=['fP','fQ'],figure_caption_original_center=612.0)
(B/'authoring/page07-layout-proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
errors=[]
for lang in ['ko','en']:
 _,metric,_=new_font(font_path(lang),' '.join(re.sub(r'\[\[[^\]]+\]\]','',r[lang])for r in rows))
 for row in rows:
  try:
   if row['id']=='caption':
    tokens,end=row_layout(row,lang,metric)
    row.setdefault('left_by_language',{})[lang]=612.0-(end-row['left'])/2
    row['original_caption_center']=612.0
   row_layout(row,lang,metric)
  except ValueError as e:errors.append((lang,row['id'],str(e)));print(*errors[-1],flush=True)
print('PAGE06_LAYOUT_PROPOSAL',len(rows),len(used),'FONT_SIZE_UNCHANGED_OVERFLOWS',len(errors),flush=True)

(B/'authoring/page07-layout-proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
