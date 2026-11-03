from pathlib import Path
import json,sys,hashlib,pikepdf
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');F=B/'natural/2012/TS';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_native_inline_reposition import inspect_inline_groups
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();numbers=list(map(int,sys.argv[1:]));plans={n:json.loads((F/f'plans/page{n:02}.json').read_text('utf8'))for n in numbers};bases={d['source_base']for d in plans.values()};assert len(bases)==1;base=Path(bases.pop());assert all(d['source_base_sha256']==sha(base)for d in plans.values());controls={};receipts={}
for n,d in plans.items():
 pdf=B/f'2012/native-reference-isolation/{d["source_base_sha256"][:16]}/page{n:02}.pdf'
 if not pdf.exists():continue
 q=json.loads(pdf.with_suffix('.roundtrip.json').read_text('utf8'));assert q['passed']and q['reference_forms_sha256']==sha(pdf)and q['source_base_sha256']==sha(base);assert all(r['changed_RGB_samples']==0 for r in q['renderers'])
 controls[n]=pdf;receipts[n]=json.loads(pdf.with_suffix('.native-cid-qa.json').read_text('utf8'))
assert controls
version=hashlib.sha256((sha(base)+''.join(str(n)+sha(p)for n,p in sorted(controls.items()))).encode()).hexdigest()[:16];target=B/f'2012/native-reference-isolation/IZhO_2012_TS_reference_forms_{version}.pdf'
if not target.exists():
 with pikepdf.open(base)as original,pikepdf.Pdf.new()as out:
  for n,page in enumerate(original.pages,1):
   if n in controls:
    with pikepdf.open(controls[n])as replacement:out.pages.append(replacement.pages[0])
   else:out.pages.append(page)
  out.save(target,compress_streams=False)
for n,d in plans.items():
 old=F/f'plans/page{n:02}.json';history=old.parent/'history'/sha(old)[:16];history.mkdir(parents=True,exist_ok=True)
 if not(history/old.name).exists():(history/old.name).write_bytes(old.read_bytes())
 d['source_base']=str(target);d['source_base_sha256']=sha(target)
 if n in controls:
  inv=inspect_inline_groups(target,n);forms=inv['forms'];groups=receipts[n]['reference_groups'];added=[]
  for group in groups:
   matches=[form for form in forms if form['original_raw_sha256']==group['form_sha256']]
   if len(matches)!=1:raise ValueError('Original source reference Form program not uniquely rejoined')
   form=matches[0];glyphs=[g for g in form['glyphs']if g['c'].strip()];at=group['source_at'];baselines={round(p['source_baseline'],4)for p in d['prose_placements']if p['at']==at};assert len(baselines)==1
   rect=[min(g['bbox'][0]for g in glyphs),min(g['bbox'][1]for g in glyphs),max(g['bbox'][2]for g in glyphs),max(g['bbox'][3]for g in glyphs)]
   rule=dict(reviewed=True,original_source_only=True,rect=rect,font_regex='CambriaMath',baseline=next(iter(baselines)),source_native_glyphs=glyphs,source_form_path=form['path'],source_form_bbox=form['native_page_bbox'],source_form_program_sha256=form['original_raw_sha256'],source_reference_preserve_original_glyph_advance=True,reason='Complete original source reference CIDs and original row clips, fonts, physical points, matrices and paints copied losslessly into one native Form; independent fresh MuPDF4x/8x and Poppler144dpi roundtrips are exact. FormBBox includes source ink safety padding; Korean line width uses the actual unchanged native glyph advance. No Unicode mathematical text or substitute font.')
   d.setdefault('explicit_native_math_atoms',[]).append(rule);added.append(rule)
  d['reviewed_clipped_native_source_reference_forms']=dict(original_base_sha256=receipts[n]['source_sha256'],zero_pixel_roundtrip=controls[n].with_suffix('.roundtrip.json').as_posix(),reference_forms=added)
 from izho_2012_stationary_table_grids import apply as apply_grids
 apply_grids(d)
 old.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('ACTIVATED_EXACT_ORIGINAL_SOURCE_REFERENCE_FORMS',sorted(controls),'FOR_SELECTED_PLANS',numbers,sha(target),flush=True)
