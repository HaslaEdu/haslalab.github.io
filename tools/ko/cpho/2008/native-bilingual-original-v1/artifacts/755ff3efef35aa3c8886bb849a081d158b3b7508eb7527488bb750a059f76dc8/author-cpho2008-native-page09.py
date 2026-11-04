import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read satellite geometry, uncertainty and receiver solution."""
from pathlib import Path
import json,re,hashlib
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page09-native-row-proposals.json').read_text('utf8'))
T=[
('위성이 신호를 보낼 때 두 관측소까지의 거리는 같으며 다음과 같다.','At emission, the satellite distances to both stations are equal:'),
('위성 [[0]]가 위 삼각형의 평면 안에 있을 때 지표면에서의 높이가 최대 [[1]]가 된다. [[2]]를','When satellite [[0]] is in the triangle plane, its altitude is maximal, [[1]]. Let [[2]] be'),
('[[0]]의 위도라 하면 코사인 법칙에서 다음을 얻는다.','the latitude of [[0]]. The cosine rule gives'),
('식 [[0]][[1]] [[2]]에서 다음을 얻는다.','Equations [[0]][[1]] [[2]] give'),
('식 [[0]]는 그림에서도 바로 쓸 수 있다.','Equation [[0]] also follows directly from the diagram.'),
('[[0]] 위도의 작은 오차 [[1]]는 식 [[2]]에 따라 [[3]]의 오차 [[4]]를 일으킨다. 이때','[[0]] A small latitude error [[1]] gives, by [[2]], an error [[4]] in [[3]]. Then'),
('다음이 성립한다.','we have'),
('식 [[0]]을 전개하자. [[1]]가 작으므로 [[2]]도 작다. 고차항을 버리고 식 [[3]]을 빼면','Expand [[0]]. Small [[1]] gives small [[2]]. Drop higher orders and subtract [[3]],'),
('다음과 같다.','giving'),
('[[0]]는 식 [[1]]로 주어진다.','Here [[0]] is given by [[1]].'),
('[[0]] 시간 [[1]]에 오차 [[2]]가 있으면 [[3]]의 오차는 다음과 같다.','[[0]] An error [[2]] in time [[1]] gives an error in [[3]]:'),
('식 [[0]]에 따라 [[1]]의 오차 [[2]]가 생긴다. 이때 다음이 성립한다.','By [[0]], this gives an error [[2]] in [[1]]. Then'),
('식 [[0]][[1]] [[2]]와 [[3]]에서 고차항을 버리면 다음을 얻는다.','From [[0]][[1]] [[2]] and [[3]], neglect higher orders to obtain'),
('[[0]]는 식 [[1]]로 주어진다.','Here [[0]] is given by [[1]].'),
('[[0]][[1]][[2]] 식 [[3]]에 대입하면 [[4]]이다[[5]] [[6]] 식 [[7]]에 대입하면','[[0]][[1]][[2]] From [[3]], [[4]][[5]] [[6]] From [[7]],'),
('[[0]]이다[[1]] [[2]] 식 [[3]]에 수치를 넣으면 [[4]]이다[[5]]','[[0]][[1]] [[2]] Substituting into [[3]] gives [[4]][[5]]'),
('[[0]]. 좌표계를 정해 물체의 미지 위치 좌표를 [[1]], 미지 시각을 [[2]]라 하자. [[3]]번째','[[0]]. Choose a frame. Unknown object coordinates: [[1]], time [[2]]. Satellite [[3]]'),
('위성의 시각 [[0]]에서 좌표는 [[1]]이다. 신호는 광속으로 전파되므로 다음과 같다.','has coordinates [[1]] at time [[0]]. Its signal travels at light speed, so'),
('식 [[0]]의 미지수 [[1]] 네 개를 정하려면 독립 방정식 네 개가 필요하다.','[[0]] has four unknowns [[1]], requiring four independent equations.'),
('서로 다른 위성 최소 네 개의 신호를 동시에 받는다. 물체 위치와 시각은 식 [[0]]의 [[1]]','Receive four or more satellites at once. Position and time follow from [[0]], [[1]]'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Complete original native inline expressions, references and Chinese list punctuation; original literal errata/signs/references preserved. All source display fractions, scripts, rules and footer remain stationary.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
ink_path=B/'inspection/page09-authored-original-native-outline-bounds.json'
ink=json.loads(ink_path.read_text('utf8'));assert ink['source_sha256']==q['source_sha256']
outlines={v['id']:v for v in ink['atoms']}
for row in q['rows']:
 for atom in row['native_atoms']:
  proof=outlines[atom['id']];assert atom['rect']==proof['source_metric_rect'];original=atom['rect'];actual=proof['actual_original_ink_rect']
  atom['source_metric_rect']=original[:];atom['rect']=[min(original[0],actual[0]),original[1],max(original[2],actual[2]),original[3]]
  atom['actual_original_outline_envelope_evidence']=dict(path=str(ink_path),sha256=hashlib.sha256(ink_path.read_bytes()).hexdigest(),atom_id=atom['id'])
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page09-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE09_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
