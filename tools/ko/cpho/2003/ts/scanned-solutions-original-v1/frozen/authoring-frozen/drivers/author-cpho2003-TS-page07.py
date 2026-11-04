"""Manually read source7: wheel graph and two magnetic-field trajectories."""
from pathlib import Path
import sys
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
sys.path[:0]=[str(B/'TS/engine'),str(B/'engine')]
from cpho2003_manual_scan_layout import ManualPage
p=ManualPage(7); A=p.atom; R=p.row
R('steady-speed',1,[0,78,866,125],'可',[0,80,34,123],'可见电阻R越大，达到稳定时，飞轮的角速度Ω0越大，而达到稳','[[R]]이 클수록 정상 상태의 각속도 [[Omega0]]는 커지며','Larger [[R]] gives larger steady [[Omega0]];',[A(1,'R',[134,81,165,123]),A(1,'Omega0',[616,81,664,124])])
R('steady-current',1,[0,128,322,173],'定',[0,130,34,172],'定时电流I0与R无关。','정상 전류 [[I0]]는 [[R]]과 무관하다.','steady current [[I0]] is independent of [[R]].',[A(1,'I0',[137,130,174,171]),A(1,'R',[211,130,243,172])])
R('problem4',1,[0,511,58,550],'四',[0,514,32,548],'四、','4.','4.')
R('particle-data',1,[61,557,557,605],'带',[61,560,100,604],'带电荷量为q、质量为m、初速为v','전하 [[q]], 질량 [[m]], 속력 [[v]]','[[q]] charge, [[m]] mass; [[v]]',[A(1,'q',[231,559,258,604]),A(1,'m',[375,559,408,604]),A(1,'v',[528,559,554,604])],right=237)
R('uniform-field',1,[0,606,558,650],'的',[0,608,34,649],'的粒子，当它在磁感应强度为B的均匀磁','인 입자의 처음 속도와 자기장 [[B]]가','is initial speed in field [[B]].',[A(1,'B',[383,607,415,650])],right=237)
R('normal-field',1,[0,654,558,699],'场',[0,656,34,698],'场中运动时，如果其初速度的方向与磁','수직이고 자기장이 균일할 때,','The uniform field is normal',right=237)
R('lorentz-newton',1,[0,703,558,746],'场',[0,705,34,745],'场方向垂直，由洛伦兹力和牛顿定律可','로런츠 힘과 뉴턴 법칙에 의해','to velocity. Lorentz/Newton:',right=237)
R('circular-period',1,[0,750,558,795],'知',[0,753,34,793],'知，它将在磁场中做匀速圆周运动。令T','등속 원운동을 한다. 주기 [[T]]와','uniform circular motion. [[T]]',[A(1,'T',[526,751,556,795])],right=237)
R('orbital-radius',1,[0,798,558,843],'和',[0,800,34,841],'和R分别表示其周期和轨道半径，则有','궤도 반지름 [[R]]에 대해','and [[R]] are period and radius:',[A(1,'R',[36,799,65,842])],right=237)
R('hence',1,[0,926,143,965],'由',[0,929,34,963],'由此求得','따라서','Hence:',right=237)
R('apply-particle-a',1,[63,1126,558,1168],'把',[63,1128,101,1167],'把这些结论用到本题中，可知a粒','이를 적용하면 처음에 [[a]]는','Applied here, [[a]] initially',[A(1,'a',[487,1126,517,1170])],right=237)
R('right-quadrant',1,[0,1174,557,1214],'子',[0,1176,34,1212],'子开始在第一象限中运动(y轴以右)','[[y]]축 우측 제1사분면에서 운동한다.','moves right of [[y]], quadrant I:',[A(1,'y',[373,1173,398,1214])],right=237)
r=R('trajectory-caption',1,[619,1214,814,1243],'图',[621,1215,649,1243],'图决解20-4-1','그림 [[number]]','Fig. [[number]]',[A(1,'number',[702,1215,811,1243])],size=8,left=256,right=337.5)
r['align']='center';v=p.rect(1,[619,1214,814,1243]);r['source_caption_horizontal_center']=(v[0]+v[2])/2
R('a-enters-left',2,[0,206,1045,286],'经',[0,227,43,267],'经半个周期(即1/2Tar)后，进入第二三象限中(y轴以左)，周期','[[halfTar]] 후 [[y]]축 왼쪽(제2·3사분면)으로 가며','After [[halfTar]]: II/III, left of [[y]];',[A(2,'halfTar',[248,207,343,286]),A(2,'y',[760,225,793,278])])
R('a-period-radius',2,[0,294,300,336],'和',[0,297,43,335],'和轨道半径变为','주기와 궤도 반지름은','the period and radius become:')
R('dashed-repeat',2,[0,546,1045,598],'以',[0,550,43,596],'以后就按此模式在xy平面内沿图决解20-4-1中的虚线运动。','이후 [[xy]]평면에서 그림 [[ref]]의 점선을 따라 반복한다.','Repeat the dashed [[xy]] path (Fig. [[ref]]).',[A(2,'xy',[314,548,356,598]),A(2,'ref',[641,548,786,595])])
R('b-starts-left',2,[74,603,891,656],'同',[76,607,118,654],'同理，粒子b开始在第三象限(y轴以左)中运动','[[b]]도 제3사분면([[y]]축 왼쪽)에서 출발한다.','[[b]] too starts in quadrant III, left of [[y]]:',[A(2,'b',[253,606,283,655]),A(2,'y',[584,607,618,657])])
R('b-enters-right',2,[0,860,1045,947],'经',[0,883,43,930],'经半个周期(即1/2Tbl)后，进入第四象限(y轴以右)运动，周期','[[halfTbl]] 후 [[y]]축 오른쪽 제4사분면으로 가며','After [[halfTbl]]: quadrant IV, right of [[y]];',[A(2,'halfTbl',[249,860,344,947]),A(2,'y',[685,884,720,941])])
R('b-period-radius',2,[0,949,300,995],'和',[0,953,43,993],'和轨道半径变为','주기와 궤도 반지름은','the period and radius become:')
R('solid-repeat',2,[74,1206,1045,1253],'以',[76,1209,119,1251],'以后就按此模式在xy平面内沿图决解20-4-1中的实线','이후 [[xy]]평면에서 그림 [[ref]]의 실선을 따라 반복한다.','Repeat the solid [[xy]] path (Fig. [[ref]]).',[A(2,'xy',[400,1206,441,1254]),A(2,'ref',[728,1206,897,1252])])
R('common-period-right',2,[0,1263,1045,1306],'运',[0,1266,43,1304],'运动。由以上分析可知，只要在右边，不管a还是b，周期皆为','따라서 우측에서는 [[a]], [[b]] 모두 주기가','Thus on the right both [[a]] and [[b]] have period',[A(2,'a',[701,1264,734,1305]),A(2,'b',[820,1264,851,1306])])
R('period-definition',2,[0,1310,711,1377],'只',[252,1324,295,1371],'T0=πm/qB0；只要在左边，周期皆为2T0。','[[T0eq]]이며 좌측에서는 모두 [[2T0]]이다.','[[T0eq]], and [[2T0]] on the left.',[A(2,'T0eq',[0,1313,236,1377]),A(2,'2T0',[623,1320,689,1377])],left=431.6,first_known_char_is_first_token=False)
R('meeting-points',2,[74,1380,1045,1430],'由',[76,1384,119,1429],'由图决解20-4-1可见，只有在两轨迹交叉或相切的那些','그림 [[ref]]처럼 두 궤적이 교차하거나 접하는 점에서만','Fig. [[ref]]: meeting is possible only where paths cross',[A(2,'ref',[239,1380,401,1431])])
R('minimum-difference',2,[0,1438,1045,1483],'点',[0,1442,43,1482],'点，才有相遇的可能性。为求得题中所说的时间差的最小值，下','만날 수 있다. 시간 차의 최솟값을 구하기 위해, 아래에서','or touch. To find the minimum time difference, first')
R('simultaneous-start',2,[0,1496,1045,1536],'面',[0,1499,43,1536],'面我们先假设，如果a、b同时开始运动，分析经过哪个交叉或相','[[a]], [[b]]가 동시에 출발한다고 두고 교점·접점을 지나는','assume [[a]], [[b]] start together. Compare passage at',[A(2,'a',[339,1497,368,1536]),A(2,'b',[385,1497,416,1536])])
protected=[]
for image,box in [(1,[270,0,866,77]),(1,[63,180,667,498]),(1,[575,506,866,1211]),(1,[31,848,558,926]),(1,[179,973,558,1046]),(1,[179,1051,558,1125]),(2,[294,0,1045,201]),(2,[367,344,1045,547]),(2,[367,670,1045,872]),(2,[367,1000,1045,1202])]:protected.append(p.rect(image,box))
p.save(protected)
print('C03 TS7 manual full page:',len(p.rows),'rows',sum(len(r['atoms'])for r in p.rows),'complete original expressions')
