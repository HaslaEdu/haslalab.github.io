import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read first solution. The independent displayed programs are fixed."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page07-native-row-proposals.json').read_text('utf8'))
T=[
('제[[0]]회 전국 중고등학생 물리경시대회 결선 참고 해설','[[0]]th National High School Physics Competition: Final Solutions'),
('1.','1.'),
('[[0]]. 풀이 1: 수비수가 시간 [[1]] 뒤 [[2]]의 [[3]]에서','[[0]]. Method 1: intercept at [[3]] on [[2]], time [[1]].'),
('공을 가로챈다. [[0]]은 [[1]]–[[2]] 거리, [[3]]는 [[4]]와','Let [[0]] be the [[1]]–[[2]] distance and [[3]] the distance from [[4]]'),
('[[0]] 사이 거리(그림 [[1]])이면 다음과 같다.','to [[0]] (Fig. [[1]]). Then'),
('및','and'),
('그림 [[0]]','Fig. [[0]]'),
('식 [[0]][[1]] [[2]]를 풀면 다음을 얻는다.','Solving [[0]][[1]] [[2]] gives'),
('식 [[0]]에서, 공을 가로챌 필요조건은 실근이 존재하는 것이므로 다음과 같다.','In [[0]], interception requires real roots, giving the necessary condition'),
('풀이 2: [[0]]와 [[1]] 사이 각을 [[2]](그림 [[3]])라 하자. 사인 법칙에서','Method 2: let [[2]] be the angle between [[0]] and [[1]] (Fig. [[3]]). The sine rule gives'),
('식 [[0]]을 쓰면 다음과 같다.','Using [[0]] gives'),
('[[0]]에서 필요조건 [[1]]를 얻는다[[2]]','[[0]] gives the necessary condition [[1]][[2]]'),
('[[0]]. 수비수가 공을 가로챌 수 있는 곳과 [[2]] 사이 최단거리를 [[1]]이라 하자. 식 [[3]]에서','[[0]]. Let [[1]] be the least interception distance from [[2]]. From [[3]],'),
('수신자가 [[0]]에서 [[1]]보다 가까우면 먼저 공을 받아 가로채이지 않는다. 따라서','If the receiver is closer to [[0]] than [[1]], he gets the ball first. The condition'),
('공을 가로채이지 않는 조건은 다음과 같다.','for avoiding interception is'),
('식 [[0]][[1]] [[2]]에서 다음을 얻는다.','From [[0]][[1]] [[2]],'),
('식 [[0]]에서 [[1]]축의 공격수가 [[2]]에서 거리 [[3]]인 곳에 있고 이 부등식을 만족하면','By [[0]], if a receiver on [[1]], distance [[3]] from [[2]], satisfies this inequality,'),
('원래 [[0]]에 있던 수비수에게 공을 가로채이지 않는다.','the defender initially at [[0]] cannot intercept the ball.'),
('[[0]]. 풀이 1: [[1]]의 수비수가 [[2]] 위에서 [[3]]로부터 [[4]] 떨어진 [[5]]에 도착하기 전에,','[[0]]. Method 1: before the defender at [[1]] reaches [[5]] on [[2]], distance [[4]] from [[3]],'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 if r['id']=='r05':
  r['source_display_atoms_explicitly_stationary']=r['native_atoms'];r['native_atoms']=[]
 if r['id']=='r06':
  r['source_display_subscript_p_stationary']=r['native_atoms'][0];r['native_atoms']=r['native_atoms'][1:];a=r['native_atoms'][0];a['id']='r06a0';g=r['erase_glyphs'][0]
  r.update(left=g['bbox'][0],original_center=(g['bbox'][0]+a['rect'][2])/2,source_text='图[[0]]')
 r.update(ko=ko,en=en,reviewed=True,align='center'if r['id']in['r00','r06']else'left',allowed_horizontal=[89,350]if r['id']in['r02','r03','r04']else[24,571]if r['id']=='r00'else[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Source-read complete native inline references/tokens only. Entire original independent displayed formula programs (including cross-baseline subscript p), vector fraction rules and diagram stay stationary.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page07-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE07_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
