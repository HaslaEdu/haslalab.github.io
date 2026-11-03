"""Exact original encoded U+0020/GID1318 arrowhead programs, actual ink."""
from pathlib import Path
from io import BytesIO
import sys,json,hashlib,pikepdf,pymupdf as f,numpy as np,subprocess,os
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');E=B/'engine';F=B/'natural/2019/TS';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces,inspect_inline_groups,_raw_regions,_number,_font_programs
from pdf_original_text_ops import glyph_key
from pdf_native_glyph_promote import PAINT_STATE
from izho_2019_ts_painted_arrow_cids import expected_heads,SOURCE
POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
def audit(n,override=None,report=None):
 P=F/f'plans/page{n:02}.json';p=json.loads(P.read_text('utf8'));q=json.loads((F/f'page{n:02}.qa.json').read_text('utf8'));pdf=Path(override)if override else F/f'page{n:02}.pdf';before=sha(pdf);heads=expected_heads(p,q);out=B/f'natural/2019-literal-original-arrowhead-ink/page{n:02}'/before[:16];out.mkdir(parents=True,exist_ok=True);records=[];geometry_errors=[]
 with f.open(pdf)as doc:actual=_traces(doc[0])
 for row in heads:
  g=row['glyph'];matches=[h for h in actual if all(h.get(k)==g.get(k)for k in['c','font','trace_gid','render_mode','color','opacity','direction'])and abs(h['size']-g['size'])<.001 and abs(h['origin'][1]-g['origin'][1])<.001 and abs(h['origin'][0]-g['origin'][0]-row['dx'])<.001]
  if len(matches)!=1:geometry_errors.append(dict(expected_original_glyph=g,dx=row['dx'],actual_matches=matches))
 source=p['original_english_source'];assert sha(source)==SOURCE;inv=inspect_inline_groups(source,n,include_text_shows=True)
 with pikepdf.open(source)as original,pikepdf.Pdf.new()as target:
  src=original.pages[n-1];target.pages.append(src);page=target.pages[0];content,regions=_raw_regions(src);ops=list(pikepdf.parse_content_stream(src));resources=page.Resources;new=pikepdf.Dictionary(resources);new.XObject=pikepdf.Dictionary(resources.get('/XObject',{}));commands=[]
  for index,row in enumerate(heads):
   g=row['official_source_glyph'];key=glyph_key(g);shows=[s for s in inv['top_level_text_shows']if any(glyph_key(h)==key for part in s['parts']for h in part['glyphs'])];assert len(shows)==1;show=shows[0];assert len(show['parts'])==1 and len(show['parts'][0]['glyphs'])==1;part=show['parts'][0];assert part['raw_hex']=='0526'and part['code']==1318 and part['glyphs'][0]['c']==' 'and part['glyphs'][0]['trace_gid']==1318;state=show['state'];assert state['tf']==12 and state['tr']==0 and tuple(state['ctm'])==(1.,0.,0.,1.,0.,0.)and state['clips']and all(c['rect']is not None for c in state['clips'])
   clips=[c for c in inv['clip_groups']if c['known_rectangular_clips']and c['clip_rects']==[state['clips'][-1]['rect']]and c['operator_indices'][0]<show['operator_index']<c['operator_indices'][-1]];assert clips;clip=min(clips,key=lambda c:c['operator_indices'][-1]-c['operator_indices'][0]);start,end=clip['operator_indices'];inside=[s for s in inv['top_level_text_shows']if start<=s['operator_index']<=end];assert inside==[show]and str(ops[start].operator)=='q'and str(ops[end].operator)=='Q';program=content[regions[start][0]:regions[end][1]];history=[];stack=[];ancestor_clips=[]
   for ancestor in state['clips'][:-1]:
    ci=ancestor['operator_index'];assert str(ops[ci-1].operator)=='re'and str(ops[ci].operator)in['W','W*']and str(ops[ci+1].operator)=='n';ancestor_clips.append(content[regions[ci-1][0]:regions[ci+1][1]])
   for i,inst in enumerate(ops[:start]):
    op=str(inst.operator)
    if op=='q':stack.append(history[:])
    elif op=='Q':history=stack.pop()
    elif op in PAINT_STATE:history.append(content[regions[i][0]:regions[i][1]])
   prefix=('q\nBT '+state['active']+' '+_number(state['tf'])+' Tf '+_number(state['tc'])+' Tc '+_number(state['tw'])+' Tw '+_number(state['th']*100)+' Tz '+str(state['tr'])+' Tr '+_number(state['ts'])+' Ts ET\n').encode('ascii');body=b'\n'.join([prefix,*history,*ancestor_clips,program,b'\nQ\n']);form=target.make_stream(body);form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form;box=f.Rect(g['bbox']);height=float(page.MediaBox[3])-float(page.MediaBox[1]);form.BBox=pikepdf.Array([box.x0,height-box.y1-3,box.x1,height-box.y0+3]);form.Resources=resources;name=pikepdf.Name('/LiteralOriginalArrowHeadReference'+str(index));assert name not in new.XObject;new.XObject[name]=form;commands.append(('q 1 0 0 1 '+_number(row['dx'])+' 0 cm '+str(name)+' Do Q\n').encode('ascii'));records.append(dict(source_glyph=g,expected_dx=row['dx'],original_encoded_CID_hex=part['raw_hex'],original_font_resource=state['active'],original_Tf=state['tf'],original_Tm=show['text_matrix'],original_exact_clips=state['clips'],original_ancestor_raw_clip_programs_copied=len(ancestor_clips),original_literal_head_program_operator_range=[start,end],original_literal_head_program_sha256=hashlib.sha256(program).hexdigest(),reference_Form_raw_sha256=hashlib.sha256(body).hexdigest(),Unicode_U0020_preserved=True,source_GID1318_preserved=True))
  page.Resources=new;page.Contents=target.make_stream(b''.join(commands));buffer=BytesIO();target.save(buffer,compress_streams=False);reference_bytes=buffer.getvalue();reference=out/('exact-original-encoded-arrowhead-reference-'+hashlib.sha256(reference_bytes).hexdigest()[:16]+'.pdf')
  if reference.exists():assert reference.read_bytes()==reference_bytes
  else:reference.write_bytes(reference_bytes)
  with pikepdf.open(pdf)as actualpdf:font_programs_preserved=_font_programs(src)<=_font_programs(actualpdf.pages[0]);assert font_programs_preserved
 program_results=[]
 if n==4:
  contract=p['reviewed_complete_original_painted_space_arrow_programs'];finalforms=inspect_inline_groups(str(pdf),1)['forms'];moves={glyph_key(g):s['dx']for s in q['native_shifts']for g in s['glyphs']if g['c'].strip()}
  for group in contract['groups']:
   start,end=group['original_official_operator_range'];program=content[regions[start][0]:regions[end][1]];assert hashlib.sha256(program).hexdigest()==group['original_program_sha256'];assert Path(group['original_program_path']).read_bytes()==program;native=[r['glyph']for r in group['native_CID_records']if r['glyph']['c'].strip()];dx=moves.get(glyph_key(native[0]),0.);bb=f.Rect(group['Form_bbox_page'])+(dx,0,dx,0);matches=[v for v in finalforms if v['original_raw_sha256']==group['Form_raw_sha256']and max(abs(x-y)for x,y in zip(v['native_page_bbox'],bb))<.001];program_results.append(dict(original_program_sha256=group['original_program_sha256'],full_original_Form_program_sha256=group['Form_raw_sha256'],expected_bbox=list(bb),actual_identical_complete_program_and_geometry_matches=len(matches),passed=len(matches)==1))
 checks=[]
 for scale in[4,8]:
  with f.open(reference)as expected,f.open(pdf)as final:
   a=expected[0].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);b=final[0].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,3);mask=aa.min(axis=2)<80;missing=int((mask&(bb.min(axis=2)>=220)).sum());checks.append(dict(renderer='MuPDF RGB',scale=scale,original_encoded_head_dark_pixels=int(mask.sum()),missing_actual_original_head_pixels=missing,passed=missing==0))
 for file,label in[(reference,'reference'),(pdf,'actual')]:subprocess.run([POP,'-f','1','-l','1','-singlefile','-r','144','-png',str(file),str(out/label)],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 from PIL import Image
 a=np.asarray(Image.open(out/'reference.png').convert('RGB'));b=np.asarray(Image.open(out/'actual.png').convert('RGB'));mask=a.min(axis=2)<80;missing=int((mask&(b.min(axis=2)>=220)).sum());checks.append(dict(renderer='independent external Poppler RGB',dpi=144,original_encoded_head_dark_pixels=int(mask.sum()),missing_actual_original_head_pixels=missing,passed=missing==0));assert sha(pdf)==before
 result=dict(original_source_sha256=SOURCE,proof_sha256=before,source_page=n,plan_sha256=sha(P),literal_original_U0020_CIDs_checked=len(records),original_CID_hex='0526',original_GID=1318,original_point=12,original_font='CambriaMath',all_original_native_font_programs_preserved=font_programs_preserved,actual_literal_CID_font_GID_point_paint_X_Y_errors=geometry_errors,source_literal_encoded_CID_programs=records,complete_original_program_geometry=program_results,exact_original_encoded_CID_rgb_checks=checks,reference_pdf=str(reference),reference_pdf_sha256=sha(reference),no_unicode_retyping_or_new_font_or_original_clip_changes=True,shared_guard_sha256=sha(E/'pdf_native_inline_reposition.py'),passed=not geometry_errors and all(r['passed']for r in program_results)and all(r['passed']for r in checks));report=Path(report)if report else pdf.with_suffix('.literal-original-arrowheads.json');report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');return result
if __name__=='__main__':
 for n in map(int,sys.argv[1:]):
  with page_worker():q=audit(n)
  print('SOURCE2019_LITERAL_ORIGINAL_U0020_ARROWHEAD_CID_PROGRAM_AND_RGB',n,q['passed'],q['literal_original_U0020_CIDs_checked'],q['proof_sha256'],flush=True);assert q['passed']
