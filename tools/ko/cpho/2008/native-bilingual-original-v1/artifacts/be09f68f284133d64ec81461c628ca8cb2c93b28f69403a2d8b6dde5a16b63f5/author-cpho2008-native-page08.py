import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read football continuation and satellite solution; all display fixed."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page08-native-row-proposals.json').read_text('utf8'))
T=[
('수신자가 [[0]]에서 [[1]]보다 가까이 도착하면 원래 [[2]]의 수비수에게 가로채이지 않는다(그림','if the receiver gets closer to [[0]] than [[1]], the defender at [[2]] cannot intercept (Fig.'),
('[[0]]). [[1]]이면 [[2]]번 물음과 같다. [[3]]','[[0]]). If [[1]], it is part [[2]]. If [[3]]'),
('[[0]]이면 수신자가 [[1]] 위의 [[2]]에 있다고 하자.','[[0]], let the receiver be at [[2]] on [[1]].'),
('[[0]]까지 달리는 데 걸리는 시간은','His time to reach [[0]] is'),
('수비수의 [[0]] 도착 소요 시간은','Defender arrival time at [[0]]:'),
('그림 [[0]]','Fig. [[0]]'),
('공이 가로채이지 않는 조건은 다음과 같다.','The condition for avoiding interception is'),
('즉','Thus'),
('여기서 [[0]]은 식 [[1]]로 주어진다.','where [[0]] is given by [[1]].'),
('풀이 2: 수비수와 공이 [[0]]에 도착하는 시간은 같으므로 다음과 같다.','Method 2: the defender and ball reach [[0]] at the same time, so'),
('공이 가로채이지 않는 조건 [[0]]과 식 [[1]]에서 다음을 얻는다.','The no-interception condition [[0]] and equation [[1]] give'),
('[[0]]은 역시 식 [[1]]로 주어진다. 식 [[2]]와 [[3]]은 같음을 쉽게 보일 수 있다.','Again [[0]] is given by [[1]]. Equations [[2]] and [[3]] clearly agree.'),
('2.','2.'),
('[[0]][[1]][[2]] 좌표계를 정하면 위성의 운동 측정은 매 순간 위치 좌표 [[3]][[4]]','[[0]][[1]][[2]] In a chosen frame, satellite motion gives its coordinates [[3]][[4]]'),
('[[0]]를 정하는 것이다. 시각 [[1]]에 위성이 보낸 신호가 [[2]]번째 관측소에 도착하는 시각은 [[3]]이다.','[[0]] at every instant. A signal emitted at [[1]] reaches ground station [[2]] at [[3]].'),
('신호는 광속 [[0]]로 전파되므로 다음과 같이 쓸 수 있다.','The signal travels at light speed [[0]], hence'),
('[[0]]는 [[1]]번째 지상 관측소의 좌표로 미리 측정해 알고 있다. [[2]]도','[[0]] are known, premeasured station [[1]] coordinates; its clock measures [[2]].'),
('지상 시계로 측정된다. [[0]]는 위성 신호에서 알 수 있다. 따라서 식 [[1]]의 세 미지수는','The signal supplies [[0]], also known. Equation [[1]] thus has three unknowns,'),
('[[0]]이다. 독립 방정식 세 개, 즉 지상 관측소 최소 세 곳이 필요하다. 세 식은','[[0]], requiring three independent equations: at least three ground stations.'),
('식 [[0]]에서 [[1]]에 해당한다.','These are [[0]] for [[1]].'),
('[[0]][[1]] 지구 중심 [[2]]와','[[0]][[1]] Earth centre [[2]]'),
('두 관측소 [[0]]가 이루는','and stations [[0]] form an'),
('삼각형은 이등변삼각형이다.','isosceles triangle; the'),
('같은 두 변은 [[0]]이다. 조건에서','equal sides are [[0]]. Thus'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 if r['id']=='r04':
  r['source_split_display_formula_stationary']=r['native_atoms'][1];r['native_atoms']=r['native_atoms'][:1]
 if r['id']=='r05':
  r['source_display_exponent_stationary']=r['native_atoms'][0];r['native_atoms']=r['native_atoms'][1:];a=r['native_atoms'][0];a['id']='r05a0';g=r['erase_glyphs'][0];r.update(left=g['bbox'][0],original_center=(g['bbox'][0]+a['rect'][2])/2,source_text='图[[0]]')
 if r['id']=='r07':
  r['source_complete_fraction_display_stationary']=r['native_atoms'];r['native_atoms']=[]
 bounds=[89,244]if r['id']in['r20','r21','r22','r23']else[89,331]if r['id']in['r01','r02','r03']else[89,250]if r['id']=='r04'else[89,170]if r['id']=='r07'else[89,506]
 r.update(ko=ko,en=en,reviewed=True,align='center'if r['id']=='r05'else'left',allowed_horizontal=bounds)
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Exact original complete native inline expression/reference including original list commas. The full split defender time equation, its exponent and fraction display10 remain stationary as entire original programs, with original clips/rules/CIDs unchanged. Original figures and footer fixed.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page08-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE08_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
