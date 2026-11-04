import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read heat-pump saving and Coulomb blockade derivation."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page13-native-row-proposals.json').read_text('utf8'))
T=[
('따라서 이 이중창으로 바꾼 뒤 열펌프를 [[0]] 가동하면 절약하는 전기요금은','Thus the selected double glazing saves the following cost over [[0]]:'),
('위안.','yuan.'),
('4.','4.'),
('[[0]]. 먼저 전자가 축전기 판 [[1]]에서 [[2]]로 터널링한다고 하자. 터널링 전 판의 전하를 [[3]]라','[[0]]. First let one electron tunnel from plate [[1]] to [[2]]. Let [[3]] be the charge on'),
('하자. 판 [[0]]의 전하이며, [[1]]는 두 판 사이 전압이다(문제의 그림 [[2]]). 그러면','plate [[0]] before tunnelling, and [[1]] the plate voltage (problem Fig. [[2]]). Then'),
('이때 축전기에 저장된 에너지는 다음과 같다.','The stored capacitor energy is'),
('전자가 판 [[0]]로 터널링한 뒤 판 [[1]]의 전하는 다음과 같다.','After the electron tunnels to [[0]], the charge on [[1]] is'),
('[[0]]는 전자 전하의 크기이다. 이때 판 사이 전압과 저장 에너지는 각각 다음과 같다.','Here [[0]] is electron charge magnitude. The new voltage and stored energy are'),
('쿨롱 봉쇄로 터널링이 금지되려면 다음 조건이 필요하다.','Coulomb blockade, forbidding tunnelling, requires'),
('식 [[0]][[1]][[2]]에서 다음을 얻는다.','Equations [[0]][[1]][[2]] give'),
('다음으로 전자가 판 [[0]]에서 [[1]]로 터널링한다고 하자. [[2]]는 역시 터널링 전 판 [[3]]의','Now let an electron tunnel from [[0]] to [[1]]. Again [[2]] is the charge on [[3]] before'),
('전하, [[0]]는 두 판 사이 전압이다. 전자가 [[1]]에서 [[2]]로 터널링하면 판 [[3]]의','tunnelling, [[0]] the plate voltage. When it tunnels from [[1]] to [[2]], plate [[3]] has'),
('전하는 [[0]]이다. 같은 계산으로 [[1]]에서 [[2]]로의 터널링이 금지되는','charge [[0]]. Similarly, forbidding tunnelling from [[1]] to [[2]]'),
('조건은 다음과 같다.','requires the following condition:'),
('식 [[0]][[1]] [[2]]에서 전압 [[3]]가 [[4]] 사이이면 단전자 터널링이 쿨롱','From [[0]][[1]] [[2]], voltage [[3]] between [[4]] blocks'),
('봉쇄된다. 즉 쿨롱 봉쇄 조건은 다음과 같다.','single-electron tunnelling. The blockade condition is'),
('[[0]]. 주어진 조건과 식 [[1]]에서 터널링이 막 가능해질 때 다음이 성립한다.','[[0]]. By the stated condition and [[1]], the tunnelling threshold satisfies'),
('식 [[0]]에 주어진 수치를 넣으면 다음과 같다.','Substituting the data into [[0]] gives'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 if r['id']=='r01':
  r['complete_source_cost_and_reference_stationary']=r['native_atoms'];r['native_atoms']=[];r['left']=next(g['origin'][0]for g in r['erase_glyphs']if g['c']=='元')
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Complete original native inline references, signs, variables and full source slash interval. All source displayed threshold/fraction/cost equations, counters and rules stay fixed; preserve original literal problem-Fig3 reference.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page13-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE13_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
