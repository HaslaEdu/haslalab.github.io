import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Full source clock-difference and heat-pump solution prose."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page11-native-row-proposals.json').read_text('utf8'))
T=[
('따라서','Thus'),
('대입하면 [[0]]로 매우 작다. 위처럼 식 [[1]]은 다음과 같이','Numerically [[0]], very small. As above, [[1]] is approximately'),
('근사된다.','given by'),
('식 [[0]][[1]] [[2]]를 빼면 위성 시계와 지상 시계 표시의 차이를 얻는다.','Subtract [[0]][[1]] [[2]] to find satellite minus ground clock readings:'),
('식 [[0]]에서 [[1]]를 구해 식 [[2]]에 넣으면 다음과 같다.','Solve [[0]] for [[1]] and substitute into [[2]]:'),
('문제의 [[0]]는 지상 시계의 경과 시간 [[1]]이다. 마지막으로 [[2]] 뒤 위성 시계와','The stated [[0]] is ground elapsed time [[1]]. Finally, after [[2]], the satellite'),
('지상 시계 표시의 차이는 다음과 같다.','minus ground reading is'),
('3.','3.'),
('[[0]]. 실내 온도가 일정하려면 열펌프가 실내에 내는 열출력과 방의 실외 방열률이','[[0]]. For constant room temperature, the heat pump output must equal the room heat'),
('같아야 한다. 실내 열출력을 [[0]], 소비 전력을 [[1]]라 하면, 실외 저온부에서','loss rate. Let [[0]] be the indoor heat output and [[1]] the electric input. The heat'),
('흡수하는 열출력은 [[0]]이다. 문제의 조건에서 다음이 성립한다.','extracted outdoors at low temperature per unit time is [[0]]. Then'),
('[[0]]은 실내 고온부의 절대 온도, [[1]]는 실외 절대 온도이다. 식 [[2]]에서','[[0]] is the indoor hot absolute temperature, [[1]] the outdoor one. From [[2]],'),
('전기요금이 최소이려면 [[0]]가 최소여야 한다. 즉 식 [[1]]의 “[[2]]”를 등호로 두는 이상적','Minimum cost requires minimum [[0]]: equality in “[[2]]” in [[1]], the ideal'),
('경우에 [[0]]가 최소이다. 따라서 최소 전력은 다음과 같다.','case, minimizes [[0]]. Thus the least electric power is'),
('방의 열은 유리판을 통해 전도로 빠져나간다. 방열률은 다음과 같다.','Heat conducts out of the room through the glass. The loss rate is'),
('실내 온도를 일정하게 유지하려면 다음과 같아야 한다.','For a constant room temperature,'),
('식 [[0]][[1]][[2]]에서 다음을 얻는다.','Equations [[0]][[1]][[2]] give'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 if r['id']=='r00':r['complete_source_phi_fraction_stationary']=r['native_atoms'];r['native_atoms']=[]
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,159]if r['id']=='r00'else[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Only complete source-native inline counters, symbols and original reference-range punctuation move. Every displayed clock/heat-pump equation, fraction rule and script, including top phiE/c2, remains stationary.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page11-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE11_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
