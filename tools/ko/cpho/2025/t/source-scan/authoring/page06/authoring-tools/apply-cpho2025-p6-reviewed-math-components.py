from pathlib import Path
import json,math
P=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring');path=P/'plans/page06-draft-layout.json';q=json.loads(path.read_text('utf8'));data={x['key']:x for x in json.loads((P/'component-bounds.json').read_text('utf8'))}
# Component identifiers were manually checked on six annotated source contact
# sheets, including every disconnected subscript, fraction bar and prime.
selected={
'debye-value/lambda':[3,5], 'quasineutral-scale/lambda1':[2,5], 'quasineutral-scale/lambda2':[3,5], 'ion-flow-equilibrium/vi':[3,4],
'gradient-frequency/gradient':[1,4,5,6,7,8,9], 'gradient-frequency/omega0':[1,2,4,5,7,8,9], 'gradient-frequency/wpe':[3,5,6], 'gradient-frequency/wpe-definition':[1,2,3,4,5,8,10,11,12,13], 'gradient-frequency/wce-definition':[1,2,6,7,8], 'gradient-frequency/w0':[2,3], 'gradient-frequency/ratio':[1,2,6,8],
'density-estimate/freq':[1,2,4,5,6,8,9,10,12,13,14], 'density-estimate/B':[2,3,4,5,7,8], 'density-estimate/ratio':[1,2,5,7],
'small-perturbation/exp':[2,3,5,6,7,8,9,11,12,13,14,15,16,17], 'small-perturbation/omega':[3],
'dispersion-variables/omega':[2], 'dispersion-variables/lambda':[2,3,4], 'dispersion-variables/kb':[3,4],
'ion-sound-scale/omega':[1,5], 'ion-sound-scale/ion-scale':[1,2,3,4,5,7,8,9,10], 'ion-sound-scale/Te':[2,5], 'ion-sound-scale/Ti':[3,4], 'ion-sound-scale/dispersion':[1,3,5,6,7,8,9,10,11],
'electron-scale/omega':[1,4], 'electron-scale/electron-scale':[1,2,3,4,5,7,9], 'electron-scale/Te':[2,4], 'electron-scale/Ti':[3,5,6],
'group-velocity/vg':[3,4], 'group-velocity/wpe':[1,4,5,6], 'boltzmann-electrons/poisson':[1,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18], 'quasineutral-dispersion/dispersion':[1,2,3,4,5,6,7,8,10],
'classical-ion-sound/relation':[1,2,3,4,5,6,7,8,9,10,11,12,14,15,16,17,18,21,23,24,26,27,28]
}
caps={'gradient-frequency/gradient':(132.75,None,None,None),'gradient-frequency/ratio':(512.25,None,525.5,None),'density-estimate/ratio':(394.75,None,409,None),'ion-sound-scale/ion-scale':(None,None,153.25,None),'electron-scale/electron-scale':(None,None,153.5,None)}
records=[]
for row in q['rows']:
 for atom in row['atoms']:
  key=row['id']+'/'+atom['id']
  if key not in selected:continue
  cc=[c for c in data[key]['components']if c['id']in selected[key]]
  if len(cc)!=len(selected[key]):raise ValueError(key)
  rect=[math.floor((min(c['rect'][j]for c in cc)-.5)*4)/4 for j in [0,1]]+[math.ceil((max(c['rect'][j]for c in cc)+.5)*4)/4 for j in [2,3]]
  for i,cap in enumerate(caps.get(key,())):
   if cap is not None:rect[i]=cap
  for c in cc:
   if any(c['rect'][i]<rect[i] for i in [0,1])or any(c['rect'][i]>rect[i]for i in [2,3]):raise ValueError(('Full original mathematical component clipped',key,c,rect))
  records.append(dict(key=key,old_rect=atom['rect'],reviewed_rect=rect,manually_reviewed_original_math_components=cc,excluded_components=[c for c in data[key]['components']if c['id']not in selected[key]],source_contact_review='cc-sheet-1.png through cc-sheet-6.png, original 4x scan. No OCR redraw or changes to source JPEG, CTM, original y or 1x scale.'))
  atom['rect']=rect;atom['component_review']=records[-1]
q['root_reviewed_math_component_records']=records
path.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8');print('Reviewed whole original mathematical component groups',len(records))
