import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read relativistic clock solution. Literal independent math fixed."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page10-native-row-proposals.json').read_text('utf8'))
T=[
('[[0]]에 해당하는 독립 방정식 네 개로 정한다.','[[0]]: four independent equations.'),
('[[0]][[1]][[2]] 위성 시계 지연 인자는 [[3]]이다. 지상 시계 표시 [[4]]와 위성 시계','[[0]][[1]][[2]] Satellite slowing factor: [[3]]. The ground reading [[4]] minus'),
('표시 [[0]]의 차이는 다음과 같다.','satellite reading [[0]] is'),
('[[0]]는 지상에 대한 위성의 속력이며 다음 식으로 정한다.','Here [[0]] is satellite speed relative to the ground, determined by'),
('[[0]]는 중력 상수, [[1]]은 지구 질량, [[2]]는 궤도 반지름이다. 식 [[3]]에서','[[0]] is gravity constant, [[1]] Earth mass, [[2]] orbit radius. From [[3]],'),
('[[0]]는 지구 반지름, [[1]]는 위성 높이, [[2]]는 지표 중력 가속도이다. 수치를','Here [[0]] is Earth radius, [[1]] altitude, [[2]] ground gravity. Substitution'),
('넣으면 [[0]]이다. 따라서 [[1]]로 매우 작다. 그러므로','gives [[0]], hence [[1]], which is very small. Thus'),
('마지막으로 [[0]] 동안 생기는 시계 차이는 다음과 같다.','Finally the clock difference over [[0]] is'),
('[[0]] 위성 시계의 표시 [[1]]와 무한히 먼 관성계 시계의 표시 [[2]]의 차이는','[[0]] Satellite reading [[1]] minus inertial clock [[2]] at infinity:'),
('위성 시계 위치의 중력 퍼텐셜 크기는 다음과 같다.','The gravitational potential magnitude at the satellite clock is'),
('따라서','Thus'),
('수치를 넣으면 [[0]]로 매우 작다. 식 [[1]]은 다음과 같이 근사된다.','Numerically [[0]], very small. Equation [[1]] is approximately'),
('마찬가지로 지상 시계의 표시 [[0]]와 무한히 먼 관성계 시계의 표시의 차이는','Similarly, ground reading [[0]] minus the inertial clock at infinity is'),
('지상 시계 위치의 중력 퍼텐셜 크기는 다음과 같다.','The gravitational potential magnitude at the ground clock is'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 if r['id']=='r10':r['complete_source_display_fraction_stationary']=r['native_atoms'];r['native_atoms']=[]
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,150]if r['id']=='r10'else[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Exact complete original native inline clock expressions/counters; wide independent phi/c-squared fraction program, source rules/scripts, all original displayed equations and footer stationary.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page10-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE10_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
