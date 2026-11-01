from pathlib import Path
import json
P=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring');path=P/'plans/page06-draft-layout.json';q=json.loads(path.read_text('utf8'));by={r['id']:r for r in q['rows']}
a=next(a for a in by['ion-sound-scale']['atoms']if a['id']=='ion-scale');a['rect'][0]=119.5
by['footer']['baseline']=783.0
by['footer']['source_baseline_evidence']=json.loads((P/'page06-footer-source-calibration.json').read_text('utf8'))
q['root_final_source_contact_corrections']=['Expanded source k^2 kBTe/mi left edge to119.5: full original k connected component extends to120.0 and was .25pt outside the preceding crop; no resampling or mathematical motion in y.','Footer point8.4 retained; median of three independently measured original SimSun glyph baselines783.25/783.0/782.75 used (783.0). Original two numeric6 bitmap y positions kept.']
q['status']='MANUALLY_REVIEWED_PLAN_PENDING_FINAL_PROOF_QA'
path.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
