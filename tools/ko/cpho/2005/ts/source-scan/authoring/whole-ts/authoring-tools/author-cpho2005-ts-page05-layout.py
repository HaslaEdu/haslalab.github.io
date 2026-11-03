"""Explicit reviewed source-line geometry; fixed measured type and native math."""
from pathlib import Path
import json,sys,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import new_font,font_path,row_layout
language=json.loads((B/'authoring/page05-language-row-proposals.json').read_text('utf8'))
types=json.loads((B/'page05-per-row-source-type-proposals.json').read_text('utf8'));weights=json.loads((B/'page05-row-weight-calibration.json').read_text('utf8'))
assert types['complete']and weights['complete']
types={r['id']:r for r in types['rows']};weights={r['id']:r for r in weights['rows']}
atoms={r['id']:r for r in json.loads((B/'authoring/page05-native-math-proposals.json').read_text('utf8'))['atoms']}
assert not any(a['search_boundary_touched']for a in atoms.values())
geometry={
'angle-threshold':(63,410.7,[62,56.93,408.9,93]),'angle-transit':(66.25,410.7,[64,92.8,408.9,112.8]),'angle-transit-end':(66.25,410.7,[64,113,160.5,132]),'section-two':(91.75,220.5,[89.5,133,115,149]),'axis-direction':(92.25,220.5,[90,150,220,167.5]),'axis-origin':(67.5,220.5,[65.5,168.3,220.5,186.5]),'axis-position':(67.5,220.5,[65.5,187.2,220.5,205]),'release':(66.5,220.5,[65.5,206,220.5,224.5]),'spring-system':(66.5,222.5,[65.5,224.5,222.5,243.6]),'one-system':(63,410.7,[61.5,247.3,408.5,265]),'system-force':(63,410.7,[61.5,265.5,409.2,285.2]),'initial-friction':(63.25,410.7,[61.5,285.3,409.2,305]),'initial-acceleration':(63,410.7,[61.5,305.2,409.2,323.3]),'acceleration-definition':(63,410.7,[61.5,323.5,106.5,341.5]),'zero-acceleration':(63,410.7,[61.5,361.5,409.5,380.5]),'equilibrium-position':(63,410.7,[61.5,381.5,382.5,401]),'overshoot':(63.75,410.7,[61.5,430,408.5,448.5]),'constant-gravity':(63.5,410.7,[61.5,448.5,409.5,468.7]),'spring-restoration':(63.5,410.7,[61.5,468.7,409.5,487.5]),'shm-period':(63.5,410.7,[61.5,487.5,265.5,507.5]),
'amplitude-and-time':(439,784.85,[437.5,97.5,717.5,115.3]),'right-travel':(465.5,784.85,[463,146,782.5,165]),'turning-forces':(438,784.85,[437.5,165.3,783,184.5]),'turning-resultant':(439,784.85,[437.5,185.5,635,206]),'left-acceleration':(439.25,784.85,[437.5,228.3,783.5,247]),'left-coordinates':(439.5,784.85,[437.5,247.3,691,266]),'second-equilibrium':(440,784.85,[437.5,286.3,771,305.5]),'left-SHM-first':(437.5,784.85,[436,335.5,773.5,355.5]),'left-SHM-second':(438.5,784.85,[436,355.8,773.5,376.5]),'left-SHM-third':(439,784.85,[436,376.5,774,395.5]),'left-SHM-fourth':(439,784.85,[436,395.5,522,414]),'last-rest':(440,784.85,[438.5,442,616.5,460]),'extension':(441,784.85,[438.5,479,648,498])}
rows=[];used=[]
for record in language['rows']:
 id=record['id'];t=types[id];w=weights[id];left,right,erase=geometry[id];ids=re.findall(r'\[\[([^\]]+)\]\]',record['ko'])
 assert sorted(ids)==sorted(re.findall(r'\[\[([^\]]+)\]\]',record['en'])),id
 used+=ids
 original_atoms=[]
 for name in ids:
  a=atoms[name];original_atoms.append(dict(id=name,rect=a['rect'],image_path=a['image_path'],reviewed=True,reason='Complete original mathematical glyph/object manually reviewed in corrected source crop atlas; no Chinese or unwanted punctuation, no clipped edge. Native bitmap program and vertical geometry retained.'))
 en=w['English_source_SimSun_stroke']['stroke_points'];ko=w['Korean_source_role_Batang_stroke']['stroke_points']
 row=dict(id=id,source_ocr_hint=record['source_ocr_hint'],reviewed=False,source_prose_face='SimSun',size=t['best']['source_point_size'],baseline=t['best']['source_baseline'],left=left,right=right,ko=record['ko'],en=record['en'],source_atom_ids=ids,atoms=original_atoms,erase_rects=[erase],printed_regular_stroke=en,printed_bold_stroke=en,printed_stroke_by_language=dict(en=dict(regular=en,bold=en),ko=dict(regular=ko,bold=ko)),source_CJK_type_evidence=t,source_print_weight_evidence_id=id,math_after_gaps_by_language={'en':{m[0]:.55 for m in re.findall(r"\[\[([^\]]+)\]\]([,:;.'\u0021])",record['en'])}})
 if id=='spring-system':row['math_after_gaps_by_language']['ko']={'B-system':.5}
 rows.append(row)
assert sorted(used)==sorted(atoms),(set(used)^set(atoms))
plan=dict(source_page=5,source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',manual_rois_reviewed=False,publication_ready=False,source_only_type_calibration=str(B/'page05-per-row-source-type-proposals.json'),source_only_weight_calibration=str(B/'page05-row-weight-calibration.json'),rows=rows,
 protected_source_display_and_figure_rects=[[237,159,399,227],[149,343,407,362],[163,405,407,427],[527,66,783,95],[552,120,783,140],[564,208,783,226],[538,266,783,286],[534,310.047,772,333.5],[545,414,773,441],[487,460.5,730,480],[749,456,776,476],[548,497.5,655,516],[747,495.5,776,514],[560,516,635,536.54],[746,513,776,533]],
 source_split_formulas_preserved=[dict(parts=['x-equal','x1-equal'],reason='Source x=x1 genuinely breaks across left-column source lines; keep both bitmap fragments at their original y positions.'),dict(parts=['2x1-amplitude','minus-x2-amplitude'],reason='Source amplitude2x1-x2 breaks across right-column source lines; keep both fragments at their original y positions.')])
(B/'authoring/page05-layout-proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
for lang in ['ko','en']:
 _,metric,_=new_font(font_path(lang),' '.join(re.sub(r'\[\[[^\]]+\]\]','',r[lang])for r in rows))
 for row in rows:
  try:row_layout(row,lang,metric)
  except ValueError as e:print(lang,row['id'],e,flush=True)
print('UNREVIEWED_PAGE05_LAYOUT',len(rows),len(used),flush=True)
