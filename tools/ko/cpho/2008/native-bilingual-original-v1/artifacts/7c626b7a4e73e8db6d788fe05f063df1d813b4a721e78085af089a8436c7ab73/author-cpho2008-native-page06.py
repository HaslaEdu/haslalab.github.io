import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Full source-read helium model and cloud-chamber problem."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page06-native-row-proposals.json').read_text('utf8'))
T=[
('7.','7.'),
('[[0]]. 헬륨 바닥상태의 보어 모형에서, 각 전자는 헬륨핵 중심의 원궤도를 돈다.','[[0]]. In the Bohr model of ground-state helium, each electron circles the nucleus,'),
('두 반지름은 같고 각운동량은 모두 [[0]]이며, [[1]]는 플랑크 상수이다.','with equal radii and angular momenta [[0]], where [[1]] is the Planck constant.'),
('[[0]] 전자 간 상호작용을 무시할 때, 헬륨의 제1 이온화 에너지(eV)를 구하라. 이온화','[[0]] Ignore electron interaction. Find first ionization energy (eV): energy'),
('에너지는 전자 하나를 무한히 먼 곳으로 옮기는 데 필요한 에너지이다.','needed to move one electron to infinity.'),
('[[0]] 헬륨의 제1 이온화 에너지 실험값은 [[1]]이다. 모형에 전자 간 상호작용을','[[0]] The measured ionization energy is [[1]]. Include electron interaction'),
('고려하자. 두 전자가 언제나 핵을 지나는 지름의 양 끝에 있다고 더 가정한다. 이 모형과','in this model. Assume the two electrons always occupy opposite ends of a diameter'),
('가정으로 궤도 반지름 [[0]], 바닥상태 에너지 [[1]], 제1 이온화 에너지 [[2]]를 구하고, 측정한','through the nucleus. Find orbit radius [[0]], ground energy [[1]], ionization energy [[2]].'),
('헬륨의 제1 이온화 에너지와 비교하라.','Compare the predicted first ionization energy with experiment.'),
('전자 질량 [[0]][[1]] 광속 [[2]], 상수 [[3]]','Mass [[0]][[1]] light speed [[2]]; [[3]]'),
('[[0]][[1]] [[2]][[3]] [[4]]는 정전기력 상수, [[5]]는 기본 전하량이다.','[[0]][[1]] [[2]][[3]] [[4]]: Coulomb constant; [[5]]: unit charge.'),
('[[0]]. 오른쪽은 구름상자를 지난 입자의 궤적 사진이다. 종이 평면 안의 궤적 가운데','[[0]]. The photo is a cloud-chamber track, in the paper plane. In its middle a lead'),
('종이에 수직인 납판이 있다. 균일한 일정 자기장은','plate is normal to paper. A steady uniform field goes'),
('종이 안쪽이다. 전하 크기는 기본 전하량 [[0]]','into it. The particle charge magnitude is [[0]]'),
('[[0]]이다. 납판 아래 곡률 반지름은 [[1]],','[[0]]. Track radii: below the plate [[1]],'),
('위의 곡률 반지름은 [[0]]이다. 판 안의','above it [[0]]. The track in the plate makes'),
('궤적과 판 법선 사이 각 [[0]], 판 두께 [[1]],','[[0]] with its normal; thickness [[1]];'),
('자기장 [[0]], 질량 [[1]]','[[0]]; mass [[1]]'),
('[[0]]이다. 구름상자 기체의 입자 저항은 무시한다.','[[0]]. Ignore gas drag on the particle.'),
('[[0]] 입자의 운동 방향과 전하의 부호를 써라.','[[0]] State the direction of motion and sign of charge.'),
('[[0]] 입자가 통과하는 동안 납판에 작용하는 평균 힘은 몇 N인가?','[[0]] Find the average force in N on the plate while the particle passes through.'),
('[[0]] 입자 대신 유량 [[1]]의 가속기 펄스 빔이 납판에 입사한다.','[[0]] Instead, an accelerator pulse of flux [[1]] hits the plate.'),
('펄스 하나는 [[0]] 동안 지속된다. 빔이 통과하는 동안 납판에 작용하는 평균 힘은','One pulse lasts [[0]]. Find the average force in N on the plate while the pulse'),
('몇 N인가? 그동안 납판이 흡수하는 열량은 몇 J인가?','passes through, and the heat in J absorbed by the plate during it.'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,349]if r['id']in['r12','r13','r14','r15','r16','r17','r18']else[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Complete exact source native inline formula, split physical row continuation, source numbered reference or original list punctuation. Cloud chamber source image, encoded bytes/CTM, all source footer and nonlanguage ink remain stationary.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page06-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE06_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
