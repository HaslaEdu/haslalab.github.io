"""Compare actual final full nonspace glyph-box centers with reviewed originals."""
from pathlib import Path
import argparse,hashlib,json,re
import pymupdf as f
import natural_plan_compose_icho2019 as c
import icho2019_write_guard as g
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();B=Path(__file__).resolve().parent;face=lambda s:re.sub('[^a-z0-9]','',s.lower())

def run(n,strict=True):
 path=g.PROOFS/f'page{n:02}.pdf';g.assert_output(path,n);q=json.loads(path.with_suffix('.layout.json').read_text('utf8'));assert q['page']==n and Path(q['source']).resolve()==g.SOURCE and q['source_sha256']==g.SOURCE_SHA and sha(path)==q['output_sha256']
 effective=json.loads(Path(q['effective_plan_path']).read_text('utf8'));scope=effective['layout_scope'];specs=scope.get('source_caption_alignment_review',[])
 if not specs:return None
 assert sha(q['effective_plan_path'])==q['effective_plan_sha256'];slotlines={s['id']:s['at'][:2]for s in effective['slots']};source=f.open(g.SOURCE);target=f.open(path);sp=source[n-1];actual=c._glyphs(target[0]);rawblocks=sp.get_text('rawdict')['blocks'];selected={c.ops.glyph_key(v)for v in q['selected_glyphs']};dx={c.ops.glyph_key(v):s['dx']for s in q['native_shifts']for v in s['glyphs']};metrics=c.FontMetrics({r:Path(p)for r,p in q['new_font_paths'].items()});rows=[];errors=[]
 for spec in specs:
  b,l=spec['source_line'];raw=[dict(ch,font=s['font'],size=s['size'],color=s['color'])for s in rawblocks[b]['lines'][l]['spans']for ch in s['chars']if ch['c'].strip()];native=c.original_helpers.canonical_selected(sp,raw);native=[v for v in native if c.ops.glyph_key(v)not in selected];found=[]
  for v in native:
   wanted=[v['origin'][0]+dx.get(c.ops.glyph_key(v),0.),v['origin'][1]];matched=[a for a in actual if a['c']==v['c']and a['gid']==v['gid']and a['font']==v['font']and abs(a['size']-v['size'])<.001 and max(abs(x-y)for x,y in zip(a['origin'],wanted))<.001];assert len(matched)==1,(n,spec['source_line'],v,matched);found+=matched
  placements=[p for p in q['placements']if slotlines[p['id']]==spec['source_line']]
  for p in placements:
   metric=metrics[p['font_role']];x,y=p['point']
   for char in p['text']:
    if not char.isspace():
     matched=[a for a in actual if a['c']==char and face(a['font'])==face(metric.name)and abs(a['size']-p['size'])<.001 and max(abs(a['origin'][0]-x),abs(a['origin'][1]-y))<.001];assert len(matched)==1,(n,p['id'],char,x,y,matched);found+=matched
    x+=c.word_space(metric,p['size'])if char==' 'else metric.text_length(char,fontsize=p['size'])
  assert found,(n,spec);r=[min(v['bbox'][0]for v in found),min(v['bbox'][1]for v in found),max(v['bbox'][2]for v in found),max(v['bbox'][3]for v in found)];center=(r[0]+r[2])/2;error=center-spec['source_center_x'];row=dict(source_line=spec['source_line'],source_text=spec['source_text'],source_center_x=spec['source_center_x'],actual_full_nonspace_output_glyph_box=r,actual_full_output_glyph_box_center_x=center,signed_center_error_pt=error,source_baseline=spec['source_baseline'],actual_original_native_glyphs_verified=len(native),actual_Korean_glyphs_verified=len(found)-len(native),passed=abs(error)<=.001);rows.append(row)
  if not row['passed']:errors.append(row)
 report=dict(page=n,passed=not errors,proof_sha256=sha(path),measurement_code_sha256=sha(__file__),source_sha256=g.SOURCE_SHA,rows=rows,errors=errors,center_tolerance_pt=.001,basis='Same measured full nonspace glyph-box basis as the original source centering review. Read actual final glyph boxes and exact retained native GID/font/size/origin; mixed native variables/subscripts remain part of their own caption, never replaced by a page-center constant.')
 q['actual_source_caption_center_audit']=report;path.with_suffix('.layout.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');path.with_suffix('.caption-center-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');source.close();target.close()
 if strict and errors:raise ValueError('Actual mixed caption glyph-box center differs from its original '+repr(errors))
 return report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('pages',nargs='+',type=int);ap.add_argument('--calibrate',action='store_true');args=ap.parse_args();journal=[]
 for n in args.pages:
  result=run(n,strict=False)
  if not result:continue
  if args.calibrate and result['errors']:
   path=B/f'page{n:02}.overrides.json';q=json.loads(path.read_text('utf8'));layout=json.loads((g.PROOFS/f'page{n:02}.layout.json').read_text('utf8'));assert sha(path)==layout['overrides_sha256'],'Refuse calibration from a stale override snapshot'
   for row in result['errors']:
    offset=-row['signed_center_error_pt'];assert abs(offset)<1.,row
    values=q.setdefault('__line_optical_offsets__',[]);match=[v for v in values if abs(v['baseline']-row['source_baseline'])<.0002];assert len(match)<=1
    previous=match[0]['dx']if match else 0.;entry=dict(baseline=row['source_baseline'],dx=previous+offset,source_sha256=g.SOURCE_SHA,source_line=row['source_line'],source_center_x=row['source_center_x'],measured_candidate_actual_center_x=row['actual_full_output_glyph_box_center_x'],measured_candidate_proof_sha256=result['proof_sha256'],review='Common horizontal caption-only correction measured from actual final Korean+native glyph boxes on the original full-run source-center basis. Preserve every original source point size/baseline/GID/font and all glyph contents; no page-center replacement or font resizing.')
    if match:values.remove(match[0])
    values.append(entry);journal.append(dict(page=n,**entry))
   path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
  print(n,result['passed'],[(v['source_line'],v['signed_center_error_pt'])for v in result['rows']],flush=True)
 if args.calibrate:(B/'source-caption-actual-glyph-center-calibration.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,rows=journal),ensure_ascii=False,indent=2)+'\n','utf8')
