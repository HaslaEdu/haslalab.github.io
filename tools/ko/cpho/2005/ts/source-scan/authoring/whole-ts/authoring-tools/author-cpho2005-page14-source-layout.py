"""Manual source-line translations; original ring-field and energy graph paints."""
from cpho2005_manual_seed_tools import generate
rows=[];samples=[];geometry={};specs=[]
def row(id,hint,ko,en,text,window,left,erase):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en));geometry[id]=(left,erase)
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=text,source_measurement_window=window))
def atom(id,rect,path):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=None))
row('origin-first',1,'관찰점이 원점 근처이므로 좌표 [[small-z1]]는 작은 양이다.','Near the origin, coordinate [[small-z1]] is small. Note that','由于考察',[68,57,120,76],70,[68,57.9,409,77])
row('origin-second',3,'[[small-z2]]가 매우 작을 때','for very small [[small-z2]],','很小时有',[94,78,145,95],71,[69,78,145,94])
row('substitution',17,'식 [[prime4]]에 대입하면','Substitution in [[prime4]] gives','代入',[59,202,86,220],61,[59,202.5,139,220])
row('inward-first',24,'[[inward-condition]]이면 [[field-E]]는 [[minus-z]]에 비례한다. [[z-positive]]에서는 음이고 [[z-negative]]에서는','For [[inward-condition]], [[field-E]] is proportional to [[minus-z]]: negative at [[z-positive]], positive at [[z-negative]].','成正比',[185,266,223,285],61,[59,265,409,286])
row('inward-second',25,'양이므로 원점 근처 전기장은 항상 원점을 향한다. 따라서 [[stable-zero]]은','The nearby field points towards the origin. Thus [[stable-zero]] is','表示原点',[138,290,188,310],61,[59,291,409,310])
row('inward-third',26,'대전 입자의 안정 평형점이며 전위 [[stable-V]]는 곡선 [[curve-I]]이다.','stable for the charged particle; [[stable-V]] has profile [[curve-I]].','为带电粒',[59,310,112,330],61,[59,311,399,330])
row('outward-first',27,'[[outward-condition]]이면 근처 전기장은 양쪽 바깥을 향한다. 따라서 [[unstable-zero]]은','For [[outward-condition]], nearby fields point outward. Thus [[unstable-zero]] is','在原点附',[119,336,170,356],61,[59,332,409,356])
row('outward-second',28,'대전 입자의 불안정 평형점이며 전위 [[unstable-V]]는 곡선 [[curve-II]]이다.','unstable for the particle; [[unstable-V]] has profile [[curve-II]].','处为带电',[59,361,112,381],61,[59,362,405,381])
row('initial-first',32,'대전 입자가 [[initial-z]]에서 초기 속도로 [[initial-axis]]축을 따라 두 고리를','Let a charged particle start at [[initial-z]], moving along [[initial-axis]]','若带电粒',[85,406,139,426],87,[85,407,409,426])
row('initial-second',34,'향해 간다. 초기 운동 에너지를 [[Ek0-initial]], 좌표 [[at-z]]에서의 운동 에너지를 [[Ek-initial]]라','towards both rings. Initial kinetic energy: [[Ek0-initial]]; at [[at-z]]: [[Ek-initial]].','表示其初',[120,426,172,446],61,[59,427,409,446])
row('initial-third',36,'하면 에너지 보존으로','Energy conservation gives','则由能量',[110,446,161,464],62,[60,447,197,465])
row('profile-first',40,'좌표 [[profile-z]]의 운동 에너지는 일정한 값에서 정전기적 위치 에너지를','At [[profile-z]], kinetic energy equals a constant minus potential','因粒子在',[59,487,111,506],62,[60,488,409,506])
row('profile-second',44,'뺀 값이다. 따라서 [[profile-Ek]]의 곡선은 [[profile-W]]의 곡선으로 결정된다.','energy; thus the [[profile-Ek]] profile follows from [[profile-W]].','的图线取',[145,506,196,525],62,[60,507,409,523.796])
row('two-cases',2,'두 경우로 나누어 보자.','Consider two cases:','下面分两',[435,63,486,82],438,[435,63.97,583,82])
row('two-peak-first',5,'[[case-i]] [[wide-condition]]로 두 고리 사이 거리가 크면 전위','[[case-i]] For wider ring separation, [[wide-condition]], potential','即两个圆',[568,89,622,109],463,[461,83,783,114])
row('two-peak-second',7,'[[two-V]]는 두 봉우리와 한 골짜기를 갖고, 위치 에너지 [[two-W]]도','[[two-V]] has two peaks and a valley, as does potential energy [[two-W]];','的图线具',[466,116,517,135],438,[435,116,784,135])
row('two-peak-third',9,'같은 형태이다. 그림 [[figure3-a]]의 [[curve-I1-a]]과 같다. 입자가 두 고리를 막','see curve [[curve-I1-a]] in Fig. [[figure3-a]]. To just pass both rings,','具有两个',[434,136,486,155],437,[434,137,784,155])
row('threshold-first',12,'통과하므로 초기 운동 에너지 [[threshold-Ek0]]는 위치 에너지 [[threshold-W]]의 최댓값,','the initial kinetic energy [[threshold-Ek0]] equals the maximum of [[threshold-W]],','能通过两',[434,155,488,175],438,[435,156,784,174.22])
row('threshold-second',16,'즉 봉우리 높이와 같다. 그림 [[figure3-b]]에서 [[horizontal-z]]축과 평행하며 [[tangent-W]]의','the peak height. In Fig. [[figure3-b]], a line parallel to [[horizontal-z]], tangent to [[tangent-W]]','大值',[434,180,461,201],437,[433.5,181.65,784,201])
row('threshold-third',18,'두 봉우리에 접하는 직선이 [[line-Ek0]]이다. 식 [[energy-eq7]]과 곡선 [[curve-I1-b]]에서','at both peaks is [[line-Ek0]]. Equation [[energy-eq7]] and curve [[curve-I1-b]] give','线的双峰',[434,199,486,221],437,[433.5,200,784,221])
row('threshold-fourth',19,'[[curve-Ek]]를 그리면 그림 [[figure3-c]]의 곡선 [[curve-I2]]가 된다.','the [[curve-Ek]] profile, curve [[curve-I2]] in Fig. [[figure3-c]].','的图线',[500,220,537,239],438,[435,221,692,240])
row('caption',29,'그림 [[caption3]]','Figure [[caption3]]','图',[601,367,614,382],604,[599,366.5,625,383])
samples[-1]['source_size_range']=[7.5,12,.025]
row('single-first',31,'[[case-ii]] [[narrow-condition]]로 두 고리가 가까우면 전위 [[single-V]]의','[[case-ii]] For closer rings, [[narrow-condition]], potential [[single-V]] has','即两个圆',[567,387,620,410],466,[464,387.67,783,411])
row('single-second',33,'곡선에는 [[single-zero1]]에서 봉우리 하나만 있다. 위치 에너지 [[single-W]]도','one peak, at [[single-zero1]]; the potential energy [[single-W]] likewise has','的图线只',[437,413,488,435],440,[437,414,783,435])
row('single-third',35,'[[single-zero2]]에서 봉우리 하나만 있다. 그림 [[figure4]]의 곡선 [[curve-II1]]과 같다.','one peak at [[single-zero2]], as in curve [[curve-II1]], Fig. [[figure4]].','亦只有位',[437,433,490,454],440,[437,434,753,455])
row('peak-height',39,'전위 봉우리의 높이는','The potential peak height is','电势图线',[465,467,515,485],468,[465,467,556,485])
row('continuation',45,'입자가 두 고리를 막 통과하므로 초기 운동 에너지는','To just pass both rings, its initial kinetic energy is','已知粒子',[440,521,491,539],443,[441,522,689,538.421])
for id,rect in {'small-z1':[290,58,299,74],'small-z2':[84,78,93,94]}.items():atom(id,rect,316)
for id,rect in {'prime4':[86.5,202,113,220],'inward-condition':[75,262,131,293],'field-E':[135,266,148,283],'minus-z':[163,267,184,282],'z-positive':[245,268,282,284],'z-negative':[372,268,408,285],'stable-zero':[361.5,292,392,309],'stable-V':[250,312,280,329],'curve-I':[360,312,370,329],'outward-condition':[60,331,114,361],'unstable-zero':[373,338,406,355],'unstable-V':[275,363,306,380],'curve-II':[382,362,398,381]}.items():atom(id,rect,325)
for id,rect in {'initial-z':[163,408,218,425],'initial-axis':[316,409,325,424],'Ek0-initial':[97,427,117,445],'at-z':[370,428,380,444],'Ek-initial':[202.5,427,239.5,446],'profile-z':[139,489,149,505],'profile-Ek':[107,508,143,524],'profile-W':[277.5,507,363.5,525]}.items():atom(id,rect,334)
for id,rect in {'case-i':[461,91,487,108],'wide-condition':[506,83,561,115],'two-V':[435,117,465,135],'two-W':[694,117,726,135],'figure3-a':[583,138,594,154],'curve-I1-a':[651,138,668,155],'threshold-Ek0':[623,157,644.25,174],'threshold-W':[724,157,756,174]}.items():atom(id,rect,343)
for id,rect in {'figure3-b':[568,182,578,199],'horizontal-z':[606,182,616,199],'tangent-W':[725,182,757,200],'line-Ek0':[617,201,639.75,220],'energy-eq7':[656,201,680,220],'curve-I1-b':[737,202,754,221],'curve-Ek':[464.5,222,501,241],'figure3-c':[573.5,221,582,239],'curve-I2':[640,222,659,240],'caption3':[614,368,622,381]}.items():atom(id,rect,352)
for id,rect in {'case-ii':[464,391,489,409],'narrow-condition':[507,387.67,560.5,415.5],'single-V':[750,390,782,410],'single-zero1':[529,418,560,434],'single-W':[710,414,739,434],'single-zero2':[501.5,435,537,454],'figure4':[635,434,647,453],'curve-II1':[698,434,718,454]}.items():atom(id,rect,361)
protected=[[116,94,390,202],[148,220,409,263],[59,387,266,393],[123,466,409,486],[491,244,694,366],[532,485.5,689,520]]
for spec in specs:
 if spec['id']=='profile-W':
  spec['reviewed_rect']=[278.75,510,359.75,525]
  spec['source_edge_padding_reason']='Original q descender reaches nominal image boundary523.796pt. Include unchanged original image edge interpolation and empty page padding to525pt; source image program/scale/y unchanged. Exact source-only roundtrip at4x and8x required by a pinned page14/image334/rect-only engine rule.'
complete_windows={'inward-first':[184,265,227,286],'initial-second':[117,425,172,446],'initial-third':[104,445,157,465],'threshold-fourth':[498,219,541,241],'profile-first':[58,487,113,507]}
translations={
 'inward-first':('[[inward-condition]]이면 [[field-E]]는 [[minus-z]]에 비례한다. [[z-positive]]에서 음, [[z-negative]]에서','[[inward-condition]]: [[field-E]] and [[minus-z]] are proportional. [[z-positive]], [[z-negative]]:'),
 'inward-second':('양이므로 전기장은 원점을 향한다. [[stable-zero]]은','negative, positive: the fields point inward. [[stable-zero]] is'),
 'outward-first':('[[outward-condition]]이면 전기장은 양쪽 바깥을 향한다. 따라서 [[unstable-zero]]은',None),
 'initial-first':('입자가 [[initial-z]]에서 초기 속도로 [[initial-axis]]축을 따라 두 고리를','A charged particle starts at [[initial-z]], moving along [[initial-axis]]'),
 'initial-second':('향한다. 초기 운동 에너지는 [[Ek0-initial]], 좌표 [[at-z]]에서의 값은 [[Ek-initial]]이며','to the rings. Initial kinetic energy: [[Ek0-initial]]; at [[at-z]]: [[Ek-initial]].'),
 'initial-third':('대전 입자의 에너지 보존으로',None),
 'profile-first':('[[profile-z]]에서 운동 에너지는 일정한 값에서 정전기적 위치 에너지를',None),
 'profile-second':('뺀 값이다. [[profile-Ek]]의 곡선은 [[profile-W]]로 정해진다.',None),
 'two-peak-first':(None,'[[case-i]] For wider separation, [[wide-condition]], potential'),
 'two-peak-second':(None,'[[two-V]] and potential energy [[two-W]] have two peaks and a valley;'),
 'threshold-first':('통과하므로 초기 운동 에너지 [[threshold-Ek0]]는 [[threshold-W]]의 최댓값,','initial kinetic energy [[threshold-Ek0]] equals the maximum of [[threshold-W]],'),
 'threshold-second':(None,'the peak height. In Fig [[figure3-b]], parallel to [[horizontal-z]] and tangent to [[tangent-W]]'),
 'threshold-third':(None,'at both peaks, the line is [[line-Ek0]]. From [[energy-eq7]] and [[curve-I1-b]] comes')}
for r in rows:
 if r['id']in translations:
  for lang,value in zip(['ko','en'],translations[r['id']]):
   if value is not None:r[lang]=value
for sample in samples:
 if sample['id']in complete_windows:sample['source_measurement_window']=complete_windows[sample['id']]
gaps={r['id']:{v:.75 for v in __import__('re').findall(r'\[\[([^\]]+)\]\]',r['ko'])}for r in rows}
generate(14,rows,samples,geometry,protected,specs,ko_math_gaps=gaps,center_slots={'caption':{'original_source_center':612.0}})
