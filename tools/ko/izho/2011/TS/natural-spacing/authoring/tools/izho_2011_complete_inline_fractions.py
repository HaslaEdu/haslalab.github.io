"""Three manually reviewed original MathType clips and their external rules.

The source paints fraction rules immediately BEFORE its rectangular glyph clip.
The original glyphs and those exact original paths must share one horizontal dx.
No equation is redrawn, retyped, rescaled, or converted to an image.
"""
from pathlib import Path
import json,hashlib,pymupdf as f
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
FIELDS={4:[dict(label='Complete original E=U/l',rect=[205.76,273.30998291015624,240.76,304.2599829101563],baseline=292.20,glyph_count=4,rule_count=1)],8:[dict(label='Complete original exp(-epsilon/kBT) approximately1-epsilon/kBT',rect=[175.96,505.35998291015625,284.81,543.6599829101563],baseline=527.64,glyph_count=21,rule_count=2),dict(label='Complete original low-temperature exp(-epsilon/kBT) much-less-than1',rect=[310.76,561.6609829101562,395.56,599.9599829101562],baseline=583.92,glyph_count=17,rule_count=1)]}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def apply_reviewed_fractions(plan):
 page=plan['page']
 if page not in FIELDS:return
 assert plan['original_english_source_sha256']=='ecc4a34a50fade6a08fd5f629480bebfa20ec418cdc19fa87915f6c0465ee008'
 inv=inspect_inline_groups(plan['source_base'],page);compiled=[];rules=[]
 with f.open(plan['original_english_source'])as source:original_keys={glyph_key(g)for g in _traces(source[page-1])if g['c'].strip()}
 for field in FIELDS[page]:
  clips=[v for v in inv['clip_groups']if v.get('known_rectangular_clips')and len(v.get('clip_rects',[]))==1 and max(abs(a-b)for a,b in zip(v['clip_rects'][0],field['rect']))<.001];assert len(clips)==1
  clip=clips[0];gs=[g for g in clip['glyphs']if g['c'].strip()and g.get('trace_gid',g.get('gid',-1))>=0];assert len(gs)==field['glyph_count']and all(glyph_key(g)in original_keys for g in gs)
  box=f.Rect(field['rect']);paths=[v for v in inv['vector_paths']if box.contains(f.Rect(v['rect']))and f.Rect(v['rect']).width>1 and f.Rect(v['rect']).height<2];assert len(paths)==field['rule_count']
  assert all(v['paint_operator']=='S'for v in paths)
  compiled.append(dict(field,native_glyphs=gs,fraction_paths=paths,original_clip_operator_indices=clip['operator_indices'],source_base_sha256=plan['source_base_sha256'],reviewed=True))
  rules.append(dict(reviewed=True,original_source_only=True,rect=field['rect'],font_regex='.*',baseline=field['baseline'],source_native_glyphs=gs,include_zero_height_vector_bounds=True,reason=field['label']+': every original native glyph, fractional-point script and original stroked fraction rule outside the glyph clip shares one horizontal dx. Exact manually reviewed source clip membership; no equation retyping, new geometry or size fitting.'))
 plan['reviewed_source_inline_fraction_clips']=compiled;plan['explicit_native_math_atoms']=rules
def audit(plan_path,*,final_override=None,composition_override=None,report_override=None):
 plan_path=Path(plan_path);plan=json.loads(plan_path.read_text('utf8'));proof=Path(final_override)if final_override else plan_path.parents[1]/(plan_path.stem+'.pdf');composition=composition_override or json.loads(proof.with_suffix('.qa.json').read_text('utf8'));assert sha(proof)==composition['output_sha256'];assert sha(plan['source_base'])==plan['source_base_sha256']
 groups=plan.get('reviewed_source_inline_fraction_clips',[]);shifts={glyph_key(g):s['dx']for s in composition['native_shifts']for g in s['glyphs']};target=inspect_inline_groups(proof,1)
 with f.open(proof)as doc:actual=_traces(doc[0])
 rows=[]
 for group in groups:
  glyph_errors=[];deltas=[]
  for g in group['native_glyphs']:
   dx=shifts.get(glyph_key(g),0.);hits=[a for a in actual if a['c']==g['c']and a['font']==g['font']and a['trace_gid']==g.get('trace_gid',g.get('gid'))and abs(a['size']-g['size'])<.001 and abs(a['origin'][1]-g['origin'][1])<.001 and abs(a['origin'][0]-g['origin'][0]-dx)<.001]
   if len(hits)!=1:glyph_errors.append(dict(source=g,matches=len(hits)))
   else:deltas.append(hits[0]['origin'][0]-g['origin'][0])
  spread=max(deltas)-min(deltas)if deltas else None;dx=deltas[0]if deltas else None;bars=[]
  for path in group['fraction_paths']:
   expected=[v+(dx if i in[0,2]else 0)for i,v in enumerate(path['rect'])]if dx is not None else[]
   hits=[v for v in target['vector_paths']if v['paint_operator']==path['paint_operator']and len(expected)==4 and max(abs(a-b)for a,b in zip(v['rect'],expected))<.001]
   bars.append(dict(original=path,expected_actual_rect=expected,actual_matching_painted_paths=hits,passed=len(hits)==1))
  rows.append(dict(label=group['label'],original_native_glyphs=len(group['native_glyphs']),source_native_font_gid_point_y_and_actual_dx_matched=not glyph_errors,glyph_errors=glyph_errors,actual_native_common_dx=dx,actual_native_relative_dx_spread_pt=spread,original_fraction_rules=bars,passed=not glyph_errors and spread is not None and spread<.001 and all(r['passed']for r in bars)))
 q=dict(source_sha256=plan['original_english_source_sha256'],source_base_sha256=plan['source_base_sha256'],proof_sha256=sha(proof),method='Independent actual final-PDF original native font/GID/point/y matching AND actual painted fraction-rule endpoint/paint-operator matching at the same common horizontal dx. Do not infer rule movement from glyph metadata or from the motion journal alone.',groups=rows,reviewed_complete_expressions=len(rows),original_fraction_rules_checked=sum(len(r['original_fraction_rules'])for r in rows),passed=all(r['passed']for r in rows))
 report=Path(report_override)if report_override else proof.with_suffix('.inline-fractions.json');report.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return q
