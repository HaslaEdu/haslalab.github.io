"""Concise whole-meaning prose at unchanged source points and baselines."""
from pathlib import Path
import json,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
changes=r'''1-3-0	개의 등질량 균질구 중,	equal-mass uniform spheres; set
1-3-1	개는 반지름	of radius
1-3-2	이고, 반지름	at rest in a hemisphere of radius
1-3-3	인 반구형 그릇에 정지해 있다.	,
1-4-0	중심은 같은 수평면에 있다. 나머지	Centers share a horizontal plane. A further
1-4-1	개는 반지름	of radius
1-4-2	이며,	sits atop the
1-4-3	개 위에 놓는다. 이때	. For what
1-4-4	에 관한	value
1-5-0	조건을 구하여라: 모든 접촉면이 매끄러울 때 아래 공들이 서로 떨어지는 조건이다.	do the lower spheres separate? All contacts are smooth.
1-9-0	~	launches a probe of mass
1-9-1	~	forward; Earth's gravity gives a hyperbolic orbit.
1-10-0	초점은 지구 중심이고, 실반경은 원래 원지점 거리와 같다. 발사 때 탐사선에	Its focus is Earth. Its semi-transverse axis equals the original apogee distance. Find
1-11-0	~	the launch energy. Known: Earth's mass
1-11-1	~	and
1-11-2	~	; ignore other celestial bodies.
1-13-0	그림의 금속 플라이휠은	The metal wheel shown has
1-13-1	개의 살이 있다. 길이는	spokes of length
1-13-2	이며, 축	and rotates about
1-13-3	주위로 돈다. 균일한 자기장	in a uniform magnetic field.
1-14-0	은 축과 평행하고 세기는	Field is axial, flux density
1-14-1	이다. 축과 테두리를 브러시로	. Brushes link axle and rim to
1-14-2	과 코일	and
1-14-3	에 연결해 폐회로를 이룬다.	in a closed circuit.
1-15-0	휠과 축의 저항 및 회전 마찰은 무시한다.	Ignore wheel/axle resistance and rotational friction.
1-18-1	정상 상태에서 돌림힘	At steady speed remove torque
1-18-2	~	; speed
1-18-3	~	and current in
1-18-5	~	then vary with time.
1-19-0	~	Different
1-19-1	~	values give different speed curves
1-20-0	제시된 각속도	The supplied
1-20-2	~	plots number
1-20-3	개다. 돌림힘	. Take removal of
1-20-4	~	as the start:
1-20-5	으로 삼았다.	,
1-21-0	이때 각속도는	Initially
1-21-1	~	and
1-21-2	이다. 각속도	. The
1-21-3	그래프와 전류	and
1-21-4	그래프들의 각 세로축 단위는	plots each share a vertical scale;
1-22-0	~	all time scales agree. Choose physically possible angular-speed
1-24-0	이에 대응하는 전류	and the closest correct current
1-24-1	~	curve
1-24-3	~	. Link each chosen
1-24-5	와 대응 전류	with its matching
1-26-0	주의: 모두 맞으면 만점, 일부만 맞으면 부분 점수, 하나라도 틀리면 0점이다.	All links correct: full credit. Incomplete correct links: partial credit. Any wrong link: zero.
1-28-0	그림에서	As shown, right of
1-28-1	축 오른쪽은	the uniform field is
1-28-2	의 균일 자기장,	; left of
1-28-3	축 왼쪽은	it is
1-28-4	의 균일 자기장이다. 양쪽 장	. Both fields
2-0-0	~	point inward. At
2-0-1	~	, a positive particle has charge
2-0-2	~	and mass
2-0-3	인	.
2-1-0	입자	Particle
2-1-1	는	at
2-1-2	에 속력	has speed
2-1-3	으로 양의	along positive
2-1-4	축으로 출발한다. 입자	. After
2-1-5	~	starts,
2-2-0	~	Like
2-2-1	~	in mass and charge,
2-2-2	~	leaves
2-2-3	~	at
2-2-4	~	along negative
2-3-0	운동 중 두 입자	For
2-3-2	가 만나도록 출발시킨다.	to meet, find the least difference between their
2-4-0	출발 시각 차이의 최솟값과 만남 좌표를 구하여라. 자기장 영역은	launch times and the corresponding meeting coordinates. Assume
2-5-0	진공이다. 중력 및 두 입자	the whole field is vacuum; ignore gravity and interaction between
2-5-2	사이의 힘은 무시한다.	.
2-7-0	근시안이 안경 없이 뚜렷이 보는 거리는	Unaided, a myopic eye sees clearly only within
2-7-1	이내이다. 눈 앞에 작은 원형 구멍이 난	. Holding a card near the eye,
2-8-0	~	he sees distant objects more clearly through its small circular hole, without glasses.
2-9-0	. 구멍 지름이	. A hole has diameter
2-9-1	일 때, 근시안이 먼 점광원을 볼 때 망막에 생기는 광점 지름을	. Find the retinal spot diameter for a distant point source,
2-10-0	기하광학으로 구하여라.	viewed directly by the myopic eye, using geometrical optics.
2-11-0	~	. Include diffraction; find optimum hole diameter. Use mean visible wavelength
2-12-1	~	. Model the complex eye as a thin lens of adjustable focal length
2-13-0	상 맺는 망막으로 본다. 동공은 렌즈 테두리, 양쪽은 공기다. 렌즈와 망막 간격은	an imaging retina. The lens rim is the pupil; air on both sides, retina-lens spacing
2-14-0	. 구멍의 결상 영향은 다음과 같다. 기하광학에서 먼 점이 보낸 광축 평행광은	. The hole's effect: geometrical optics focuses distant-point light parallel to the axis
2-15-0	~	at the lens focus. A circular aperture of diameter
2-15-1	~	placed before the lens diffracts light.
2-16-0	~	At the focus the pattern shown appears: a bright central disk surrounded
2-17-0	명암의 동심원이 있다. 원반보다 훨씬 어두워 관찰할 때 무시해도 된다. 중앙 원반의 반지름이	by fading concentric bright/dark rings. Being much fainter, these may be ignored.
2-19-0	여기서	where
2-19-1	는 파장이다. 그림의 원반은 구멍으로 본 점물체의 상이다. 위 식에서	is wavelength. The shown disk is the point image through the hole. Larger
2-19-2	가 커지면	gives
2-20-0	~	a smaller, sharper, more point-like image. Smaller
2-20-1	~	gives a larger diffraction spot and a
2-24-0	지구는 반지름	Spherical Earth has radius
2-24-1	의 구다. 적도면에서 고도	. In the equatorial annulus, to over
2-24-2	천여 km의 원과 적도 사이 고리의 자기장은	thousand km altitude,
2-25-1	~	. A charged cosmic particle has rest mass
2-26-0	이며 전하는	; charge
2-26-1	이다. 적도 위 균일장에서 원 궤도 반지름은	. In the equatorial uniform field, its orbit radius is
2-27-0	이며 지구 중심 주위를 돈다.	. The circle is centered on Earth.
2-28-0	~	In relativity, when force
2-28-1	~	always acts perpendicular to velocity
2-28-2	~	, mass
2-29-4	은 상대론적 질량이다. 질문:	~
3-1-0	~	. On its circle it hits an uncharged stationary particle of rest mass
3-1-1	~	.
3-2-0	~	Absorption forms a composite. Find its rest mass'''
updates={}
for line in changes.splitlines():
 key,ko,en=line.split('\t');assert key not in updates;updates[key]=dict(ko=ko,en=en)
history=B/'authoring/native/history-before-concise-v2';assert not history.exists();history.mkdir()
for n in [1,2,3]:
 j=B/f'authoring/native/page{n:02}-bilingual-prose.json';t=j.with_name(f'page{n:02}.tsv');shutil.copy2(j,history/j.name);shutil.copy2(t,history/t.name);q=json.loads(j.read_text('utf8'))
 for row in q['records']:
  changes=updates.pop(row['source_slot'],None)
  if changes:
   for lang,value in changes.items():
    if value!='~':row['translations'][lang]=value
 q['notes']+=' Concise v2 keeps every source condition while moving grammatical clause continuations only among existing adjacent prose baselines; original mathematical/numerical atoms never change y or point size.'
 j.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');t.write_text('\n'.join(r['source_slot']+'\t'+r['translations']['ko']+'\t'+r['translations']['en']for r in q['records'])+'\n','utf8')
assert not updates
