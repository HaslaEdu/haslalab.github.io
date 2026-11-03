"""Manual bilingual translation of every original native T prose slot."""
from pathlib import Path
import json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
data=json.loads((B/'inputs/original-all10-source-slots.json').read_text('utf8'))
text=r'''1-0-0	제20회 전국 중학생 물리 경시대회	20th National High School Physics Contest
1-1-0	결선 문제	Final Problems
1-2-0	1.	1.
1-3-0	개의 같은 질량의 균질한 공 중,	equal-mass uniform spheres: place
1-3-1	개의 반지름은	with radius
1-3-2	이고, 반지름	at rest in a hemispherical bowl of radius
1-3-3	인 반구형 그릇에 정지해 있다. 중심은 같은	, their centers in one
1-4-0	수평면에 있다. 나머지	horizontal plane. Put the remaining
1-4-1	개의 반지름은	sphere of radius
1-4-2	이고, 이 공을	atop the
1-4-3	개 위에 놓는다. 모든 접촉면은 매끄럽다. 그릇 반지름	. All contacts are smooth. What condition on the bowl radius
1-4-4	에 관한 어떤 조건에서	makes the lower spheres
1-5-0	아래의 공들이 서로 떨어지는가?	separate from each other?
1-6-0	2.	2.
1-7-0	지구 중심을 한 초점으로 하는 위성의 타원 궤도는 직교좌표계에서	An Earth satellite follows an ellipse with Earth at a focus. Its Cartesian equation is
1-8-1	는 각각 알려진 장반경과 단반경이다. 위성이 원지점에 있을 때 큰 에너지를 주어	are its known semi-major and semi-minor axes. At apogee, a large sudden energy input
1-9-0	진행 방향으로 질량이	launches a probe along the satellite's motion, with mass
1-9-1	인 탐사선을 발사한다. 탐사선은 지구 중력에 의해 쌍곡선을 그린다.	. Under Earth's gravity the probe follows a hyperbola.
1-10-0	쌍곡선의 초점은 지구 중심이고, 실반경은 원래 궤도의 원지점과 지구 중심 사이 거리와 같다. 발사 때 탐사선에	Its focus is Earth and its semi-transverse axis equals the original apogee distance. Find the energy
1-11-0	준 에너지를 구하여라. 지구 질량	given to the probe at launch. Earth's mass
1-11-1	와 중력 상수	and the gravitational constant
1-11-2	는 알려져 있다. 다른 천체의 영향은 무시한다.	are known. Ignore other celestial bodies.
1-12-0	3.	3.
1-13-0	그림의 금속 플라이휠에는	The metal flywheel shown has
1-13-1	개의 살이 있고, 각 살의 길이는	spokes, each of length
1-13-2	이다. 회전축	, and rotates about
1-13-3	둘레로 돌며, 균일한 자기장 속에 있다. 자기장	in a uniform magnetic field. The field
1-14-0	방향은 축과 평행하고 자기장 세기는	is parallel to the axle, with flux density
1-14-1	이다. 축과 테두리는 브러시를 통해 저항	. Brushes connect the axle and rim through resistance
1-14-2	과 인덕턴스	and inductance
1-14-3	의 폐회로를 이룬다. 휠과 축의	to form a closed circuit. Neglect the wheel and axle's
1-15-0	저항 및 회전 중 마찰은 무시한다.	resistance and all rotational friction.
1-16-1	일정한 외부 돌림힘	A constant external torque
1-16-2	으로 정지한 휠을 돌린다. 정상 상태에서 구하여라: 각속도	starts the wheel from rest. Find its steady angular speed
1-17-0	와 저항	and the current through resistance
1-17-1	에 흐르는 전류	,
1-18-1	정상 상태에서 외부 돌림힘	After steady rotation is reached, suddenly remove torque
1-18-2	을 갑자기 제거한다. 각속도	. The angular speed
1-18-3	와 저항	and the current through resistance
1-18-4	의 전류	,
1-18-5	는 시간에 따라	, then change with time.
1-19-0	변한다. 저항	Different resistance
1-19-1	값에 따라 각속도 그래프	values give different angular-speed curves
1-19-3	와 전류 그래프	and current curves
1-19-5	의 모양이 달라진다.	.
1-20-0	다음에 제시한 각속도	The attached set gives
1-20-2	그래프는	curves,
1-20-3	개이다. 모든 그래프에서 돌림힘	in all. In each, the instant when torque
1-20-4	을 제거한 순간을	is removed defines the start,
1-20-5	인	,
1-21-0	시작 시각으로 삼았다. 이때 각속도는	when angular speed is
1-21-1	, 전류는	and current is
1-21-2	이다. 각속도	. All angular-speed
1-21-3	그래프들의 세로축 단위와 전류	plots share a vertical scale, as do the current
1-21-4	그래프들의 세로축 단위는 각각	plots.
1-22-0	같으며 모든 시간축 단위도 같다. 가능한 각속도	All time axes share a scale. Select the physically possible angular-speed
1-22-1	의 시간 변화	versus-time
1-23-0	그래프를 골라라:	curves
1-24-0	각 그래프에 대응하는 전류	and, for each, the closest correct current
1-24-1	의 시간 변화 그래프	versus-time curve
1-24-3	를 골라라. 고른 각속도	. Connect each selected
1-24-5	및 대응하는 전류	curve to its corresponding
1-25-1	의 기호들을 아래에서 곧은 실선으로 연결하여라.	curve by a straight solid line between their symbols below.
1-26-0	주의: 모두 정확히 연결해야 만점이다. 일부만 맞게 연결하면 부분 점수를 주지만, 잘못 연결한 것이 있으면 0점이다.	Full credit requires all links. An incomplete correct set earns partial credit; any wrong link earns zero.
1-27-0	4.	4.
1-28-0	그림처럼	As shown, the
1-28-1	축 오른쪽에는 세기가	axis has uniform field
1-28-2	인 균일한 자기장이,	on its right and the
1-28-3	축 왼쪽에는 세기가	axis has uniform field
1-28-4	인 균일한 자기장이 있다. 두 자기장	to its left. Both fields
1-29-0	제	Page
1-29-1	쪽	of
1-29-2	/ 총	
1-29-3	쪽	
2-0-0	은 종이 면에 수직으로 들어간다. 원점	point into the paper. At origin
2-0-1	에서 양전하	, a particle with positive charge
2-0-2	, 질량	and mass
2-0-3	인 입자	,
2-1-0	를	called
2-1-1	라 하자. 이 입자는	, starts at
2-1-2	에 속력	with initial speed
2-1-3	으로	along the positive
2-1-4	축의 양의 방향으로 출발한다. 입자	axis. After
2-1-5	가 출발한 뒤,	starts,
2-2-0	질량과 전하량이	another particle with the same mass and charge as
2-2-1	와 같은 입자	,
2-2-2	가 원점	, leaves origin
2-2-3	에서 속력	with speed
2-2-4	으로 음의	along the negative
2-2-5	축	axis.
2-3-0	방향으로 출발한다. 두 입자	For the particles
2-3-1	와	and
2-3-2	가 운동 중 만나도록 하려면 출발 시각의	to meet during their motion, analyze and find the
2-4-0	차이가 최소 얼마여야 하는가? 그때 만나는 점의 좌표도 구하여라. 자기장 영역 전체는	minimum launch delay and the meeting point's coordinates. The entire field region is
2-5-0	진공이다. 중력과 두 입자	vacuum. Ignore gravity and interaction between
2-5-2	사이의 상호작용은 무시한다.	.
2-6-0	5.	5.
2-7-0	근시인 사람이 안경 없이 뚜렷이 볼 수 있는 물체는 눈에서	A myopic person sees clearly without glasses only objects within
2-7-1	안에 있다. 눈 가까이에 작은 원형 구멍이 난	. He notices that a small circular hole in a card held
2-8-0	카드를 대고 보면 안경 없이도 먼 물체가 더 선명해진다는 것을 발견했다.	close to the eye also makes distant objects clearer without glasses.
2-9-0	. 원형 구멍의 지름이	. For a hole of diameter
2-9-1	일 때, 먼 점광원을 직접 보는 근시안의 망막에 생기는 광점의 지름을 기하광학으로	, use geometrical optics to find the diameter of the spot formed on the retina
2-10-0	구하여라.	when the myopic eye looks directly at a distant point source.
2-11-0	. 회절도 고려하여 가장 적합한 구멍 지름을 구하여라. 가시광선의 평균 파장은	. Include diffraction and find the optimum hole diameter. Use mean visible wavelength
2-12-0	힌트:	Hints:
2-12-1	. 복잡한 광학계인 눈을, 초점 거리	. Model the complex optical system of the eye as a thin lens of adjustable focal length
2-12-2	를 조절할 수 있는 얇은 렌즈와	and
2-13-0	상을 맺는 망막으로 단순화한다. 렌즈의 테두리가 동공이며 양쪽 매질은 공기다. 렌즈와 망막 사이 거리는	an image-forming retina. The lens edge is the pupil; air is on both sides. Lens-retina distance is
2-14-0	. 구멍이 렌즈의 결상에 미치는 영향은 다음과 같다. 기하광학에서 먼 물체가 보내는 광축에 평행한 빛은	. The hole affects imaging as follows. Geometrical optics focuses parallel light from a distant
2-15-0	렌즈의 초점에 모여 상을 이룬다. 렌즈 앞에 지름이	point at the lens focus. Placing a circular hole of diameter
2-15-1	인 원형 구멍을 두면 회절이 일어나,	before the lens causes diffraction.
2-16-0	초점의 스크린에 그림과 같은 회절 무늬가 생긴다. 밝은 중앙 원반 주위에는 점점 어두워지는	At the focus, the screen shows the illustrated diffraction pattern: a bright central disk surrounded
2-17-0	명암의 동심원들이 있다. 동심원들은 중앙 원반보다 훨씬 어두워 무시해도 된다. 중앙 원반의 반지름이	by alternating bright and dark rings of decreasing brightness. The rings are much fainter and can be ignored.
2-18-0	렌즈 중심에서 이루는 각	The disk's angular radius
2-18-1	는 구멍 지름	at the lens center depends on
2-18-2	에 따라 달라진다. 이론적으로	. Theory gives
2-19-0	여기서	Here
2-19-1	는 빛의 파장이다. 원반이 그림처럼 구멍을 통해 관찰한 점물체의 '상'이다. 위 식에서	is the wavelength. This disk is the point's image through the hole, as shown. Increasing
2-19-2	가 커질수록	makes
2-20-0	광점은 작아져 점에 가까운 선명한 상이 된다. 반대로	its image smaller, more point-like and sharper. Conversely, decreasing
2-20-1	가 작아지면 회절 광점이 커져 물체의	makes the diffraction spot larger and the
2-21-0	상이 흐려진다. 스크린이 초점 근처에 있으면 비슷한 회절 무늬가 생기며, 중앙 밝은 원반이 렌즈	image less clear. Near the focus the screen shows a similar pattern, and the central disk's
2-22-0	중심에서 이루는 각	angular radius
2-22-1	는 위 식으로 근사할 수 있다.	is approximately given by the same formula.
2-23-0	6.	6.
2-24-0	지구를 반지름	Treat Earth as a sphere of radius
2-24-1	의 구로 보자. 적도와 같은 평면에서 지표면 위로	. The equatorial annulus extending to over
2-24-2	천여 km인 원과 적도 사이의 고리 모양 영역에서 지구 자기장은	thousand kilometers above the surface has an approximately uniform
2-25-0	균일하다고 볼 수 있고, 그 세기는	geomagnetic field of flux density
2-25-1	이다. 대전된 우주선 입자의 정지 질량은	. A charged cosmic-ray particle has rest mass
2-26-0	이고, 전하량은	and charge
2-26-1	이다. 이 입자는 적도 위의 균일한 자기장 속에서 지구 중심을 중심으로 반지름	. In the uniform field above the equator it circles Earth's center with radius
2-27-0	인 원 궤도를 돈다.	.
2-28-0	상대론에서 입자에 작용하는 힘	In relativity, if the force
2-28-1	의 방향이 항상 속도	on the particle is always perpendicular to its velocity
2-28-2	에 수직이면, 입자의 질량	, the particle's mass
2-29-0	과 가속도	and acceleration
2-29-1	및 힘	still relate to force
2-29-2	의 관계는 여전히	by
2-29-3	이다. 여기서	, but
2-29-4	은 상대론적 질량이다. 다음을 구하여라.	is the relativistic mass. Find:
2-30-0	제	Page
2-30-1	쪽	of
2-30-2	/ 총	
2-30-3	쪽	
3-0-0	. 입자의 운동에너지를 구하여라.	. Find the particle's kinetic energy.
3-1-0	. 입자가 원 궤도를 도는 도중, 정지 질량이	. On its circular orbit, the particle collides with a stationary uncharged particle of rest mass
3-1-1	인 정지한 중성 입자에 흡수되어	and is absorbed to form
3-2-0	복합 입자가 된다. 복합 입자의 정지 질량을 구하여라:	one composite particle. Find its rest mass
3-3-0	제	Page
3-3-1	쪽	of
3-3-2	/ 총	
3-3-3	쪽	'''
translations={}
for line in text.splitlines():
 key,ko,en=line.split('\t');assert key not in translations;translations[key]=dict(ko=ko,en=en)
for page in data['pages'][:3]:
 n=page['source_page'];records=[];lines=[]
 for slot in page['slots']:
  key=slot['id']
  if slot.get('retain_native'):
   assert key not in translations,key;values=dict(ko='',en='')
  else:values=translations.pop(key)
  assert values['ko']or slot.get('retain_native')
  records.append(dict(source_slot=key,source=slot['source'],retain_original_native_punctuation=bool(slot.get('retain_native')),translations=values,source_size=slot['size'],source_baseline=slot['origin'][1]))
  lines.append(key+'\t'+values['ko']+'\t'+values['en'])
 out=B/f'authoring/native/page{n:02}.tsv';out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists();out.write_text('\n'.join(lines)+'\n','utf8')
 q=dict(source_sha256=data['source_sha256'],source_page=n,original_full_page_visually_read=True,original_math_and_figures_not_retyped=True,source_point_sizes_and_baselines_retained=True,translated_prose_only=True,source_physical_part='T',records=records,notes='Full original problem prose translated, with grammatical continuations across original rows. Original mathematical/numerical glyphs and punctuation remain native. English footer 共/page suffix semantics are expressed once by Page ... of ... . Original source footer total7 is retained; no invented missing problem3 curve plate.')
 out=out.with_name(f'page{n:02}-bilingual-prose.json');assert not out.exists();out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('CPHO2003_NATIVE_PROSE_AUTHORED',n,len(records),flush=True)
assert not translations,translations
