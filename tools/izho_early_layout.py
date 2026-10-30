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
from izho_early_math import consolidate,candidate,math_pixmap,register_math_regions
ROOT=Path(__file__).resolve().parents[1]
def block_index(e):return int(re.match(r'\d+-(\d+)',e['id'])[1])

FLOW={
 (2017,'T','5-2'):[([85,73,556,88],'각기둥의 저항'),([85,89,556,103],'1. 수학적 도입 (3.0점)'),([85,104,556,143],'수열의 각 항이 앞선 항들로 표현되면 점화 관계를 만족한다고 한다. 예를 들어 잘 알려진 등비수열에서는')],
 (2017,'T','6-1'):[([85,57,420,157],'2.1 [0.8점] 그림처럼 이웃한 두 꼭짓점에 전원을 연결했을 때 정육면체의 전체 저항을 구하라. 이제 옆면이 [[0]]개인 정각기둥 도선 틀을 생각한다. 각 모서리의 저항은 [[1]]이다.'),([85,159,556,226],'아래 그림처럼 한 옆 모서리의 양 끝점에 전원을 연결한다. 위아래 밑면의 꼭짓점에 차례로 번호를 붙이고 전위를 표시한다. 0번 꼭짓점들에 직류 전압원을 연결하여 전위를 각각 다음과 같이 정한다.')],
 (2016,'T','3-3'):[([85,175,556,205],'관 안의 물 높이를 [[0]]라 하자. 반드시 평형 높이일 필요는 없다.'),([85,207,430,277],'2.1 [0.5점] 수면의 작은 추가 상승량 [[2]]에 따른 표면 에너지 변화 [[1]]의 식을 구하라. 2.2 [0.5점] 같은 상승에 따른 중력 위치 에너지')],
 (2016,'T','3-7'):[([85,497,420,534],'관 안의 물 높이를 [[0]]라 하자. 반드시 평형 높이일 필요는 없다.'),([85,536,556,719],'3.1 [0.5점] 작은 추가 상승량 [[2]]에 따른 표면 에너지 변화 [[1]]의 식을 구하라. 3.2 [0.5점] 상승량 [[4]]에 따른 중력 위치 에너지 변화 [[3]]의 식을 구하라. 3.3 [1.0점] 평형 높이 방정식을 [[5]]와 물음 2.3의 [[6]]로 나타내라. 3.4 [1.0점] 각이 [[7]]일 때 관을 높이 [[8]]까지 물로 채웠다. 최종 수면 높이를 [[9]]의 함수로 구하라. 3.5 [1.0점] 물이 관을 완전히 채우는 각 [[10]]의 범위를 수치와 함께 제시하라.')],
 (2016,'T','4-1'):[([85,57,556,79],'4.1 [3.0점] 물이 병 밖으로 흐르기 시작하는 구멍 반지름의 최솟값은?'),([175,82,360,100],'수학적 도움말'),([85,102,360,126],'구면의 작은 볼록 부분은 다음 함수로 근사할 수 있다.')],
 (2015,'T','2-5'):[([85,383,556,407],'문제 2. 물이 든 용기 (7점)'),([85,408,556,426],'단면적 [[0]], 높이 [[1]]인 원통 용기가 있다.'),([85,427,344,578],'밀폐된 뚜껑에 양 끝이 열린 길이 [[2]]의 관을 수직으로 끼웠다. 아래 끝은 용기 바닥보다 조금 높다. 그림처럼 밀도 [[3]] [[4]]인 물을 붓는다. 관의 단면적은 용기보다 매우 작고 용기 벽은 열을 잘 전도한다. 대기압은 [[5]], 주위 온도는 [[6]] [[7]], 중력 가속도는 [[8]] [[9]]이다.'),([85,582,556,633],'1. [2.0점] 관 전체가 물로 채워지는 순간 용기 안의 수면 높이 [[10]]를 구하라. [[11]]로 나타내고 수치를 계산하라.')],
 (2012,'T','6-2'):[([72,76,330,96],'정전기 상호작용 에너지는 대략 다음과 같다:')],
 (2012,'T','6-4'):[([72,104,413,123],'3.8 [2점] 임계값의 식과 수치를 구하라:'),([72,134,556,153],'알려진 물리 상수:'),([72,153,280,169],'기본 전하'),([363,153,385,169],'C'),([72,169,280,186],'진공 유전율'),([363,169,395,186],'F/m')],
 (2010,'T','2-15'):[([85,715,556,770],'한 변 a = 10 cm인 불투명 정사각형 판을 광원 아래, 바닥에서 [[0]] 높이에 수평으로 놓았다(그림 1). 그림 2의 바닥 그림자는 짙은 직사각형을 옅은 직사각형이 둘러싸며, 바깥 가장자리로 갈수록 밝아진다. 눈금 한 칸은 1.0 cm이다. 광원의 크기')],
 (2010,'T','3-5'):[([333,225,556,273],'반지름 [[0]], 길이 [[1]], 관성 모멘트 [[2]]인 긴 코일이 있다.'),([85,274,556,347],'길이 [[3]], 질량 [[4]]인 금속선을 한 겹 감았으며 단위 길이당 감은 수는 [[5]]이다. 양 끝은 미끄럼 접점을 통해 검류계에 연결된다. 코일과 금속선을 각속도 [[6]]으로 회전시킨 뒤 토크 [[7]]의 마찰력으로 멈춘다. 회로의 전체 저항은 [[8]]이고 전기 용량은 무시한다.')],
 (2010,'T','2-12'):[([85,369,466,411],'[[0]]에 비해 작다. 시험관 안에는 질량을 무시할 수 있는 기체가 부피 [[1]]만큼 들어 있다. 온도는 일정하다.'),([85,412,556,459],'시험관이 바닥에서 일정 높이 위에 정지할 수 있는가? 가능하다면 조건과 높이를 구하고 평형의 안정성을 판정하라. 시험관 벽의 부피는 [[2]]에 비해 무시한다.')],
 (2010,'T','3-13'):[([410,692,458,711],'여기서 [[3]]')],
 (2012,'T','2-9'):[([72,524,556,540],'두께 [[0]]인 투명한 원형 평행 평판은'),([72,541,333,583],'굴절률이 중심축에서 거리 [[1]]에 따라 다음과 같이 변하는 물질로 만들어졌다.')],
 (2012,'T','2-10'):[([72,600,336,675],'여기서 [[1]]는 알려진 양의 상수이다. 평판은 굴절률 [[2]]인 공기 중에 있다. 축 위에서 평판까지 거리 [[3]] [[4]])인 곳에 점광원 [[5]]가 있다.'),([72,676,556,719],'이 평판이 상을 만드는 렌즈처럼 작용함을 보여라. 광원 [[7]]의 상이 평판에서 떨어진 거리 [[6]] 및 초점 거리를 구하라.')],
 (2012,'T','3-2'):[([235,101,556,291],'높이 [[0]] [[1]] cm, 단면적 [[2]] cm²인 열린 원통 용기에 대기압 [[3]] Pa, 온도 [[4]] K인 공기가 있다. 위에서 질량 [[5]] [[6]] kg인 얇고 무거운 피스톤을 조심스럽게 끼운다. 벽과 피스톤은 열전도성이 매우 낮다. 공기는 평균 몰질량 [[7]] g/mol인 이상 이원자 기체이다. 중력 가속도는 [[8]] m/s², 기체 상수는 [[9]] J/(mol·K)이다. 용기·피스톤의 열용량과 벽면 마찰은 무시한다.'),([72,292,556,425],'피스톤을 놓으면 최종 평형까지 두 단계를 거친다. 첫 단계에서는 피스톤이 진동하며 기체 과정은 비평형이다. 이로 인해 진동이 감쇠하고 역학적 에너지가 소산된다. 소산 에너지의 절반은 용기 안 기체에, 절반은 대기에 전달된다. 이 단계에서는 벽과 피스톤을 통한 열전도를 무시한다. 진동이 멎을 때 높이는 [[10]]이다. 두 번째 단계는 느리게 진행되어 높이 [[11]]에서 완전히 멈춘다.'),([91,426,556,463],'2.1 [0.5점] 첫 단계가 끝날 때 압력 [[12]]를 대기압 [[13]], 비열비 [[14]] 및 다음 매개변수로 나타내라.')],
 (2012,'TS','1-2'):[([256,90,414,107],'문제 1 (10점)'),([113,122,280,137],'문제 1A. 2012'),([85,138,281,280],'계에 작용하는 힘은 그림과 같다. 막대가 강체이고 실이 늘어나지 않으므로 추의 가속도 비는 1:2:3이다. 질량 없는 막대의 토크 합은 0이다. 이 조건들과 각 추의 뉴턴 제2법칙으로 다음 연립방정식을 얻는다.')],
 (2012,'TS','2-12'):[([85,533,322,612],'[[0]]의 전류에 해당 배수를 곱하면 된다. 여러 전압에서 전류를 읽고 각각 2배, 3배 한 점을 그래프에 찍는다.'),([85,614,556,644],'직렬 연결의 전체 전압은 각 부분 전압의 합이므로')],
 (2013,'T','2-4'):[([218,358,424,375],'문제 1C 피라미드 (3.0점)'),([85,375,304,518],'정삼각뿔 ABCD는 굴절률 [[0]]인 투명 물질로 만들어졌다. 꼭짓점의 세 각은 모두 직각이고 밑면의 변 길이는 [[1]]이다. 정육면체의 모서리 부분을 잘라낸 모양이다. 빛을 높이 방향, 즉 밑면에 수직으로 고르게 비춘다.'),([85,519,556,577],'1. 면 ABC에서 굴절한 빛이 비추는 밑면 영역을 그려라. 2. 밑면에서 L = 10 cm 떨어진 곳에 평행한 스크린을 놓는다. 굴절한 빛이 비추는 영역을 그리고 위치와 크기를 밝혀라.')]
}
FLOW.update({
 (2013,'T','4-4'):[([85,257,556,300],'2. [1.0점] 궤도 반지름 [[0]]에 따른 전자 속력 v를 구하라. 3. [0.5점] 궤도 반지름 [[2]]에 따른 전자의 각운동량 [[1]]을 구하라.'),([85,299.8,556,313.4],'보어는 전자의 각운동량이 환산 플랑크 상수의 정수배라고 가정했다.')],
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
EARLY_TABLE_IDS[(2015,'TS')]=set('1-6 1-8 1-9 2-1 2-2 3-1 3-3 3-5 3-7 3-10 3-11 3-12 4-1 4-2 5-12 5-14 5-26 5-31 5-33 5-75 10-15 10-16 10-17 10-18 10-20 10-21 10-23 10-24 10-26 10-28 10-30 10-31 10-38 11-1 11-9 11-25 11-42'.split())
EARLY_TABLE_IDS[(2011,'TS')]=set('1-14 2-23 10-13 10-14 10-15 10-16'.split())
EARLY_TABLE_IDS[(2014,'T')]=set('4-10 4-11 4-12'.split())
EARLY_TABLE_IDS[(2014,'TS')]=set('1-19 3-4 3-6 3-7 3-9 3-10 3-11 3-12 3-15 4-5 6-61 7-1 7-2 9-29 9-30 10-1'.split())
EARLY_TABLE_IDS[(2010,'T3S')]=set('5-22 5-23 5-25'.split())
TABLE_CUTOFFS={(2013,'TS','1-53'):760,(2013,'TS','2-15'):400}
TABLE_CUTOFFS[(2011,'TS','1-14')]=680
ATOM_IDS={(2013,'TS'):set('2-17 2-19 2-21 2-22 2-23 2-24 2-25 2-26 3-1'.split())}
ATOM_IDS[(2011,'TS')]={'4-10'}
ATOM_IDS[(2010,'TS')]=set('3-4 3-12 3-16 3-21 3-25 4-3 4-5 4-7 4-9 4-13 4-17 4-19 4-21 4-23 4-25 4-27 4-29 4-31 4-33 4-35 4-37 4-39 4-41'.split())
ATOM_IDS[(2010,'TS')].update({'6-18','6-22'})
ATOM_IDS[(2012,'TS')]={'3-4'}
ATOM_IDS[(2012,'TS')].add('6-27')
ATOM_IDS[(2012,'T')]={'4-4','6-8','6-9'}
ATOM_IDS[(2013,'TS')].add('1-31')
ATOM_IDS[(2013,'TS')].add('9-21')
ATOM_IDS[(2014,'TS')]={'1-15','2-3','2-49','6-42'}
ATOM_IDS[(2014,'TS')].add('7-15')
ATOM_IDS[(2014,'T')]={'4-7'}
ATOM_IDS[(2014,'T')].add('5-4')
ATOM_IDS[(2015,'TS')]={'6-16','8-55','8-59','8-60'}
ATOM_IDS[(2015,'TS')].update({'7-30','7-31'})
ATOM_IDS[(2016,'T')]={'2-14','2-15','2-16','2-17'}
ATOM_IDS[(2017,'T')]={'6-4'}
ATOM_IDS[(2017,'T')].update({'5-3','5-4','5-7','5-8','5-10','5-11','5-12'})
ATOM_WORDS={', thus':', 따라서','. Thus,':'. 따라서','the pyramid. The height of the lateral facet is':'옆면의 높이는','pyramid’s height':'피라미드 높이는','Then,':'따라서','.Finally, the point':'. 구하는 점은','sought is located at the':'다음만큼','distance':'떨어져 있다:','. The':'. 또한 이','same point is located at a distance':'점의 밑변 중점까지 거리는','fromthemiddlepointofbase’sside Thus,the beam refracted by the facet':'이다. 따라서 옆면에서 굴절한 광선은'}
ATOM_WORDS['and']='및'
ATOM_WORDS.update({', thus':', 즉','distance':'거리는','. The':'. 이','sought is located at the':'구하는'})
ATOM_WORDS.update({'where':'단,','— the inverse of graphically given functions':'는 그래프로 주어진 함수의 역함수이다.',
 'Let':'길이','bethelengthofthatpart,':'는 이 부분의 길이,','isitsmass,':'는 질량,','is thetension at the top':'는 위쪽 장력이다.',
 'Thus, the efficiency of the steam engine is':'따라서 증기 기관의 효율은',
 '8. In the proper reference frame the rocket motion is classical, and its acceleration is given by':'8. 고유 기준계에서 로켓의 운동은 고전적으로 다룰 수 있으며, 가속도는 다음과 같다.'})
ATOM_WORDS.update({'arcsin':'arcsin','при':'단,'})
ATOM_WORDS.update({'где':'단,','– постоянная Больцмана.':'는 볼츠만 상수이다.'})
ATOM_WORDS.update({',   при':'단,','equivalent source with the parameters':'등가 전원의 매개변수는','On substituting':'대입하면','we finally obtain':'최종적으로 다음을 얻는다.'})
ATOM_WORDS[', we finally obtain']=', 최종적으로 다음을 얻는다.'
ATOM_WORDS.update({'At':'단,','it simplifies to':'이면 다음과 같이 된다.',
 'The electric field strength of the point charge is determined by the formula':'점전하의 전기장 세기는 다음과 같다.',
 'Equating these two expression the surface density of the induced charges is found as':'두 식을 같게 놓으면 유도 면전하 밀도는',
 'and the magnitude of the induced charge on each side of the disc':'원판의 각 표면에 유도된 전하량의 크기는',', where':', 단'})
ATOM_WORDS['it simplifies to']='이면'
ATOM_WORDS[', we finally obtain']=', 따라서'
ATOM_WORDS.update({'we obtain':'얻는다','is the coefficient determined in formula (16).':'는 식 (16)의 계수이다.',
 'the surface tension':'표면 장력','the contact angle':'접촉각','the mass density':'밀도','the acceleration of gravity':'중력 가속도'})
ATOM_WORDS.update({'Wire frame in the shape of a prism':'각기둥 모양의 도선 틀',"Numbering and denoting vertices' potentials":'꼭짓점 번호와 전위 표시'})
ATOM_WORDS.update({'9. The fallingtime':'9. 낙하 시간','is found from the condition':'는 다음 조건으로 정한다:',
 '. By substituting this into equation (14)':'. 이를 식 (14)에 대입하면'})
ATOM_WORDS['stands for the power loss per unit surface of the wire with the surface temperature']='는 전선의 단위 면적당 열손실률이고, 표면 온도는'
ATOM_WORDS.update({
 'Curves 1 and 2 don’t intersect (Fig.1), if the condition':'다음 조건에서 곡선 1, 2는 만나지 않는다(그림 1):',
 'Fig.4':'그림 4','In this case the test-tube will always sink.':'이 경우 시험관은 항상 가라앉는다.','If the conditions':'다음 두 조건이','If conditions':'다음 조건이',
 'Point A is unstable because the test-tube will sink due to the shift down, and it will rise due to the':'점 A에서 아래로 옮기면 가라앉고 위로 옮기면 떠오르므로 불안정하다.',
 'shift up. Analysis of stability of the point B will be presented below.':'점 B의 안정성은 아래에서 분석한다.',
 'are fulfilled in the same time, curves intersect in two points A and B (Fig.2):':'동시에 성립하면 두 곡선은 A, B 두 점에서 만난다(그림 2).',
 'are fulfilled, only the intersection point B exists (Fig.3). But one should take into account that at the':'성립하면 교점 B만 존재한다(그림 3). 다만 다음 점을 고려해야 한다.',
 'horizontal part of curve 2 motion to the right along this curve results to the gas flow out of the test-':'곡선 2의 수평 부분을 오른쪽으로 이동할 때는 기체가 시험관 밖으로 빠져나간다.',
 'tube. Consequently, motion to the left along the curve will be quite different. It will take place':'따라서 왼쪽으로 되돌아갈 때는 다른 경로를 따른다. 즉,',
 'along the parabola corresponding to (6) (upper line of the formula), but with the new (larger) value':'식 (6)의 위쪽 포물선을 따르지만, 다음 값은 이전보다 커진다:',
 'corresponding to the amount of gas remained in the test-tube.':'이는 시험관 안에 남은 기체의 양에 해당한다.',
 'is fulfilled for':'가 성립하는 경우이다.','газа':'기체','жидкости':'액체',
 'The form of shape described in the problem is explained by the appearance of the full shade (dark':'문제의 그림자는 본그림자(짙은 직사각형)와',
 'rectangle)  and the semi-shadow (lighter outer rectangle). Fig. 1 illustrates the course of outer rays':'반그림자(옅은 바깥 직사각형)가 겹쳐 생긴다. 그림 1은 광선 경로를 나타낸다.',
 'forming a shadow':'본그림자 광선','and the semi-shadow (':'및 반그림자 광선(',
 ') in cross section perpendicular to':')는 광원의',
 'one sides of the source. Denote the full width of the shadow':'한 변에 수직인 단면의 광선이다. 본그림자의 폭을',
 ',, the width of the semi-':', 반그림자','shadow':'의 폭을',
 '. These values can be expressed through the geometric dimensions of the source':'로 놓는다. 이 값들은 광원의 기하학적 크기와',
 'and the plate.':'판의 크기로 나타낼 수 있다.','From the similarity of the triangles':'다음 삼각형의 닮음에서',
 'it follows':'다음을 얻는다.','From the drawing of shadows, we define the':'그림자의 도면에서',
 'required sizes':'필요한 길이를 구하면','Using formula (1) we find':'식 (1)을 이용하면',
 'Hence,':'따라서','we':'','find':'즉','From':'또한',
 'formula (2) we find one of the transverse':'식 (2)로 광원의 한 방향 크기를','source size':'구하면',
 '. Similar calculations for the perpendicular cross section gives the following':'. 수직인 다른 단면에서 같은 계산을 하면',
 'results:':'다음과 같다:','Then, it follows that':'따라서',
 'The results indicate that the long side of the source is placed horizontally (if you use fig.2 from the':'이 결과에서 광원의 긴 변이 수평으로 놓였음을 알 수 있다',
 'conditions of the problem).':'(문제의 그림 2 기준).'
})
ATOM_WORDS.update({'and the plate.':'판 크기로 구한다.','required sizes':'길이를 구하면','results:':'얻는다:'})
ATOM_WORDS.update({'The mutual orientation of the vectors':'다음 벡터의 상대적 방향', 'is shown below.':'은 아래와 같다.'})
ATOM_WORDS.update({'whence':'따라서','Help! The value of the magnetic constant is':'참고: 자기 상수는','Гн':'H','м .':'m .'})
ATOM_WORDS.update({
 'stands for a fixed number and zeroth term of the numerical sequence has':'는 상수이며, 수열의 0번째 항은',
 'some value of':'다음과 같다:', ', i.e.':', 즉', '[0.2 points]':'[0.2점]', '[0.4 points]':'[0.4점]', '[0.7 points]':'[0.7점]',
 'Obtain an explicit formula for an arbitrary term of the sequence':'다음 수열의 일반항을 구하라:',
 'express it through the successive number':'항 번호', ', the initial value':', 초기값',
 'Let us consider the number':'다음 수를 생각하자:', '. Taking its natural power of':'의 자연수',
 ', the result can be':'제곱은 다음과 같다:', 'presented in the following form':'',
 'Find the recurrence relations, expressing the values of':'다음 계수의 점화 관계를 구하라:',
 'through the':'앞선', 'previous values':'값으로 나타내라:',
 '. Find also the inverse relations, expressing':'. 또한 역방향 관계도 구하라:', 'through':'다음 값으로',
 'Calculate the numerical values of the coefficients':'다음 계수의 수치를 계산하라:', 'for':'단,',
 'Express the number':'다음 수를 구하라:', 'in terms of':'표현 변수:',
 'Let the terms of a certain numerical sequence obey the recurrence relation':'이제 다음 점화 관계를 만족하는 수열을 생각하자.'})
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
TABLE_WORDS.update({
 'Marking scheme':'채점 기준','(the sign important)':'(부호 중요)','(the sign is important)':'(부호 중요)','(the sign is unimportant)':'(부호 무관)',
 '- in circle 1;':'- 원 1 안에 작도','- in circle 2;':'- 원 2 안에 작도','- in circle 3;':'- 원 3 안에 작도',
 'Adiabatic equation has been written,':'단열 과정의 식 제시','Carnot cycle has been taken':'카르노 순환 선택',
 'Coefficient in the above expression is 21/32 instead of 9/32':'위 식의 계수가 9/32 대신 21/32일 때',
 'Correct':'올바른 값','Correct α':'올바른 α','Correct β':'올바른 β','Energy losses in the disc are found':'원판의 에너지 손실 계산',
 'Focal points of the lens are found and':'렌즈의 초점을 구하여','Force':'힘','Found position of the center of mass':'질량 중심 위치 작도','Found position of the third ball:':'세 번째 공의 위치 작도:',
 'If the minus sign in the above expression is absent':'위 식에 음의 부호가 없을 때','Image of the second source is found':'두 번째 점광원의 상을 구하여',
 'It has been indicated that the straight':'직선이','Magnetic moment':'자기 모멘트','Ohm’s law in differential form':'미분 형태의 옴의 법칙','Radial component is found':'반지름 성분 계산',
 'Relation between':'관계식','Simplification uses z':'근사 조건 z','Straight lines have been properly':'직선을 올바르게',
 'The basic idea of the constancy of the':'기본 원리인','The component of the force is found':'힘의 성분 계산','The constant component of the force is found':'힘의 일정한 성분 계산',
 'The efficiency has been found':'효율 계산','The field is found on the axis':'축 위 자기장 계산','The field of the dipole is found':'쌍극자 전기장 계산','The frequency changes due to attenuation':'감쇠에 의한 진동수 변화',
 'The optical center of the lens has been':'렌즈의 광학 중심을','The power of the friction force is determined':'마찰력의 일률 계산','The power of the friction force is found':'마찰력의 일률 계산','They are equal':'두 값이 같음을 확인',
 'and plotted':'작도','center of mass is formulated':'질량 중심의 불변성 제시','found':'구함','including the formulation of it in':'다음 표현 포함:',
 'lines are isotherms':'등온선임을 확인','logarithmic scale':'로그 눈금에서의 식','plotted':'작도'
})
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
 register_math_regions(doc,data['entries'],prefer_svg=bool(data.get('small_glyph_heights')))
 split=[]
 for e in data['entries']:
  match=re.match(r'(.*?(?:Page|с\.)\s*\d+\s*/\s*\d+)\s*(.+)',e['source']) if e['rect'][1]<51 else None
  if not match or len(match[2].strip())<9:split.append(e);continue
  if '\n\n' not in e['ko']:raise ValueError('Header contains untranslated problem text: '+e['id'])
  header_ko,body_ko=e['ko'].split('\n\n',1)
  spans=[s for l in doc[e['page']].get_text('dict')['blocks'][block_index(e)]['lines'] for s in l['spans'] if s['text'].strip()]
  top=[s for s in spans if s['bbox'][1]<51];body=[s for s in spans if s['bbox'][1]>=51]
  def bounds(ss):
   r=fitz.Rect(ss[0]['bbox'])
   for s in ss[1:]:r|=fitz.Rect(s['bbox'])
   return list(r)
  head=copy.deepcopy(e);head.update(source=match[1],ko=header_ko,math=[],rect=bounds(top),no_source_bbox_trim=True)
  tail=copy.deepcopy(e);tail.update(id=e['id']+'b0',source=match[2],ko=body_ko,rect=bounds(body),size=max(s['size'] for s in body),no_source_bbox_trim=True)
  split.extend([head,tail])
 data['entries']=split
 data['preserve_rects']=[]
 data['native_math_blocks']=[]
 data['erase_rects']=copy.deepcopy(data.get('base_erase_rects',[]))
 data['transparent_math_restore']=True
 data['math_line_height']=True
 if not (year==2010 and kind=='T'):data['mask_prose_instead_of_redact']=True
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
  if year==2013 and kind=='T' and pi==3:entries=[e for e in entries if e['id'] not in {'4-6','4-8'}]
  if year==2017 and kind=='T' and pi==2:entries=[e for e in entries if e['id'] not in {'3-13','3-16','3-17','3-18'}]
  if year==2017 and kind=='T' and pi==4:
   # The source divides one prose/formula line between blocks 11 and 12.
   # Translate only its prose outlines so the negative-power radical stays native.
   duplicate=copy.deepcopy(next(e for e in entries if e['id']=='5-11'));duplicate['id']='5-12';entries.append(duplicate)
   next(e for e in entries if e['id']=='5-1')['align']='center'
  for e in list(entries):
   if e['id'] not in ATOM_IDS.get((year,kind),set()):continue
   entries.remove(e);j=0
   if year==2012 and kind=='T' and e['id'] in {'6-8','6-9'}:
    # These Word blocks mix a Russian conjunction with a complete native
    # approximation formula; translate the conjunction alone.
    for ri,rr in enumerate(page.search_for('при',clip=fitz.Rect(e['rect']))):
     cells.append({'id':e['id']+f'a{ri}','page':pi,'rect':list(rr),'size':11.4,'source':'при','ko':'단','math':[],'formula_adjacent_prose':True})
    continue
   for line in page.get_text('dict')['blocks'][block_index(e)].get('lines',[]):
    for span in line['spans']:
     t=span['text'].strip()
     if (not re.search(r'[A-Za-zА-Яа-яЁё]{3,}',t) and t not in ATOM_WORDS) or (candidate(span) and t not in ATOM_WORDS):continue
     if t not in ATOM_WORDS:raise ValueError('Untranslated formula-adjacent prose: '+t)
     if not ATOM_WORDS[t]:
      data['erase_rects'].append({'page':pi,'rect':list(span['bbox'])});continue
     cells.append({'id':e['id']+f'a{j}','page':pi,'rect':list(span['bbox']),'size':min(e['size'],span['size'],11.4),'source':t,'ko':ATOM_WORDS[t],'math':[],'formula_adjacent_prose':True})
     j+=1
  for drawing in page.get_drawings():
   r=drawing['rect']
   if 44<r.y0<50 and r.width>400 and r.height<2:data['preserve_rects'].append({'page':pi,'rect':list(r),'kind':'original_header_rule'})
  if year==2010 and kind=='T' and pi==2:data['preserve_rects'].append({'page':pi,'rect':[325,684.5,406,717.5],'kind':'original_display_formula'})
  if year==2012 and kind=='T' and pi==1:data['preserve_rects'].append({'page':pi,'rect':[178,574.8,337,601.5],'kind':'original_display_formula'})
  if year==2012 and kind=='T' and pi==5:
   for rr in [[333,73,482,104],[414,104,482,124],[285,150,361,168],[285,168,361,186]]:data['preserve_rects'].append({'page':pi,'rect':rr,'kind':'original_display_formula'})
  if year==2011 and kind=='T' and pi==1:
   for rr in [[85,136,263,270],[306,307,554,424]]:data['preserve_rects'].append({'page':pi,'rect':rr,'kind':'original_diagram_ink','source_type':'vector'})
  if year==2011 and kind=='T' and pi==2:
   for rr in [[84,143,220,237],[93,514,331,674]]:data['preserve_rects'].append({'page':pi,'rect':rr,'kind':'original_diagram_ink','source_type':'vector'})
  if year==2013 and kind=='T' and pi==3:
   for rr in [[207,313.4,278,330],[352,313.5,385,330]]:data['preserve_rects'].append({'page':pi,'rect':rr,'kind':'original_display_formula'})
  if year==2017 and kind=='T' and pi==2:data['preserve_rects'].append({'page':pi,'rect':[178,215,458,397.3],'kind':'original_diagram_ink','source_type':'vector'})
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
      if (year,kind,e['id'])==(2013,'T','4-4') and span['bbox'][1]>=313.5:continue
      if (year,kind,e['id'])==(2010,'T','3-13') and 'where' not in span['text']:continue
      data['erase_rects'].append({'page':pi,'rect':list(span['bbox'])})
    for fi,(r,ko) in enumerate(flow):
     q=copy.deepcopy(e);q['id']+=f'f{fi}';q['rect']=r;q['ko']=ko;q['source_unsegmented']=e['source'];q['flow_segment']=True
     if (year,kind,e['id'])==(2017,'T','5-2') and fi<2:q['align']='center'
     if year>=2014:q['size']=min(e['size'],12)
     if year==2012 and kind=='T' and pi==5:q['size']=min(e['size'],11.4)
     if (year,kind,e['id'],fi)==(2013,'T','4-4',1):q['size']=11.2
     markers=re.findall(r'\[\[\d+\]\]',ko);q['source']=re.sub(r'\[\[\d+\]\]','',e['source'])+' '+' '.join(markers)
     entries.append(q)
   elif not e.get('no_source_bbox_trim') and not (year==2012 and kind=='TS' and e['id']=='10-0'):
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
     if candidate(span):continue
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
   for e in list(entries):
    words=re.findall(r'[A-Za-z]{3,}',e['source'])
    if words and all(candidate({'text':w}) for w in words):
     entries.remove(e)
     rr=list(page.get_text('dict')['blocks'][block_index(e)]['bbox'])
     data['preserve_rects'].append({'page':pi,'rect':rr,'kind':'original_display_formula'})
     data['native_math_blocks'].append({'id':e['id'],'page':pi,'source':e['source'],'rect':rr})
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
     if any(not candidate({'text':w}) and w.lower() not in {'sin','cos','tan','exp','log','max','min','surf','sur','tot','rot','crtitcal','critical','arcsin'} for w in words):prose_lines.append(line)
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
    if (year,kind,e['id'])==(2014,'T','3-3'):e['ko']=re.sub(r'^\s*1\s+At\s*','',e['ko'])
    label=re.match(r'\s*\[\[(\d+)\]\]\s*(\(\d+\))',e['source'])
    if label and int(label[1]) in outside:
     e['ko']=re.sub(r'^\s*'+re.escape(label[2])+r'\s*','',e['ko'])
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
    forced=year==2014 and kind=='T' and {e['id'],*(q['id'] for q in g)}=={'3-4','3-5'}
    if forced or any((r&fitz.Rect(q['rect'])).height>3.4 and (r&fitz.Rect(q['rect'])).width>1 for q in g):
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
     math_pixmap(page,r).save(folder/name)
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
  match=re.search(r'(?:Page|с\.)\s*(\d+)\s*/\s*(\d+)',e['source']) if e['rect'][1]<50 else None
  if match:
   number=match[1]+'/'+match[2];e['ko']=re.sub(r'\s*\d+/\d+쪽$','',e['ko']);e['rect'][2]=480
   counters.append({'id':e['id']+'p99','page':e['page'],'rect':[500,e['rect'][1],558,e['rect'][3]],'redact_rect':[480,e['rect'][1],558,e['rect'][3]],'size':min(e['size'],10),'source':'Page '+number,'ko':number+'쪽','math':[]})
 out+=counters
 # Inline equations can extend above or below the Word prose bounding box.
 # Mask their complete old positions before placing the exact crops in Korean.
 # This avoids residual numerator/subscript ink along paragraph edges while
 # keeping independent native display equations untouched.
 if not (year==2010 and kind=='T'):
  for e in out:
   for mi in set(map(int,re.findall(r'\[\[(\d+)\]\]',e['ko']))):
    if mi<len(e.get('math',[])):
     data['erase_rects'].append({'page':e['page'],'rect':e['math'][mi]['rect']})
 if year==2012 and kind=='T':
  data['post_overlays']=[{'page':2,'rect':[107,107,176,124],'text':'대기','size':10.5,'align':'center'},
    {'page':2,'rect':[175,139,228,154],'text':'피스톤','size':10,'align':'center'},
    {'page':2,'rect':[116,228,156,242],'text':'공기','size':10.5,'align':'center'}]
  unit_labels={'1еВ':'1eV','В':'V','Дж':'J'}
  for line in doc[5].get_text('dict')['blocks'][6]['lines']:
   for span in line['spans']:
    if span['text'].strip() in unit_labels:data['post_overlays'].append({'page':5,'rect':list(span['bbox']),'text':unit_labels[span['text'].strip()],'size':10.5,'align':'left'})
 if year==2010 and kind=='T':
  data['post_overlays']=[{'page':3,'rect':[85,803,556,824],
    'text':'정오: 델타(1232) 질량은 1.232 x 10^9 eV/c^2이다. 원문의 10^6은 10^9의 오탈자다.',
    'size':8,'align':'left'}]
  data['editorial_corrections']=[{'page':3,'original':'m_Delta=1.232×10^6 eV/c²','correct':'m_Delta=1.232×10^9 eV/c²',
     'source':'https://pdgweb.lbl.gov/2025/tables/rpp2025-tab-baryons-Delta.pdf',
     'note':'Both official EN and RU statements have the exponent typo; original glyphs are retained and an explicit Korean erratum is added in the margin.'}]
 if year==2010 and kind=='TS':
  data['post_overlays']=[]
  data['post_overlays'].append({'page':3,'rect':[297,496.5,335,509],'text':'그림 1','size':10.5,'align':'left'})
  data['post_overlays'].append({'page':5,'rect':[277.2,537.36,289.68,553.524],'text':',','size':11.4,'align':'left'})
  short={'i.e.':'즉','e.g.':'예:','No.':'번호','No':'번호','as':'즉'}
  for pi,page in enumerate(doc):
   for b in page.get_text('dict')['blocks']:
    for line in b.get('lines',[]):
     for span in line['spans']:
      t=span['text'].strip();rr=fitz.Rect(span['bbox'])
      if t in short and not any(e['page']==pi and (rr&fitz.Rect(e['rect'])).get_area()>1 for e in out):
       data['post_overlays'].append({'page':pi,'rect':list(rr),'text':short[t],'size':min(11,span['size']),'align':'left'})
 if year==2011 and kind=='T':
  data['post_overlays']=[{'page':2,'rect':[106,523,130,540],'text':'이온','size':9.5,'align':'center'},
    {'page':2,'rect':[218,647,261,665],'text':'전자','size':10,'align':'center'}]
 if year==2013 and kind=='T':
  data['post_overlays']=[{'page':3,'rect':[85,314.8,204,330],'text':'환산 플랑크 상수','size':10.5,'align':'left'},
    {'page':3,'rect':[279,314.8,305,330],'text':'J·s','size':10.5,'align':'left'},
    {'page':3,'rect':[305,314.8,350,330],'text':', 즉','size':10.5,'align':'left'},
    {'page':3,'rect':[385,314.8,428,330],'text':', 여기서','size':10.5,'align':'left'},
    {'page':3,'rect':[439,314.8,556,330],'text':'은 주양자수이다.','size':10.5,'align':'left'},
    {'page':3,'rect':[85,329.8,128,343.3],'text':'','size':10.5,'align':'left'}]
 if year==2017 and kind=='T':
  data['post_overlays']=[]
  labels={'Spacecraft':'우주선','Planet':'행성','Course':'진로','Center':'중심'}
  for b in doc[2].get_text('dict')['blocks']:
   for l in b.get('lines',[]):
    for s in l['spans']:
     if s['text'].strip() in labels:data['post_overlays'].append({'page':2,'rect':list(s['bbox']),'text':labels[s['text'].strip()],'size':min(10.5,s['size']),'align':'center'})
  for pi,page in enumerate(doc):
   for b in page.get_text('dict')['blocks']:
    for l in b.get('lines',[]):
     for s in l['spans']:
      if s['text'].strip()=='to' and pi==2:
       data['post_overlays'].append({'page':pi,'rect':list(s['bbox']),'text':'','size':10,'align':'left'})
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
