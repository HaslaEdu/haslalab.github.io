"""Source-line geometry and native scan atoms, all measured independently."""
from pathlib import Path
import json,sys,re
import pymupdf as f,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import new_font,font_path,row_layout
language=json.loads((B/'authoring/page10-language-row-proposals.json').read_text('utf8'))
types=json.loads((B/'page10-per-row-source-type-proposals.json').read_text('utf8'));weights=json.loads((B/'page10-row-weight-calibration.json').read_text('utf8'))
assert types['complete'] and weights['complete'];types={r['id']:r for r in types['rows']};weights={r['id']:r for r in weights['rows']}
atoms={r['id']:r for r in json.loads((B/'authoring/page10-native-math-proposals.json').read_text('utf8'))['atoms']}
assert not any(r['search_boundary_touched']for r in atoms.values())
source_geometry=json.loads((B/'authoring/page10-source-geometry-proposal.json').read_text('utf8'));geometry=source_geometry['geometry']
rows=[];used=[];edge_errors=[]
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as source:
 for r in language['rows']:
  id=r['id'];left,erase=geometry[id];t=types[id];w=weights[id];assert w['source_point_size']==t['best']['source_point_size'] and w['source_measurement_window']==t['source_measurement_window'];ids=re.findall(r'\[\[([^\]]+)\]\]',r['ko'])
  assert sorted(ids)==sorted(re.findall(r'\[\[([^\]]+)\]\]',r['en'])),id
  native=[]
  for name in ids:
   a=atoms[name];p=source[9].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(a['rect']),colorspace=f.csGRAY,alpha=False);ar=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<150
   sides={n:int(v.sum())for n,v in [('top',ar[:2,:]),('bottom',ar[-2:,:]),('left',ar[:,:2]),('right',ar[:,-2:])]}
   if any(sides.values()):edge_errors.append(dict(id=name,sides=sides))
   native.append(dict(id=name,rect=a['rect'],image_path=a['image_path'],reviewed=True,reason='Manual source/atlas review: complete original mathematical bitmap object and native equation/digit/list punctuation. Source image encoded program, original y and unit scale retained; all four crop borders independently clear at8x.'))
  en=w['English_source_SimSun_stroke']['stroke_points'];ko=w['Korean_source_role_Batang_stroke']['stroke_points']
  rows.append(dict(id=id,source_ocr_hint=r['source_ocr_hint'],reviewed=False,source_prose_face='SimSun',size=t['best']['source_point_size'],baseline=t['best']['source_baseline'],left=left,right=source_geometry['right_edges'].get(id,409.95 if left<420 else 784.85),ko=r['ko'],en=r['en'],source_atom_ids=ids,atoms=native,erase_rects=[erase],printed_regular_stroke=en,printed_bold_stroke=en,printed_stroke_by_language=dict(en=dict(regular=en,bold=en),ko=dict(regular=ko,bold=ko)),source_CJK_type_evidence=t,source_print_weight_evidence_id=id,math_after_gaps_by_language={'ko':source_geometry['ko_math_gaps'].get(id,{}),'en':{m[0]:.55 for m in re.findall(r'\[\[([^\]]+)\]\]([,:;.])',r['en'])}}));used+=ids
assert not edge_errors,edge_errors
assert sorted(used)==sorted(atoms),(set(used)^set(atoms))
plan=dict(source_page=10,source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',manual_rois_reviewed=False,publication_ready=False,source_only_type_calibration=str(B/'page10-per-row-source-type-proposals.json'),source_only_weight_calibration=str(B/'page10-row-weight-calibration.json'),rows=rows,
 protected_source_display_and_figure_rects=source_geometry['protected'])

errors=[]
for lang in ['ko','en']:
 _,metric,_=new_font(font_path(lang),' '.join(re.sub(r'\[\[[^\]]+\]\]','',r[lang])for r in rows))
 for row in rows:
  try:
   if row['id']in source_geometry['center_slots']:
    _,end=row_layout(row,lang,metric);center=source_geometry['center_slots'][row['id']]['original_source_center']
    row.setdefault('left_by_language',{})[lang]=center-(end-row['left'])/2;row['original_source_center']=center
   row_layout(row,lang,metric)
  except ValueError as e:errors.append((lang,row['id'],str(e)));print(*errors[-1],flush=True)
(B/'authoring/page10-layout-proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
print('PAGE10_LAYOUT_PROPOSAL',len(rows),len(used),'FIXED_SIZE_OVERFLOWS',len(errors),flush=True)
