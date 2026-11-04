import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source heat-pump costs; display mathematics and actual reference columns fixed."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page12-native-row-proposals.json').read_text('utf8'))
T=[
('가동 시간이 [[0]], kWh당 요금이 [[1]]이면 최소 전기요금은 다음과 같다.','For operating time [[0]] and price per kWh [[1]], the least electricity cost is'),
('유의:','Note:'),
('단위[[0]]이다. 식 [[1]][[2]] [[3]]에 주어진 수치를 넣으면 다음과 같다.','unit[[0]]. Equations [[1]][[2]] [[3]], with the stated data, give'),
('위안.','yuan.'),
('따라서 이상적으로 이 열펌프를 [[0]] 가동하면 약 [[1]]위안이 든다.','Thus, ideally, this heat pump costs about [[1]] yuan for [[0]].'),
('[[0]]. 중간 공기층의 안쪽 표면 온도를 [[1]], 바깥쪽을 [[2]]라 하자. 안쪽 유리,','[[0]]. Let [[1]], [[2]] be the inner and outer air-layer surface temperatures. The rates of'),
('공기층, 바깥 유리를 단위 시간에 통과하는 열량은 각각 다음과 같다.','heat conduction through the inner glass, air and outer glass are respectively'),
('정상 열전도 상태에서 다음이 성립한다.','In steady heat conduction,'),
('식 [[0]][[1]][[2]]에서 다음을 얻는다.','Equations [[0]][[1]][[2]] give'),
('및','and'),
('식 [[0]]을 풀면 다음과 같다.','Solving [[0]] gives'),
('식 [[0]]을 식 [[1]]에 넣으면 다음과 같다.','Substitute [[0]] into [[1]]:'),
('실내 온도가 일정하려면 [[0]]이어야 한다. 식 [[1]]에서 이중창의 최소','Constant temperature requires [[0]]. By [[1]], for double glazing the minimum'),
('소비 전력은 다음과 같다.','electric power is'),
('이상적인 경우, 열펌프 가동 시간 [[0]]에 필요한 전기요금은 다음과 같다.','Ideally, the cost for operation time [[0]] is'),
('수치를 넣으면 다음과 같다.','Substituting the data gives'),
('위안.','yuan.'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 fixed=r['id']in ['r01','r03','r09','r16']
 if fixed:
  r['complete_original_display_and_reference_programs_stationary']=r['native_atoms'];r['native_atoms']=[]
  # Preserve actual source mathematical x positions on both sides of the
  # language slot. Chinese display clauses are not left-aligned as a row.
  hans=[g for g in r['erase_glyphs']if re.search('[\u3400-\u9fff]',g['c'])];r['left']=hans[0]['origin'][0]
 bounds=[89,148]if r['id']=='r01'else[244.679,276.481]if r['id']=='r09'else[89,400]if fixed else[89,506]
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=bounds)
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Complete original inline symbols/references only. Actual source temperature identities, cost8/18 equations, fractions and paired display13, their original counters/clips/rules all stay fixed. Translate only literal prose in original gaps; no equation repacking.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page12-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE12_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
