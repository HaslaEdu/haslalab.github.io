"""Original source -> actual initial/final native, graphics and prose QA.

No source math is retyped; no raw failed audit is converted into a pass.
Future source-specific witnesses, if necessary, require their own closed
original-CID/program evidence. This module has no raster-phase exclusions.
"""
from pathlib import Path
from collections import Counter,defaultdict
import sys,json,hashlib,math,re
import pikepdf,pymupdf as f,numpy as np
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_native_geometry_motion import audit as graphics_audit
from pdf_native_script_motion_audit import audit as script_audit
from pdf_new_prose_native_text_overlap import audit as collision_audit
from pdf_hangul_visibility import audit as hangul_audit
from pdf_new_prose_outlines import audit as outline_audit
B=Path(__file__).resolve().parents[1];S=B/'source/CPhO_2008_original_combined_ZH.pdf';SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text('utf8'))

def semantic(v):
 if isinstance(v,pikepdf.Stream):return dict(decoded_sha256=hashlib.sha256(v.read_bytes()).hexdigest(),dictionary={str(k):semantic(x)for k,x in sorted(v.items())if str(k)not in('/Length','/Filter','/DecodeParms')})
 if isinstance(v,pikepdf.Dictionary):return {str(k):semantic(x)for k,x in sorted(v.items())}
 if isinstance(v,pikepdf.Array):return[semantic(x)for x in v]
 if isinstance(v,pikepdf.String):return{'hex':bytes(v).hex()}
 if isinstance(v,pikepdf.Name):return{'literal_pdf_name_bytes_hex':bytes(v).hex()}
 if v is None or isinstance(v,(str,int,float,bool)):return v
 return float(v)

def physical_id(g):return json.dumps([g.get(k)for k in('c','font','trace_gid','size','render_mode','color','opacity','linewidth','direction','stroke_color','stroke_opacity','wmode','colorspace')],sort_keys=True,separators=(',',':'))
def source_match(a,b):return physical_id(a)==physical_id(b)and abs(a['origin'][1]-b['origin'][1])<.001
def group_dx(gs,actual,requested):
 # Requested layout is only a tie breaker for indistinguishable repeated
 # literal references. Actual original GID/font/point/paint/Y supplies the
 # candidate pattern, and every complete expression must share its motion.
 lists=[[a for a in actual if source_match(g,a)]for g in gs];assert all(lists)
 possibilities=[]
 for a in min(lists,key=len):
  seed=next(i for i,v in enumerate(lists)if v is min(lists,key=len));dx=a['origin'][0]-gs[seed]['origin'][0]
  if all(any(abs(h['origin'][0]-g['origin'][0]-dx)<.001 for h in hs)for g,hs in zip(gs,lists)):possibilities.append(dx)
 good=[dx for dx in possibilities if abs(dx-requested)<.001];assert good,('No complete original expression pattern at actual requested layout',requested,possibilities)
 return min(good,key=lambda dx:abs(dx-requested))

def path_programs(path,n,inv):
 with pikepdf.open(path)as doc:
  ops=list(pikepdf.parse_content_stream(doc.pages[n-1]));rows=[]
  for v in inv['vector_paths']:
   raw=pikepdf.unparse_content_stream([ops[i]for i in v['operator_indices']]);rows.append(dict(**v,literal_original_path_operator_program_sha256=hashlib.sha256(raw).hexdigest()))
 return rows

def audit(n,lang,final_override=None):
 assert sha(S)==SHA;target=Path(final_override)if final_override else B/f'proofs/{lang}/page{n:02}.pdf';report_path=target.with_suffix('.independent-native-audit.json');c=read(B/f'proofs/{lang}/page{n:02}.composition.json');p=Path(c['actual_immutable_producing_plan']);assert sha(p)==c['plan_sha256'];q=read(p)
 assert q['source_sha256']==SHA;inv=read(B/f'inspection/page{n:02}-original-native-programs.json');original=inv['actual_original_glyphs'];erased={glyph_key(g)for r in q['rows']for g in r['erase_glyphs']};erased_indices={g['source_trace_index']for r in q['rows']for g in r['erase_glyphs']}
 locked=set(q['source_read_original_CJK_math_list_comma_trace_indices'])|{i for group in q['source_read_complete_original_CJK_math_parenthesis_trace_groups']for i in group};assert not(locked&erased_indices),'Source-read mathematical punctuation may never be erased as prose'
 native=[g for g in original if glyph_key(g)not in erased];nonspace=[g for g in native if g['c'].strip()];actual_inv=inspect_inline_groups(target,1)
 with f.open(target)as doc:actual=_traces(doc[0])
 errors=[];groups=[];path_dx={}
 for row in q['rows']:
  placements=next(v for v in c['placements']if v['id']==row['id']);layout={v['id']:v['dx']for v in placements['tokens']if v['kind']=='native'}
  for a in row['native_atoms']:
   try:dx=group_dx(a['glyphs'],actual,layout[a['id']]);groups.append(dict(id=a['id'],original_native_glyphs=len(a['glyphs']),actual_original_GID_font_point_paint_Y_common_dx=dx,passed=True));
   except Exception as e:errors.append(dict(id=a['id'],error=repr(e)));continue
   for v in a['vector_paths']:path_dx[tuple(v['operator_indices'])]=dx
 moving={glyph_key(g):s['dx']for s in c['native_shifts']for g in s['glyphs']}
 for g in nonspace:
  dx=moving.get(glyph_key(g),0)
  if not any(source_match(g,h)and abs(h['origin'][0]-g['origin'][0]-dx)<.001 for h in actual):errors.append(dict(source_native_glyph=g,error='Literal original native glyph/font/GID/point/paint/Y/X absent'))
 old_paths=path_programs(S,n,inv);new_paths=path_programs(target,1,actual_inv);paths=[]
 for old in old_paths:
  dx=path_dx.get(tuple(old['operator_indices']),0);hits=[i for i,v in enumerate(new_paths)if v['literal_original_path_operator_program_sha256']==old['literal_original_path_operator_program_sha256']and all(abs(v['rect'][j]-old['rect'][j]-(dx if j in(0,2)else 0))<.001 for j in range(4))]
  ok=bool(hits)
  if ok:new_paths.pop(hits[0])
  else:errors.append(dict(original_path=old,actual_required_dx=dx,error='Literal original mathematical/graphical path program or geometry absent'))
  paths.append(dict(original_path_program_sha256=old['literal_original_path_operator_program_sha256'],source_rect=old['rect'],actual_independent_dx=dx,passed=ok))
 with pikepdf.open(S)as src,pikepdf.open(target)as final,pikepdf.open(B/f'proofs/{lang}/page{n:02}.native-control.pdf')as initial:
  source=src.pages[n-1];page=final.pages[0];stage=initial.pages[0];font_rows=[]
  for alias,font in source.Resources.Font.items():
   a=semantic(font);ok=semantic(page.Resources.Font[alias])==a==semantic(stage.Resources.Font[alias]);font_rows.append(dict(original_resource=str(alias),original_font_dictionary_and_programs_exact=ok))
   if not ok:errors.append(dict(font=str(alias),error='Original font dictionary/program changed'))
  group_exact=semantic(source.obj.get('/Group'))==semantic(page.obj.get('/Group'))==semantic(stage.obj.get('/Group'));colors_exact=semantic(source.Resources.get('/ColorSpace'))==semantic(page.Resources.get('/ColorSpace'))==semantic(stage.Resources.get('/ColorSpace'));assert group_exact and colors_exact
 # Source bitmap programs and actual invocation CTMs are independent of
 # visible tool previews and of every translated language glyph.
 images=[];available=list(actual_inv['images']);stage_images=list(inspect_inline_groups(B/f'proofs/{lang}/page{n:02}.native-control.pdf',1)['images'])
 fields=['original_raw_sha256','entry_ctm','page_matrix','ancestor_clip_rects','bbox']
 image_identity=lambda v:json.dumps({k:v[k]for k in fields},sort_keys=True,separators=(',',':'))
 for v in inv['images']:
  hits=[i for i,a in enumerate(available)if image_identity(a)==image_identity(v)];initial_hits=[i for i,a in enumerate(stage_images)if image_identity(a)==image_identity(v)]
  ok=bool(hits)and bool(initial_hits)
  if ok:available.pop(hits[0])
  if initial_hits:stage_images.pop(initial_hits[0])
  if not ok:errors.append(dict(original_image=v,error='Original encoded image program/paint CTM/bounds absent'))
  images.append(dict(original_encoded_image_sha256=v['original_raw_sha256'],original_CTM=v['entry_ctm'],original_page_matrix=v['page_matrix'],original_ancestor_clip_rects=v['ancestor_clip_rects'],original_bbox=v['bbox'],source_to_initial_and_final_image_exact=ok,passed=ok))
 if available or stage_images:errors.append(dict(error='Unexpected initial/final image invocations',final=available,initial=stage_images))
 # Raw original-input outline result is kept verbatim, including any loss.
 physical=audit_moved_native_ink(S,n,target,shifts=c['native_shifts'],erased_glyphs=c['erased_original_language_glyphs'],protected_glyphs=nonspace)
 expression=[dict(label=a['id'],glyphs=a['glyphs'])for r in q['rows']for a in r['native_atoms']]
 scripts=script_audit(S,n,target,shifts=c['native_shifts'],native_glyphs=nonspace,expression_groups=expression)
 collision=collision_audit(target,native_glyphs=nonspace,shifts=c['native_shifts']);outlines=outline_audit(target);visibility=hangul_audit(target)if lang=='ko'else dict(flagged_components=0,pages=[])
 one=B/f'evidence/page{n:02}-literal-original-one-page.pdf';one.parent.mkdir(exist_ok=True)
 if not one.exists():
  with pikepdf.open(S)as d,pikepdf.Pdf.new()as out:out.pages.append(d.pages[n-1]);out.save(one,compress_streams=False)
 _,graphics=graphics_audit(one,target,c['native_shifts']);bitmap_pass=True
 if q.get('source_bitmap_language_policy_path'):
  from cpho2008_bitmap_language_qa import audit as bitmap_audit
  bitmap,graphics=bitmap_audit(n,lang,target,c,graphics);bitmap_pass=bitmap['passed']
 result=dict(original_source_sha256=SHA,source_page=n,language=lang,proof_sha256=sha(target),actual_producing_plan_sha256=sha(p),original_native_glyphs=len(nonspace),source_math_punctuation_CIDs_checked=len(locked),source_read_math_punctuation_never_erased=True,independent_original_native_geometry=dict(groups=groups,literal_original_vector_path_programs=paths,errors=errors,passed=not errors),original_font_dictionary_and_programs=font_rows,source_original_images=images,original_source_to_initial_and_final_Page_Group_exact=group_exact,original_source_to_initial_and_final_ColorSpaces_exact=colors_exact,raw_original_input_native_ink=physical,original_native_script_relative_geometry=scripts,new_prose_over_original_native_text=collision,new_prose_actual_embedded_outline_audit=outlines,Hangul_visibility=visibility,nonselected_original_native_graphical_ink=graphics,passed=not errors and physical['passed']and scripts['passed']and collision['passed']and outlines['passed']and visibility['flagged_components']==0 and graphics['changed_nonselected_native_graphical_pixels']==0)
 result['passed']=result['passed']and bitmap_pass
 report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print('C08_ACTUAL_ORIGINAL_NATIVE_AUDIT',n,lang,'pass',result['passed'],'raw_missing',physical.get('newly_missing_native_ink_pixels'),'errors',len(errors),'script',scripts['passed'],'collision',collision['passed'],'outline',outlines['passed'],'graphics',graphics['changed_nonselected_native_graphical_pixels'],flush=True);return result
if __name__=='__main__':
 sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools');from pdf_memory_gate import page_worker
 a=sys.argv[1:];n=int(a[0]);lang=a[1]
 with page_worker():audit(n,lang)
