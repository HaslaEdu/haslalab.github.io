import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Full source-read last four actual solution pages, original math untouched."""
from pathlib import Path
from copy import deepcopy
import json,re,hashlib
B=Path(__file__).resolve().parents[1];A=B/'authoring'
TEXT={
17:[
('풀이 3: 관측자에게 별빛이 벌리는 각 [[0]]는 관측점에서 두 광선의 접선 사이 각이므로','Method 3: angle [[0]] equals the angle between the ray tangents at the observer:'),
('광선 방정식 [[0]]에서 [[1]]를 구하면 다음과 같다.','From the ray equation [[0]], calculate [[1]]:'),
('관측자 좌표 [[0]], 식 [[2]]의 [[1]]를 넣고 [[3]]가 작음에 유의하면 다음을 얻는다.','Insert observer coordinates [[0]] and [[1]] from [[2]], noting small [[3]]:'),
('식 [[0]]과 같으므로 식 [[1]]도 얻는다[[2]]','This agrees with [[0]], again giving [[1]][[2]]'),
('풀이 4: 식 [[0]]로 방정식 [[1]]을 다음과 같이 고쳐 쓴다.','Method 4: use [[0]] to rewrite [[1]] as'),
('즉','Thus'),
('[[0]]일 때 식 [[1]]의 점근식은 다음과 같다.','For [[0]], the asymptote of [[1]] is'),
('이 직선의 [[0]]축 절편은 [[1]]이며 기울기는 다음과 같다.','This straight line has [[0]] intercept [[1]] and slope'),
('[[0]]이다[[1]] [[2]]에 식 [[3]]을 넣으면 식 [[4]], 따라서 식 [[5]]도 얻는다[[6]]','Thus [[0]][[1]] Substitute [[3]] for [[2]] to obtain [[4]], and hence [[5]][[6]]'),
('7.','7.'),
('[[0]][[1]][[2]] 헬륨에는 전자 두 개가 있다. 제1 이온화 에너지 [[3]]는 전자 하나를 무한대로','[[0]][[1]][[2]] Helium has two electrons; [[3]] is the energy to remove one to infinity,'),
('옮기는 에너지이며 [[0]]이다. [[1]]를 구하려면 전자 하나가','satisfying [[0]]. For [[1]], find the ion energy after one electron'),
('이온화된 뒤 헬륨 이온 에너지 [[0]]가 필요하다. 전자가 핵 주위를 돈다. 두 풀이를 보인다.','is ionized, [[0]]: one electron orbiting the helium nucleus. Here are two methods.'),
('풀이 1: 운동 방정식','Method 1: in the mechanical equation'),
('에서 [[0]]는 궤도 반지름, [[1]]는 속력이다. 바닥상태의 보어 양자화 조건(각운동량 [[2]])으로','[[0]] is radius, [[1]] speed. Ground-state Bohr quantization (angular momentum [[2]]) gives'),
('따라서 헬륨 이온의 에너지는 다음과 같다.','Thus the helium-ion energy is'),
],
18:[
('[[0]]는 바닥상태 전자의 운동량 크기이다. 수치를 넣으면 다음과 같다.','Here [[0]] is ground-state electron momentum. Substitution gives'),
('전자 간 상호작용을 무시했으므로 헬륨 원자 바닥상태 에너지 [[0]]는 이 값의 [[1]]배이다.','Ignoring electron interaction, the helium ground energy [[0]] is [[1]] times this value:'),
('헬륨 이온 에너지 [[0]]와 원자 바닥상태 에너지 [[1]]의 차이가 제1 이온화 에너지이다.','The ion energy [[0]] minus atomic ground energy [[1]] is the first ionization energy:'),
('풀이 2: 헬륨 이온의 에너지는 다음과 같다.','Method 2: the helium-ion energy is'),
('바닥상태 각운동량 관계 [[0]]를 넣으면 식 [[1]]은 다음과 같이 된다.','Insert the ground angular momentum [[0]] to rewrite [[1]]:'),
('바닥상태는 에너지가 최소이므로 식 [[0]] 우변의 첫 항이 0이다. 반지름과 에너지는','Minimum ground energy makes the first term of [[0]] zero. Thus radius and energy'),
('각각 식 [[0]][[1]] [[2]]와 같다.','are respectively as in [[0]][[1]] [[2]].'),
('[[0]] 이제 헬륨 원자 바닥상태 에너지 [[1]]와 반지름 [[2]]도 두 가지로 구한다.','[[0]] Here are two methods for helium ground energy [[1]] and radius [[2]].'),
('풀이 1: 운동 방정식','Method 1: the mechanical equation'),
('과 바닥상태 양자화 조건 [[0]]에서 다음 반지름을 얻는다.','and ground-state quantization [[0]] give the radius'),
('따라서 헬륨 원자 바닥상태 에너지는 다음과 같다.','Thus the helium ground energy is'),
('수치를 넣어 계산하면 다음과 같다.','Numerical substitution gives'),
('그러므로 헬륨의 제1 이온화 에너지는 다음과 같다.','Therefore the helium first ionization energy is'),
('이는 여전히 헬륨 제1 이온화 에너지 실험값 [[0]]보다 [[1]] 높다[[2]]','This still exceeds the measured helium ionization energy [[0]] by [[1]][[2]]'),
],
19:[
('풀이 2: 헬륨 원자의 에너지는 다음과 같다.','Method 2: the helium atom energy is'),
('다음과 같이 고칠 수 있다.','This can be rewritten as'),
('위 식 우변의 첫 항이 0일 때 에너지가 최소이다. 따라서 바닥상태 에너지와 반지름은','The first term on the right vanishes at minimum energy. The ground energy and radius'),
('각각 식 [[0]][[1]] [[2]]와 같다.','are respectively as in [[0]][[1]] [[2]].'),
('[[0]][[1]][[2]] 입자는 아래에서 납판을 통과해 위로 가며 전하는 양이다.','[[0]][[1]][[2]] The particle crosses the lead plate upward. Its charge is positive.'),
('[[0]] 그림처럼 속도 [[1]]는 자기장에 수직이고 로런츠 힘은 종이 평면에 있다. 자기력은','[[0]] Velocity [[1]] is normal to the field; Lorentz force is in the paper. Magnetism'),
('입자 운동량의 크기를 바꾸지 않고 방향만 바꾼다. 기체 저항을 무시하면 일정 자기장 속','changes momentum direction, not magnitude. Neglecting gas drag, in the steady field'),
('입자 궤적은 곡률 반지름이 일정한 원호이다. 운동 방정식은 다음과 같다.','the path is a circular arc of constant radius. The equation of motion is'),
('[[0]]는 전하, [[1]]는 속력, [[2]]는 운동량 크기이며, [[3]]는 시간 [[4]] 동안 입자가','Here [[0]] is charge, [[1]] speed, [[2]] momentum; [[3]] is the angle turned in time [[4]],'),
('회전한 각, [[0]]는 궤적의 곡률 반지름이다. 따라서 다음과 같다.','and [[0]] the curvature radius. Hence'),
('[[0]]이다. 납판 입사 및 출사 운동량의 크기를 각각 [[1]], [[2]]라 하자. 식 [[3]]에','[[0]]; let [[1]], [[2]] be entering and exiting momenta. In [[3]],'),
('주어진 수치를 넣어 계산하면 다음과 같다.','substitute the data to obtain'),
('[[0]]일 때는 특수 상대론을 써야 한다. 다음 식에서','For [[0]], use special relativity. From'),
('다음을 얻는다.','we obtain'),
('납판 입사 및 출사 속력을 [[0]], [[1]]라 하자. 식 [[2]]와 [[3]]를','Let [[0]], [[1]] be entering and exiting speeds. Insert [[2]] and [[3]]'),
('식 [[0]]에 넣으면 다음과 같다.','into [[0]] to obtain'),
('',''),
],
20:[
('시간이라 하면 다음과 같다.','time. Then'),
('납판 통과 중 운동량 변화의 크기를 [[0]]라 하면 납판에 작용하는 평균 힘의 크기는','Let [[0]] be the momentum change magnitude. The mean force on the plate is'),
('수치를 넣으면 다음과 같다.','Substitution gives'),
('[[0]] 한 입자가 납판을 통과하는 시간은','[[0]] The time for one particle to cross the plate is'),
('펄스 주기 [[0]]보다 훨씬 짧다. 빔이 통과할 때 납판의 평균 힘의','far below pulse period [[0]]. The mean plate force during'),
('크기는 다음과 같다.','the pulse passage is'),
('수치를 넣으면 다음과 같다.','Substitution gives'),
('식 [[0]]에서 입자의 에너지는 다음과 같이 쓸 수 있다.','Using [[0]], the particle energy can be written'),
('따라서 납판을 통과하기 전과 후의 입자 에너지는 각각 다음과 같다.','Thus the particle energies before and after crossing are'),
('그러므로 펄스 빔이 통과하는 동안 납판이 흡수하는 열량은 다음과 같다.','The heat absorbed by the plate during the pulse is therefore'),
('수치를 넣으면 다음과 같다.','Substitution gives'),
]}
for n,T in TEXT.items():
 q=json.loads((A/f'page{n:02}-native-row-proposals.json').read_text('utf8'));assert len(T)==len(q['rows']);rows=[]
 for r,(ko,en)in zip(q['rows'],T):
  if n==17 and r['id']=='r05':r['complete_original_display_formula_stationary']=r['native_atoms'];r['native_atoms']=[]
  if n==19 and r['id']=='r16':
   formula,timing=r['native_atoms'];r['complete_original_inline_mean_speed_fraction_stationary']=formula
   first=deepcopy(r);first['id']='r16a';first['native_atoms']=[];first['erase_glyphs']=[g for g in r['erase_glyphs']if g['origin'][0]<formula['rect'][0]]
   first.update(ko='따라서 납판 통과 중 평균 속도는',en='Mean speed through lead plate:',reviewed=True,align='left',allowed_horizontal=[89,formula['rect'][0]])
   second=deepcopy(r);second['id']='r16b';timing['id']='r16ba0';second['native_atoms']=[timing];second['erase_glyphs']=[g for g in r['erase_glyphs']if g['origin'][0]>=formula['rect'][0]]
   second.update(ko='[[0]]는 통과',en='[[0]]: transit',reviewed=True,align='left',left=timing['rect'][0],allowed_horizontal=[timing['rect'][0],506])
   assert first['erase_glyphs']and second['erase_glyphs'];rows.extend([first,second]);continue
  r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,153]if n==17 and r['id']=='r05'else[89,506]);rows.append(r)
 for r in rows:
  for a in r['native_atoms']:
   assert not a['proposed_vector_paths'],(n,r['id'],a['id']);a.update(vector_paths=[],reviewed=True,source_review_reason='Complete exact source-native inline expressions/references and original mathematical Chinese punctuation. Every original independent display and inline split mean-speed fraction, root/rule/clip program, literal missing relation glyph, all mathematical counters and footer remain fixed; no physical errors corrected.')
  for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(n,r['id'],lang)
 if n==19:
  ink_path=B/'inspection/page19-authored-original-native-outline-bounds.json';ink=json.loads(ink_path.read_text('utf8'));assert ink['source_sha256']==q['source_sha256'];outlines={v['id']:v for v in ink['atoms']}
  for row in rows:
   for atom in row['native_atoms']:
    evidence=outlines[atom['id']];assert atom['rect']==evidence['source_metric_rect'];original=atom['rect'];actual=evidence['actual_original_ink_rect']
    atom['source_metric_rect']=original[:];atom['rect']=[min(original[0],actual[0]),original[1],max(original[2],actual[2]),original[3]]
    atom['actual_original_outline_envelope_evidence']=dict(path=str(ink_path),sha256=hashlib.sha256(ink_path.read_bytes()).hexdigest(),atom_id=atom['id'])
 q.update(rows=rows,source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
 atomic_text(A/f'page{n:02}-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_FULL_SOURCE_PROSE_MANUALLY_AUTHORED',n,len(rows))
