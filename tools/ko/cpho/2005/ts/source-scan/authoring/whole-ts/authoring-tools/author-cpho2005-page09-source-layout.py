"""Explicit human-read source rows, geometry and native bitmap math windows."""
from pathlib import Path
import json,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');rows=[];samples=[];geometry={}
def row(id,hint,ko,en,sample,window,left,erase):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en));geometry[id]=(left,erase)
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=sample,source_measurement_window=window))
row('eq3-6',1,'식 [[eq3-6]]에서','From [[eq3-6]],','各式可得',[134,62,185,78],67,[65,61.5,186,78])
row('wavelength-since',None,'다음 관계에서','Since','因',[67,128,80,143],68,[66,127,81,143])
row('wavelength-result',14,'따라서','hence','故得',[67,163,94,179],68,[66,162,95,180])
row('towards-first',18,'[[part-two]] 검출기로 접근하는 들뜬 핵을 보자. 최대 속력 [[approach-u]]로','[[part-two]] Excited nucleus towards detector. Maximum speed: [[approach-u]],','考虑激发',[104,186,157,203],92,[90,185,407,203])
row('towards-second',20,'접근하는 핵의 방출 후 운동량을 [[p1]], 광자 진동수를','nuclear momentum after emission: [[p1]], photon frequency:','向仪器运',[67,204,119,222],69,[67,203,407,223])
row('towards-third',22,'[[nu1]]이라 하면 운동량 보존으로','[[nu1]]. Momentum conservation gives','表示光子',[82,224,134,241],69,[67,223,264,242])
row('energy',33,'에너지 보존으로','Energy conservation gives','由能量守',[70,315,121,332],71,[69,314,134,333])
row('first-mass',39,'바닥상태 핵의 상대론적 질량을 [[m1]], 속도를 [[v1]]이라 하면','Ground-state nucleus: relativistic mass [[m1]], velocity [[v1]].','表示基态',[114,396,167,414],71,[69,395,407,415])
row('eq9-13',50,'식 [[eq9-13]]에서','From [[eq9-13]],','式可得',[144,488,183,504],73,[71,487,184,504])
row('eq8',9,'식 [[eq8]]을 쓰면','Using [[eq8]],','注意到',[446,95,484,110],447,[445,94,535,111])
row('approach-range-first',12,'식 [[eq15]]에서 접근하는 핵의 속력이 [[range-u]]보다 작으면 방출','By [[eq15]], approach speeds below [[range-u]] give photon wavelengths','向着仪器',[537,144,590,161],448,[446,142.5,781,161])
row('approach-range-second',16,'광자 파장은 [[range-lambda1]]보다 크다. 속력이 영에서 [[range2-u]] 사이인 핵이','above [[range-lambda1]]. Speeds from zero to [[range2-u]] give photon','发出的光',[446,162,499,180],448,[446,161,781,180])
row('approach-range-third',19,'방출하는 광자 파장은 [[lambda0]]와 [[lambda1]] 사이에 분포한다.','wavelengths between [[lambda0]] and [[lambda1]].','态核发出',[439,187,491,205],440,[438,186,685,205])
row('away-first',21,'다음은 검출기에서 멀어지는 들뜬 핵이다. 최대 속력 [[away-u]]로','Excited nuclei moving away at maximum speed [[away-u]],','再考虑激',[464,207,516,225],466,[464,205.5,784,225])
row('away-second',23,'멀어지는 핵은 같은 방법으로 다음을 얻는다.','an analogous argument gives','离仪器运',[439,226,491,244],440,[438,225,701,244])
row('second-mass-first',38,'[[p2]]는 핵의 방출 후 운동량, [[nu2]]는 광자 진동수, [[m2]]는','[[p2]]: momentum after emission; [[nu2]]: photon frequency; [[m2]]:','为发射光',[481,377,534,396],439,[437,375.5,784,395.5])
row('second-mass-second',40,'바닥상태 핵의 상대론적 질량이다. 핵의 속도가 [[v2]]이면','ground-state nuclear relativistic mass. Velocity: [[v2]];','基态核的',[534,396,586,415],439,[437,395.5,670,415])
row('eq16-19',51,'식 [[eq16-19]]를 풀면','Solving [[eq16-19]] gives','各式解得',[522,500,573,517],439,[437,499,574,517.25])
protected=[[170,80,407,114.9],[210,120,407,150],[180,151,407,183],[154,244,407,306.07],[156,334,407,394.75],[192,415.5,407,433],[192,434,407,484],[564,60,784,91.5],[565,112,784,142],[515,245,784,307],[516,309,784,375],[570,423,784,448],[561,450,784,498.5]]
specs=[]
def atom(id,rect,path):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=None))
atom('eq3-6',[78,61,133,79],301)
for id,rect in {'part-two':[90,185,104,203],'approach-u':[394,185,407,203],'p1':[226,203,244,224],'nu1':[67,223,82,243]}.items():atom(id,rect,310)
for id,rect in {'m1':[97,394,113,415],'v1':[258,394,274,415],'eq9-13':[82,486,145,504]}.items():atom(id,rect,319)
for id,rect in {'eq8':[481,93,501,112],'eq15':[458,142,484,162],'range-u':[672,142,686,162],'range-lambda1':[557,161,575,181],'range2-u':[703,161,717,181]}.items():atom(id,rect,328)
for id,rect in {'lambda0':[604,185,624,205],'lambda1':[638,185,656,205],'away-u':[754,205,769,225],'p2':[466,374,483,397],'nu2':[640,374,657,397],'m2':[739,374,757,397],'v2':[625,394,643,416]}.items():atom(id,rect,337)
atom('eq16-19',[449,498,524,517.3],346)
refinements={'eq8':[482,93,501,112],'range-u':[674.5,142,684.5,162],
 'range-lambda1':[557,161,572.5,181],'range2-u':[704,161,714.5,181],
 'lambda1':[638,185,653,205],'nu2':[640,379,654,397],
 'm2':[737,379,754.5,397],'v2':[625,399,638,416],
 'eq16-19':[449,498,519.5,517.3]}
for spec in specs:
 if spec['id']in refinements:spec['search_rect']=refinements[spec['id']]
for name,data in [('authoring/page09-language-row-proposals.json',dict(rows=rows,reviewed=False,scope='Manual bilingual source-line translation. All original math/digit programs retained natively.')),
 ('page09-row-baseline-proposals.json',dict(rows=samples,scope='Source-only explicit CJK font point/baseline/weight samples.')),
 ('authoring/page09-source-geometry-proposal.json',dict(geometry=geometry,protected=protected,math_specs=specs,source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',reviewed=False))]:
 (B/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
for what in ['per-row-type','row-weights']:
 s=Path(f'D:/CodexBuilds/calibrate-cpho2005-page08-{what}.py').read_text('utf8').replace('page08','page09').replace('source[7]','source[8]').replace('original[7]','original[8]').replace('page=8','page=9')
 Path(f'D:/CodexBuilds/calibrate-cpho2005-page09-{what}.py').write_text(s,'utf8')
s=Path('D:/CodexBuilds/propose-cpho2005-page08-native-math.py').read_text('utf8');a=s.index('specs=[]');b=s.index('S=8;out=[]',a)
s=s[:a]+"specs=json.loads((B/'authoring/page09-source-geometry-proposal.json').read_text('utf8'))['math_specs']\n"+s[b:]
a=s.index('corrections=');b=s.index('boxes=',a);s=s[:a]+s[b:]
s=s.replace('page08','page09').replace("original.pdf',8)","original.pdf',9)").replace('page=d[7]','page=d[8]').replace('page=8','page=9')
Path('D:/CodexBuilds/propose-cpho2005-page09-native-math.py').write_text(s,'utf8')
s=Path('D:/CodexBuilds/author-cpho2005-ts-page08-layout.py').read_text('utf8').replace('page08','page09').replace('source[7]','source[8]').replace('source_page=8','source_page=9').replace('PAGE08','PAGE09')
a=s.index('geometry={');b=s.index('\nrows=[]',a);s=s[:a]+"geometry=json.loads((B/'authoring/page09-source-geometry-proposal.json').read_text('utf8'))['geometry']"+s[b:]
a=s.index('protected_source_display_and_figure_rects=');b=s.index('\nerrors=[]',a)
s=s[:a]+"protected_source_display_and_figure_rects=json.loads((B/'authoring/page09-source-geometry-proposal.json').read_text('utf8'))['protected'])\n"+s[b:]
s=s.replace("({'eq11-12':.5,'F-prime':.75} if id=='recovery-force-first'else{})", "({'range-u':.75} if id=='approach-range-first' else {'range-lambda1':.75} if id=='approach-range-second' else {})")
Path('D:/CodexBuilds/author-cpho2005-ts-page09-layout.py').write_text(s,'utf8')
print('PAGE09_EXPLICIT_SOURCE_AUTHORING',len(rows),'rows',len(specs),'original_math_objects',flush=True)
