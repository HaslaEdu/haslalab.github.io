"""Read actual new glyphs: source role/point/baseline, text and natural spaces."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import json,re,hashlib,sys
import pikepdf,pymupdf as f,numpy as np
from fontTools.ttLib import TTFont
from cpho2008_prose_outline_primitives import trace_font_resources
from pdf_native_inline_reposition import _traces
B=Path(__file__).resolve().parents[1];S=B/'source/CPhO_2008_original_combined_ZH.pdf';SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text('utf8'))
FACES={'ËÎÌå+FPEF':'SimSun','ºÚÌå+FPEF':'SimHei'}

def audit(n,lang,final_override=None):
 target=Path(final_override)if final_override else B/f'proofs/{lang}/page{n:02}.pdf';c=read(B/f'proofs/{lang}/page{n:02}.composition.json');q=read(c['actual_immutable_producing_plan']);assert sha(S)==SHA and sha(c['actual_immutable_producing_plan'])==c['plan_sha256']
 errors=[];font_data={};fonts=[]
 with f.open(S)as original:source_glyphs=_traces(original[n-1])
 with pikepdf.open(target)as doc,f.open(target)as native:
  page=native[0];mapped,_=trace_font_resources(doc,page);actual=[g for g in mapped if g['font_alias'].startswith('/C08Translated')and not g['c'].isspace()]
  for face,record in c['fonts'].items():
   path=Path(record['subset_path']);assert sha(path)==record['subset_sha256'];raw=path.read_bytes();tt=TTFont(BytesIO(raw),recalcTimestamp=False);cmap=tt.getBestCmap();metric=tt['hmtx'].metrics;em=tt['head'].unitsPerEm;gid={code:tt.getGlyphID(name)for code,name in cmap.items()};adv={code:metric[name][0]/em for code,name in cmap.items()};tt.close()
   alias='/C08Translated'+face;font=doc.pages[0].Resources.Font[pikepdf.Name(alias)];descriptor=font.get('/DescendantFonts',[font])[0].FontDescriptor;field=next(k for k in('/FontFile2','/FontFile3')if k in descriptor);embedded=descriptor[field].read_bytes();ok=embedded==raw
   fonts.append(dict(original_source_role=face,actual_new_resource=alias,expected_real_font_subset_sha256=record['subset_sha256'],actual_embedded_font_program_sha256=hashlib.sha256(embedded).hexdigest(),exact_original_role_font_subset_embedded=ok))
   if not ok:errors.append(dict(role=face,error='Actual new language font differs from the reviewed exact source-role donor subset'))
   font_data[face]=dict(gid=gid,advance=adv,alias=alias)
  expected=[];row_checks=[];word_streams=0
  for row in q['rows']:
   # The true source glyphs, not a mutable plan's alleged size, determine
   # the original prose role, point, colour and physical baseline.
   hans=[source_glyphs[g['source_trace_index']]for g in row['erase_glyphs']if re.search('[\u3400-\u9fff]',g['c'])];assert hans
   assert all(g['size']==row['size']and FACES[g['font']]==row['source_prose_face']and abs(g['origin'][1]-row['baseline'])<1.05 for g in hans)
   assert tuple(row['source_prose_color'])==Counter(tuple(g['color'])for g in hans).most_common(1)[0][0]
   tag_index={(14,'r02'):56,(14,'r10'):461}.get((n,row['id']));literal=None;tag_color=None
   if tag_index is not None:
    source_tag=source_glyphs[tag_index];assert source_tag['c']=='图'and list(source_tag['color'])==[1.,0.,1.]and source_tag['font']=='ËÎÌå+FPEF'
    literal='그림'if lang=='ko'else'Fig.';assert row[lang].count(literal)==1
    binding=row['source_prose_color_literals'];assert len(binding)==1 and binding[0][lang]==literal and binding[0]['source_glyph']['source_trace_index']==tag_index
    assert binding[0]['source_glyph']['c']==source_tag['c']and binding[0]['source_glyph']['origin']==list(source_tag['origin'])and binding[0]['source_glyph']['color']==list(source_tag['color']);tag_color=list(source_tag['color'])
   else:assert not row.get('source_prose_color_literals')
   fd=font_data[row['source_prose_face']];point=row['size'];parts=[];width=0
   for text in re.split(r'(\[\[\d+\]\])',row[lang]):
    if not text:continue
    if text.startswith('[['):a=row['native_atoms'][int(text[2:-2])];w=a['rect'][2]-a['rect'][0];parts.append((None,w))
    else:w=sum(point/4 if ch==' 'else fd['advance'][ord(ch)]*point for ch in text);parts.append((text,w))
    width+=w
   x=row['original_center']-width/2 if row.get('align')=='center'else row['left'];start=x;lo,hi=row['allowed_horizontal'];assert lo-.001<=x and x+width<=hi+.001
   for text,w in parts:
    if text is None:x+=w;continue
    word_streams+=len([ch for ch in text if ch!=' '])
    colored_at=text.find(literal)if literal else-1
    for char_index,ch in enumerate(text):
     if ch==' ':x+=point/4;continue
     color=tag_color if colored_at>=0 and colored_at<=char_index<colored_at+len(literal)else row['source_prose_color']
     expected.append(dict(row=row['id'],c=ch,gid=fd['gid'][ord(ch)],font_alias=fd['alias'],size=point,origin=[x,row['baseline']],color=color,render_type=0));x+=fd['advance'][ord(ch)]*point
   row_checks.append(dict(row=row['id'],source_size=point,source_baseline=row['baseline'],expected_word_gap_pt=point/4,source_alignment=row.get('align','left'),source_center=row['original_center'],expected_left=start,expected_right=x))
  if len(actual)!=len(expected):errors.append(dict(expected_new_glyphs=len(expected),actual_new_glyphs=len(actual),error='New language glyph omission/duplication'))
  for i,(want,got)in enumerate(zip(expected,actual)):
   problems=[]
   for key in('c','gid','font_alias','render_type'):
    if want[key]!=got[key]:problems.append(key)
   if abs(want['size']-got['size'])>.001:problems.append('original point')
   if max(abs(a-b)for a,b in zip(want['origin'],got['origin']))>.001:problems.append('source baseline/center/word gap or glyph advance')
   color=want['color']*3 if len(want['color'])==1 else want['color']
   if color!=got['color']:problems.append('source prose color')
   if problems:errors.append(dict(index=i,expected=want,actual=got,errors=problems))
  # Retain actual encoded new-word programs as an independent visibility
  # control. No native math, image, white cover or mutable journal is used.
  chunks=list(doc.pages[0].Contents)if isinstance(doc.pages[0].Contents,pikepdf.Array)else[doc.pages[0].Contents];chosen=[];programs=[]
  allowed={'q','Q','BT','ET','Tm','Tf','Tr','Tj','TJ','rg','RG','g','G','w'}
  for stream in chunks:
   raw=stream.read_bytes()
   if b'/C08Translated'not in raw:continue
   ops=list(pikepdf.parse_content_stream(stream));assert all(str(op.operator)in allowed for op in ops),'A new prose word stream must be text-only and unclipped'
   assert any(str(op.operator)in('Tj','TJ')for op in ops);chosen.append(stream);programs.append(hashlib.sha256(raw).hexdigest())
  assert len(chosen)==word_streams,('Exact expected original-font glyph-program count changed',len(chosen),word_streams)
  folder=B/'evidence/new-prose-native-program-references';folder.mkdir(parents=True,exist_ok=True);reference=folder/f'page{n:02}-{lang}-{sha(target)[:16]}.pdf'
  with pikepdf.Pdf.new()as out:
   out.pages.append(doc.pages[0]);pg=out.pages[0];pg.Contents=pikepdf.Array([s for s in(list(pg.Contents)if isinstance(pg.Contents,pikepdf.Array)else[pg.Contents])if b'/C08Translated'in s.read_bytes()]);out.save(reference,compress_streams=False)
 with f.open(reference)as ref,f.open(target)as final:
  a=ref[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);b=final[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,3);ink=aa.min(2)<255;rgb_errors=int((np.any(aa!=bb,2)&ink).sum());missing=int(((aa.min(2)<32)&(bb.min(2)>=220)).sum())
 rgb_rows=[]
 if rgb_errors:
  yy,xx=np.nonzero(np.any(aa!=bb,2)&ink);rgb_rows=[dict(point=[float(x/4),float(y/4)],original_new_font_reference_RGB=aa[y,x].tolist(),actual_proof_RGB=bb[y,x].tolist())for y,x in list(zip(yy,xx))[:100]]
 result=dict(original_source_sha256=SHA,source_page=n,language=lang,proof_sha256=sha(target),actual_producing_plan_sha256=c['plan_sha256'],new_original_role_font_programs=fonts,actual_new_encoded_glyphs_checked=len(expected),actual_expected_original_role_glyph_programs=word_streams,source_point_baseline_center_and_quarter_em_word_gap_rows=row_checks,errors=errors,actual_original_new_glyph_program_sha256s=programs,new_prose_native_program_reference_sha256=sha(reference),reference_path=str(reference),actual_new_font_native_reference_dark_pixels=int((aa.min(2)<32).sum()),missing_actual_new_font_native_ink_pixels=missing,nonwhite_actual_new_font_native_RGB_errors=rgb_errors,raw_actual_new_font_native_RGB_differences=rgb_rows,reference_has_only_actual_encoded_new_language_glyph_programs=True,original_math_or_PDF_modified_by_audit=False,passed=not errors and missing==0 and rgb_errors==0)
 out=target.with_suffix('.new-prose-style-spacing-visibility.json')
 if out.exists():
  h=B/'history/previous-new-prose-audits';h.mkdir(parents=True,exist_ok=True);(h/f'{n:02}-{lang}-{sha(out)}.json').write_bytes(out.read_bytes())
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print('C08_ACTUAL_NEW_PROSE_SOURCE_POINT_ROLE_BASELINE_CENTER_GAPS_NATIVE_INK',n,lang,'pass',result['passed'],'glyphs',len(expected),'layout_errors',len(errors),'missing',missing,'RGB',rgb_errors,flush=True);return result
if __name__=='__main__':
 sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools');from pdf_memory_gate import page_worker
 with page_worker():audit(int(sys.argv[1]),sys.argv[2])
