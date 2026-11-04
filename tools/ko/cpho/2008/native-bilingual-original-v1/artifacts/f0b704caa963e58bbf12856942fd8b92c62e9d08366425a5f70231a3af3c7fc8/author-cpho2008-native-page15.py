import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read semicylinder solution; mixed-baseline fractions entirely fixed."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page15-native-row-proposals.json').read_text('utf8'))
T=[
('5.','5.'),
('[[0]]. 그림 [[1]]에서 [[2]]축은 [[3]]면에 수직이다. 평행광의','[[0]]. Fig. [[1]]: [[2]] is normal to [[3]]. Two parallel rays'),
('두 광선이 [[0]]면의 [[1]], [[2]]에 입사각 [[3]]로','enter plane [[0]] at [[1]], [[2]], with incidence angle [[3]].'),
('투명 기둥으로 들어온다. [[0]]는 굴절각이다. 두 굴절광은','The refraction angle is [[0]]. The two refracted rays'),
('곡면의 [[0]], [[1]]에 도달하며, 곡면에서의 입사각은','reach the surface at [[0]], [[1]], at incidence angles'),
('[[0]], [[1]]이다. [[2]]에서 [[3]]와 입사점 [[4]] 사이의','[[0]], [[1]]. In [[2]], the distance from [[3]] to entry [[4]]'),
('거리를 [[0]]라 하면 사인 법칙에서 다음을 얻는다.','is [[0]]. By the sine rule,'),
('즉','so'),
('그림 [[0]]','Fig. [[0]]'),
('같은 방법으로 [[0]]에서 [[1]]와 입사점 [[2]] 사이 거리도 다음과 같다.','Likewise, in [[0]], the distance from [[1]] to entry [[2]] satisfies'),
('즉','so'),
('입사각 [[0]]를 바꾸면 굴절각 [[1]], 곡면의 입사각 [[2]], [[3]]도 변한다. 곡면 입사각이','Varying [[0]] changes refraction [[1]] and surface incidence [[2]], [[3]]. At the critical angle'),
('임계각에 도달할 때,','given by'),
('전반사가 일어난다. [[0]]을 식 [[1]][[2]] [[3]]에 각각 넣으면 다음과 같다.','total reflection occurs. Substitute [[0]] into [[1]][[2]] [[3]] to obtain'),
('즉','Thus'),
('[[0]], [[1]]일 때 기둥으로 들어와 곡면에 도달한 빛의 입사각은','If [[0]] and [[1]], the rays enter, but reach the curved surface at angles above'),
('임계각 [[0]]보다 커 전반사해 나가지 못한다. 굴절각 [[1]]는 [[2]]와 함께 증가한다. [[3]]에서','the critical [[0]], so cannot exit. Refraction [[1]] rises with incidence [[2]]. From [[3]],'),
('[[0]], 즉 [[1]](수직 입사)일 때 [[2]]의 최솟값은 다음과 같다.','at [[0]], i.e. [[1]] (normal incidence), [[2]] is minimal:'),
('[[0]](스침 입사)이면 [[1]]이다. [[2]]를','At [[0]] (grazing), [[1]]. Substitute [[2]]'),
('식 [[0]]에 넣으면 [[1]]이다[[2]] [[3]]','into [[0]] to find [[1]][[2]] [[3]]'),
('[[0]]. 그림 [[1]]에서 [[2]]는 [[3]]축과 [[4]] 사이 각,','[[0]]. In Fig. [[1]], [[2]] is the [[3]]–[[4]] angle;'),
('[[0]]는 [[1]]축과 [[2]] 사이 각이다. 전반사할 때','[[0]] the [[1]]–[[2]] angle. At total reflection,'),
('및','and'),
('따라서 [[0]]는 [[1]]와 무관하다. 즉 [[2]]는 [[3]]에 독립이다. 스침 입사','Thus [[0]] is independent of [[1]], i.e. [[2]] of [[3]]. At grazing'),
('그림 [[0]]','Fig. [[0]]'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 if r['id']in ['r07','r10','r14','r22']:
  r['complete_original_source_display_programs_stationary']=r['native_atoms'];r['native_atoms']=[]
  # The comma between two original mathematical equalities is not language.
  r['original_math_punctuation_restored_stationary']=[g for g in r['erase_glyphs']if not re.search('[\u3400-\u9fff]',g['c'])]
  r['erase_glyphs']=[g for g in r['erase_glyphs']if re.search('[\u3400-\u9fff]',g['c'])];assert len(r['erase_glyphs'])==1;r['left']=r['erase_glyphs'][0]['origin'][0]
 if r['id']=='r08':
  r['original_display_fraction_denominators_stationary']=r['native_atoms'][0];r['native_atoms']=r['native_atoms'][1:];r['native_atoms'][0]['id']='r08a0';g=r['erase_glyphs'][0];r.update(left=g['bbox'][0],original_center=(g['bbox'][0]+r['native_atoms'][0]['rect'][2])/2)
 bounds=[89,349]if r['id']in['r01','r02','r03','r04','r05','r06','r18','r19','r20','r21','r23']else[89,506]
 if r['id']in ['r07','r10']:
  original=r['complete_original_source_display_programs_stationary'];a=next(v for v in original if v['rect'][0]>r['left']);bounds=[r['left'],a['rect'][0]]
 r.update(ko=ko,en=en,reviewed=True,align='center'if r['id']in['r08','r24']else'left',allowed_horizontal=bounds)
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Only complete source native inline expressions/references move. All original fractions7/10/14, split fraction denominators, equation counters and displays, mathematical separating commas, figures and footer stay fixed as actual original programs.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page15-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE15_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
