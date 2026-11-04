import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read satellite/GPS and refrigerator introduction, original-size rows."""
from pathlib import Path
import json,re,hashlib
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page02-native-row-proposals.json').read_text('utf8'))
T=[
('최소 몇 개의 지상 관측소가 필요한가? 위성 위치를 정하는 식을 써라.','What minimum number of ground stations is needed? Give the position equations.'),
('[[0]] 두 관측소 [[1]]는 같은 경선의 북위 [[2]], 남위 [[3]]에 있다(단위: [[4]][[5]]','[[0]] Stations [[1]] lie on one meridian at [[2]] N and [[3]] S (unit: [[4]][[5]]'),
('위성이 송신한 뒤 [[0]]에 두 관측소가 동시에 신호를 받는다. [[1]] 송신 순간의','Both receive a satellite signal [[0]] after emission. [[1]] Find its maximum altitude'),
('최대 고도 [[0]]를 구하라[[1]] [[2]] [[3]]의 위도에 작은 오차 [[4]]가 있으면 [[5]]의 오차','[[0]] above ground[[1]] [[2]] For small latitude errors [[4]] at [[3]], find the error in [[5]]'),
('를 구하라. [[0]] 시간 [[1]]에 작은 오차 [[2]]가 있을 때 [[3]]의 오차를 구하라.','[[0]] For a small error [[2]] in time [[1]], find the error in [[3]].'),
('[[0]]. 위 [[1]][[2]]에서 [[3]]이다[[4]] [[5]] 송신 순간 위성의 지표면 위','[[0]]. In [[1]][[2]], take [[3]][[4]] [[5]] Find the maximum altitude'),
('최대 고도 [[0]]는 몇 km인가? [[1]] [[2]]이면 [[3]]의 오차는? [[4]] [[5]]','[[0]] in km. [[1]] If [[2]], how large is the error in [[3]]? [[4]] If [[5]]'),
('[[0]]일 때 [[1]]의 오차는? 구형 지구의 반지름 [[2]], 광속 [[3]]','[[0]], what error in [[1]]? Earth is a sphere of radius [[2]]; [[3]]'),
('[[0]]이고, 지표면 중력 가속도는 [[1]]이다[[2]]','[[0]], and ground gravitational acceleration [[1]][[2]]'),
('[[0]]. 위성 운동을 기준으로 물체 운동을 측정한다. 상대론적 효과는 무시한다.','[[0]]. Now use reference-satellite motion to track an object. Neglect relativity.'),
('위성이 계속 보내는 전파에는 운동 상태, 즉 각 신호의 송신 시각과 그 순간의','Each continuously emitted radio signal states its emission time and the satellite’s'),
('위치가 담겨 있다. 관측할 물체에는 위성 신호 수신기가 있다. 시계는 없으며, 이로써','position then. A receiver aboard the object, with no clock, obtains these data.'),
('이 정보를 얻는다. 수신 순간 물체가 있는 위치와 그 시각, 즉 물체의 운동 상태를','To infer its motion state, its position and time on receiving a signal,'),
('정하려면, 일반적으로 최소 몇 개의 서로 다른 위성이 보낸 신호를 동시에 받아야','what minimum number of different satellites must it receive simultaneously?'),
('하는가? 수신 순간의 물체 위치와 시각을 정하는 식을 써라.','Write the equations for the object’s position and time at reception.'),
('[[0]]. 특수 상대론에서 움직이는 시계는 정지한 시계보다 느리다. 일반 상대론에서는','[[0]]. Special relativity slows moving clocks; general relativity slows clocks'),
('중력장 속 시계가 느려진다. 두 효과를 고려하자. 위성과 지상 관측소 시계의 영점은','in a gravitational field. Include both effects. Satellite and station clocks have'),
('일치한다. 지표면 높이 [[0]]의 원궤도를 돈다. 지구 반지름 [[1]], 광속 [[2]],','aligned zero readings. Orbit height [[0]]; radius [[1]], light speed [[2]],'),
('지표면 중력 가속도 [[0]]는 [[1]]번 물음의 값을 쓴다.','and ground acceleration [[0]] are as given in part [[1]].'),
('[[0]] 지상 시계로 [[1]]이 지난 뒤 두 시계의 표시 차이를 특수 상대론으로','[[0]] By special relativity, estimate the reading difference after [[1]] on Earth:'),
('추정하라. 등속 직선 운동의 시간 지연 식은 등속 원운동에도 적용된다고 가정한다.','ground minus satellite. Use uniform rectilinear time dilation for circular motion.'),
('[[0]] 일반 상대론의 지연 인자는 [[1]]이다[[2]] [[3]]는 그 위치의','[[0]] The GR slowing factor is [[1]][[2]] where [[3]] is the magnitude'),
('중력 퍼텐셜 크기이다. 중력 위치 에너지를 물체 질량으로 나눈 값이며, 무한대에서 0이다.','of gravitational potential: potential energy per unit mass, zero at infinity.'),
('지상 시계로 [[0]]이 지난 뒤, 위성 시계와 지상 시계의 표시 차이를 구하라.','After [[0]] on the ground clock, find the satellite-minus-ground clock reading.'),
('3.','3.'),
('냉동기는 외부에서 받은 일로, 저온부에서 흡수한 열과 외부의 일에서 얻은 에너지를','A refrigerator sends heat from a cold reservoir, plus energy from external work,'),
('함께 고온부로 보낸다. 따라서 저온부는 더 차가워지고 고온부는 더 뜨거워진다. 고온부의','to a hot reservoir, cooling the cold one and warming the hot one. If it works'),
('절대 온도가 [[0]], 저온부의 절대 온도가 [[1]]일 때, 저온부에서 흡수한','between absolute temperatures [[0]] (hot) and [[1]] (cold), taking heat'),
]
assert len(T)==len(q['rows'])
ink_path=B/'inspection/page02-original-native-outline-bounds.json'
ink=json.loads(ink_path.read_text('utf8'));assert ink['source_sha256']==q['source_sha256']
outlines={v['id']:v for v in ink['atoms']}
for r,(ko,en)in zip(q['rows'],T):
 en=en.replace('’',"'")
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Complete original native inline expression or separate original numbered/Roman reference, with source scripts and slash fractions. All display formulas/footers remain stationary.')
  evidence=outlines[a['id']];assert a['rect']==evidence['source_metric_rect'];a['source_metric_rect']=a['rect'][:]
  # Italic H/tau/phi ink genuinely overhangs the PDF advance. Reserve the
  # actual original outline envelope, so adjacent Korean particles and
  # English punctuation never touch mathematical ink. No glyph is scaled,
  # redrawn or replaced, and all source expression members share one dx.
  original=a['rect'];actual=evidence['actual_original_ink_rect'];a['rect']=[min(original[0],actual[0]),original[1],max(original[2],actual[2]),original[3]]
  a['actual_original_outline_envelope_evidence']=dict(path=str(ink_path),sha256=hashlib.sha256(ink_path.read_bytes()).hexdigest(),atom_id=a['id'])
 for lang in('ko','en'):assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,publication_ready=False)
atomic_text(A/'page02-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE02_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
