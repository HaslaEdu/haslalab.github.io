from pathlib import Path
import json
P=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring');path=P/'plans/page06-draft-layout.json';q=json.loads(path.read_text('utf8'));by={r['id']:r for r in q['rows']}
text={
'debye-given':('[[label]] 값: [[given]]','[[label]] Use [[given]]'),
'quasineutral-scale':('[[label]] 데바이 차폐에 따른 전하 분리는 [[lambda1]] 규모에만 있다. [[lambda2]]보다 훨씬 큰 규모의 플라스마는','[[label]] Debye charge separation occurs only on scale [[lambda1]]. At scales far above [[lambda2]], plasma is'),
'ion-flow-equilibrium':('준중성이다. 단, 이온의 거시 속도 [[vi]]와 외부 자기장 [[B]]가 영이 아니면, 압력을 무시한 이온의','quasineutral. Nonzero ion bulk [[vi]] and field [[B]] require a nonzero equilibrium electric field'),
'equilibrium-electric-field':('힘 평형에는 영이 아닌 평형 전기장이 필요하여 [[delta]]다. [[E]]의 기울기 길이는 [[L]]이다. [[x]] 방향으로 분포가','when pressure is ignored, giving [[delta]]. Let [[L]] be the gradient scale of [[E]]; for variation along [[x]],'),
'gradient-frequency':('불균일하면 [[gradient]]다. 특성 각진동수는 [[omega0]]다. [[wpe]]([[wpe-definition]]), [[wce]]([[wce-definition]])와 [[w0]]로 [[ratio]]을','the scale is [[gradient]]. The characteristic frequency is [[omega0]]. Use [[wpe]] ([[wpe-definition]]), [[wce]] ([[wce-definition]]) and [[w0]] to estimate [[ratio]]'),
'density-estimate':('근사하라. 특성 진동수 [[freq]], 자기장 [[B]], [[n0]]일 때 [[ratio]]의 수치를 어림하라.','approximately. For [[freq]], [[B]] and [[n0]], estimate [[ratio]] numerically.'),
'waves-intro':('[[label]] 전자와 이온의 큰 질량 차이로 플라스마 파동은 다양하고 복잡하다. 초저주파 음파부터','[[label]] Electron/ion mass disparity makes plasma waves diverse and complex, from infrasound'),
'acoustic-waves':('초고주파 전자기파까지 관측된다. 여기서는 음파 범위의 파동을 다룬다. 자기장이 없을 때 각 성분은','to ultrahigh-frequency EM waves. Consider acoustic waves. With no magnetic field, each species'),
'wave-equations-intro':('문항 [[one]]의 운동량 방정식 외에 다음 연립방정식도 만족한다.','obeys the momentum equation in part [[one]] and the following system:'),
'polytropic-index':('[[gamma]]는 다방 지수다. 평형 플라스마가 자유 공간에 균일하게 분포하며 거시적 흐름은 없다고 하자.','[[gamma]]: polytropic index. Equilibrium is uniform in free space, with no bulk flow.'),
'small-perturbation':('[[exp]] 꼴의 작은 섭동에 대해 일차 항만 남겨 위 식에서 [[omega]]와 [[k]]의 일반 관계를 구하라.','For small perturbations [[exp]], retain first-order terms to relate [[omega]] and [[k]].'),
'dispersion-variables':('관계식은 [[omega]], [[k]], [[gamma]], [[m]], [[T]], [[lambda]], [[kb]]로 나타내라. 모든 섭동량의 아래 첨자는 [[one]], 섭동 전 값은 [[zero]]이다.','Use [[omega]], [[k]], [[gamma]], [[m]], [[T]], [[lambda]], [[kb]]; subscripts [[one]] = perturbed, [[zero]] = unperturbed.'),
'ion-sound-scale':('[[label]] [[omega]]와 [[ion-scale]]가 같은 크기이고 [[Te]]와 [[Ti]]도 같은 크기일 때, 문항 [[four]]에서 [[dispersion]]의','[[label]] For [[omega]] of order [[ion-scale]] and comparable [[Te]], [[Ti]], use part [[four]] to simplify [[dispersion]]'),
'ion-sound-leading':('근사식, 즉 분산 관계를 구하라(선도항만 남긴다). 이 관계가 고전적 이온 음파의 분산 관계인','to leading order. When does this dispersion relation reduce to the classical ion-acoustic result'),
'electron-scale':('[[label]] [[omega]]와 [[electron-scale]]가 같은 크기이고 [[Te]]와 [[Ti]]도 같은 크기일 때, 문항 [[four]]는 어떤 근사 분산','[[label]] For [[omega]] of order [[electron-scale]], with comparable [[Te]], [[Ti]], how does part [[four]] simplify'),
'group-velocity':('관계를 주는가(선도항만 남긴다)? 파동의 군속도 [[vg]]를 [[wpe]]와 다른 주어진 양으로 나타내라.','to leading order? Also find group velocity [[vg]] using [[wpe]] and other known quantities.'),
'boltzmann-electrons':('[[label]] 약결합 조건의 볼츠만 분포를 전자에 가정하자. 문항 [[four]]의 [[poisson]]을 준중성 조건으로','[[label]] Electrons are Boltzmann-distributed at weak coupling. Replace [[poisson]] in part [[four]] by'),
'quasineutral-dispersion':('[[neutral]] 대체하라. 이온 방정식은 그대로 두고 이온 음파의 분산 관계 [[dispersion]]을 구하라. 이를 고전적 이온 음파의','[[neutral]]; keep ion equations unchanged. Derive ion-acoustic dispersion [[dispersion]] and recover it')
}
for id,(ko,en)in text.items():by[id]['ko']=ko;by[id]['en']=en
old=by['acoustic-waves'];one=next((a for a in old['atoms']if a['id']=='one'),None)
if one:old['atoms'].remove(one);by['wave-equations-intro']['atoms'].append(one)
for r in q['rows']:r['source_atom_ids']=[a['id']for a in r['atoms']]
g=next(a for a in by['debye-given']['atoms']if a['id']=='given');g.update(fixed_original_x=True,fixed_x_evidence='One original scalar e=1.602 x10^-19 C crosses the printed line break. Its two source bitmap parts must retain the same x translation (zero), original y and 1x scale. Short given-value prose meets the unchanged original numeric block within one em.')
q['linked_original_math_dx']={'debye-value/continuation':'debye-given/given'}
q['linked_original_math_dx_evidence']='The electron-charge numeric value is printed across two physical lines. Keep both original source parts at identical dx=0, unchanged native y and scale.'
path.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
