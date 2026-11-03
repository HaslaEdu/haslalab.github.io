"""Source-line geometry and native scan atoms, all measured independently."""
from pathlib import Path
import json,sys,re
import pymupdf as f,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import new_font,font_path,row_layout
language=json.loads((B/'authoring/page08-language-row-proposals.json').read_text('utf8'))
types=json.loads((B/'page08-per-row-source-type-proposals.json').read_text('utf8'));weights=json.loads((B/'page08-row-weight-calibration.json').read_text('utf8'))
assert types['complete'] and weights['complete'];types={r['id']:r for r in types['rows']};weights={r['id']:r for r in weights['rows']}
atoms={r['id']:r for r in json.loads((B/'authoring/page08-native-math-proposals.json').read_text('utf8'))['atoms']}
assert not any(r['search_boundary_touched']for r in atoms.values())
geometry={
 'recovery-force-first':(62,[60,56.5,405,76.5]), 'recovery-force-second':(62,[60,76.5,121,94]),
 'linear-fixed':(62,[60,165,407,184.5]), 'linear-coefficients':(62,[60,184.5,407,203.5]),
 'linear-constant':(62,[60,203.5,407,223]), 'linear-variable':(62,[60,223,362,243]),
 'coefficients':(62,[60,280.5,92,299.5]), 'compression-work':(65,[63,443,333,460.5]),
 'recovery-work':(439,[437,64.5,709,84.5]), 'absorption':(440,[438,121.5,637,141]),
 'efficiency':(439,[437,171.5,686,190]), 'section-five':(464,[462,208.5,485,225.5]),
 'excited-energy':(464,[462,227,579,244.5]), 'emission-first':(439,[437,263.5,780,281.5]),
 'emission-second':(439,[437,281.5,737,300]), 'recoil-momentum':(439,[437,330,591,347.5]),
 'emission-energy':(439,[437,376.5,598,394.75]), 'relativistic-first':(440,[438,418.5,777,437]),
 'relativistic-second':(440,[438,437,660,455])
}
rows=[];used=[];edge_errors=[]
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as source:
 for r in language['rows']:
  id=r['id'];left,erase=geometry[id];t=types[id];w=weights[id];ids=re.findall(r'\[\[([^\]]+)\]\]',r['ko'])
  assert sorted(ids)==sorted(re.findall(r'\[\[([^\]]+)\]\]',r['en'])),id
  native=[]
  for name in ids:
   a=atoms[name];p=source[7].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(a['rect']),colorspace=f.csGRAY,alpha=False);ar=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<150
   sides={n:int(v.sum())for n,v in [('top',ar[:2,:]),('bottom',ar[-2:,:]),('left',ar[:,:2]),('right',ar[:,-2:])]}
   if any(sides.values()):edge_errors.append(dict(id=name,sides=sides))
   native.append(dict(id=name,rect=a['rect'],image_path=a['image_path'],reviewed=True,reason='Manual source/atlas review: complete original mathematical bitmap object and native equation/digit/list punctuation. Source image encoded program, original y and unit scale retained; all four crop borders independently clear at8x.'))
  en=w['English_source_SimSun_stroke']['stroke_points'];ko=w['Korean_source_role_Batang_stroke']['stroke_points']
  rows.append(dict(id=id,source_ocr_hint=r['source_ocr_hint'],reviewed=False,source_prose_face='SimSun',size=t['best']['source_point_size'],baseline=t['best']['source_baseline'],left=left,right=409.95 if left<420 else 784.85,ko=r['ko'],en=r['en'],source_atom_ids=ids,atoms=native,erase_rects=[erase],printed_regular_stroke=en,printed_bold_stroke=en,printed_stroke_by_language=dict(en=dict(regular=en,bold=en),ko=dict(regular=ko,bold=ko)),source_CJK_type_evidence=t,source_print_weight_evidence_id=id,math_after_gaps_by_language={'ko':({'eq11-12':.5,'F-prime':.75} if id=='recovery-force-first'else{}),'en':{m[0]:.55 for m in re.findall(r'\[\[([^\]]+)\]\]([,:;.])',r['en'])}}));used+=ids
assert not edge_errors,edge_errors
assert sorted(used)==sorted(atoms),(set(used)^set(atoms))
plan=dict(source_page=8,source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',manual_rois_reviewed=False,publication_ready=False,source_only_type_calibration=str(B/'page08-per-row-source-type-proposals.json'),source_only_weight_calibration=str(B/'page08-row-weight-calibration.json'),rows=rows,
 protected_source_display_and_figure_rects=[[100,95,409,164.75],[130,244,409,278.5],[100,300,409,367.95],[112,375.6,409,442.5],[150,461,409,486.6],[523,85.5,784,113.02],[465,142,784,171],[563,190.5,784,208],[548,244.75,784,262.5],[565,300.25,784,329],[565,348,784,375],[522,395,784,413.55],[574,456,784,476],[560,477,784,521.846]])
errors=[]
for lang in ['ko','en']:
 _,metric,_=new_font(font_path(lang),' '.join(re.sub(r'\[\[[^\]]+\]\]','',r[lang])for r in rows))
 for row in rows:
  try:row_layout(row,lang,metric)
  except ValueError as e:errors.append((lang,row['id'],str(e)));print(*errors[-1],flush=True)
(B/'authoring/page08-layout-proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
print('PAGE08_LAYOUT_PROPOSAL',len(rows),len(used),'FIXED_SIZE_OVERFLOWS',len(errors),flush=True)
