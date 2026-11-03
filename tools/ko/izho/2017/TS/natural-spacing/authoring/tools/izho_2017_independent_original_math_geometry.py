"""Independent original PDF -> actual final glyph/Form/rule geometry, no journal."""
from pathlib import Path
from collections import defaultdict
import json,hashlib,pymupdf as f
from pdf_native_inline_reposition import inspect_inline_groups,_traces
SOURCE='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(g):
 fields=['c','font','trace_gid','render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace']
 return json.dumps([g.get(k)for k in fields],sort_keys=True,separators=(',',':'))
def same(a,b):return identity(a)==identity(b)and abs(a['size']-b['size'])<.001 and abs(a['origin'][1]-b['origin'][1])<.001
def translated(a,b,dx):return max(abs(b[i]-a[i]-(dx if i in[0,2]else 0))for i in range(4))<.001
def infer(gs,actual):
 # Entire original relative geometry must resolve to one actual pattern.
 # A source glyph's actual GID/paint/Y participates, never only Unicode or
 # compositor-selected labels. No final motion metadata is consulted.
 lists=[[a for a in actual if same(g,a)]for g in gs]
 if not all(lists):raise ValueError('An original expression glyph/font/GID/point/paint/Y is absent')
 seed=min(range(len(gs)),key=lambda i:len(lists[i]));candidates=[]
 for a in lists[seed]:
  dx=a['origin'][0]-gs[seed]['origin'][0]
  if any(abs(dx-v)<.001 for v in candidates):continue
  if all(any(abs(h['origin'][0]-g['origin'][0]-dx)<.001 for h in hs)for g,hs in zip(gs,lists)):candidates.append(dx)
 if len(candidates)!=1:raise ValueError(('Original complete-expression geometry is absent/ambiguous',len(gs),candidates))
 return candidates[0]
def audit(plan_path,*,final_override=None,report_override=None):
 plan_path=Path(plan_path);p=json.loads(plan_path.read_text('utf8'));proof=Path(final_override)if final_override else plan_path.parents[1]/(plan_path.stem+'.pdf')
 assert p['original_english_source_sha256']==sha(p['original_english_source'])==SOURCE
 n=p['source_page'];cache=Path(p['original_english_source']).parents[1]/'inspection'/f'page{n:02}-original-native-inline-inventory.json';original=json.loads(cache.read_text('utf8'));final=inspect_inline_groups(proof,1)
 with f.open(proof)as doc:actual=_traces(doc[0])
 errors=[];profiles=[];path_dx={}
 for index,r in enumerate(p.get('reviewed_independent_original_expression_geometry_profiles',[])):
  gs=r['original_glyphs']
  try:
   if r.get('original_form'):
    form=r['original_form'];hits=[v for v in final['forms']if v['original_raw_sha256']==form['original_raw_sha256']and abs(v['native_page_bbox'][1]-form['native_page_bbox'][1])<.001 and abs(v['native_page_bbox'][3]-form['native_page_bbox'][3])<.001 and abs((v['native_page_bbox'][2]-v['native_page_bbox'][0])-(form['native_page_bbox'][2]-form['native_page_bbox'][0]))<.001]
    if len(hits)!=1:
     # Identical repeated original Forms are assigned in original x order.
     same_source=[v for v in original['forms']if v['original_raw_sha256']==form['original_raw_sha256']and abs(v['native_page_bbox'][1]-form['native_page_bbox'][1])<.001];same_source.sort(key=lambda v:v['native_page_bbox'][0]);hits.sort(key=lambda v:v['native_page_bbox'][0]);assert len(hits)==len(same_source)
     rank=next(i for i,v in enumerate(same_source)if v['path']==form['path']);hits=[hits[rank]]
    target=hits[0];dx=target['native_page_bbox'][0]-form['native_page_bbox'][0];assert translated(form['native_page_bbox'],target['native_page_bbox'],dx)
    for g in gs:assert any(same(g,a)and abs(a['origin'][0]-g['origin'][0]-dx)<.001 for a in actual),('Form member did not share native Form dx',g,dx)
   else:
    dx=infer(gs,actual)
    for path in r.get('original_vector_paths',[]):
     key=tuple(path['operator_indices'])
     if key in path_dx:assert abs(path_dx[key]-dx)<.001,'Conflicting original complete expression rules'
     path_dx[key]=dx
   profiles.append(dict(profile=index,native_glyphs=len(gs),independently_inferred_common_dx=dx,native_program=r['native_program'],passed=True))
  except Exception as e:errors.append(dict(profile=index,rect=r['reviewed_rect'],error=repr(e)));profiles.append(dict(profile=index,passed=False))
 # Every original invoked Form must remain byte-identical, at its exact
 # original y/width/height. The literal program binds scripts, fraction bars,
 # roots, clips and intrinsic backgrounds independently of compositor claims.
 forms=[];buckets=defaultdict(list)
 for v in final['forms']:buckets[v['original_raw_sha256']].append(v)
 for digest in sorted({v['original_raw_sha256']for v in original['forms']}):
  old=[v for v in original['forms']if v['original_raw_sha256']==digest];new=buckets[digest]
  old.sort(key=lambda v:(round(v['native_page_bbox'][1],2),v['native_page_bbox'][0],len(v['path'])));new.sort(key=lambda v:(round(v['native_page_bbox'][1],2),v['native_page_bbox'][0],len(v['path'])))
  if len(old)!=len(new):errors.append(dict(form_program=digest,original_invocations=len(old),actual_final_invocations=len(new)));continue
  for a,b in zip(old,new):
   dx=b['native_page_bbox'][0]-a['native_page_bbox'][0];ok=translated(a['native_page_bbox'],b['native_page_bbox'],dx)
   forms.append(dict(original_operator_path=a['path'],literal_source_program_sha256=digest,independent_actual_dx=dx,exact_original_width_height_y_and_program=ok))
   if not ok:errors.append(dict(form_program=digest,original=a['native_page_bbox'],final=b['native_page_bbox']))
 # Original top-level paths not in a reviewed moving math expression remain
 # stationary. Thus a missed or left-behind fraction bar cannot hide in the
 # unselected-native preservation audit. Actual physical path geometry is
 # read afresh from final content, not from its movement journal.
 paths=[];available=list(final['vector_paths'])
 isolation=p.get('reviewed_source2017_complete_original_expression_program_isolation')
 if isolation:
  assert isolation['source_sha256']==SOURCE and isolation['source_page']==n and isolation['passed']
  for r in isolation['programs']:
   wrappers=[v for v in final['forms']if v['original_raw_sha256']==r['Form_raw_sha256']]
   assert len(wrappers)==1
   # These rules retain their literal original programs inside a new ordinary
   # Form; require actual final path geometry at the independently inferred dx.
   available.extend(wrappers[0]['own_vector_paths'])
 for path in original['vector_paths']:
  dx=path_dx.get(tuple(path['operator_indices']),0.);hits=[i for i,v in enumerate(available)if v['paint_operator']==path['paint_operator']and translated(path['rect'],v['rect'],dx)]
  ok=bool(hits)
  if ok:available.pop(hits[0])
  else:errors.append(dict(original_vector=path,expected_independent_dx=dx,error='Original actual native rule/graphics geometry absent at required expression dx'))
  paths.append(dict(original_operator_indices=path['operator_indices'],original_rect=path['rect'],independent_expression_dx=dx,passed=ok))
 result=dict(source_sha256=SOURCE,proof_sha256=sha(proof),source_page=n,method='Independent literal original source native Forms and actual final programs; exact original glyph/font/GID/fractional point/paint/Y infer one whole-expression dx; every original native rule is independently found at that dx. No compositor journal or metadata supplies expected mathematical motion. Existing0.001pt geometry tolerance; no exclusions of mathematical ink.',profiles=profiles,original_forms=forms,all_original_top_level_vector_paths=paths,errors=errors,passed=not errors)
 report=Path(report_override)if report_override else proof.with_suffix('.independent-original-math-geometry.json');report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');return result
