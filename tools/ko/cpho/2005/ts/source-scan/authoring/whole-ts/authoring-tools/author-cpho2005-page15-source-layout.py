"""Explicit original source rows, including z<D split across columns."""
from cpho2005_manual_seed_tools import generate
rows=[];samples=[];geometry={};specs=[]
def row(id,hint,ko,en,text,window,left,erase):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en));geometry[id]=(left,erase)
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=text,source_measurement_window=window))
def atom(id,rect,path):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=None))
row('caption',8,'그림 [[caption4]]','Figure [[caption4]]','图',[225,179,238,195],227,[223,178.5,250,196])
samples[-1]['source_size_range']=[7.5,12,.025]
row('kinetic-first',12,'그림 [[fig4-a]]에서 [[parallel-z]]축과 평행하고 곡선 [[II1-a]]의 봉우리에 접하는 직선이 초기 운동','In Fig. [[fig4-a]], the line parallel to [[parallel-z]], tangent to the peak of [[II1-a]], is','在图',[63,232,90,252],65,[63,233,409,252])
row('kinetic-second',14,'에너지 [[Ek0]]이다. 식 [[eq7]]과 곡선 [[II1-b]]에서 [[Ek-z]]를 그리면 그림 [[fig4-b]]의','[[Ek0]]. From [[eq7]] and [[II1-b]], [[Ek-z]] is shown in Fig. [[fig4-b]],','式和曲线',[123,252,174,272],65,[63,253,409,272])
row('kinetic-third',17,'곡선 [[II2]]가 된다.','curve [[II2]] in that figure.','所示',[100,273,125,292],65,[62.5,274,132,292])
row('part-two-first',19,'[[part2]] 원점의 입자에 [[small-axis]]축 방향 작은 속도를 주었을 때의 운동도','[[part2]] Motion from the origin with a small [[small-axis]] velocity also','粒子位于',[100,291,152,312],89,[87.5,293,409,312])
row('part-two-second',21,'전위 곡선의 형태에 달려 있다. 두 경우로 나누어 보자.','depends on the potential profile. Consider two cases:','电势图线',[62,311,115,331],65,[63,312,351,331])
row('wide-first',24,'[[case-i]] [[wide-condition]]로 두 고리 사이 거리가 크면 전위 [[wide-V]]의','[[case-i]] For wider ring separation, [[wide-condition]], potential [[wide-V]]','即两个环',[193,337,245,358],92,[90,331,409,361])
row('wide-second',31,'곡선은 두 봉우리를 갖고 위치 에너지 [[wide-W]]도 두 봉우리를 갖는다.','has two peaks, as does the potential energy [[wide-W]]. This is','的图线具',[63,364,114,384],65,[63,365,409,384])
row('wide-third',34,'그림 [[fig3]]의 곡선 [[curve-I1]]과 같다. [[valley-zero]]은 골짜기로 위치 에너지가 극소이다. 입자에','curve [[curve-I1]] in Fig. [[fig3]]. At [[valley-zero]], a valley, energy is a minimum.','中的曲线',[89,383,140,403],65,[63,384,409,403])
row('escape-first',36,'[[velocity-z]]축 방향 속도를 주었을 때 초기 운동 에너지가 양쪽 장벽의 높이보다','Give it a [[velocity-z]] velocity. If initial kinetic energy exceeds both','获得沿',[63,403,102,423],65,[63,404,409,423])
row('escape-second',38,'크면 입자는 장벽을 넘어 무한히 멀리 간다. 초기 운동 에너지가 양쪽','barrier heights, it escapes to infinity. Below the barrier height,','则粒子将',[81,421,134,441],65,[62.5,423,409,441])
row('trapped',40,'장벽보다 작으면 두 봉우리 사이에서 왕복한다. 초기 운동 에너지가','it moves back and forth between the peaks. For initial energy','侧电势能',[63,441,115,460],65,[63,442,409,460])
row('harmonic',43,'장벽보다 매우 작으면 [[harmonic-zero]]을 평형점으로 단진동한다. 이를 위해','much less than the peak height, it oscillates harmonically about [[harmonic-zero]].','远小于势',[62,460,113,480],65,[62.5,461,409,480])
row('study-field',45,'두 대전 고리가 만드는 [[study-z]]축 위 전기장 분포를 구하자.','Find the field of both charged rings along [[study-z]].','此研究两',[62,479,113,499],65,[62.5,480,407,499])
row('superposition-first',48,'[[axis-z]]축의 좌표 [[coordinate-z]]에서 전기장은 고리 [[ring1-a]]의 [[E1]]과 고리','At [[coordinate-z]] on axis [[axis-z]], the field is [[E1]] from ring [[ring1-a]] plus','轴上任一',[73,498,123,518],64,[62,499,409,518])
row('superposition-second',50,'[[ring2-a]]의 [[E2]]를 더한 값이다. 고리 [[ring1-b]]의 중심은 [[center-zD]]이다. [[split-zless]]','[[E2]] from ring [[ring2-a]]. Ring [[ring1-b]] is centered at [[center-zD]]. For [[split-zless]]','产生的场',[70,517,124,537],64,[61.5,519,408,537.072])
row('ring-point',1,'[[split-D]]인 좌표 [[point-z]]의 관찰점에서 고리 [[ring1-c]]의 전기장은 모든 전하가','[[split-D]], at [[point-z]], ring [[ring1-c]] gives the sum of fields from all its charges,','的范围内',[450,61,502,80],440,[438,61.87,783,80])
row('sum-fields',2,'만드는 전기장을 더한 값이다. 대칭성에 따라 그 방향은','with the resultant field axial by symmetry.','所有电荷',[438,80,490,99],440,[438,81,783,99])
row('element-field',3,'[[element-axis]]축 방향이다. 미소 전하 [[Qi]]의 전기장이 갖는 [[element-z]]축 성분은','Along [[element-axis]], a small charge [[Qi]] has a field whose [[element-z]] component is','环上任一',[486,99,537,119],440,[437.5,100,783,119])
row('geometry',6,'여기서 [[r-distance]]은 고리 위 점과 관찰점 사이 거리, [[theta]]는 [[r-angle]]과 [[angle-z]]축 사이 각이다.','Here [[r-distance]] is distance to the ring; [[theta]] is the angle of [[r-angle]] to axis [[angle-z]].','是考察点',[474,155,527,175],440,[437,156,771,175])
row('ring-one',13,'고리 [[ring1-total]] 전체가 만드는 전기장은','Total field produced by ring [[ring1-total]]:','整个圆环',[436,231,489,251],439,[437,232.122,563,251])
row('ring-two',18,'같은 방법으로 고리 [[ring2-total]]의 좌표 [[ring2-z]] 전기장은','Similarly, ring [[ring2-total]] gives at [[ring2-z]]:','同理得圆',[438,283,488,302],441,[438.5,284,589,302])
row('total-field',26,'[[total-z]]에서의 전체 전기장은','Total field at [[total-z]]:','处的总场',[447,337,498,355],442,[439.5,338,513,355])
row('near-origin',35,'관찰점이 원점 근처이므로 좌표 [[near-z]]는 작은 양이다. 따라서','Near the origin, coordinate [[near-z]] is small. Note that','由于考察',[440,386,491,407],442,[440,386.5,777,407])
row('substitution',49,'식 [[eq8]]에 대입하면','Substitution in [[eq8]] gives','代入',[441,508,467,524],444,[442,509.5,515,520.872])
atom('caption4',[237,180,245,195],316)
for id,rect in {'fig4-a':[90,234,101,251],'parallel-z':[130,234,140,251],'II1-a':[232,234,251,252],'Ek0':[63,254,85,272],'eq7':[100,254,122,271],'II1-b':[175,254,197,272],'Ek-z':[250,254,288,273],'fig4-b':[359,254,369,271],'II2':[81,275,100,292],'part2':[88,293,100,311],'small-axis':[232,295,242,311],'case-i':[90,340,116,357],'wide-condition':[134,331,186,363],'wide-V':[379,339,409,359],'wide-W':[240,365,273,384],'fig3':[77,385,88,402],'curve-I1':[145,385,162,403],'valley-zero':[167,386,199,403],'velocity-z':[104,404,113,422],'harmonic-zero':[224,461,260,480],'study-z':[299,481,308,498],'axis-z':[62,500,71,518],'coordinate-z':[174,500,184,518],'ring1-a':[276,500,285,518],'E1':[350,500,366,519],'ring2-a':[61.5,519,70,537],'E2':[136,520,154,537],'ring1-b':[239,520,249,537],'center-zD':[313,520,351,537],'split-zless':[383,520,404,537]}.items():atom(id,rect,325)
for id,rect in {'split-D':[438.5,62,450,80],'point-z':[552,63,563,81],'ring1-c':[632,63,641,81],'element-axis':[452,101,462,118],'Qi':[615,100,633,119],'element-z':[709,101,718,118],'r-distance':[465,157,475,175],'theta':[660,156,671,175],'r-angle':[685,157,695,175],'angle-z':[707,157,717,175]}.items():atom(id,rect,334)
for id,rect in {'ring1-total':[488,233,497,251],'ring2-total':[502,285,512,302],'ring2-z':[525,285,535,303],'total-z':[439.5,338,448,355],'near-z':[658,388,668,407],'eq8':[466,509.5,489,520.872]}.items():atom(id,rect,343)
protected=[[115,64,316,178.5],[157,200.322,316,230.5],[546,121,674,153],[553,175.5,669,195],[568,195.5,652,223.12],[461,250.5,697,286],[487,301.5,659,339],[451,353,776,392],[486,407,758,508.5]]
protected.remove([451,353,776,392])
protected.extend([[451,353,632,389],[632,353,776,387.5]])
# Source scan skew: left denominator ink reaches388.5pt while the rightmost
# following Chinese starts388.5pt. Explicit two-part language geometry keeps
# every original equation8 denominator pixel, without retaining Chinese ink.
geometry['near-origin']=(442,[[440,389,632,407],[632,387.5,777,407]])
# The source text's last printed stroke rasterizes slightly past its nominal
# inner clip. The paper below is empty; include it in this language-only frame.
geometry['substitution']=(444,[442,509.5,515,522])
for spec in specs:
 if spec['id']=='E2':spec['search_rect']=[136,520,152,535]
 if spec['id']=='ring1-b':spec['search_rect']=[241.5,520,248,535]
 if spec['id']=='ring1-c':spec['search_rect']=[634,63,640,79]
 if spec['id']=='eq8':
  spec['search_rect']=[467,509.5,485,522]
  spec['reviewed_rect']=[467.375,509.75,484.375,521.75]
  spec['source_edge_padding_reason']='The original equation-reference parentheses reach the nominal image bottom520.872pt. Preserve the unchanged original inner clip and image, while enlarging only the enclosing crop through empty paper; exact source roundtrip at4x and8x required.'
gaps={r['id']:{v:.75 for v in __import__('re').findall(r'\[\[([^\]]+)\]\]',r['ko'])}for r in rows}
translations={
 'kinetic-first':('그림 [[fig4-a]]의 [[parallel-z]]축과 평행하고 곡선 [[II1-a]]의 봉우리에 접하는 직선이','In Fig. [[fig4-a]], a line parallel to [[parallel-z]], tangent to the peak of [[II1-a]], is'),
 'kinetic-second':('초기 운동 에너지 [[Ek0]]이다. [[eq7]]과 [[II1-b]]로 얻는 [[Ek-z]]는 그림 [[fig4-b]]의',None),
 'part-two-first':('[[part2]] 원점의 입자에 [[small-axis]]축 방향 작은 속도를 주면 그 운동도',None),
 'wide-first':('[[case-i]] [[wide-condition]]로 두 고리 사이 거리가 크면 전위 [[wide-V]]는','[[case-i]] For wider separation, [[wide-condition]], potential [[wide-V]]'),
 'wide-second':('두 봉우리를 갖는다. 위치 에너지 [[wide-W]]도 두 봉우리를 갖는다.',None),
 'wide-third':('그림 [[fig3]]의 [[curve-I1]]이다. [[valley-zero]]은 에너지가 극소인 골짜기다. 입자에',None),
 'escape-first':('[[velocity-z]]축 방향 속도를 줄 때 초기 운동 에너지가 양쪽 장벽 높이보다',None),
 'escape-second':('크면 장벽을 넘어 무한히 멀어진다. 이 운동 에너지가 장벽보다','peak heights, it escapes to infinity. Below those heights,'),
 'trapped':('작으면 두 봉우리 사이에서 왕복한다. 초기 운동 에너지가','it moves between the peaks. If initial kinetic energy is'),
 'harmonic':('장벽보다 매우 작으면 [[harmonic-zero]]을 중심으로 단진동한다. 따라서','far below the peak, motion about [[harmonic-zero]] is harmonic.'),
 'geometry':('[[r-distance]]은 고리와 관찰점 사이 거리, [[theta]]는 [[r-angle]]과 [[angle-z]]축 사이 각이다.',None),
 'ring-point':(None,'[[split-D]], at [[point-z]], ring [[ring1-c]] gives the sum of fields from all charges;')}
for r in rows:
 if r['id']in translations:
  for lang,value in zip(['ko','en'],translations[r['id']]):
   if value is not None:r[lang]=value
generate(15,rows,samples,geometry,protected,specs,ko_math_gaps=gaps,center_slots={'caption':{'original_source_center':236.0}})
