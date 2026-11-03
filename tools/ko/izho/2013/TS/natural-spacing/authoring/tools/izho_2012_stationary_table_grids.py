"""Human-reviewed original table grids; metric-box contact is not ink contact."""
import pymupdf as f
from pdf_native_inline_reposition import inspect_inline_groups
FRAMES={2:[[110,93,528,284]],3:[[110,475,528,690]],5:[[110,307,528,522],[110,552,528,776]],8:[[195,131,442,737]],11:[[172,145,466,720]]}
def apply(plan):
 assert plan['original_english_source_sha256']=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db'
 frames=[f.Rect(v)for v in FRAMES.get(plan['source_page'],[])];rows=[]
 if not frames:return
 inv=inspect_inline_groups(plan['source_base'],plan['page']);math=[f.Rect(r['rect'])+(-.01,-.01,.01,.01)for r in plan.get('explicit_native_math_atoms',[])]
 with f.open(plan['source_base'])as doc:
  for drawing in doc[plan['page']-1].get_drawings():
   r=f.Rect(drawing['rect']);color=drawing.get('fill')
   if not any(frame.contains(r)for frame in frames)or any(box.contains(r)for box in math):continue
   if drawing['type']!='f'or color is None or max(color)>.001 or drawing.get('color')is not None or drawing.get('fill_opacity')!=1:continue
   if not drawing['items']or any(item[0]!='re'for item in drawing['items']):continue
   if not(r.width<=1.6 and r.height>=5 or r.height<=1.6 and r.width>=5):continue
   matches=[v for v in inv['vector_paths']if max(abs(a-b)for a,b in zip(v['rect'],r))<.001]
   if len(matches)!=1:raise ValueError('Original source pure table-grid path not uniquely resolved')
   rows.append(dict(**matches[0],reviewed_nonmathematical_source_table_grid=True,actual_fill_color=list(color),reason='Human-read original2012 table grid, an exact opaque black thin rectangle inside the reviewed table frame. It remains byte-identical at its source coordinates. Source glyph metric boxes can touch a grid even when actual glyph ink does not; independent final new Hangul AND non-Hangul prose ink/graphics collision checks remain mandatory.'))
 options=plan['native_move_options'];values=options.get('reviewed_stationary_vector_paths',[])+rows;options['reviewed_stationary_vector_paths']=list({tuple(v['operator_indices']):v for v in values}.values());plan['reviewed_original_stationary_table_grid_paths']=rows
