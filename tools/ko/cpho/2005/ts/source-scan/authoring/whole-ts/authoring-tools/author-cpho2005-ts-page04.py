from pathlib import Path
import json,sys,re
import pymupdf as f
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import new_font,font_path,width,row_layout
atoms={}
def atom(name,rect,path):
 atoms[name]=dict(id=name,rect=rect,image_path=[path],reason='Manually selected original bitmap mathematical glyphs; preserve source image program, scale and vertical position.')
for a in json.loads((B/'authoring/page04-definition-atom-proposals.json').read_text())['atoms']:
 atom(a['id'],[355.3,118.8,364.1,132.06] if a['id']=='t2' else a['rect'],343)
for name,rect in dict(c=[79.5,263.1,88.2,272.8],eq1=[79.1,365.7,96.5,378.6],eq2=[104.1,365.7,121.3,378.6],eq3=[129.0,365.7,146.2,378.6],cond_lt=[104.2,454.4,306.0,485.2],rel_lt=[326.1,467.3,368.3,480.4],cond_gt=[104.2,490.1,306.0,520.19],rel_gt=[326.1,503.2,368.3,516.8]).items():atom(name,rect,352)
for name,rect in dict(cond_eq=[481.0,67.0,675.5,96.8],rel_eq=[702.1,81.5,740.0,91.7],rel_five=[459.0,163.5,501.0,174.97],circ_five=[548.0,161.5,560.8,174.9]).items():atom(name,rect,361)
for name,rect in dict(rel_six=[456.1,238.1,495.0,249.4],circ_six=[539.5,234.6,553.2,248.8],rel_seven=[457.1,293.8,495.6,306.0],item2=[463.5,310.5,473.7,321.0],nfirst1=[492.4,309.5,545.6,322.5],nfirst2=[552.5,308.9,606.0,321.9],sin_i=[455.5,366.0,475.8,379.2],one=[519.0,366.0,525.5,379.5],eq5=[541.7,366.5,558.6,379.0],eq6=[580.8,366.0,597.7,378.3],circ_always=[721.0,359.9,734.1,375.1],nsecond1=[481.4,405.8,536.7,420.0],nsecond2=[541.5,403.5,595.25,416.5]).items():atom(name,rect,370)
for name,rect in dict(last5=[454.0,472.1,471.5,487.0],last6=[479.0,471.7,496.8,486.4],angle=[596.5,472.3,603.5,484.0],circ_large=[692.0,465.7,705.8,481.0],angle_small=[521.0,493.2,528.0,505.7],circ_small=[627.5,486.0,640.9,501.0]).items():atom(name,rect,379)
# Complete source glyph edges, reviewed against the original line rulers and
# source-only connected-component bounds. These add original white scan padding;
# no glyph is reconstructed, stretched, or displaced vertically.
for name,rect in dict(light2=[348.7,97.8,365.0,112.8],t2=[353.8,118.8,364.1,132.06],eq1=[79.1,365.1,96.5,378.6],eq2=[104.1,365.1,121.3,378.6],cond_lt=[104.2,452.9,306,485.2],rel_lt=[324.6,466.8,368.3,480.4],cond_gt=[104.2,488.6,306,520.19],rel_gt=[324.6,501.7,368.3,516.8],cond_eq=[481,66.2,677,98.3],rel_five=[457.5,163.5,501,174.97],circ_five=[546.5,160,560.8,174.9],rel_six=[456.1,238.1,496,249.4],circ_six=[539.5,234.6,554.3,248.8],rel_seven=[457.1,293.8,496.6,306],sin_i=[454.5,366,475.8,379.2],one=[517.7,365.5,526.8,379.5],circ_always=[719.5,359.9,734.1,376.6],nsecond1=[481.4,403.8,535.7,420],last5=[454,470.6,471.5,487],last6=[477.5,470.2,496.8,486.4],angle=[596.5,470.8,603.5,484],circ_large=[690.5,465.7,705.8,481]).items():
 atoms[name]['rect']=rect
for name,rect in dict(cond_eq=[481,66.2,679.3,98.3],rel_five=[462,164,500.5,173.8],one=[518,368,522.6,378],last6=[477.5,470.2,496.8,485.0]).items():atoms[name]['rect']=rect
rows=[]
def row(name,baseline,left,right,size,ko,en,erase,face='SimSun'):
 ids=re.findall(r'\[\[([^\]]+)\]\]',ko)
 assert sorted(ids)==sorted(re.findall(r'\[\[([^\]]+)\]\]',en)),(name,ko,en)
 rows.append(dict(id=name,reviewed=False,baseline=baseline,left=left,right=right,size=size,source_prose_face=face,ko=ko,en=en,source_atom_ids=ids,atoms=[atoms[k]for k in ids],erase_rects=erase))
row('title',73.5,97,151.5,12.125,'참고 해설','Solutions',[[98.3,60.1,149.9,76.5]],'SimHei')
for lang,text in [('ko','참고 해설'),('en','Solutions')]:
 _,m,_=new_font(font_path(lang,'SimHei'),text)
 rows[-1].setdefault('left_by_language',{})[lang]=123.75-width(m,text,12.125)/2
row('section',92,90.5,410,12.3,'1.','1.',[[89.5,84.8,110.1,94.0]])
row('definitions-1',110,90.5,409.95,12.3,'[[item1]] 판의 두께를 [[d]], [[light1]], [[light2]]의 판 내 속력을 각각 [[v1]], [[v2]],','[[item1]] [[d]]: slab thickness; [[v1]], [[v2]]: speeds of [[light1]], [[light2]];',[[89.5,98.0,409.9,116.0]])
row('definitions-2',128.75,66.5,409.95,12.3,'굴절각을 [[r1]], [[r2]], 판 통과 시간을 [[t1]], [[t2]]라 하면','[[r1]], [[r2]]: refraction angles; [[t1]], [[t2]]: transit times',[[65,117.0,409.9,132.07]])
row('definitions-3',154.75,66.5,409.95,12.425,'다음이 성립한다.','through the slab. Then',[[65,142.0,312.2,157.3]])
row('vacuum-1',269.75,66.5,262,12.425,'진공 속 빛의 속력을 [[c]]라 하자.','Let [[c]] be the speed of light',[[65,257.8,259.2,274.8]])
row('vacuum-2',289.25,66.5,409.95,12.425,'공기 중 속력과 거의 같으며 다음을 만족한다.','in vacuum, nearly its speed in air. Then',[[65,277.5,265.0,293.5]])
row('snell',338.25,66.5,409.95,12.425,'굴절 법칙에 따라','By the law of refraction,',[[65,326.3,153.2,341.9]])
row('equations-1-3',375.5,66.5,409.95,12.425,'식 [[eq1]], [[eq2]], [[eq3]]에서','From [[eq1]], [[eq2]], [[eq3]],',[[65,363.0,218,380.6]])
row('condition-lt',475.75,94,409.95,12.425,'[[cond_lt]]이면 [[rel_lt]]','If [[cond_lt]], [[rel_lt]]',[[65,454.4,369.5,485.2]])
row('condition-gt',511.5,94,409.95,12.425,'[[cond_gt]]이면 [[rel_gt]]','If [[cond_gt]], [[rel_gt]]',[[103.5,490.1,369.5,520.19]])
row('condition-eq',91.5,468,784.85,12.475,'[[cond_eq]]이면 [[rel_eq]]','If [[cond_eq]], [[rel_eq]]',[[480.5,67,743,97]])
row('simplified',115,441.75,784.85,12.475,'정리하면 다음과 같다.','Simplifying gives:',[[440,102.0,514.5,119.5]])
row('sin-greater',171.25,439,784.85,12.475,'이면 [[rel_five]]로 단색광 [[circ_five]]의 통과 시간이 짧다.','Then [[rel_five]]: light [[circ_five]] crosses sooner.',[[437,160.0,670.5,175]])
row('sin-less',246.25,438,784.85,12.175,'이면 [[rel_six]]로 단색광 [[circ_six]]의 통과 시간이 짧다.','Then [[rel_six]]: light [[circ_six]] crosses sooner.',[[435,232.5,666,251.5]])
row('sin-equal',301.5,438,784.85,12.175,'이면 [[rel_seven]]로 두 단색광의 통과 시간이 같다.','Then [[rel_seven]]: both lights take equal time.',[[435,288.5,653,307.5]])
row('indices-first',320.5,464,784.85,12.175,'[[item2]] [[nfirst1]], [[nfirst2]]이면','[[item2]] For [[nfirst1]], [[nfirst2]],',[[462.5,307.8,647,325.7]])
row('always-second-1',376.0,438,784.85,12.175,'[[sin_i]]의 최댓값은 [[one]]이다. 식 [[eq5]], [[eq6]]에 따라 단색광 [[circ_always]]의','Since [[sin_i]] cannot exceed [[one]], [[eq5]], [[eq6]] show that light [[circ_always]]',[[435,359,784.85,383]])
row('always-second-2',397.75,438,784.85,12.175,'통과 시간이 입사각에 관계없이 더 짧다.','crosses sooner at every angle of incidence.',[[435,384.5,610,401.5]])
row('indices-second',415.75,464,784.85,12.175,'[[nsecond1]], [[nsecond2]]이면','For [[nsecond1]], [[nsecond2]],',[[463,402.0,637,422.0]])
row('large-small-angle-1',482,438,784.85,12.425,'식 [[last5]], [[last6]]에 따라 입사각 [[angle]]가 크면 단색광 [[circ_large]]의','From [[last5]], [[last6]], light [[circ_large]] crosses sooner for large [[angle]],',[[435,464.7,784.85,488]])
row('large-small-angle-2',503.75,438,784.85,12.425,'시간이 짧고, [[angle_small]]가 작으면 [[circ_small]]의 시간이 짧다. 그 이유는','and light [[circ_small]] for small [[angle_small]]. Since',[[435,488,784.85,506.69]])
calibration=json.loads((B/'page04-source-stroke-calibration.json').read_text('utf8'))
source_strokes={r['field']:r['best']['stroke_points']for r in calibration['fields']}
korean_calibration=json.loads((B/'page04-korean-stem-calibration.json').read_text('utf8'))
korean_strokes={r['field']:r['best']['stroke_points']for r in korean_calibration['fields']}
for r in rows:
 field='heading'if r['id']=='title'else 'left-top'if r['size']==12.3 else 'left-bottom'if r['left']<410 else 'right-top'if r['size']==12.475 else 'right-middle'
 r.update(printed_regular_stroke=source_strokes[field],printed_bold_stroke=source_strokes[field],source_stroke_calibration_field=field)
 r['printed_stroke_by_language']=dict(en=dict(regular=source_strokes[field],bold=source_strokes[field]),ko=dict(regular=korean_strokes[field],bold=korean_strokes[field],evidence='page04-korean-stem-calibration.json: independent primary vertical/horizontal stem widths and contrast at fixed original physical font pointsize; no density/width fitting.'))
 r['math_after_gaps_by_language']={'en':{match[0]:.55 for match in re.findall(r'\[\[([^\]]+)\]\]([,:;.])',r['en'])}}
plan=dict(source_page=4,source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',manual_rois_reviewed=False,publication_ready=False,source_only_stroke_calibration=str(B/'page04-source-stroke-calibration.json'),rows=rows)
plan['protected_source_display_and_figure_rects']=[[108,160,261,254],[268,164,384,264],[134,297,407,326],[121,345,406,361.5],[155,384,406,448],[526,124,783,157.3],[520,201,780,230],[520,253,778,285],[538,331,679,362],[538,424,680,455]]
(B/'authoring/page04-layout-proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
canvas=Image.new('RGB',(1500,((len(atoms)+5)//6)*150),'#ddd');draw=ImageDraw.Draw(canvas)
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf') as d:
 for i,(name,a)in enumerate(atoms.items()):
  pix=d[3].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(a['rect']),alpha=False)
  im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
  if im.width>235:
   # Contact-sheet preview only. Source and replay assets are never resampled.
   im.thumbnail((235,112))
  x=i%6*250;y=i//6*150;canvas.paste(im,(x+6,y+22));draw.text((x+6,y+3),name,fill='black')
canvas.save(B/'source-renders/page04-all-atom-proposals.png')
for lang in ['ko','en']:
 for face in ['SimSun','SimHei']:
  _,metric,_=new_font(font_path(lang,face),''.join(re.sub(r'\[\[[^\]]+\]\]','',r[lang])for r in rows if r['source_prose_face']==face))
  for r in rows:
   if r['source_prose_face']!=face:continue
   try:row_layout(r,lang,metric)
   except Exception as e:print(lang,r['id'],repr(e),flush=True)
print('UNREVIEWED_PAGE04_PLAN_CREATED',len(rows),len(atoms),flush=True)
