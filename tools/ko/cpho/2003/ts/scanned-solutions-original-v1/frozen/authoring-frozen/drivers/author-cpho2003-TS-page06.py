"""Source6 prose around untouched original hyperbola and wheel equations."""
from pathlib import Path
import sys
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path[:0]=[str(B/'TS/engine'),str(B/'engine')]
from cpho2003_manual_scan_layout import ManualPage
p=ManualPage(6);A=p.atom;R=p.row
R('angular-at-infinity',1,[0,0,359,39],'根',[77,0,114,39],'mvd。根据角动量守恒，有','[[mvd]]이다. 각운동량 보존에서','[[mvd]]. Conservation of angular momentum gives:',[A(1,'mvd',[7,0,67,37])],left=54,first_known_char_is_first_token=False)
R('vertex-energy1',1,[3,96,868,140],'探',[3,96,41,140],'探测器在双曲线的顶点的机械能应等于它到达无限远处的机械','쌍곡선 꼭짓점의 역학적 에너지는 무한히 먼 곳의','The probe’s energy at the hyperbola vertex equals')
R('vertex-energy2',1,[3,145,124,189],'能',[3,145,41,189],'能，故有','역학적 에너지와 같으므로','its mechanical energy at infinity, so')
R('hyperbola-reference',1,[3,274,344,320],'由',[3,274,41,320],'由图决解20-2-2可知','그림 [[ref]]에서','From Fig. [[ref]]:',[A(1,'ref',[141,275,277,318])])
R('hyperbola-semi-axes',1,[69,369,868,415],'若',[69,369,110,415],'若A、B分别表示双曲线的实半轴和虚半轴，C表示双曲线','쌍곡선 실반축 [[A]], 허반축 [[B]], [[C]]는 쌍곡선','Semi-axes: transverse [[A]], conjugate [[B]]; [[C]] is',[A(1,'A',[112,370,141,414]),A(1,'B',[150,370,183,414]),A(1,'C',[684,370,716,414])])
R('focus-condition',1,[3,419,868,465],'中',[3,419,41,465],'中心到地心的距离，因地心是双曲线的焦点，根据题给的条件和','중심과 지구 중심의 거리이다. 지구 중심이 초점이므로 조건과','the center-to-focus distance; Earth is a focus. Conditions')
R('analytic-geometry',1,[3,469,190,513],'解',[3,469,41,513],'解析几何，有','해석기하학에서','and analytic geometry give:')
R('sine-alpha',2,[5,155,47,200],'而',[5,155,43,200],'而','또한','and')
R('from-equations',2,[5,226,260,270],'由',[5,226,43,270],'由以上各式，可得','위 식들에서','These equations give:')
R('solve7-8-9-14',2,[5,356,411,404],'解',[5,356,43,404],'解式(7)、(8)、(9)和(14)，得','식 [[7]], [[8]], [[9]], [[14]]를 풀면','Solving [[7]], [[8]], [[9]], and [[14]]:',[A(2,'7',[75,356,122,402]),A(2,'8',[136,356,188,402]),A(2,'9',[201,356,251,402]),A(2,'14',[288,356,359,402])])
R('ejection-energy1',2,[5,487,868,533],'探',[5,487,43,533],'探测器被射出后，其能量就是做双曲线运动时的能量，故射出后','방출 후 탐사기는 쌍곡선 운동의 에너지를 가지므로','After ejection its energy is that of hyperbolic motion,')
R('ejection-energy2',2,[5,536,240,579],'探',[5,536,43,579],'探测器的能量为','그 에너지는','the energy after ejection is:')
R('energy-given',2,[5,664,475,710],'发',[5,664,43,710],'发射探测器时给探测器的能量为','발사할 때 탐사기에 공급한 에너지는','The energy given at launch is:')
R('solve1-6-16',3,[0,0,329,39],'由',[0,0,33,39],'由式(1)、(6)和(16)，得','식 [[1]], [[6]], [[16]]에서','From [[1]], [[6]], and [[16]]:',[A(3,'1',[62,0,111,37]),A(3,'6',[126,0,178,37]),A(3,'16',[213,0,280,37])])
R('problem3',3,[59,140,115,184],'三',[59,140,101,184],'三、','3.','3.')
R('wheel-emf',3,[59,188,805,237],'当',[59,188,101,237],'当飞轮的角速度为Ω时，每一辐条中的感应电动势为','각속도 [[Omega]]일 때 바큇살당 유도 기전력은','Angular speed [[Omega]]: induced emf per spoke',[A(3,'Omega',[325,188,361,236])])
R('spoke-current',3,[0,309,637,358],'当',[0,309,35,358],'当有电流I通过电阻R时，每条辐条中的电流','저항 [[R]]을 지나는 전류가 [[I]]이면 바큇살마다','Through resistor [[R]] flows [[I]]; each spoke carries:',[A(3,'I',[134,310,161,357]),A(3,'R',[289,310,321,357])])
R('magnetic-force',3,[0,435,199,481],'受',[0,435,35,481],'受到的安培力','작용하는 자기력은','The magnetic force is:')
R('spoke-torque',3,[0,532,327,580],'安',[0,532,35,580],'安培力对转轴的磁力矩','회전축에 대한 자기 토크는','Magnetic torque about the axle:')
R('total-torque',3,[0,654,394,700],'作',[0,654,35,700],'作用于整个飞轮的总磁力矩','플라이휠 전체의 자기 토크는','Total magnetic torque on the wheel:')
R('when-torque-equal',3,[0,755,37,805],'当',[0,755,35,805],'当','여기서','When')
R('steady-rotation',3,[0,805,859,854],'时',[0,805,35,854],'时，飞轮做匀速转动，即转动达到稳定，这时Ω=Ω0，I=I0。由','이면 등각속도: [[Omega0]], [[I0]]이다. 위','uniform rotation: [[Omega0]], [[I0]]. These',[A(3,'Omega0',[594,806,715,853]),A(3,'I0',[728,806,824,853])])
R('wheel-equations-give',3,[0,853,167,901],'以',[0,853,35,901],'以上各式得','식들을 적용하면','equations give:')
R('ohms-law',4,[0,57,181,98],'由',[0,57,35,98],'由欧姆定律有','옴의 법칙에서','Ohm’s law gives:')
R('solve7-8-9',4,[0,145,281,190],'解',[0,145,35,190],'解式(7)、(8)和(9)得','식 [[7]], [[8]], [[9]]를 풀면','Solving [[7]], [[8]], and [[9]]:',[A(4,'7',[53,145,94,189]),A(4,'8',[108,145,153,189]),A(4,'9',[188,145,233,189])])
protected=[]
for image,box in [(1,[251,42,868,88]),(1,[230,191,868,272]),(1,[250,318,868,367]),(2,[299,0,868,40]),(2,[308,41,868,83]),(2,[308,84,868,137]),(2,[291,142,868,223]),(2,[299,280,868,351]),(2,[308,411,868,479]),(2,[249,588,868,664]),(2,[308,712,868,750]),(3,[244,41,859,137]),(3,[279,241,859,312]),(3,[332,365,859,435]),(3,[333,481,859,531]),(3,[328,582,859,653]),(3,[339,706,859,757]),(3,[328,760,859,802]),(3,[301,916,859,982]),(4,[263,0,777,55]),(4,[288,102,777,145]),(4,[299,191,777,256])]:protected.append(p.rect(image,box))
p.save(protected)
print('C03 TS6 manual full page:',len(p.rows),'rows',sum(len(r['atoms'])for r in p.rows),'complete original inline expressions')
