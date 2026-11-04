import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Full first-page source-read bilingual language; native tokens are original."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page01-native-row-proposals.json').read_text('utf8'))
T=[
('중국과학기술대 물리학원 예방자오 정리','Prepared by Ye Bangjiao, School of Physics, USTC'),
('제[[0]]회 전국 중고등학생 물리경시대회 결선 문제','[[0]]th National High School Physics Competition: Final Problems'),
('[[0]]년 [[1]]월  베이징','[[0]]-[[1]]  Beijing'),
('[[0]] 이론 부문','[[0]] Theory'),
('1.','1.'),
('축구 경기에서 공격수가 그림의 [[0]]에서 [[1]] 방향으로 공을 찬다. 공은 속력 [[2]]로','In football, an attacker at [[0]] passes along [[1]]; the ball rolls at speed [[2]]'),
('잔디 위를 등속 운동한다. 수비수는 [[0]]에 있다. [[2]] 사이는 [[1]], [[4]]와 [[5]]의 각은 [[3]]이며,','uniformly on grass. Defender at [[0]]; [[2]] separation: [[1]]; [[4]]–[[5]] angle: [[3]].'),
('[[0]]이다. 공이 [[1]]를 떠나는 순간,','Given [[0]], as the ball leaves [[1]],'),
('[[0]]의 수비수가 직선으로 등속으로 달리기 시작한다.','the defender at [[0]] starts along a straight line'),
('속력은 [[0]]이다. 공을 가로채려 하며 경계는 무시한다.','at speed [[0]] to intercept it. Ignore field boundaries.'),
('문제에 주어진 매개변수 사이의 관계식으로','Answer the following in terms of the given'),
('다음 물음의 답을 나타내라.','parameters.'),
('[[0]]. 수비수가 공을 가로챌 수 있는 필요조건을 구하라.','[[0]]. Find the necessary condition for interception by the defender.'),
('[[0]]. 공격팀의 다른 선수가 [[1]] 위에서 공을 기다린다. [[3]]까지의 거리를 [[2]]라 하자. 공이','[[0]]. An attacker waits on [[1]], distance [[2]] from [[3]]. Find when the ball is'),
('원래 [[0]]에 있던 수비수에게 가로채이지 않을 조건을 구하라.','not intercepted by the defender initially at [[0]].'),
('[[0]]. 공격팀의 다른 선수가 [[1]] 위, [[3]]에서 거리 [[2]]에 있다. 공이 [[4]]를 떠나는 순간','[[0]]. An attacker is on [[1]], distance [[2]] from [[3]]. As the ball leaves [[4]],'),
('속력 [[0]]로 등속으로 달려 공을 받는다. 공이 원래 [[1]]에 있던 수비수에게','he runs at constant speed [[0]] to receive it. Find when the defender initially at [[1]]'),
('가로채이지 않을 조건을 구하라.','does not intercept it.'),
('2.','2.'),
('지상 관측으로 위성의 운동을 정할 수 있다. 위성의 운동을 알면 우주 비행체나','Ground observations give satellite motion, then the motion of spacecraft or'),
('지상 물체의 운동도 정할 수 있다. 시간과 공간 좌표의 측정이 필요하다. 해석과 계산을','ground objects. Both require time and spatial coordinates. To simplify analysis and'),
('간단히 하려고 지구의 자전과 공전을 무시하고, 지구를 관성계로 본다.','calculation, ignore Earth’s spin and orbit; use Earth as an inertial frame.'),
('[[0]]. 먼저 위성의 운동을 측정한다. 상대론적 효과는 무시한다. 위성에는 전파 송신기와','[[0]]. To measure satellite motion, ignore relativity. It has a radio transmitter'),
('정밀한 원자시계가 있다. 위성의 각 전파 신호에는 그 신호를 송신한 시각이 담겨 있다.','and a precise atomic clock. Each signal contains its transmission time.'),
('[[0]] 여러 관측소로 된 지상 관측계는 이 정보와 관측소의 알려진 위치, 자체 시계로','[[0]] Several ground stations use these data, their known positions and clocks'),
('매 순간 위성의 위치를 정하여 위성의 운동을 측정한다. 이런 측정계에','to find its position at each instant, hence its motion. For this system,'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 en=en.replace('’',"'")
 r.update(ko=ko,en=en,reviewed=True,align='center'if r['id']in('r00','r01','r02')else'left',allowed_horizontal=[24,571]if r['id']in('r00','r01','r02')else[89,506])
 if r['id']in('r07','r08','r09','r10','r11'):r['allowed_horizontal']=[89,355]
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Complete original source native token; no fraction/radical paths in this page’s moving inline expressions. Figure1 remains separate and stationary.')
 for lang in('ko','en'):assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,all_source_figure_vectors_and_labels_separate_and_stationary=True,publication_ready=False)
atomic_text(A/'page01-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE01_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
