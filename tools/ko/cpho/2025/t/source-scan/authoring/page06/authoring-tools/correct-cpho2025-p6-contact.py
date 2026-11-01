from pathlib import Path
import json
P=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring');path=P/'plans/page06-draft-layout.json';q=json.loads(path.read_text('utf8'));by={r['id']:r for r in q['rows']}
rects={
 'debye-value/lambda':[198.75,104,211.5,116.75],
 'quasineutral-scale/lambda1':[322.25,119.5,334.75,134], 'quasineutral-scale/lambda2':[435,119.5,447.75,134],
 'ion-flow-equilibrium/vi':[201.5,135.5,215,150.75], 'ion-flow-equilibrium/B':[254.5,135.5,263.5,149],
 'equilibrium-electric-field/delta':[177.5,151,255.25,165], 'equilibrium-electric-field/E':[325,151,333,165], 'equilibrium-electric-field/L':[394,150,402,165], 'equilibrium-electric-field/x':[459,152,466,165],
 'gradient-frequency/gradient':[130.5,170.5,163.75,200], 'gradient-frequency/omega0':[284,175,319.25,194.5],
 'gradient-frequency/wpe':[336,179.5,356,194], 'gradient-frequency/wpe-definition':[372,168,412,203], 'gradient-frequency/wce':[422,180,441,195], 'gradient-frequency/wce-definition':[453.5,174,472.75,201.5], 'gradient-frequency/w0':[493,180,505,194], 'gradient-frequency/ratio':[511,173,526,200],
 'density-estimate/freq':[162.5,203,218.5,229.5], 'density-estimate/B':[242,210,278,224], 'density-estimate/n0':[285.5,207,367,225], 'density-estimate/ratio':[394,204,411.5,230],
 'small-perturbation/exp':[123,359,200,375.5], 'small-perturbation/omega':[457,359,468,374], 'small-perturbation/k':[477,359,484,374],
 'dispersion-variables/one':[365.5,378,372,389], 'dispersion-variables/zero':[455,378,463,389],
 'ion-sound-scale/omega':[97,390.5,118,408], 'ion-sound-scale/ion-scale':[123.75,389.5,154.75,413.5], 'ion-sound-scale/dispersion':[464.25,391.5,530,409],
 'classical-ion-sound/relation':[112,429,223.75,454.75],
 'electron-scale/omega':[97,456.5,118,474], 'electron-scale/electron-scale':[123.75,454.5,154.75,479.5], 'electron-scale/four':[342,460,360.5,474],
 'group-velocity/vg':[276,482,289,495.5], 'group-velocity/wpe':[347.5,477.5,365.5,498],
 'boltzmann-electrons/poisson':[381,496,463.5,518], 'quasineutral-dispersion/dispersion':[362,519,417,535]
}
for r in q['rows']:
 for a in r['atoms']:
  if r['id']+'/'+a['id']in rects:a['rect']=rects[r['id']+'/'+a['id']]
def replace_atoms(id,old,new):
 r=by[id];r['atoms']=[a for a in r['atoms']if a['id']!=old]+[dict(id=n,rect=rect,image_path=[10],reviewed=False,reason='Manually separated original mathematical glyphs around Chinese conjunctions; source-contact review required')for n,rect in new]
replace_atoms('dispersion-variables','variables',[
 ('omega',[110,376,124,389]),('k',[130,375.5,141,389]),('gamma',[145,376,158,391]),('m',[164,377,180,391]),('T',[187,375,200,391]),('lambda',[205,375,224,392]),('kb',[230,375,244,391])])
by['dispersion-variables']['ko']='관계식은 [[omega]], [[k]], [[gamma]], [[m]], [[T]], [[lambda]], [[kb]]로 나타내라. 모든 섭동량의 아래 첨자는 [[one]], 섭동 전 값은 [[zero]]이다.'
by['dispersion-variables']['en']='Use [[omega]], [[k]], [[gamma]], [[m]], [[T]], [[lambda]] and [[kb]]. Subscripts [[one]] and [[zero]] denote perturbations and unperturbed quantities.'
for id in ['ion-sound-scale','electron-scale']:
 replace_atoms(id,'temps',[('Te',[205,393 if id=='ion-sound-scale'else 460,217,408 if id=='ion-sound-scale'else 475]),('Ti',[227,393 if id=='ion-sound-scale'else 460,240,408 if id=='ion-sound-scale'else 475])])
 for lang in ['ko','en']:by[id][lang]=by[id][lang].replace('[[temps]]','[[Te]]와 [[Ti]]'if lang=='ko'else'[[Te]] and [[Ti]]')
for r in q['rows']:r['source_atom_ids']=[a['id']for a in r['atoms']]
q['root_contact_revision']='Original 4x labelled-coordinate grid and all56 first-pass source snippets reviewed. Mathematical source ROIs refined and mixed Chinese conjunction bundles separated before replay; no mathematical glyphs retyped.'
path.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
print('revised',sum(len(r['atoms'])for r in q['rows']),'math atoms')
