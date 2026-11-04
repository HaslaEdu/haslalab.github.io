import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Full source-read energy-table, refraction and gravitational-lensing page."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page05-native-row-proposals.json').read_text('utf8'))
T=[
('[[0]]이다. 가로축 [[1]], [[2]]의 단위는 [[3]]이다). 주요 좌표를 표시하고 [[4]][[5]]','[[0]]; horizontal: [[1]], with [[2]] in units of [[3]]). Mark key points. For [[4]][[5]]'),
('[[0]]일 때 [[1]]의 범위를 표에 써라. (이 물음은 그래프와 표 [[2]]만 채점한다.)','[[0]], enter [[1]] ranges below. (Only the graph and Table [[2]] are scored.)'),
('표 [[0]]','Table [[0]]'),
('[[0]]의 범위','[[0]] range'),
('5.','5.'),
('굴절률 [[0]], 반지름 [[1]]인 투명 반원기둥이 공기 중에 있다.','A clear semicylinder, index [[0]], radius [[1]], is in air.'),
('축에 수직인 단면은 그림과 같다. [[0]]는 단면과 축의 교점이다.','The figure is a normal section; [[0]] is its axis intersection.'),
('빛은 평면 [[0]]로만 들어온다. 충분히 넓은 평행 단색광이','Light enters only through plane [[0]]. A broad parallel'),
('기둥 축에 수직으로 입사각 [[0]]로 [[1]] 전면을 비춘다.','monochromatic beam, normal to the axis, covers [[1]] at angle [[0]].'),
('일부 빛은 반원기둥을 통과해 곡면으로 나간다. 그 빛이','Some light passes through and exits the curved surface. Its'),
('[[0]]에 입사할 때 [[1]]축을 따른 폭을 [[2]]라 하자. 기둥 안에서','width on [[0]] along [[1]] is [[2]]. Exclude rays reflected'),
('한 번 이상 반사된 뒤 밖으로 나가는 경우는 고려하지 않는다.','one or more times inside the cylinder before exiting.'),
('[[0]]. 입사각 [[1]]가 [[2]]에서 변할 때 [[3]]의 최솟값 [[4]]과 최댓','[[0]]. As incidence angle [[1]] varies over [[2]], find the minimum [[4]] of [[3]],'),
('값 [[0]]을 구하라[[1]]','and its maximum [[0]][[1]]'),
('[[0]]. 그림 평면에서, 출사광과 곡면이 만나는 원호가 [[1]]에 대해 벌리는 각과 [[2]]의','[[0]]. In the figure plane, relate the arc subtended at [[1]] by the exit beam to [[2]].'),
('관계를 구하라. 또 스침 입사일 때 이 원호의 위치를 구하라.','Also locate this arc at grazing incidence.'),
('6.','6.'),
('일반 상대론에서 빛은 천체의 중력장 안에서 휘며, 중력 중심을 포함하는 평면 안에서','General relativity bends light in a stellar gravity field. The ray is in a plane'),
('중심 근처에서 약간 휜 곡선이다. 중력 중심에 가장 가까운 점이 근성점이다. 근성점과','through the centre, bending slightly near it. Its closest point is periapsis. A line'),
('중력 중심을 잇는 직선이 광선의 대칭축이다. 광선의 평면에서 평면 극좌표 [[0]]의','through periapsis and centre is its symmetry axis. In polar coordinates [[0]],'),
('원점을 중력 중심으로, 극축을 이 대칭축으로 정하면 광선(광자 궤적)의 방정식은','take the centre as origin, symmetry axis as polar axis. The photon trajectory is'),
('[[0]]는 중력 상수, [[1]]은 천체 질량, [[2]]는 광속이며 [[3]]의 절댓값은 [[4]]보다 매우 작다. 지구에서','[[0]] is gravity constant, [[1]] stellar mass, [[2]] light speed; [[3]] is far below [[4]] in'),
('[[0]]광년 떨어진 별이 있고, 별과 지구를 잇는 선분의 중점에 백색왜성이 있다고 하자.','magnitude. A star is [[0]] light years away; a white dwarf lies halfway to Earth.'),
('왜성 양쪽의 두 별빛이 지구에서 벌리는 각이 [[0]]일 때 왜성 질량(kg)은?','At Earth, rays past either side subtend [[0]]. Find the dwarf mass (kg).'),
('주어진 값: [[0]]','Given [[0]]'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 r.update(ko=ko,en=en,reviewed=True,align='center'if r['id']in ['r02','r03']else'left',allowed_horizontal=[89,399]if r['id']in['r05','r06','r07','r08','r09','r10','r11']else[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Original native complete inline expression/list/coordinate, including all Chinese mathematical punctuation. Original lensing display fraction, all table columns/entries/grids and embedded ray diagram stay stationary.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page05-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE05_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
