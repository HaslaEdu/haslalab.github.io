"""Two original ring-potential derivations, including source field signs."""
from cpho2005_manual_seed_tools import generate
rows=[];samples=[];geometry={}
def row(id,hint,ko,en,sample,window,left,erase):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en));geometry[id]=(left,erase)
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=sample,source_measurement_window=window))
row('second-order',5,'고차항을 버려 식 [[taylor-eq1]]에 대입하고 [[taylor-eq2]]를 쓰면','Drop higher orders; substitute in [[taylor-eq1]], using [[taylor-eq2]]:','略去高次',[63,97,118,115],66,[64,96.5,298,115])
row('case-introduction',17,'다음 조건이면','Thus, if','由此可得',[65,183,119,201],67,[65,182.5,137,201])
row('double-peak',22,'[[V0-a]]은 극소이며 [[Vz-a]]는 그림 [[fig2-a]], 곡선 [[I-a]]의 이중 봉우리이다.','[[V0-a]]: minimum; [[Vz-a]]: twin peaks, Fig. [[fig2-a]], curve [[I-a]].','为极小值',[111,232,164,251],66,[64,232,404,251])
row('other-case',None,'반면','If','若',[65,252,81,271],67,[65,251,82,271])
row('single-peak',28,'[[V0-b]]은 극대이며 [[Vz-b]]는 그림 [[fig2-b]], 곡선 [[II-b]]의 단일 봉우리이다.','[[V0-b]]: maximum; [[Vz-b]]: single peak, Fig. [[fig2-b]], curve [[II-b]].','为极大值',[111,300,166,320],67,[65,300,404,320])
row('alternative-heading',31,'전위 곡선의 형태 조건을 구하는 다른 방법:','Another way to find the potential-profile conditions:','确定电势',[90,341,144,360],92,[89,341.5,359,360])
row('stable-first',33,'[[stable-Vz]]가 그림 [[stable-fig2]], 곡선 [[stable-I]]이면 [[stable-z0]]은 골짜기이며','For [[stable-Vz]], Fig. [[stable-fig2]], curve [[stable-I]], [[stable-z0]] is a valley,','若电势',[89,359,130,378],92,[89,359,404,378])
row('stable-second',35,'전위 극솟값이자 대전 입자의 안정 평형점이다.','a minimum and stable equilibrium for the charged particle.','处是曲线',[65,378,118,397],67,[65,377.5,404,397])
row('inward-first',37,'근처 전기장의 특징은, [[inward-positive]]이면 원점, 즉','Nearby, for [[inward-positive]], fields point towards the origin, i.e.','该处附近',[88,396,142,415],67,[65,396.5,404,415])
row('inward-second',39,'[[inward-z-negative]]축 음의 방향을 향한다. [[inward-negative]]에서도 원점, 즉','negative [[inward-z-negative]]. At [[inward-negative]], also towards the origin,','场强沿',[65,414,104,434],67,[65,414.5,404,434])
row('inward-and-unstable',43,'[[inward-z-positive]]축 양의 방향이다. [[unstable-Vz]]가 그림 [[unstable-fig2]]의 [[unstable-II]]이면','positive [[inward-z-positive]]. For [[unstable-Vz]], Fig. [[unstable-fig2]], curve [[unstable-II]],','若电势',[143,432,183,452],67,[65,432.5,404,452])
row('unstable-first',45,'[[unstable-z0]]은 봉우리이자 전위 극댓값으로, 대전 입자의 불안정','At [[unstable-z0]], a peak, the particle has unstable equilibrium.','电势为极',[207,450,261,470],68,[66,451,405,470])
row('unstable-second',47,'평형점이다. 근처에서는 [[outward-positive]]일 때 전기장이','This is a potential maximum. For [[outward-positive]], the field points','稳定平衡',[65,469,119,489],67,[65,469.5,405,489])
row('outward-directions',52,'[[outward-z-positive]]축 양의 방향, [[outward-negative]]이면 [[outward-z-negative]]축 음의 방향으로 향한다. 원점','along positive [[outward-z-positive]]; for [[outward-negative]], along negative [[outward-z-negative]].','指向',[66,488,94,507],68,[65,488,405,503.247])
row('field-condition-first',2,'근처 전기장의 이 특성 조건이 곧 전위 곡선의 형태','Near the origin, field-direction conditions also determine','附近的场',[435,62,488,82],438,[435.5,62,778,82])
row('field-condition-second',4,'조건이다. 먼저 두 원형 고리가 만드는 전기장의','the potential profile. First find the field of the two rings','种形状所',[435,80,489,100],438,[435.5,80.5,778,100])
row('field-condition-third',6,'[[field-axis-z]]축 위 분포를 구하자.','along axis [[field-axis-z]].','分布情况',[512,100,567,120],439,[436,100,571,119])
row('field-superposition-first',8,'[[axis-z]]축 좌표 [[coord-z]]에서 전기장은 고리 [[ring1-a]]의 [[E1]]과','At [[coord-z]] on axis [[axis-z]], the field is [[E1]] from ring [[ring1-a]] plus','轴上任一',[474,118,529,138],464,[461,117,779,138])
row('field-superposition-second',12,'고리 [[ring2]]의 [[E2]]를 더한 값이다. 고리 [[ring1-b]]의 중심은 [[ring-zD]],','[[E2]] from ring [[ring2]]. Ring [[ring1-b]] is centered at [[ring-zD]],','叠加而成',[557,135,612,156],439,[436,135,779,156])
row('ring-point',14,'[[point-zlessD]]인 점 [[point-z]]의 전기장은 고리 [[ring1-c]]의 각 전하가','At [[point-zlessD]], point [[point-z]], ring [[ring1-c]] gives the sum of fields','的范围内',[488,153,543,174],439,[436,154,780,174])
row('sum-charges',16,'만드는 전기장을 더한 값이다. 대칭성에 따라 전기장은','from all its charges; symmetry makes the field axial.','由环上所',[436,171,491,192],440,[437,172,780,192])
row('ring-element',18,'[[element-axis-z]]축 방향이다. 미소 전하 [[Qi]]의 전기장이 갖는 [[element-z]]축','Along [[element-axis-z]], ring charge [[Qi]] has a field whose [[element-z]] component','环上任一',[522,189,577,211],440,[437,190,780,211])
row('component',20,'성분은','is','分量为',[437,210,481,231],439,[436,210,483,231])
row('geometry-introduction',25,'여기서','where','式中',[438,261,470,281],440,[438,260,472,280])
row('geometry',29,'[[r-distance]]은 관찰점과 고리 위 점 사이 거리, [[theta]]는 [[r-angle]]과 [[angle-z]]축 사이 각이다.','[[r-distance]]: distance to ring; [[theta]]: angle between [[r-angle]] and axis [[angle-z]].','是考察的',[449,295,504,316],441,[439,294,752,315])
row('ring-one-total',32,'고리 [[total-ring1]] 전체 전기장은','Total field of ring [[total-ring1]]:','整个圆环',[440,346,492,366],442,[439,346,569,364])
row('ring-two-total',38,'같은 방법으로 고리 [[total-ring2]]의 좌표 [[total-z2]] 전기장은','Similarly, ring [[total-ring2]] at [[total-z2]] gives','同理得圆',[441,405,495,425],443,[441,405,594,425])
row('total-field',46,'[[total-z]]에서의 전체 전기장은','Total field at [[total-z]]:','处的总场',[451,459,505,479],444,[441,458,519,477])
protected=[[78,61.42,369,96],[88,115.5,408,182],[188,202,408,231.5],[188,271,408,300],[65,329,265,333],[536,231.5,779,260],[555,280.5,666,294],[568,315.5,648,345.5],[476,369.146,779,404.5],[516,425.5,779,457.5],[454,477.5,779,508.646]]
specs=[]
def atom(id,rect,path):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=None))
for id,rect in {'taylor-eq1':[163,96,186,116],'taylor-eq2':[241,96,264,116],'V0-a':[81,231,111,252],'Vz-a':[167,231,197,252],'fig2-a':[291,231,305,252],'I-a':[344,231,358,252],'V0-b':[81,299,111,321],'Vz-b':[167,299,198,321],'fig2-b':[292,299,306,321],'II-b':[342,299,359,321]}.items():atom(id,rect,260)
for id,rect in {'stable-Vz':[130,358,163,379],'stable-fig2':[234,358,247,379],'stable-I':[285,358,299,379],'stable-z0':[367,358,405,379],'inward-positive':[244,395,281,416],'inward-z-negative':[103,413,116,435],'inward-negative':[192,413,228,435],'inward-z-positive':[64,431,77,453],'unstable-Vz':[181,431,216,453],'unstable-fig2':[288,431,302,453],'unstable-II':[340,431,356,453],'unstable-z0':[92,450,130,472],'outward-positive':[306,468,344,490],'outward-z-positive':[91,487,105,506],'outward-negative':[180,487,217,506],'outward-z-negative':[293,487,308,506]}.items():atom(id,rect,269)
for id,rect in {'field-axis-z':[464,99,476,121],'axis-z':[461,115,474,139],'coord-z':[570,115,583,139],'ring1-a':[670,115,683,139],'E1':[742,115,765,139],'ring2':[463,133,478,157],'E2':[538,133,561,157],'ring1-b':[642,133,657,157],'ring-zD':[716,133,759,157],'point-zlessD':[451,152,490,176],'point-z':[586,152,600,176],'ring1-c':[665,152,680,176],'element-axis-z':[488,188,503,213],'Qi':[647,188,670,213],'element-z':[737,188,752,213],'r-distance':[439,293,451,317],'theta':[643,293,657,317],'r-angle':[664,293,679,317],'angle-z':[687,293,703,317],'total-ring1':[490,344,505,367]}.items():atom(id,rect,278)
for id,rect in {'total-ring2':[504,404,520,427],'total-z2':[527,404,542,427],'total-z':[440,457,455,480]}.items():atom(id,rect,287)
refinements={
 'taylor-eq1':[166,96,186,116],'taylor-eq2':[243.5,96,264,116],
 'fig2-b':[292,299,303,321],'stable-Vz':[130,358,159,379],
 'inward-positive':[244,395,276,416],'inward-z-negative':[103,413,113.25,432],
 'inward-negative':[196,413,227,430],'inward-z-positive':[64,431,74.5,449],
 'unstable-Vz':[181,431,213,449],'unstable-fig2':[288,431,302,448],
 'unstable-II':[340,431,356,449],'unstable-z0':[92,450,126.75,467],
 'outward-positive':[306,468,344,485.5],'outward-z-positive':[91,487,101,506],
 'outward-negative':[183.25,487,214,506],'outward-z-negative':[293,487,303,506],
 'coord-z':[573,115,580.5,135],'ring1-a':[672.5,115,679,133.5],
 'E1':[742,115,760.5,134],'ring2':[463,133,474,153],
 'E2':[538,133,555.5,155],'ring1-b':[642,133,652.5,154],
 'ring-zD':[716,133,754.5,151],'point-z':[589,152,596,171],
 'ring1-c':[668,152,674.5,170],'element-axis-z':[491.5,188,500,210.5],
 'Qi':[651.5,188,665.5,212],'element-z':[742,188,750,210],
 'r-distance':[439,293,448,315],'theta':[643,293,652,315],
 'r-angle':[667.5,293,675,315],'angle-z':[689.5,293,697.5,315],
 'total-ring1':[490,344,501,364],'total-ring2':[504,404,515,424],
 'total-z2':[530,404,539.5,424],'total-z':[440,457,450.5,476]}
for spec in specs:
 if spec['id']in refinements:spec['search_rect']=refinements[spec['id']]
gaps={}
for r in rows:
 ids=__import__('re').findall(r'\[\[([^\]]+)\]\]',r['ko'])
 if ids:gaps[r['id']]={id:.75 for id in ids}
generate(13,rows,samples,geometry,protected,specs,ko_math_gaps=gaps)
