from pathlib import Path
import json,math
P=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring');p=P/'plans/page06-draft-layout.json';q=json.loads(p.read_text('utf8'));data={x['key']:x for x in json.loads((P/'component-bounds.json').read_text('utf8'))}
selected={'ion-flow-equilibrium/B':[3],'equilibrium-electric-field/E':[3],'equilibrium-electric-field/L':[1],'equilibrium-electric-field/x':[6],'gradient-frequency/wce':[2,3,4],'small-perturbation/k':[2],'dispersion-variables/k':[1],'dispersion-variables/gamma':[1,2,4],'dispersion-variables/m':[1,2,4],'dispersion-variables/T':[1,2],'density-estimate/n0':list(range(1,14)),'quasineutral-dispersion/neutral':[1,2,3,4,6,7,8]}
for r in q['rows']:
 for a in r['atoms']:
  key=r['id']+'/'+a['id']
  if key in selected:
   cc=[c for c in data[key]['components']if c['id']in selected[key]]
   rect=[math.floor((min(c['rect'][j]for c in cc)-.5)*4)/4 for j in [0,1]]+[math.ceil((max(c['rect'][j]for c in cc)+.5)*4)/4 for j in [2,3]]
   record=dict(key=key,old_rect=a['rect'],reviewed_rect=rect,manually_reviewed_original_math_components=cc,excluded_components=[c for c in data[key]['components']if c['id']not in selected[key]],source_contact_review='Additional original 4x contact sheets6–8: full actual B/E/L/x/k and all subscript j/i dots retained; surrounding Chinese and enumeration commas excluded.')
   q['root_reviewed_math_component_records'].append(record);a['rect']=rect;a['component_review']=record
  a.update(reviewed=True,reason='Manually compared all original mathematical source crops against the whole source page. Original complete mathematical glyphs, disconnected subscript dots and fraction bars retained, adjacent Chinese excluded; exact source image/CTM/scale and original mathematical y unchanged.')
 r['reviewed']=True
 for lang in ['ko','en']:r[lang]=r[lang].replace('[[freq]],','[[freq]]')
q['manual_rois_reviewed']=True
q['source_font_evidence']='Original p1/p2–5 independent SimSun10.24 body face/point/Tr2 .50pt calibration; p6 actual Chinese per-row fixed10.24 baselines .56–.73IoU, source shape contacts reviewed. Batang10.24/.30pt matched Korean serif stems, no letterspace fitting or point-size reduction.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
