"""Apply reviewed original-glyph measurement windows, never target fitting."""
from pathlib import Path
import json,subprocess,sys,os
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/cpho2005/TS';proposal=json.loads((B/'expanded-weak-source-window-proposals.json').read_text('utf8'));assert proposal['authored_layouts_and_reviewed_outputs_unchanged']
changes={7:[('author-cpho2005-page07-language-rows.py','[600,220,615,238]','[598,218,617,240]')],8:[('author-cpho2005-page08-language-rows.py','[567,172,620,190]','[565,170,622,192]')],10:[('author-cpho2005-page10-source-layout.py','[63,167,113,186]','[61,165,115,188]'),('author-cpho2005-page10-source-layout.py','[472,196,524,212]','[470,194,526,214]')]}
expected={(7,'caption'):(10.025,.876),(8,'efficiency'):(12.6,.742),(10,'receding-second'):(12.9,.709),(10,'unloaded-fourth'):(12.475,.777)}
for key,(point,minimum)in expected.items():
 row=next(r for r in proposal['rows']if(r['page'],r['id'])==key);assert row['new']['source_point_size']==point and row['new']['iou']>=minimum-.001 and row['new']['iou']>row['old']['iou']
for page,items in changes.items():
 for file,old,new in items:
  p=R/file;s=p.read_text('utf8');assert old in s or new in s;(p).write_text(s.replace(old,new),'utf8')
# The original caption source point must not be clipped by a body-only search
# interval. Ordinary source body size candidates remain exactly unchanged.
p=R/'calibrate-cpho2005-page07-per-row-type.py';s=p.read_text('utf8');old='for size in np.arange(11.5,14.751,.025):';new="for size in np.arange(7.5 if row['id']=='caption'else 11.5,14.751,.025):";assert old in s or new in s;p.write_text(s.replace(old,new),'utf8')
p=B.parents[1]/'current-task-state-20261101.json';d=json.loads(p.read_text('utf8'));d['CPhO2005_TS_source_font_window_recheck']=dict(source_only_probe=str(B/'expanded-weak-source-window-proposals.json'),changed_source_measurement_rows=[dict(page=k[0],id=k[1],independently_measured_original_point=v[0])for k,v in expected.items()],unchanged_source_samples_pages5_and7_other_rows_verified=True,pages_requiring_fresh_private_proofs_and_manual_visual_review=[7,8,10],all_required_new_proofs_reviewed=False,no_already_published_source_edition_modified=True,next='Recompose7/8/10 at the improved source-only measured sizes and baseline/stem weights. Re-run source MuPDF4x and independent Poppler144 plus actual omission negatives. Explicitly view both fresh language previews, then update each private visual review; do not publish with stale review hashes.')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1')
for page in [7,8,10]:
 name=f'page{page:02}';author=f'author-cpho2005-{name}-language-rows.py'if page in[7,8]else f'author-cpho2005-{name}-source-layout.py'
 scripts=[(R/author,[]),(R/f'calibrate-cpho2005-{name}-per-row-type.py',[]),(R/f'calibrate-cpho2005-{name}-row-weights.py',[]),(R/f'author-cpho2005-ts-{name}-layout.py',[]),(R/f'compose-cpho2005-ts-{name}-proof.py',[]),(R/'qa-cpho2005-ts-pages04-05.py',[str(page)]),(R/'negative-cpho2005-page04-native-math-visibility.py',[str(page)])]
 for script,args in scripts:subprocess.run([sys.executable,'-X','utf8',str(script),*args],env=env,cwd=R/'Hasla-publish-20261031',check=True)
 print('REFINED_ORIGINAL_FONT_POINT_PAGE_ALL_FOUR_RENDERER_CHECKS_PASS_REQUIRES_FRESH_VISUAL_REVIEW',page,flush=True)
print('SOURCE_FONT_RECHECK_PROOFS_READY_MANUAL_VISUAL_REVIEW_REQUIRED',flush=True)
