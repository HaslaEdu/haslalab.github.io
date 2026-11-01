"""Reviewed wording revisions; same point size, no shrinking or clipping."""
from pathlib import Path
import json
BASE=Path(__file__).resolve().parents[1]
EDITS={1:{
0:dict(EN="{m0}st Chinese Physics Olympiad: Final Theory Paper"),
28:dict(EN="{m79}. Thread these {m80} beads in order on a smooth, level, closed, large fixed rigid circular ring."),
29:dict(EN="Neighbors ({m81}, {m82} included) share identical light springs of constant {m83}, in static equilibrium.")},2:{
1:dict(EN="{m1}) Fix bead {m2}; others slide frictionlessly. Find all eigenfrequencies of {m3} for small"),
2:dict(EN="oscillations, {m4}; for modes of frequency {m5}, derive {m6}{m7}) (no {m8} in either result)."),
3:dict(EN="{m9}) Free bead {m10} and set its mass to {m11}. Some eigenfrequencies {m12} are wholly"),
4:dict(EN="independent of {m13}. For small oscillations of {m14}, find all {m15}-independent {m16}; for {m17} modes, give"),
6:dict(EN="3. ({m21} points) Use complex form; e.g. write a field component at propagation distance {m22} and time {m23}"),
9:dict(EN="Part I: Optical elements in matrix form."),
10:dict(EN="{m36}) The {m38} (or {m39}"),
11:dict(KO="그림 {m40}처럼 입사광은 반투과·반사 분할기에서",EN="interferometer is in Fig. {m40}. Light passes a"),
12:dict(KO="나뉘어 위·아래 두 전반사 거울을 거친다.",EN="half-reflecting, half-transmitting splitter and"),
13:dict(KO="위 경로는 {m41}, 아래는 {m42}로 향한다. 다시 같은",EN="two full mirrors: upper path to {m41}, lower to {m42}."),
14:dict(KO="반투과·반사 분할기를 거쳐 간섭한다. 광로를",EN="They interfere at an identical second splitter."),
15:dict(KO="조절해 두 번째 분할기 밑 검출 강도를 0으로 하자.",EN="Null its lower detector by tuning the paths."),
16:dict(KO="입사 에너지는 어디로 가나? 그려 간단히 설명하라.",EN="Where is input energy? Sketch; explain briefly."),
17:dict(KO="{m43}) 그림 {m44}의 장치로 분할기의 반사·투과계수",EN="{m43}) Fig. {m44} relates the reflection and"),
18:dict(EN="Fig. {m45}: Mach{m46}Zehnder interferometer (part)"),
19:dict(KO="관계를 연구한다. 모든 편광에 대해 이 분할기는",EN="transmission coefficients. For all polarizations,"),
20:dict(EN="it is a {m47} beam splitter; reflection {m48} and transmission {m49}{m50} have magnitudes satisfying"),
23:dict(KO="{m52}) 그림 {m53}은 {m54} 편광의 양의 방향이다. {m55}에서 {m56}는 전파방향, {m57}는 오른손 직교계이다.",EN="{m52}) Fig. {m53}: positive {m54} pol. directions. In {m55}, {m56}: propagation; {m57}: right-handed,"),
24:dict(EN="orthogonal. {m58} is horizontal {m59} vertical {m60}. Fig. {m61} shows"),
25:dict(EN="incident/reflected/transmitted {m62}. For reflection: {m63}"),
26:dict(EN="{m64} are propagation and positive {m65} directions. Reflected"),
27:dict(KO="반사광의 {m66} 성분을 입사광의 {m67} 성분으로 다음과 같이 쓴다.",EN="{m66} components use incident {m67} components as follows:"),
30:dict(KO="{m78} 행렬을 분할기의 반사행렬이라",EN="This {m78} is the reflection"),
31:dict(KO="한다. 다른 경우도 같다. {m79} 및 {m80}의",EN="matrix; likewise elsewhere. {m79}, {m80}"),
32:dict(KO="반사계수가 각각 {m81}{m82}와",EN="reflect with {m81}{m82} and"),
33:dict(EN="{m83}{m84}. Find matrices"),
34:dict(EN="{m85}{m86} and {m87}{m88} explicitly, using"),
35:dict(EN="given quantities and constants."),
37:dict(KO="{m94}) 그림 {m95} 전반사 거울의",EN="{m94}) Fig. {m95}: a full mirror. Find"),
39:dict(KO="반사행렬 {m97}{m98}를 써라{m126}",EN="its reflection matrix {m97}{m98}{m126}"),
40:dict(EN="{m99}) For a {m100} waveplate, fast-axis phase leads slow by {m101}. In Fig. {m102}, its fast axis lies"),
},3:{
1:dict(EN="{m14}) Fig. {m18}: linear polarizers along {m15}, {m16}, and {m17}. Give their matrices:"),
4:dict(EN="An interferometer reads phase changes from"),
5:dict(EN="intensity changes. Usual ones, e.g. Michelson,"),
6:dict(EN="give only the magnitude of {m20}, not its sign."),
9:dict(KO="4사분면 간섭계로, {m23} 검출기의 간섭"),
11:dict(KO="레이저는 종이에 수직인 투과축의 선편광판을",EN="Laser passes a linear polarizer with axis"),
12:dict(EN="normal to the page {m26}, then full mirror {m27},"),
10:dict(EN="fix {m24} from only interference intensity ({m25}"),
14:dict(EN="splitter {m29} splits into paths {m30},{m31}; path {m32}: full mirror {m33}."),
16:dict(KO="{m36}에서 다시 나뉘어 편광판 {m37}를 거쳐 검출기 {m38}, 편광판 {m39}를 거쳐 검출기 {m40}로 간다. 광로 {m41}는"),
17:dict(EN="reflects at mirrors {m42}, {m43}, passes a {m44} linear polarizer, then splitter {m45}, to detectors"),
19:dict(KO="{m47}) 분할기 {m48} 앞 레이저 진폭은 {m49}이다. 뒤의 세 양은 각각 분할기 {m50}에서 광로 {m51}를 따라",EN="{m47}) Before splitter {m48}: amplitude {m49}. Last 3: optical paths from splitter {m50} via {m51} to"),
20:dict(EN="splitter {m52}, and the vacuum wave number. Give interference terms in intensities at detectors {m53}, {m54}:"),
21:dict(KO="{m55}(간섭항: 두 광로가 함께 있을 때 강도에서 각 광로만의 강도의 합을 뺀 값).",EN="{m55} (interference = both-path intensity minus the sum of the separate-path intensities)."),
25:dict(EN="4. ({m63} points) Model a ridden two-wheel balancer on rigid, rough level ground."),
37:dict(EN="free to turn independently about the axle; their masses are negligible."),
39:dict(EN="stays in the axle's vertical plane at fixed inward tilt {m80}. Rear view: Fig. {m81}."),
42:dict(KO="{m84}) 지면이 왼쪽·오른쪽 바퀴에 주는 수직항력 크기 {m85}({m86} 없이).",EN="{m84}) ground normal forces on left/right wheels {m85} (no {m86})."),
},4:{
0:dict(KO="아래 ({m0})에서 막대는 차축에 수직인 평면에서 움직이고, 두 바퀴는 차축과",EN="In ({m0}), the rod moves in an axle-normal plane; the wheels are rigidly"),
3:dict(KO="전방 기울기가 {m3}일 때, {m4}를 고정할 엔진의 차축 돌림힘을 {m5}라 하자{m91}",EN="tilt forward by {m3}; to keep {m4} fixed, the engine must apply axle torque {m5}{m91}"),
6:dict(EN="{m10}) For small oscillations, engine torque {m11} follows the function in ({m12}),"),
11:dict(EN="5. ({m23} points) A spherically symmetric star has radius {m24}, total mass {m25}, center {m26}{m92}"),
12:dict(EN="It contains only neutral or ionized atoms (atomic matter) and radiation (photon gas)."),
13:dict(EN="The gravitational constant is {m27}{m93}"),
16:dict(EN="pressure {m32}, density {m33}, mass inside radius {m34}: {m35}. In equilibrium, {m36} and"),
17:dict(EN="{m37} obey which differential equations?"),
20:dict(EN="{m44}) Find the star's own gravitational potential energy as an integral of {m45}."),
21:dict(EN="Set zero potential when all matter is pulled spherically symmetrically to infinity."),
23:dict(KO="{m49}는 단열지수이다. {m50}이고 {m51}가 {m52}와 무관할 때만 보자. 별이 해체되지 않으려면 {m53}의 조건은 무엇인가?",EN="{m49}: adiabatic index; take {m50}, {m51} independent of {m52}. What must {m53} obey to prevent breakup?"),
25:dict(KO="{m55}) 광자 기체는 어디서나 국소 열평형이라 하자. 광자의 에너지에서 내부에너지가, 복사압에서 압력이",EN="{m55}) The photon gas is everywhere in local thermal equilibrium. Its internal energy comes"),
26:dict(EN="from photon energy; its pressure is photon radiation pressure. Find its adiabatic index {m56}{m94}"),
27:dict(KO="{m57}) 원자 물질은 광자를 흡수한다. 복사가 두께 {m58}, 밀도 {m59}인 얇은 층을 지나면 광자 일부가 흡수되며 그",EN="{m57}) Atomic matter absorbs photons. A thin layer of thickness {m58}, density {m59}, absorbs the fraction"),
29:dict(EN="Absorption pushes matter, so photon pressures differ. Over the whole sphere about {m63}, radius {m64},"),
30:dict(EN="outward power (luminosity): {m65}. For {m66}, with {m67} and"),
31:dict(EN="relevant constants, give the differential equation for temperature."),
32:dict(EN="{m68}) Atomic partial pressure falls with {m69}. Bound the surface luminosity {m70} from above using"),
},5:{
0:dict(EN="6{m0} pts) Quantum displacement/momentum: {m1}{m2} ("),
1:dict(KO="{m3}는 입자 변위 {m4}, 운동량 {m5}의 불확정도이고, {m6}는",EN="{m3}: particle {m4}, {m5} uncertainties; {m6} is reduced"),
2:dict(KO="환산 플랑크 상수, {m7}는 플랑크 상수다), 조화진동자의 변위",EN="Planck constant, {m7} unreduced). Harmonic oscillators'"),
3:dict(KO="{m8}와 운동량 {m9}는 동시에 0일 수 없어 바닥상태 에너지도 0일",EN="{m8}, {m9} cannot both vanish, so ground energy is nonzero."),
4:dict(KO="수 없다. 같은 이유로 진공 양자 전자기장 최저상태(광자가",EN="Likewise, the quantum electromagnetic field's lowest"),
5:dict(EN="state (no photons) has nonzero vacuum energy. Thus two"),
6:dict(EN="parallel uncharged conductor plates, spaced in vacuum,||[5-6-1|Fig.] {m10}"),
7:dict(KO="흥미롭게도 0이 아닌 전자기 상호작용력이 생긴다.",EN="feel a nonzero electromagnetic interaction force."),
8:dict(KO="힘의 기원을 간단히 모형화하자. 전자기파는 1차원 공간에서 전파하며 편광 모드는 하나만 둔다."),
11:dict(KO="{m17}) {m18} 사이의 진공 전자기파는 판 표면이 마디인 정상파이다. {m19} 사이에서 허용되는"),
13:dict(EN="{m21}) A quantum harmonic oscillator (angular frequency {m22}) has ground energy {m23}{m24}. A vacuum mode at {m25}"),
14:dict(KO="전자기파 한 모드의 진공 장 영점에너지도 {m26}{m27}이다. {m28} 사이의 진공 전자기장 총에너지"),
17:dict(KO="{m31}) 자연의 실제 힘은 늘 유한하다. 결과가 발산한 까닭은 가정이 지나치게 단순하기 때문이다. 예로,"),
18:dict(KO="실제 도체판은 이상 도체가 아니다. 충분히 높은 진동수의 파는 박판을 지나 정상파 조건과 무관해진다."),
19:dict(KO="고진동수 모드는 판 위치에 거의 영향받지 않아 구하려는 힘에 기여하지 않는다. 이를 반영하는 방법으로"),
23:dict(KO="{m41}) ({m42})에서는 특정 지수함수로 고진동수 파의 기여를 억제하여 유한한 힘을 얻었지만, 힘의 크기는"),
24:dict(KO="함수의 구체적 형태와 무관하다. 더 일반적인 함수 {m43}에는 다음 두"),
25:dict(KO="조건만 요구하자:"),
}}

def apply():
    changes=[]
    for page,updates in EDITS.items():
        path=BASE/f'authoring/T/page{page:02}.natural.tsv'
        lines=[q.split('\t')for q in path.read_text('utf8').splitlines()if q]
        for cells in lines:
            row=int(cells[0])
            for lang,value in updates.get(row,{}).items():
                index=1 if lang=='KO'else 2
                if cells[index]!=value:changes.append(dict(page=page,row=row,language=lang,before=cells[index],after=value));cells[index]=value
        path.write_text('\n'.join('\t'.join(q)for q in lines)+'\n','utf8')
    log=BASE/'authoring/translation-revision-history.json'
    history=json.loads(log.read_text('utf8'))if log.exists()else[]
    if changes:log.write_text(json.dumps(history+changes,ensure_ascii=False,indent=1),'utf8')
    print(len(changes),'reviewed wording changes')
if __name__=='__main__':apply()
