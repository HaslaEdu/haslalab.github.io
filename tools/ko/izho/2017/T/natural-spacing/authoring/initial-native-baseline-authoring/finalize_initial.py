from pathlib import Path
import sys,json,hashlib,shutil,time
import pymupdf as fitz
B=Path(__file__).resolve().parent;E=B/'engine';M=B.parent/'izho-natural-spacing';C=Path.cwd()/'tools';sys.path[:0]=[str(E),str(C),str(M)]
from pdf_memory_gate import page_worker
from initial_final_prose_outline_audit import audit as outline_audit
from initial_source_language_coverage import audit as language_coverage
from initial_prose_reading_order import journal
from izho_natural_spacing import records
from pdf_korean_natural_composer import normalize_placements
from pdf_native_widget_motion_audit import audit_plan as widget_audit
from pdf_display_equation_numbers import audit as number_audit
import importlib.util
_ready_spec=importlib.util.spec_from_file_location('initial_private_ready',E/'izho_natural_spacing_ready.py')
_ready_module=importlib.util.module_from_spec(_ready_spec);_ready_spec.loader.exec_module(_ready_module)
ready=_ready_module.ready
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
year=int(sys.argv[1]);f=B/f'natural/{year}/T';count={2012:6,2017:7}[year]
reviews=load(f/'visual-review.json')['pages'];assert len(reviews)==count
collisions=[];outlines=[];numbers=[];widgets=[];locked=[];languages=[];labels=[];cache={}
for i in range(1,count+1):
 pp=f/f'plans/page{i:02}.json';plan=load(pp);proof=f/f'page{i:02}.pdf';a=load(proof.with_suffix('.audit.json'));c=load(proof.with_suffix('.prose-collision.json'));q=load(proof.with_suffix('.qa.json'))
 assert a['passed']and a['output_sha256']==sha(proof);assert c['passed']and c['final_sha256']==sha(proof)
 assert q['initial_prose_source_slot_reading_order'];assert reviews[i-1]['page']==i and reviews[i-1]['reviewed']and reviews[i-1]['proof_sha256']==sha(proof)
 extra=''.join(s['text']for s in plan.get('reviewed_bitmap_language_labels',[]))
 with page_worker():o=outline_audit(plan['source_base'],i,proof,plan['prose_placements'],cache,extra_text=extra,word_revisions=plan.get('hangul_word_revisions'))
 assert o['passed'];proof.with_suffix('.initial-new-prose-outlines.json').write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf8');outlines.append(o);time.sleep(.6)
 n=number_audit(plan,proof);assert n['passed'];numbers.append(dict(page=i,proof_sha256=sha(proof),source_sha256=plan['original_english_source_sha256'],**n))
 w=widget_audit(pp);assert not w['nonrigid_candidate_groups'];widgets.append(w)
 lc=language_coverage(B/f'{year}/original_style/page{i}.json');assert lc['passed'];languages.append(lc)
 with fitz.open(plan['source_base'])as base,fitz.open(proof)as final:
  before=records(base[i-1]);js=journal(base[i-1],normalize_placements(base[i-1],plan['prose_placements']));tail_count=sum(len(j['glyphs'])for j in js);prefix=before[:-tail_count];after=records(final[0]);groups=[]
  for rect in plan['frozen_display_math_rects']:
   old=[g for g in prefix if g['c'].strip()and g['gid']>=0 and rect[0]<=g['origin'][0]<=rect[2]and rect[1]<=g['origin'][1]<=rect[3]];bad=[]
   for g in old:
    match=[h for h in after if h['c']==g['c']and h['font']==g['font']and h['gid']==g['gid']and h['paint']==g['paint']and abs(h['size']-g['size'])<1e-6 and max(abs(u-v)for u,v in zip(h['origin'],g['origin']))<=.001]
    if not match:bad.append(g)
   assert not bad,(i,rect,bad)
   groups.append(dict(rect=rect,source_original_glyphs_checked=len(old),font_gid_size_paint_x_y_mismatches=bad,passed=True))
  locked.append(dict(page=i,proof_sha256=sha(proof),original_source_sha256=plan['original_english_source_sha256'],groups=groups,passed=True))
 collisions.append(c)
 if a.get('reviewed_bitmap_language_labels')or a.get('reviewed_native_figure_language_labels'):
  labels.append(dict(page=i,proof_sha256=sha(proof),bitmap=a.get('reviewed_bitmap_language_labels'),native=a.get('reviewed_native_figure_language_labels'),figure_pixel_audits=a['figure_pixel_audits'],native_graphics_audit=a['native_graphics_motion_audit']))
 print('INDEPENDENT_FINAL_CHECK',year,i,flush=True)
outputs={'independent-new-prose-collision-audits.json':dict(pages=collisions,passed=True),'initial-new-prose-outline-audits.json':dict(pages=outlines,passed=True),'final-display-equation-number-audit.json':dict(pages=numbers,passed=True),'tight-native-widget-motion-audit.json':dict(pages=widgets,passed=True),'original-displays-stationary.json':dict(pages=locked,passed=True),'source-language-coverage.json':dict(pages=languages,passed=True),'figure-language-and-nonlanguage-pixel-audits.json':dict(pages=labels,passed=True)}
for name,data in outputs.items():(f/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
if '--resume-assembled' in sys.argv:
 m=load(B/f'natural/editions/IZhO_{year}_T_KO.ready.json')
 assert m['status']=='READY' and m['sha256']==sha(m['output']) and m['pages']==count
 assert len(m['page_audits'])==count
 for row in m['page_audits']:
  assert row['proof_sha256']==sha(f/f'page{row["page"]:02}.pdf') and row['joined_vs_reviewed_proof_changed_pixels']==0
else:m=ready(year,'T',serialize_page_renders=True)
s=Path(m['authoring_snapshot']);dest=s/'independent-additional-audits';dest.mkdir(exist_ok=True)
for name in outputs:
 p=f/name;t=dest/name;shutil.copyfile(p,t);m[name.removesuffix('.json').replace('-','_')]=dict(path=str(t),sha256=sha(t),passed=True)
sources={E:['izho_initial_fixed_style.py','initial_prose_reading_order.py','test_initial_prose_reading_order.py','initial_final_prose_outline_audit.py','izho_initial_outline_qa.py','izho_math_type_table_prepare.py','initial_source_language_coverage.py','initial_bitmap_language_labels.py','initial_native_figure_language.py','test_initial_bitmap_language_labels.py','test_partial_authored_spacing.py'],M:['pdf_display_equation_numbers.py','pdf_native_widget_motion_audit.py','modern_new_prose_collision_audit.py'],C:['pdf_original_style_fonts.py','pdf_original_text_ops.py','pdf_original_style_audit.py','pdf_new_prose_native_text_overlap.py','pdf_new_hangul_graphics_overlap.py','pdf_raster_font_measure.py','pdf_original_image_ink.py','pdf_original_graphics_ink.py','izho_early_fixed_style.py']}
sources[E].append('initial_original_pattern_images.py')
for base,names in sources.items():
 for name in names:
  p=base/name
  if not p.exists():
   p=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tools')/name
  t=s/'tools'/name;shutil.copyfile(p,t);m['authoring_files'][str(t.relative_to(s))]=sha(t)
original=s/f'tools/ko/izho/{year}/T/original_style';original.mkdir(parents=True,exist_ok=True)
for pp in(B/f'{year}/original_style').glob('page*.json'):shutil.copyfile(pp,original/pp.name)
history=s/'initial-native-baseline-authoring';history.mkdir(exist_ok=True)
for pp in(E/'source-history').glob('*.py'):shutil.copyfile(pp,history/pp.name)
for i in range(1,count+1):shutil.copyfile(B/f'{year}/native-baseline/page{i:02}.qa.json',history/f'page{i:02}.qa.json')
for pp in [B/'build_initial_page.py',B/f'prepare_{year}.py',B/'coalesce_initial_scopes.py',B/'build_natural_initial.py',B/'audit_initial_page.py',Path(__file__)]:shutil.copyfile(pp,history/pp.name)
if year==2017:
 for pp in [B/'witness_2017_T_page1_all_native.py',Path('D:/CodexBuilds/refine-izho2017-translation-lines.py'),Path('D:/CodexBuilds/refine-izho2017-remaining-overflows.py'),Path('D:/CodexBuilds/refine-izho2017-natural-scopes.py'),Path('D:/CodexBuilds/revise-izho2017-page5-staging.py'),Path('D:/CodexBuilds/enable-izho2017-native-cid-profile.py'),Path('D:/CodexBuilds/test-izho2017-original-cid-witness.py')]:shutil.copyfile(pp,history/pp.name)
 for name in ['translation-row-revision','translation-row-revision-2','translation-row-revision-3','source-native-witness-regressions']:
  source=B/'2017'/name
  if source.exists():
   for pp in source.rglob('*'):
    if pp.is_file()and pp.suffix in ['.json','.py','.log']:
     target=history/name/pp.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(pp,target)
 native=load(f/'all-original-CID-witness/witness.json');assert native['passed']and native['source_native_glyphs']==96
 regression=load(B/'2017/source-native-witness-regressions/regression.json');assert regression['passed']and regression['publication_pdf_unmodified']
 m['original_native_CID_regressions']=dict(passed=True,source_native_glyphs=96,original_font_reference_scales=[4,8,12],actual_white_cover_rejected=True,source_proof_sha256=regression['source_proof_sha256'])
 m['note']='Page1 retains its raw unhinted-SVG 4x diagnostic3-pixel delta. All96 original encoded source-font CID paints are independently matched and have zero missing actual native-font reference ink at4x,8x and12x; an analysis-only white cover over an original word is rejected. Every other page passes the ordinary source-ink check. Exact per-page evidence is frozen; the delivered PDF is unmodified.'
assembly_render=Path(sys.modules[_ready_module.fresh_render.__module__].__file__)
shutil.copyfile(assembly_render,history/'assembly-actual-fresh-render-engine.py')
m['assembly_render_engine']=dict(source=str(assembly_render),snapshot=str(history/'assembly-actual-fresh-render-engine.py'),sha256=sha(assembly_render))
evidence=B/f'{year}/source-figure-review'
if evidence.exists():shutil.copytree(evidence,s/'source-figure-review',dirs_exist_ok=True)
if year==2012:
 log=B/'bitmap-label-tests.log';assert 'OK'in log.read_text('utf8');shutil.copyfile(log,dest/log.name)
 m['bitmap_label_regressions']=dict(passed=True,cases=2,path=str(dest/log.name),sha256=sha(dest/log.name),negative_case='New measured-size label moved into original gray piston drawing is rejected; positive actual-image words-only case retains original image/font programs and actual nonlanguage pixels.')
m.update(initial_native_baseline_authoring=dict(path=str(original),history=str(history),baseline_is_not_deliverable=True,staging_only_prose_overlap_removed_in_final=True,source_slot_semantic_order_verified=True),new_prose_actual_outline_empty_count=sum(len(o['actual_embedded_gid_empty_outlines'])for o in outlines),all_new_prose_nonspace_glyphs_checked=sum(o['new_prose_nonspace_glyphs_checked']for o in outlines),new_native_ascii_prose_glyphs_checked=sum(o['new_native_ascii_prose_glyphs_checked']for o in outlines),new_prose_dark_pixels_over_original_native_text=sum(c['native_text_overlap']['dark_prose_pixels_over_native_text']for c in collisions),new_prose_dark_pixels_over_native_graphics=sum(c['native_graphics_overlap']['new_hangul_dark_pixels_over_native_foreground']for c in collisions),original_display_equation_markers_checked=sum(n['original_display_equation_markers']for n in numbers),original_display_equation_marker_glyphs_checked=sum(n['original_display_equation_marker_glyphs']for n in numbers),fully_stationary_original_display_glyphs_checked=sum(g['source_original_glyphs_checked']for r in locked for g in r['groups']))
m['figure_pixel_comparison_policy']='Original full figure compared at 4x. Explicitly translated source/native language ink and final Korean glyph outlines only are mutable; all nonlanguage foreground/background pixels remain identical, including inside reviewed word regions. Raw whole-figure changes and intentional language-only changes are reported separately.'
m['source_language']='Russian'if year==2012 else'English';m['translated_figure_language_labels']=sum((r.get('bitmap')or{}).get('labels',0)+len((r.get('native')or{}).get('labels',[]))for r in labels)
# Every late independent report, source review and producing script is part of
# the immutable snapshot, including additions made after ready() captured it.
m['authoring_files']={p.relative_to(s).as_posix():sha(p)for p in s.rglob('*')if p.is_file()}
Path(m['output']).with_suffix('.ready.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8');print('FINAL_READY',m['output'],m['sha256'],m['bytes'],flush=True)
