from pathlib import Path
import json
p=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring/plans/page06-draft-layout.json');q=json.loads(p.read_text('utf8'));by={r['id']:r for r in q['rows']}
by['ion-flow-equilibrium']['ko']='준중성이다. 단, 이온의 거시 속도 [[vi]]와 외부 자기장 [[B]]가 영이 아니면 압력을 무시한 힘 평형에 따라'
by['equilibrium-electric-field']['ko']='평형 전기장은 영이 아니며 [[delta]]다. [[E]]의 기울기 길이는 [[L]]이다. [[x]] 방향으로 불균일하면'
by['gradient-frequency']['ko']='[[gradient]]다. 특성 각진동수는 [[omega0]]다. [[wpe]]([[wpe-definition]]), [[wce]]([[wce-definition]])와 [[w0]]로 [[ratio]]을'
by['ion-flow-equilibrium']['en']='quasineutral. With nonzero ion bulk [[vi]] and field [[B]], force balance (no pressure)'
by['equilibrium-electric-field']['en']='needs nonzero equilibrium [[E]], hence [[delta]]. Its gradient scale is [[L]]; along [[x]],'
by['gradient-frequency']['en']='scale [[gradient]], angular frequency [[omega0]]. Express [[ratio]] via [[wpe]] ([[wpe-definition]]), [[wce]] ([[wce-definition]]), [[w0]]'
by['boltzmann-electrons']['en']='[[label]] Assume Boltzmann electrons at weak coupling. Replace [[poisson]] in part [[four]] by'
by['quasineutral-dispersion']['ko']='[[neutral]] 대체하라. 이온 방정식은 그대로 두고 이온 음파의 분산 관계 [[dispersion]]을 구하라.'
by['classical-limit']['ko']='이를 고전적 이온 음파의 분산 관계(문항 [[five]])에서 얻는 방법을 설명하라.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
