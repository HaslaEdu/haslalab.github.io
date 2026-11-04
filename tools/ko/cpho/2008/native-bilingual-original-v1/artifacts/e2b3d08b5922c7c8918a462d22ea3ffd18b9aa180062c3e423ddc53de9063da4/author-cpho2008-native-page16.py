import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read gravitational lensing; original missing relation glyphs literal."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page16-native-row-proposals.json').read_text('utf8'))
T=[
('일 때 [[0]]이다. 식 [[1]][[2]] [[3]]에서 다음을 얻는다.','incidence, [[0]]. From [[1]][[2]] [[3]],'),
('6.','6.'),
('방정식','The equation'),
('은 [[0]]의 짝함수이므로 광선은 극축에 대칭이다. 원점 왼쪽 광선은','is even in [[0]], so the ray is polar-axis symmetric. Rays left of the'),
('[[0]], 오른쪽에 있으면 [[1]]에 해당한다. 오른쪽 그림은 [[2]]인','origin have [[0]], right have [[1]]. The figure shows [[2]],'),
('경우이며 극축은 [[0]], 백색왜성은 원점 [[1]]에 있다. 식 [[2]]에 근성점의','polar axis [[0]], dwarf at [[1]]. In [[2]], insert the periapsis'),
('좌표 [[0]]을 넣고 [[1]]에 유의하면 다음과 같다.','coordinates [[0]] and note [[1]], giving'),
('왜성 양쪽의 별빛이 관측자에게 벌리는 [[0]]는 여러 방식으로 표현할 수','Rays past both sides of the dwarf subtend [[0]] at the observer; this'),
('있으며, 이에 따라 여러 풀이가 있다.','can be expressed in different ways, yielding different solutions.'),
('풀이 1: 왜성과 지구 사이 거리가 [[0]]이면 다음 근사가 성립한다.','Method 1: for dwarf–Earth distance [[0]], approximately'),
('식 [[0]]에 관측자의 좌표 [[1]]를 넣으면 다음과 같다.','In [[0]], substitute observer coordinates [[1]]:'),
('식 [[0]]과 [[1]]에서 [[2]]를 없애면 다음을 얻는다.','Eliminate [[2]] from [[0]] and [[1]] to find'),
('식 [[0]]을 식 [[1]]에 넣으면 다음과 같다.','Substitute [[0]] into [[1]]:'),
('즉','Thus'),
('[[0]]이다. 수치를 넣으면 다음을 얻는다.','Here [[0]]. Numerical substitution gives'),
('풀이 2: 무한히 멀어지는 광선의 좌표는 다음과 같이 쓸 수 있다.','Method 2: coordinates of the ray going to infinity can be written'),
('[[0]]로 근사해 식 [[1]]을 [[2]]에 넣는다. 식 [[3]]의 분모가 0이며 [[4]]에 유의하면','Take [[0]], insert [[1]] into [[2]], set the [[3]] denominator to zero; note [[4]]:'),
('따라서','Thus'),
('식 [[0]]을 쓰고 [[1]]에 유의했다. 식 [[2]]와 [[3]]이 같으므로 식 [[4]]도 얻는다[[5]]','Use [[0]] and note [[1]]. Equations [[2]] and [[3]] agree, again giving [[4]][[5]]'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 if r['id']in ['r13','r17']:
  r['complete_original_source_display_program_stationary']=r['native_atoms'];r['native_atoms']=[];hans=[g for g in r['erase_glyphs']if re.search('[\u3400-\u9fff]',g['c'])];r['left']=hans[0]['origin'][0]
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,414]if r['id']in ['r03','r04','r05','r06','r07','r08','r09','r10']else[89,153]if r['id']in ['r13','r17']else[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Exact original native inline coordinates/conditions/references, including literal missing/square relation glyphs in source6/16; no inferred correction. All native root/fraction equation programs13/17, all other displayed expressions, image and source counters remain stationary.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,original_missing_relation_glyphs_intentionally_literal=True,publication_ready=False)
atomic_text(A/'page16-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE16_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
