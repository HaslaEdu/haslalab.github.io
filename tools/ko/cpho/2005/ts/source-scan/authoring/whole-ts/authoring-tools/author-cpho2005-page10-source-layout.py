"""Manually read bilingual motor/circuit source page; source drawing untouched."""
from pathlib import Path
from cpho2005_manual_seed_tools import generate
rows=[];samples=[];geometry={};rights={}
def row(id,hint,ko,en,sample,window,left,erase,right=None):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en));geometry[id]=(left,erase)
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=sample,source_measurement_window=window))
 if right is not None:rights[id]=right
row('eq8',6,'식 [[eq8]]에서','Using [[eq8]],','注意到',[63,94,101,110],64,[62,93,157,111])
row('receding-first',13,'식 [[eq21]]에서 멀어지는 핵의 속력이 [[recede-u]]보다 작으면 방출','By [[eq21]], nuclei receding below [[recede-u]] emit photon wavelengths','背离仪器',[173,148,225,166],64,[62,147,407,166])
row('receding-second',15,'광자 파장은 [[lambda2a]]보다 작다. 속력이 [[recede-u2]]에서 영 사이인','below [[lambda2a]]. Recession speeds from [[recede-u2]] to zero give','们发出的',[61,165,115,188],64,[62,166,408,186])
row('receding-third',17,'핵의 광자 파장은 [[lambda2b]]와 [[lambda0]] 사이에 분포한다. 따라서','wavelengths between [[lambda2b]] and [[lambda0]]. Hence','激发态核',[63,187,115,207],64,[62,186,392,207.5])
row('section-six',28,'6.','6.','六、',[88,285,110,303],89,[86,284,112,303])
row('current-first',29,'[[part-one]] 회로를 연결하면 정전류원의 일정한 전류 [[I-source]] 중 일부는','[[part-one]] On connection, a source supplies constant current [[I-source]];','接通电路',[104,305,156,321],89,[87,304.5,407,321])
row('current-second',31,'[[R0]]를, 나머지는 원판을 흐른다. 고리 브러시와 원통 금속 축은','part flows in [[R0]], the rest in the disk. An annular brush','另一部分',[81,324,133,341],64,[62,323.5,407,341])
row('current-third',32,'전류를 반지름 방향으로 흐르게','and cylindrical metal shaft','流沿着盘',[63,344,115,360],64,[62,343.5,255,360],256)
row('current-fourth',33,'한다. 이 전류에 자기 토크가','make current radial; its torque','径的电流',[63,363,115,379],64,[62,362.5,255,379],256)
row('current-fifth',35,'작용하여 부하의 기계적 토크를','overcomes the mechanical load','矩使盘克',[63,382,115,398],64,[62,381.5,255,398],256)
row('current-sixth',37,'이기고 원판의 회전을 가속한다.','and accelerates the disk.','做加速转',[63,401,115,417],64,[62,400.5,256,417],256)
row('current-seventh',39,'자기장 속에서 원판이 돌면','Rotation in the field induces','由于电磁',[82,420,134,436],64,[62,419,255,436],256)
row('current-eighth',42,'역기전력이 생긴다. 등가 회로는 그림과 같다. [[disk-R]]은 원판 저항,','a back emf. Equivalent circuit shown. [[disk-R]]: disk resistance,','其等效电',[157,438,211,455],64,[62,437.5,407,455])
row('current-ninth',43,'[[disk-E]]는 유도 기전력, [[disk-i]]는 원판 총전류이다. 원판 가지의 회로','[[disk-E]]: induced emf; [[disk-i]]: total disk current. Its branch equation','为感应电',[76,457,128,474],64,[62,456,408,474])
row('current-tenth',45,'방정식은','is','方程为',[63,476,103,490],64,[61,474.5,104,489.45])
row('or',None,'또는','or','或',[63,523,79,538],64,[62,522.5,81,538])
row('loaded-first',1,'원판 각속도가 커지면 역기전력 [[emf-E]]도 커진다. 식 [[eq1]]에 따라','As angular speed rises, emf [[emf-E]] rises; [[eq1]] implies less','随着圆盘',[439,65,491,81],440,[438,64,783,81])
row('loaded-second',5,'원판 전류 [[current-i]]는 작아진다. 어느 값까지 줄면 자기 토크와','disk current [[current-i]]. At some current, magnetic and mechanical','过圆盘的',[439,83,491,100],440,[438,82,783,100])
row('loaded-third',7,'부하 토크가 평형을 이뤄 원판은 등각속도로 회전한다.','load torques balance; the disk has constant angular','负载的机',[439,102,491,119],440,[438,100.5,783,119])
row('loaded-fourth',9,'이 각속도가 부하 정상 각속도 [[omega-loaded]]이다. 기계적','velocity [[omega-loaded]], its loaded steady value. Without a mechanical','角速度就',[439,121,491,138],440,[438,119.5,784,138])
row('unloaded-first',12,'부하가 없는 무부하 상태에서는 부하 토크가 영이므로','load, load torque is zero, so the steady magnetic torque','即处在空',[472,139,525,156],440,[438,138.5,783,156])
row('unloaded-second',14,'정상 상태의 자기 토크도 영이다. 부하 토크가 없으면','is zero. With no load torque, the disk accelerates to a','在没有负',[538,158,591,175],440,[437,157,783,175])
row('unloaded-third',16,'각속도와 역기전력이 크게 증가해 원판 전류가 영이 되고','high angular speed. Back emf rises until disk current and','角速度可',[439,177,491,193],440,[438,175.5,783,193])
row('unloaded-fourth',18,'자기 토크도 영이 된다. 이때 원판의 무부하 정상 상태','magnetic torque vanish. The disk is at its no-load steady','磁力矩亦',[470,194,526,214],440,[438,194.5,783,212])
row('unloaded-fifth',21,'각속도는 [[omega0]]이다.','angular velocity [[omega0]].','的角速度',[439,214,491,232],440,[437,212.5,513,232])
row('emf-heading',23,'[[roman-i]] 고리 원판의 유도 기전력 계산','[[roman-i]] Induced emf in the annular disk','环形圆盘',[493,234,544,251],465,[463,233,659,251])
row('spoke-first',26,'원판이 자기장 속에서 돌면 반지름은 자기력선을 자른다.','In rotation, each radius cuts magnetic field lines.','圆盘在磁',[465,253,517,270],466,[464,252,783,270])
row('spoke-second',27,'원판을 무수한 반지름 방향 살로 생각하자. 원판의 각속도가','Disk: infinitely many radial spokes. Angular speed:','把圆盘看',[461,271,514,288],440,[438,270.5,783,284.7])
row('spoke-third',None,'[[omega-spoke]]일 때 한 살이 [[delta-t]] 동안 [[delta-theta]]만큼 회전하며 쓸어 간','[[omega-spoke]], a spoke turns through [[delta-theta]] in time [[delta-t]]. The area','圆盘某根',[469,302,521,320],440,[438,300.5,783,319])
row('spoke-fourth',30,'넓이는','swept is','过的面积',[439,320,492,337],440,[438,319,505,337])
row('magnetic-flux',34,'자기 선속은','The magnetic flux is','磁通量为',[439,370,491,386],440,[438,368.5,492,386])
row('faraday',38,'전자기 유도 법칙에 따라 살의 유도 기전력 크기는','By Faraday’s law, the emf magnitude along a spoke is','由电磁感',[439,407,491,424],440,[438,405,738,424])
row('parallel-first',44,'각 살은 전원 하나에 해당하며 기전력이 같은 병렬 전원이므로','Each spoke is a source; equal-emf sources are in parallel,','每根辐条',[439,454,491,472],440,[438,452.5,780,471])
row('parallel-second',46,'원판에 생기는 기전력 크기도','so the disk’s emf magnitude remains','故圆盘中',[458,473,511,490],440,[438,471,623,488.85])
protected=[[188,62,409,93],[187,113,409,146.5],[97,209,409,239.17],[187,248,409,282],[267,349,405,430],[173,496,409,537.896],[548,338,670,368],[572,386.5,642,404.5],[463,424.5,743,452],[540,494.846,785,523.346]]
specs=[]
def atom(id,rect,path):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=None))
for id,rect in {'eq8':[100,93,124,112],'eq21':[75,146,102,168],'recede-u':[312,146,326,168],'lambda2a':[203,166,223,188],'recede-u2':[330,166,345,188],'lambda2b':[259,186,279,209],'lambda0':[288,186,307,209]}.items():atom(id,rect,273)
for id,rect in {'part-one':[87,304,102,322],'I-source':[312,304,324,322],'R0':[61,323,77,343],'disk-R':[309,436,324,456],'disk-E':[62,455,76,475],'disk-i':[158,455,168,475]}.items():atom(id,rect,282)
for id,rect in {'emf-E':[637,63,652,83],'eq1':[705,63,729,83],'current-i':[514,81,526,101],'omega-loaded':[682,119,704,139],'omega0':[488,211,511,233],'roman-i':[463,232,490,253]}.items():atom(id,rect,300)
for id,rect in {'omega-spoke':[438,299,453,321],'delta-t':[575,299,595,321],'delta-theta':[702,299,728,321]}.items():atom(id,rect,309)
refinements={'eq8':[101.75,93,124,112],'recede-u':[312,146,323,168],
 'lambda2a':[203,166,220.5,188],'recede-u2':[330,166,341,188],
 'lambda2b':[259,186,276,209],'eq1':[708,63,729,83],
 'current-i':[517,81,523.25,101],'omega-loaded':[682,119,693,139],
 'omega0':[492,211,507.25,233],'omega-spoke':[438,299,450.75,317],
 'delta-t':[573,299,589,318],'delta-theta':[702,299,721,319]}
for spec in specs:
 if spec['id']in refinements:spec['search_rect']=refinements[spec['id']]
 if spec['id']=='lambda2a':spec['padding']=[.75,.75,.75,1.5]
gaps={}
for r in rows:
 ids=__import__('re').findall(r'\[\[([^\]]+)\]\]',r['ko'])
 if ids:gaps[r['id']]={id:.75 for id in ids}
generate(10,rows,samples,geometry,protected,specs,rights,gaps)
p=Path('D:/CodexBuilds/calibrate-cpho2005-page10-row-weights.py');s=p.read_text('utf8').replace("'section-five'","'section-six'").replace("'excited-energy'","'current-first'").replace('Chinese ordinal 三','Chinese ordinal 六').replace('ordinal 三','ordinal 六');p.write_text(s,'utf8')
