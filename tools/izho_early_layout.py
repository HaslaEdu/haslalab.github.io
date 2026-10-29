"""Join overlapping Word text fragments before Korean typesetting.

Word exported each inline equation as a separate PDF block, leaving overlapping
rectangles for the prose on either side.  Reflow each connected paragraph once,
including the intervening equation objects in their source reading order.
"""
from pathlib import Path
import json,re,copy
import pymupdf as fitz
from PIL import Image
import io
from izho_early_math import consolidate,candidate
ROOT=Path(__file__).resolve().parents[1]
def block_index(e):return int(re.match(r'\d+-(\d+)',e['id'])[1])

FLOW={
 (2010,'T','2-15'):[([85,715,556,770],'한 변 a = 10 cm인 불투명 정사각형 판을 광원 아래, 바닥에서 [[0]] 높이에 수평으로 놓았다(그림 1). 그림 2의 바닥 그림자는 짙은 직사각형을 옅은 직사각형이 둘러싸며, 바깥 가장자리로 갈수록 밝아진다. 눈금 한 칸은 1.0 cm이다. 광원의 크기')],
 (2010,'T','3-5'):[([333,225,556,273],'반지름 [[0]], 길이 [[1]], 관성 모멘트 [[2]]인 긴 코일이 있다.'),([85,274,556,347],'길이 [[3]], 질량 [[4]]인 금속선을 한 겹 감았으며 단위 길이당 감은 수는 [[5]]이다. 양 끝은 미끄럼 접점을 통해 검류계에 연결된다. 코일과 금속선을 각속도 [[6]]으로 회전시킨 뒤 토크 [[7]]의 마찰력으로 멈춘다. 회로의 전체 저항은 [[8]]이고 전기 용량은 무시한다.')],
 (2010,'T','2-12'):[([85,369,466,411],'[[0]]에 비해 작다. 시험관 안에는 질량을 무시할 수 있는 기체가 부피 [[1]]만큼 들어 있다. 온도는 일정하다.'),([85,412,556,459],'시험관이 바닥에서 일정 높이 위에 정지할 수 있는가? 가능하다면 조건과 높이를 구하고 평형의 안정성을 판정하라. 시험관 벽의 부피는 [[2]]에 비해 무시한다.')],
 (2010,'T','3-13'):[([410,692,458,711],'여기서 [[3]]')],
 (2012,'T','2-9'):[([72,524,556,540],'두께 [[0]]인 투명한 원형 평행 평판은'),([72,541,333,583],'굴절률이 중심축에서 거리 [[1]]에 따라 다음과 같이 변하는 물질로 만들어졌다.')],
 (2012,'T','2-10'):[([72,600,336,675],'여기서 [[1]]는 알려진 양의 상수이다. 평판은 굴절률 [[2]]인 공기 중에 있다. 축 위에서 평판까지 거리 [[3]] [[4]])인 곳에 점광원 [[5]]가 있다.'),([72,676,556,719],'이 평판이 상을 만드는 렌즈처럼 작용함을 보여라. 광원 [[7]]의 상이 평판에서 떨어진 거리 [[6]] 및 초점 거리를 구하라.')],
 (2012,'T','3-2'):[([235,101,556,291],'높이 [[0]] [[1]] cm, 단면적 [[2]] cm²인 열린 원통 용기에 대기압 [[3]] Pa, 온도 [[4]]인 공기가 있다. 위에서 질량 [[5]] [[6]] kg인 얇고 무거운 피스톤을 조심스럽게 끼운다. 벽과 피스톤은 열전도성이 매우 낮다. 공기는 평균 몰질량 [[7]] g/mol인 이상 이원자 기체이다. 중력 가속도는 [[8]], 기체 상수는 [[9]] J/(mol·K)이다. 용기·피스톤의 열용량과 벽면 마찰은 무시한다.'),([72,292,556,425],'피스톤을 놓으면 최종 평형까지 두 단계를 거친다. 첫 단계에서는 피스톤이 진동하며 기체 과정은 비평형이다. 이로 인해 진동이 감쇠하고 역학적 에너지가 소산된다. 소산 에너지의 절반은 용기 안 기체에, 절반은 대기에 전달된다. 이 단계에서는 벽과 피스톤을 통한 열전도를 무시한다. 진동이 멎을 때 높이는 [[10]]이다. 두 번째 단계는 느리게 진행되어 높이 [[11]]에서 완전히 멈춘다.'),([91,426,556,463],'2.1 [0.5점] 첫 단계가 끝날 때 압력 [[12]]를 대기압 [[13]], 비열비 [[14]] 및 다음 매개변수로 나타내라.')],
 (2012,'TS','1-2'):[([256,90,414,107],'문제 1 (10점)'),([113,122,280,137],'문제 1A. 2012'),([85,138,281,280],'계에 작용하는 힘은 그림과 같다. 막대가 강체이고 실이 늘어나지 않으므로 추의 가속도 비는 1:2:3이다. 질량 없는 막대의 토크 합은 0이다. 이 조건들과 각 추의 뉴턴 제2법칙으로 다음 연립방정식을 얻는다.')],
 (2012,'TS','2-12'):[([85,533,322,612],'[[0]]의 전류에 해당 배수를 곱하면 된다. 여러 전압에서 전류를 읽고 각각 2배, 3배 한 점을 그래프에 찍는다.'),([85,614,556,644],'직렬 연결의 전체 전압은 각 부분 전압의 합이므로')],
 (2013,'T','2-4'):[([218,358,424,375],'문제 1C 피라미드 (3.0점)'),([85,375,304,518],'정삼각뿔 ABCD는 굴절률 [[0]]인 투명 물질로 만들어졌다. 꼭짓점의 세 각은 모두 직각이고 밑면의 변 길이는 [[1]]이다. 정육면체의 모서리 부분을 잘라낸 모양이다. 빛을 높이 방향, 즉 밑면에 수직으로 고르게 비춘다.'),([85,519,556,577],'1. 면 ABC에서 굴절한 빛이 비추는 밑면 영역을 그려라. 2. 밑면에서 [[2]] cm 떨어진 곳에 평행한 스크린을 놓는다. 굴절한 빛이 비추는 영역을 그리고 위치와 크기를 밝혀라.')]
}
FLOW.update({
 (2011,'T','2-2'):[([282,117,352,135],'1A (3.5점)'),([280,135,556,273],'정육면체 중심에 반지름 [[0]]인 구형 공동이 있다. 그 바닥에 크기를 무시할 수 있는 작은 퍽이 정지해 있다. 퍽에 수평 속도를 주어 운동시켰을 때 정육면체가 탁자에서 튀어 오르기 위한 최소 속력을, 가능한 모든 정육면체/퍽 질량비에 대해 구하라. 마찰은 없다. 이 최솟값을 주는 질량비 [[1]]는 얼마인가?'),([286,284,355,302],'1B (4점)'),([85,313,301,414],'저항 [[2]]를 오른쪽 그림처럼 같은 구조가 무한히 반복되는 전원 회로에 연결했다. 저항 [[3]]를 흐르는 전류를 구하라. 각 전원의 기전력과 내부 저항은 [[4]]')],
 (2011,'T','3-6'):[([238,249,556,281],'여기서 전류 밀도 [[0]]는 단위 시간에 단위 단면적을 통과하는 전하량이다.'),([85,282,556,307],'전류 밀도는 전자의 수 밀도와 평균 표류 속도로 결정된다.')],
 (2011,'T','3-12'):[([338,663,556,707],'열운동 때문에 실제 전자 운동은 복잡하다. 외부장에서는 모든 전자가 같은 가속도를 받아'),([85,708,556,759],'추가 속도를 얻는다. 이 규칙적인 표류 운동이 전류를 만든다. 여기서는 불규칙한 열운동에 더해진 표류 운동만 다룬다.')],
 (2014,'T','2-2'):[([248,117,394,137],'문제 1A (3.0점)'),([85,139,314,301],'증기 기관은 피스톤이 마찰 없이 움직이는 연직 원통 용기이다. 물과 전기 가열기가 들어 있다. 오른쪽 그림의 네 단계를 반복한다. 1. 피스톤에 추를 올리고 가열기를 켜면 물이 끓어 수증기가 추와 피스톤을 들어 올린다. 2. 일정 높이에 도달하면 추를 빠르게 제거하고 즉시 가열기를 끈다.'),([85,302,556,358],'3. 수증기가 냉각·응축되며 피스톤이 천천히 내려간다. 4. 다른 일정 높이에 도달하면 추를 다시 올린다. 이 순환의 [[0]] 선도를 개략적으로 그리고 효율을 구하라.'),([85,359,556,378],'대기압은 [[1]] Pa, 피스톤 질량은 [[2]] [[3]], 단면적은')],
 (2014,'T','2-6'):[([208,608,433,628],'문제 2 제트 추진 (10점)'),([85,628,556,641],'로켓 엔진은 진행 반대로 연소 생성물을 분출하여 추력을 만든다.'),([85,642,354,780],'가속하면서 로켓 질량은 줄어든다. 러시아 과학자 K. 치올콥스키가 우주 같은 진공에서의 운동에 이 원리를 제안했다. 오늘날 우주 비행은 보편적이다. 카자흐스탄의 바이코누르는 최초 인공위성과 최초 우주비행사 유리 가가린이 발사된 기지이며, 현재는')],
 (2014,'T','4-4'):[([235,219,556,372],'메타물질은 구성 원소 자체보다 인공적으로 설계한 주기 구조에 의해 성질이 결정되는 복합 재료이다. 나노 실험실에서 원래 물질에 다양한 기하학적 주기 구조를 삽입하여 물성을 크게 바꾼다. 거칠게 보면 이 구조들은 원래 물질 속의 매우 큰 인공 원자와 같다. 제작자는 구조 크기와 일정하거나 변화하는 주기 간격 등 여러 매개변수를 조절할 수 있다.')],
 (2014,'T','4-5'):[([85,376,556,440],'한 나노 실험실에서 길이 [[0]], 반지름 [[1]]인 메타물질 전선을 만들었다. 전기 전도도는 축에서 거리에 따라 [[2]]로 변한다. 측정한 물성은 다음 표와 같다.'),([85,575,556,610],'1. [1.0점] 전체 저항 [[3]]의 식과 수치를 구하라.')],
 (2014,'TS','1-2'):[([256,89,372,110],'해설'),([248,108,380,126],'문제 1 (10점)'),([246,125,382,142],'문제 1A (3점)'),([72,143,322,281],'첫 단계의 끓는 과정은 등압이므로 등온이다. 같은 이유로 세 번째 단계의 응축도 등압·등온이다. 두 번째와 네 번째 단계는 단열이다. 오른쪽 그림은 개략적인 [[0]] 선도이다. 두 등온선과 두 단열선으로 이루어진 카르노 순환이므로 효율은')]
})
TABLES={
 (2010,'TS','7-8'):['항목','배점','전체 관성 모멘트 (1)','운동 방정식 (2)','정지 시간 (3)','각속도의 시간 t 의존성 (4)','유효 전기장 (5) 또는 (6)','옴의 법칙 (7)','전류의 시간 t 의존성 (8)','검류계 통과 전하 (9)','전자의 비전하 (10)','전류 방정식 (11)','최대 전류 (12)','전류의 개략적인 시간 변화','최대 에너지 (13)','자기장 (14)','전자기 유도 법칙 (15)','소용돌이 전기장 (16)','포인팅 벡터 (17)','전자기 에너지 (18)','전자기 에너지 (19)'],
 (2011,'TS','7-20'):['항목','배점','줄–렌츠 법칙 (1)','부피당 열출력 (2)','식 (3)','최종 결과 (4)','운동 방정식 (5)','이동 거리 (6)','평균 속력 (7)','평균 속도 벡터 (8)','전류 밀도 (9)','전기 전도도 (10)','전자 운동 에너지 (11)','총 전달 열량 (12)','운동 방정식 (13)','운동 방정식 (14)–(16)','속도 (23)','속도 (24)','속도 전개 (25)','변위 (26)','평균 속력 (27)','최종 결과 (29)','올바른 면','운동 방정식 (30)–(32)','속도 (39)','속도 (40)','홀 전기장 (41)','홀 전기장 (42)']
}
EARLY_TABLE_IDS={(2012,'TS'):set('2-2 2-3 2-4 3-7 3-8 3-9 3-10 5-4 5-5 5-7 5-9 8-4 8-5 8-6 8-7 8-8 8-9 8-10 8-11 8-12 8-13 8-14 8-15 8-16 8-17 11-5 11-6 11-8 11-9 11-12'.split())}
EARLY_TABLE_IDS[(2013,'TS')]=set('1-51 1-53 2-13 2-15 3-6 7-3 7-5 7-6 7-7 7-8 7-9 7-10 8-1 9-47 9-48 10-1 10-2 10-3'.split())
EARLY_TABLE_IDS[(2010,'TS')]=set('1-33 1-34 2-1 2-3 4-42 4-44 4-46 4-48 5-1'.split())
EARLY_TABLE_IDS[(2011,'TS')]=set('1-14 2-23 10-13 10-14 10-15 10-16'.split())
EARLY_TABLE_IDS[(2014,'T')]=set('4-10 4-11 4-12'.split())
EARLY_TABLE_IDS[(2014,'TS')]=set('1-19 3-4 3-6 3-7 3-9 3-10 3-11 3-12 3-15 4-5 6-61 7-1 7-2 9-29 9-30 10-1'.split())
EARLY_TABLE_IDS[(2010,'T3S')]=set('5-22 5-23 5-25'.split())
TABLE_CUTOFFS={(2013,'TS','1-53'):760,(2013,'TS','2-15'):400}
TABLE_CUTOFFS[(2011,'TS','1-14')]=680
ATOM_IDS={(2013,'TS'):set('2-17 2-19 2-21 2-22 2-23 2-24 2-25 2-26 3-1'.split())}
ATOM_IDS[(2011,'TS')]={'4-10'}
ATOM_WORDS={', thus':', 따라서','. Thus,':'. 따라서','the pyramid. The height of the lateral facet is':'옆면의 높이는','pyramid’s height':'피라미드 높이는','Then,':'따라서','.Finally, the point':'. 구하는 점은','sought is located at the':'다음만큼','distance':'떨어져 있다:','. The':'. 또한 이','same point is located at a distance':'점의 밑변 중점까지 거리는','fromthemiddlepointofbase’sside Thus,the beam refracted by the facet':'이다. 따라서 옆면에서 굴절한 광선은'}
ATOM_WORDS['and']='및'
ATOM_WORDS.update({', thus':', 즉','distance':'거리는','. The':'. 이','sought is located at the':'구하는'})
TABLE_WORDS={
 'points':'배점','Points':'배점','Figure with all the forces':'모든 힘을 표시한 그림','The system of equations (1)':'연립방정식 (1)','The solution of (1) to speed up (2)':'식 (1)의 해, 가속도 (2)',
 'Exception 4 second load from a consideration of':'두 번째 추를 운동 방정식에서 제외','Proof of exceptions (second acceleration load greater tensile':'제외 근거: 가속도가 g보다 크거나',
 'strength filament is negative)':'실의 장력이 음수임)','Acceleration second load is equal to g':'두 번째 추의 가속도는 g','The system of equations (3)':'연립방정식 (3)','A solution of (3) for the acceleration (4)':'식 (3)의 해, 가속도 (4)','Total':'합계','Contents of number scores':'평가 항목',
 'In a parallel connection of power currents are added':'병렬 연결에서는 전류를 더함','Plotting functions':'함수 그래프','and':'및','If you are connected in parallel are added voltage':'직렬 연결에서는 전압을 더함','“Horizontal” summation':'가로 방향 합산','are calculated for:':'계산점 수:','3 points;':'3개 점;','6 points.':'6개 점.',
 'Alternatives to (realized ideas):':'대안 풀이(구현한 아이디어):','To approximate the dependence;':'의존성을 근사;','To solve the equations explicitly;':'방정식을 직접 풂;',
 'Formulation of basic idea: the constancy of the propagation':'핵심 원리: 모든 광선 경로의','time for all the paths':'전파 시간이 같음','Using the quadratic approximation (for small angles)':'작은 각도에 대한 2차 근사','Calculation of distances':'거리 계산','- The exact formula;':'- 정확한 식;','- Expansion of the approximate formula;':'- 근사식 전개;',
 'The optical path length (3)':'광학적 경로 길이 (3)','A formula of a thin lens (4)':'얇은 렌즈 식 (4)','Focal length of lens (7)':'초점 거리 (7)','Distance to the image (8)':'상까지의 거리 (8)',
 'Grading for geometrical optics approximation (alternative solution)':'기하 광학 풀이의 채점 기준(대안 풀이)','The Law of refraction':'굴절 법칙','Two small-angle approximation (but quadratic)':'작은 각도에 대한 2차 근사 두 개','The starting angle of the plate':'평판 입사각','The differential equation for the ray trajectory in a plate':'평판 내부 광선 궤적의 미분방정식','The solution to the quadratic approximation':'2차 근사 해','The value of the angle near the back edge':'뒷면에 도달할 때의 각도','The value of the angle after refraction on the rear face':'뒷면에서 굴절한 뒤 각도','The point of intersection with the optical axis':'광축과의 교점','Persistence of distance b for all the refracted rays':'모든 굴절 광선에서 거리 b가 같음','formula analogous to the thin lens':'얇은 렌즈와 같은 형태의 식','10 The formula for the focal length':'10 초점 거리 식',
 'Numerical value of':'수치','Plot:  X axis symbol indicated':'그래프: 가로축 기호','Plot: Y axis symbol indicated':'그래프: 세로축 기호','Plot: k  shown from 0 to 1':'그래프: k의 범위 0–1','Plot: appropriate values on plot':'그래프: 올바른 값','Appropriate value of k':'올바른 k값','Appropriate value of':'올바른 값'
}
TABLE_WORDS.update({'Grading scheme for Problem 1.A':'문제 1A 채점 기준','Description':'항목','Correct value of the acceleration':'올바른 가속도','There is a correct reasoning, some justification for the final':'올바른 추론과 최종 답의','answer':'근거','Correctmethodtofind':'올바른 계산법','is presented':'제시','Exact answer for':'정확한 값','Reasonable method to solve for α is presented':'α를 구하는 타당한 방법','Final answer for α':'α의 최종 답','Correct value for air pressure at T=200':'T=200에서 공기 압력','Vapor pressure was found for any temperature':'임의 온도에서 증기압','Conditionfor':'조건','was written':'제시','Correct final answer':'올바른 최종 답','Light refraction law':'굴절 법칙','Incidence angle on the facet of the pyramid':'피라미드 옆면 입사각','Location of pointF':'점 F의 위치','Illuminated regions at the base of the pyramid':'밑면의 밝은 영역','Outlet angle at the base':'밑면 출사각','Illuminated regions at the screen':'스크린의 밝은 영역','Properly set northern N and southern S poles':'북극 N, 남극 S의 올바른 표시','Solution (6)':'해 (6)','Graphof':'그래프','Graph of':'그래프',': axis signed and digitized':': 축 이름과 눈금',': there is a part with a constant velocity':': 등속 구간',': there is a part with constant acceleration':': 등가속도 구간',': continuous':': 연속',': correct numerical values':': 올바른 수치',': there is a part with constant current':': 일정 전류 구간',': there is a part with zero current':': 전류 0인 구간',': discontinuous':': 불연속','Relationship (15)':'관계식 (15)','Quasi-elastic force (16)':'준탄성력 (16)','Eq of motion (17)':'운동 방정식 (17)','Equilibrium point (19)':'평형점 (19)','Condition (20)':'조건 (20)','Eq (21) for':'식 (21)의','Numerical value':'수치','Frequency (18)':'진동수 (18)',': two periods of current oscillation':': 전류 진동 두 주기',': correct value of amplitude':': 올바른 진폭','Ohm’s Law (25)':'옴의 법칙 (25)','Eq of motion (26)':'운동 방정식 (26)','Expression (29)':'식 (29)','Correct numerical value of':'올바른 수치','The conservation law (12)':'보존 법칙 (12)','Correct numerical value':'올바른 수치'})
TABLE_WORDS.update({'Items':'항목','Content':'항목','Contents':'항목','Writing down balance equation for the kinetic and potential':'운동·위치 에너지 보존식 및','energies and determination of the angular velocity of rotation of':'질량 중심의 회전 각속도','the center of mass':'계산','Determination of the normal acceleration':'구심 가속도 계산','Determination of the tangent acceleration from the equation of':'회전 운동 방정식으로 접선 가속도','dynamics of rotation':'계산','Determination of the component of the reaction force of the':'뉴턴 제2법칙으로 지지대의','support from the 2nd Newton law':'반작용 성분 계산','Marking scheme.':'채점 기준','Solution item number':'풀이 항목','Plotting of the ray tracing to explain the emergence of the':'본그림자·반그림자의 발생을 설명하는','shadow and semi-shadow':'광선 경로','Geometric relationships between size of the source, location':'광원 크기, 판의 위치·크기,','and size of the plate and size of the shadow and the semi-':'본그림자·반그림자 크기의 기하학적','shadow (1)-(2)':'관계 (1), (2)','Calculation of height of the plate above the floor (with a':'바닥 위 판의 높이 계산','numerical value)':'(수치 포함)','Calculation of the dimensions of the source (with numerical':'광원 크기 계산(수치','values)':'포함)','Position of the source with respect to the shadow':'그림자에 대한 광원의 방향','Equivalent circuit':'등가 회로','Rule 1':'규칙 1','Rule 2':'규칙 2','Normalizing condition (1)':'정규화 조건 (1)','Calculation of the number of particles (2)':'입자 수 계산 (2)','General expression for the internal energy U':'내부 에너지 U의 일반식','Calculation of the internal energy U (3)':'내부 에너지 U 계산 (3)','Calculation of the classical limit of U (4)':'U의 고전 극한 (4)','Calculation of the low temperature limit of U (5)':'U의 저온 극한 (5)','General expression for average force (10)':'평균 힘의 일반식 (10)','General expression for P (11)':'압력 P의 일반식 (11)','Calculation of the pressure P (12)':'압력 P 계산 (12)','Calculation of the classical limit of P (13)':'P의 고전 극한 (13)','Calculation of the low temperature limit of P (14)':'P의 저온 극한 (14)','Schematic plot  P':'P의 개략적인 그래프'})
TABLE_WORDS.update({'PHYSICAL PROPERTY':'물성','NUMERICAL VALUE':'수치','Conductivity':'전기 전도도','Heat transfer coefficient':'열전달 계수','Thermal conductivity  coefficient':'열전도율',"Young's modulus":'영률','Linear expansion coefficient':'선팽창 계수','Grading scheme':'채점 기준','1 and 3 stages are isobars and isotherms':'1, 3단계는 등압·등온','2 and 4 stages are adiabats':'2, 4단계는 단열','The cycle is identified as a Carnot cycle':'카르노 순환의 확인','Correct cycle diagram':'올바른 순환 선도','Formula (1) for the efficiency of the Carnot cycle':'카르노 효율 식 (1)','Formulas (2) and (4)':'식 (2), (4)','Correct numerical value for the efficiency':'올바른 효율 수치','There is a correct set of equations allowing to obtain the answer –':'답을 구할 수 있는 올바른 연립방정식 –','if there is an error in the set or it is not complete – 0.':'식에 오류가 있거나 불완전하면 0점.','Correct expression for the current in the resistor':'저항의 전류에 대한 올바른 식','or/and for the':'또는','charge of the capacitor':'축전기 전하','Correct expression for the derivative of the square of the current':'전류 제곱의 시간 미분에 대한 올바른 식',', or correct dependence':', 또는 올바른 의존성','For manipulating errors – 1.0 points of 2.0':'계산 조작 오류는 2점 중 1점','Propagation error is not accepted':'오차 전파는 인정하지 않음','Correct formula for':'올바른 식','II. Solution with the equivalent source':'II. 등가 전원 풀이','Propagation errors are not accepted':'오차 전파는 인정하지 않음','Idea: to change the left part of the circuit by an equivalent source':'왼쪽 회로를 등가 전원으로 바꾸고','and to apply the energy conservation law':'에너지 보존을 적용하는 발상','The parameters of the equivalent source':'등가 전원의 매개변수','2.1 Two of the following statement are present:':'2.1 다음 중 두 가지 제시:','1. No-load voltage Ɛ/2':'1. 무부하 전압 ε/2','2. Short circuit current Ɛ/':'2. 단락 전류 ε/','3. Internal resistance is the parallel connection of two resistors':'3. 내부 저항은 두 저항의 병렬 연결','the dependence':'의존성',') is obtained':')를 구함','2.2 It is found that: Ɛ':'2.2 다음을 구함: ε','/2 (по 0.5 for each)':'/2 (각각 0.5점)','(Justification of the equivalent circuit is not required)':'(등가 회로의 유도는 요구하지 않음)','Total released heat in the equivalent circuit':'등가 회로의 전체 발생 열량','Correct answer':'올바른 답','Correct justification of the correct answer':'올바른 답의 타당한 근거','There is an error in the application of the lens formulas':'렌즈 식 적용에 오류가 있음','Initial condition':'초기 조건','Equating the coefficients of the polynomial in time to zero':'시간 다항식의 계수를 0으로 둠','Application of formula (19) to get equation (22)':'식 (19)로 식 (22)를 얻음'})
TABLE_WORDS.update({'Схема оценивания':'채점 기준','Содержание':'항목','баллы':'배점','Записать  аналитическое выражение (1)':'해석적 식 (1) 제시','Получить численное значение в (1)':'식 (1)의 수치 계산','Записать выражение (5)':'식 (5) 제시','Утверждение об инваринтности выражения (5)':'식 (5)의 불변성 명시','Показать из  выражения (6), что  пороговая энергия':'식 (6)으로 반대 방향 운동량에서','минимальна при антипараллельных импульсах':'문턱 에너지가 최소임을 보임','Получить выражение  (8)':'식 (8) 유도','Получить соотношение (10)':'관계식 (10) 유도','Найти (13)(16) или  (21)':'식 (13), (16) 또는 (21) 계산','Найти G-фактор (17)':'G 인자 (17) 계산','Получить (19)':'식 (19) 유도','Получить  выражение (25), (26)':'식 (25), (26) 유도','Получить (27)':'식 (27) 유도','Вывод из законов сохранения энергии-импульса (28)-(30)':'에너지·운동량 보존으로 식 (28)–(30) 유도','Вывод из преобразования Лоренца (31) пп.  A и B':'A, B의 로런츠 변환 식 (31) 유도','Вывод формулы (33)':'식 (33) 유도'})
LAYOUT_KO={
 (2010,'TS','5-5'):'2. [1점] 강체인 코일의 회전 운동 방정식은',
 (2011,'TS','1-4'):'(1) 전체 역학적 에너지도 보존된다.',
 (2011,'TS','1-9'):'식 (1)–(4)를 함께 풀면 퍽의 속력은',
 (2011,'TS','1-12'):'이 값은 다음 질량비에서 얻어진다.',
 (2011,'TS','1-14'):'1B (4점) 무한 전원 회로를 기전력 [[0]], 내부 저항 [[1]]인 등가 전원으로 바꾸면 왼쪽 회로가 된다. 저항 [[2]]를 떼고 전원 두 개를 추가한 뒤 저항 [[3]]를 다시 연결하면 오른쪽 회로를 얻는다. 전원 셀의 수는',
 (2012,'TS','6-5'):'2.2, 2.3 [2점] 첫 단계에서 기체는 압축되어 가열된다. 벽과 피스톤의 열전도성이 낮으므로 단열로 볼 수 있지만, 비평형이므로 단열 상태 방정식을 쓸 수 없다. 처음 상태에서 마지막 상태까지 피스톤과 기체에 중력과 대기압이 한 일은',
 (2012,'TS','6-6'):'문제 조건에 따라 이 일의 절반만 기체 내부 에너지를 증가시킨다.',
 (2012,'TS','6-13'):'식 (2)–(6)을 풀면',
 (2012,'TS','6-19'):'[[22]] [0.5점] 피스톤은 계속 평형이므로 압력은',
 (2012,'TS','6-22'):'[[1]] [0.5점] 충분히 시간이 지나면 용기 안 기체 온도는 주변 온도와 같아진다.',
 (2012,'TS','6-26'):'[[10]] [2점] 다음 형태의 단열 방정식에서',
 (2012,'TS','7-17'):'[[1]] [1점] 일정한 속도로 움직일 때에도 피스톤은 평형이므로 압력은',
 (2012,'TS','7-20'):'즉',
 (2012,'TS','7-29'):'에너지 보존 법칙은',
 (2012,'TS','9-57'):'표면 에너지는 바이츠제커 반경험식의 두 번째 항에 해당한다.',
 (2012,'TS','10-0'):'3.5 [2점] 핵분열이 에너지상 유리하려면 핵들의 위치 에너지가 감소해야 한다. 즉',
 (2012,'TS','10-13'):'지점에서 최솟값을 갖는다. 이는 다음에 해당한다.',
 (2012,'TS','10-27'):'핵의 불안정 조건은 다음과 같다.'
}
LAYOUT_KO[(2013,'TS','9-27')]='10. 짧은 시간 dt 동안 전자가 회전하는 각 [[0]]는 다음과 같다.'
LAYOUT_KO[(2011,'TS','8-2')]='1 [1점] 전체 입자 수의 정규화 조건으로 상수 [[0]]를 정한다.'

def table_word(t):
 if t in TABLE_WORDS:return TABLE_WORDS[t]
 norm=' '.join(t.split())
 for key,value in TABLE_WORDS.items():
  if ' '.join(key.split())==norm:return value
 if 'molar heat capacity' in norm or 'plot for' in norm or re.search(r'[CС]_V',norm):
  n=re.search(r'\(\d+\)',norm);suffix=' '+n[0] if n else ''
  if 'General expression' in norm:return '몰비열 C_V의 일반식'+suffix
  if 'classical limit' in norm:return 'C_V의 고전 극한'+suffix
  if 'low temperature limit' in norm:return 'C_V의 저온 극한'+suffix
  if 'Schematic plot' in norm:return 'C_V의 개략적인 그래프'
  if 'Calculation' in norm:return '몰비열 C_V 계산'+suffix
 if t=='Eq':return '식'
 if re.fullmatch(r'Formula \(\d+\)',t):return t.replace('Formula','식')
 if re.fullmatch(r'Formula \(\d+\) for',t):return t.replace('Formula','식').replace(' for','의')
 if re.fullmatch(r'Correct numerical(?: numerical)? value in \(\d+\)',t):return '올바른 수치 '+re.search(r'\(\d+\)',t)[0]
 if t=='Formulas (5) and (6)':return '식 (5), (6)'
 if t=='Formula for (25) for':return '식 (25)의'
 if re.fullmatch(r'Eq\s*\(\d+\)',t):return re.sub('Eq','식',t)
 if t.lower() in {'crtitcal','critical','top','vap','min','rdt'}:return None
 raise ValueError('Untranslated grading cell: '+t)

def prepare(year,kind):
 folder=ROOT/f'tools/ko/izho/{year}/{kind}'
 raw=folder/'translation.raw.json'
 if not raw.exists():raw.write_bytes((folder/'translation.json').read_bytes())
 data=json.loads(raw.read_text(encoding='utf8'));fitz.TOOLS.set_small_glyph_heights(bool(data.get('small_glyph_heights')));doc=fitz.open(ROOT/data['source']);out=[];equation_separations=[]
 if data.get('source_pages') is not None:doc.select(data['source_pages'])
 data['preserve_rects']=[]
 data['erase_rects']=copy.deepcopy(data.get('base_erase_rects',[]))
 data['transparent_math_restore']=True
 data['math_line_height']=True
 consolidation_audit=[]
 for pi,page in enumerate(doc):
  entries=[e for e in data['entries'] if e['page']==pi];groups=[];cells=[]
  # Figure captions sometimes share a Word block with another caption. Keep
  # each label in its original box rather than treating the two as a paragraph.
  for e in list(entries):
   if e.get('math') or not re.fullmatch(r'(?:\s*Fig(?:ure)?\.?\s*\d+\s*)+',e['source'],re.I):continue
   entries.remove(e);j=0
   for line in page.get_text('dict')['blocks'][block_index(e)].get('lines',[]):
    for span in line['spans']:
     match=re.fullmatch(r'\s*Fig(?:ure)?\.?\s*(\d+)\s*',span['text'],re.I)
     if match:
      cells.append({'id':e['id']+f'cap{j}','page':pi,'rect':list(span['bbox']),'size':min(e['size'],11),'source':span['text'].strip(),'ko':'그림 '+match[1],'math':[],'figure_caption':True});j+=1
  if year==2011 and kind=='T' and pi==2:entries=[e for e in entries if e['id'] not in {'3-64','3-65'}]
  for e in list(entries):
   if e['id'] not in ATOM_IDS.get((year,kind),set()):continue
   entries.remove(e);j=0
   for line in page.get_text('dict')['blocks'][block_index(e)].get('lines',[]):
    for span in line['spans']:
     t=span['text'].strip()
     if not re.search(r'[A-Za-z]{3,}',t) or candidate(span):continue
     if t not in ATOM_WORDS:raise ValueError('Untranslated formula-adjacent prose: '+t)
     cells.append({'id':e['id']+f'a{j}','page':pi,'rect':list(span['bbox']),'size':min(e['size'],11.4),'source':t,'ko':ATOM_WORDS[t],'math':[],'formula_adjacent_prose':True})
     j+=1
  for drawing in page.get_drawings():
   r=drawing['rect']
   if 44<r.y0<50 and r.width>400 and r.height<2:data['preserve_rects'].append({'page':pi,'rect':list(r),'kind':'original_header_rule'})
  if year==2010 and kind=='T' and pi==2:data['preserve_rects'].append({'page':pi,'rect':[325,684.5,406,717.5],'kind':'original_display_formula'})
  if year==2012 and kind=='T' and pi==1:data['preserve_rects'].append({'page':pi,'rect':[178,574.8,337,601.5],'kind':'original_display_formula'})
  if year==2011 and kind=='T' and pi==1:
   for rr in [[85,136,263,270],[306,307,554,424]]:data['preserve_rects'].append({'page':pi,'rect':rr,'kind':'original_diagram_ink','source_type':'vector'})
  if year==2011 and kind=='T' and pi==2:
   for rr in [[84,143,220,237],[93,514,331,674]]:data['preserve_rects'].append({'page':pi,'rect':rr,'kind':'original_diagram_ink','source_type':'vector'})
  for b in page.get_text('dict')['blocks']:
   if b['type']!=1:continue
   r=fitz.Rect(b['bbox'])
   if r.get_area()<4500 or r.height<40:continue
   im=Image.open(io.BytesIO(b['image'])).convert('L');ink=im.point(lambda v:255 if v<220 else 0).getbbox()
   if ink:
    x0,y0,x1,y1=ink;r0=[r.x0+x0/im.width*r.width,r.y0+y0/im.height*r.height,r.x0+x1/im.width*r.width,r.y0+y1/im.height*r.height]
    data['preserve_rects'].append({'page':pi,'rect':r0,'kind':'original_diagram_ink'})
  for e in list(entries):
   flow=FLOW.get((year,kind,e['id']))
   if flow:
    entries.remove(e)
    for line in page.get_text('dict')['blocks'][block_index(e)].get('lines',[]):
     for span in line['spans']:
      if not span['text'].strip():continue
      if (year,kind,e['id'])==(2010,'T','3-13') and 'where' not in span['text']:continue
      data['erase_rects'].append({'page':pi,'rect':list(span['bbox'])})
    for fi,(r,ko) in enumerate(flow):
     q=copy.deepcopy(e);q['id']+=f'f{fi}';q['rect']=r;q['ko']=ko;q['source_unsegmented']=e['source'];q['flow_segment']=True
     if year>=2014:q['size']=min(e['size'],12)
     markers=re.findall(r'\[\[\d+\]\]',ko);q['source']=re.sub(r'\[\[\d+\]\]','',e['source'])+' '+' '.join(markers)
     entries.append(q)
   elif not (year==2012 and kind=='TS' and e['id']=='10-0'):
    # Empty Word spans sometimes enlarge a paragraph by half a page.
    spans=[s for l in page.get_text('dict')['blocks'][block_index(e)].get('lines',[]) for s in l['spans'] if s['text'].strip()]
    if spans:
     r=fitz.Rect(spans[0]['bbox'])
     for s in spans[1:]:r|=fitz.Rect(s['bbox'])
     e['rect']=list(r)
  for e in list(entries):
   if e['id'] not in EARLY_TABLE_IDS.get((year,kind),set()):continue
   block=page.get_text('dict')['blocks'][block_index(e)]
   cutoff=TABLE_CUTOFFS.get((year,kind,e['id']))
   if cutoff is None:entries.remove(e)
   else:e['body_only_after']=cutoff
   j=0
   for line in block['lines']:
    if cutoff is not None and line['bbox'][1]>cutoff:continue
    for span in line['spans']:
     text=span['text'].strip()
     if not re.search(r'[A-Za-zА-Яа-яЁё]{3,}|\bEq\b',text):continue
     ko=table_word(text)
     if ko is None:continue
     r=fitz.Rect(span['bbox']);y=span['origin'][1]
     cells.append({'id':e['id']+f'c{j}','page':pi,'rect':[r.x0,y-10.8,r.x1,y+3.2],
       'redact_rect':[r.x0-.1,y-10.3,r.x1+.1,y+2.6], 'size':8.9,'source':text,'ko':ko,'math':[],'original_table_cell':True})
     j+=1
  # One Word block contains the preceding grading table and a new title next
  # to a diagram. Split that new paragraph after translating the table cells.
  if year==2013 and kind=='TS':
   for e in list(entries):
    if e['id']=='2-15':
     entries.remove(e)
     parts=[([246,413,382,429],'문제 1C 피라미드'),([72,430,344,500],'1. 꼭짓점 가까운 옆면에 입사하는 광선을 생각하자. 입사각은 옆면과 밑면 사이 각 [[2]]와 같다. 기하학적으로 다음 관계를 쉽게 보일 수 있다.')]
     for fi,(rr,ko) in enumerate(parts):
      q=copy.deepcopy(e);q['id']+=f'f{fi}';q['rect']=rr;q['ko']=ko;q['flow_segment']=True;q['source_unsegmented']=e['source'];q['source']=re.sub(r'\[\[\d+\]\]','',e['source'])+' '+' '.join(re.findall(r'\[\[\d+\]\]',ko));entries.append(q)
  if data.get('provenance',{}).get('source_language')!='Russian':
   for e in entries:
    if e.get('flow_segment'):continue
    block=page.get_text('dict')['blocks'][block_index(e)]
    prose_lines=[]
    for line in block.get('lines',[]):
     if line['bbox'][1]<e.get('body_only_after',-1):continue
     words=re.findall(r'[A-Za-z]{3,}',' '.join(s['text'] for s in line['spans']))
     if (year,kind,e['id'])==(2012,'TS','10-0') and 'International' in words:
      r0=list(line['bbox']);cells.append({'id':'10-0c999','page':pi,'rect':r0,'size':10,'source':'VIII International Zhautykov Olympiad, Almaty, Kazakhstan, 2012','ko':'제8회 국제 자우티코프 올림피아드, 알마티, 카자흐스탄, 2012','math':[]})
      continue
     if any(w.lower() not in {'sin','cos','tan','exp','log','max','min','surf','sur','tot','rot','crtitcal','critical','arcsin'} for w in words):prose_lines.append(line)
    if not prose_lines:continue
    r=fitz.Rect(prose_lines[0]['bbox'])
    for l in prose_lines[1:]:r|=fitz.Rect(l['bbox'])
    outside=[i for i,m in enumerate(e.get('math',[])) if (fitz.Rect(m['rect']).y0+fitz.Rect(m['rect']).y1)/2<r.y0+.5 or (fitz.Rect(m['rect']).y0+fitz.Rect(m['rect']).y1)/2>r.y1-.5]
    if e.get('body_only_after'):
     e['rect']=list(r);e['ko']=LAYOUT_KO.get((year,kind,e['id']),e['ko'])
    if not outside:continue
    oldko=e['ko']
    for mi in outside:e['ko']=e['ko'].replace(f'[[{mi}]]','')
    e['ko']=LAYOUT_KO.get((year,kind,e['id']),e['ko'])
    e['preserved_math']=outside
    e['rect']=list(r)
    equation_separations.append({'id':e['id'],'preserved_math':outside,'ko':e['ko'],'old_ko':oldko})
  for ei,e in enumerate(entries):
   for mi in e.pop('preserved_math',[]):e['source']=e['source'].replace(f'[[{mi}]]','')
   q,audit=consolidate(page,e,folder)
   entries[ei]=q
   if audit:consolidation_audit.append(audit)
  for e in list(entries):
   if (year,kind,e['id']) not in TABLES:continue
   translations=TABLES[year,kind,e['id']]
   block=page.get_text('dict')['blocks'][block_index(e)]
   lines=[l for l in block['lines'] if re.search(r'[A-Za-z]{3,}',' '.join(s['text'] for s in l['spans']))]
   if len(lines)!=len(translations):raise ValueError(f"Table line count {year}/{kind}/{e['id']}: {len(lines)} != {len(translations)}")
   entries.remove(e)
   for j,(line,ko) in enumerate(zip(lines,translations)):
    words=' '.join(s['text'] for s in line['spans']).strip();r=fitz.Rect(line['bbox']);baseline=max(s['origin'][1] for s in line['spans'])
    # Keep numbers, borders, and the source column geometry untouched.
    right=520 if words.lower()=='points' else 460
    x0=r.x0 if words.lower() in {'points','content','contents'} else min(r.x0,138)
    cell={'id':e['id']+f'c{j}','page':pi,'rect':[x0,baseline-10.8,right,baseline+2.5],
          'redact_rect':[r.x0-.1,baseline-10,r.x1+.1,baseline+2],
          'size':9.6,'source':words,'ko':ko,'math':[],'original_table_cell':True}
    cells.append(cell)
  for e in entries:
   r=fitz.Rect(e['rect']);hits=[]
   for g in groups:
    # More than the natural 2 pt ascender/descender overlap means Word split a
    # paragraph at an inline object. Neighbouring ordinary lines stay separate.
    if e.get('flow_segment') or any(q.get('flow_segment') for q in g):continue
    if any((r&fitz.Rect(q['rect'])).height>3.4 and (r&fitz.Rect(q['rect'])).width>1 for q in g):
     union=fitz.Rect(r)
     for q in g:union|=fitz.Rect(q['rect'])
     unsafe=False
     for fig in data['preserve_rects']:
      if fig['page']!=pi or fig.get('kind')!='original_diagram_ink':continue
      f=fitz.Rect(fig['rect'])
      if (union&f).get_area()>1 and not (r&f).get_area() and not any((fitz.Rect(q['rect'])&f).get_area() for q in g):unsafe=True
     if not unsafe:hits.append(g)
   merged=[e]
   for g in hits:merged+=g;groups.remove(g)
   groups.append(merged)
  blocks=page.get_text('dict')['blocks']
  for group in groups:
   group.sort(key=block_index);first=group[0]
   bounds=fitz.Rect(first['rect'])
   for e in group:bounds|=fitz.Rect(e['rect'])
   byblock={block_index(e):e for e in group};maths=[];ko=[];src=[]
   for bi in range(len(blocks)):
    if bi in byblock:
     e=byblock[bi];offset=len(maths)
     def renumber(t):return re.sub(r'\[\[(\d+)\]\]',lambda m:f'[[{int(m[1])+offset}]]',t)
     ko.append(renumber(e['ko']));source=e['source']
     for mi in e.get('preserved_math',[]):source=source.replace(f'[[{mi}]]','')
     src.append(renumber(source));maths+=copy.deepcopy(e.get('math',[]))
    else:
     b=blocks[bi];r=fitz.Rect(b['bbox']);inside=(r&bounds).get_area()
     if not inside or inside/r.get_area()<.85:continue
     # These intervening blocks are the inline formula objects that interrupted
     # the paragraph, rather than independent diagrams outside its column.
     if b['type']==1 and r.width*r.height>4500:continue
     text=' '.join(s['text'] for l in b.get('lines',[]) for s in l['spans'])
     if b['type']==0 and re.search(r'[A-Za-zА-Яа-яЁё]{4,}',text):continue
     if b['type']==0 and any(bi==block_index(q) for q in entries):continue
     if b['type']==0 and not text.strip():continue
     r+=(-.15,-.15,.15,.15);name=f"{first['id']}-join-{bi}.png"
     page.get_pixmap(matrix=fitz.Matrix(4,4),clip=r,alpha=False).save(folder/name)
     maths.append({'file':name,'rect':list(r),'width':r.width,'height':r.height,'text':text})
     ko.append(f'[[{len(maths)-1}]]');src.append(f'[[{len(maths)-1}]]')
   e=copy.deepcopy(first);e.pop('preserved_math',None);e.update(rect=list(bounds),math=maths,ko=' '.join(ko),source=' '.join(src),merged_ids=[q['id'] for q in group])
   if year==2013 and kind=='TS' and e['id']=='5-2':e['rect'][1]+=7
   if year==2010 and kind=='T' and e['id']=='4-3':e['rect']=[150,107,492,142];e['align']='center'
   out.append(e)
  out+=cells
 # Preserve the original right-hand page-number position separately from the
 # Korean competition header. HTML otherwise collapses the source's spacing.
 counters=[]
 for e in out:
  match=re.search(r'(?:Page|с\.)\s*(\d+/\d+)',e['source']) if e['rect'][1]<50 else None
  if match:
   number=match[1];e['ko']=re.sub(r'\s*\d+/\d+쪽$','',e['ko']);e['rect'][2]=480
   counters.append({'id':e['id']+'p99','page':e['page'],'rect':[500,e['rect'][1],558,e['rect'][3]],'redact_rect':[480,e['rect'][1],558,e['rect'][3]],'size':min(e['size'],10),'source':'Page '+number,'ko':number+'쪽','math':[]})
 out+=counters
 if year==2012 and kind=='T':
  data['post_overlays']=[{'page':2,'rect':[107,107,176,124],'text':'대기','size':10.5,'align':'center'},
    {'page':2,'rect':[175,139,228,154],'text':'피스톤','size':10,'align':'center'},
    {'page':2,'rect':[116,228,156,242],'text':'공기','size':10.5,'align':'center'}]
 if year==2010 and kind=='T':
  data['post_overlays']=[{'page':3,'rect':[85,803,556,824],
    'text':'정오: 델타(1232) 질량은 1.232 x 10^9 eV/c^2이다. 원문의 10^6은 10^9의 오탈자다.',
    'size':8,'align':'left'}]
  data['editorial_corrections']=[{'page':3,'original':'m_Delta=1.232×10^6 eV/c²','correct':'m_Delta=1.232×10^9 eV/c²',
     'source':'https://pdgweb.lbl.gov/2025/tables/rpp2025-tab-baryons-Delta.pdf',
     'note':'Both official EN and RU statements have the exponent typo; original glyphs are retained and an explicit Korean erratum is added in the margin.'}]
 if year==2011 and kind=='T':
  data['post_overlays']=[{'page':2,'rect':[106,523,130,540],'text':'이온','size':9.5,'align':'center'},
    {'page':2,'rect':[218,647,261,665],'text':'전자','size':10,'align':'center'}]
 data['entries']=sorted(out,key=lambda e:(e['page'],float(re.match(r'\d+-(\d+)',e['id'])[1])))
 data['layout_preparation']='izho_early_layout.py: joined overlapping prose fragments with intervening original equations'
 (folder/'translation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
 (ROOT/f'tmp/izho-early/{year}-{kind}-equation-separations.json').write_text(json.dumps(equation_separations,ensure_ascii=False,indent=2),encoding='utf8')
 (ROOT/f'tmp/izho-early/{year}-{kind}-equation-consolidation.json').write_text(json.dumps(consolidation_audit,ensure_ascii=False,indent=2),encoding='utf8')
 print(year,kind,len(data['entries']),'paragraphs')

if __name__=='__main__':
 import sys
 for year in map(int,sys.argv[1:] or range(2010,2018)):
  for kind in ['T','TS']:prepare(year,kind)
