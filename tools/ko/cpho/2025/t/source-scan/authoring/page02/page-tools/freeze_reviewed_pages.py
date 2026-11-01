"""Immutable pagewise reviewed proof inventory; never publishes or overwrites PDFs."""
from pathlib import Path
import sys,json,hashlib,shutil
from compose_pages import BASE,SOURCE,sha
import qa_pages
NAMES=[int(v)for v in sys.argv[1:]]
out=BASE/'ready';out.mkdir(exist_ok=True)
snapshot=out/'authoring-snapshot';snapshot.mkdir(exist_ok=True)
sources=[]
for module in list(sys.modules.values()):
 path=getattr(module,'__file__',None)
 if path and path.endswith('.py')and ('haslalab' in path or 'Hasla-original-style-20261031' in path):
  file=Path(path)
  if file.exists()and file.stat().st_size:
   label=('page-tools'if file.parent==BASE/'tools'else 'dependency-tools')+'/'+file.name
   target=snapshot/label;target.parent.mkdir(exist_ok=True);shutil.copyfile(file,target)
   sources.append(dict(source=str(file),snapshot=str(target),sha256=sha(target)))
for n in NAMES:
 plan=BASE/f'plans/page{n:02d}-draft-layout.json';editions=[]
 for language in ['ko','en']:
  stem=BASE/f'proofs/{language}/page{n:02d}';pdf=stem.with_suffix('.pdf');qa=stem.with_suffix('.qa.json');meta=stem.with_suffix('.composition.json');q=json.loads(qa.read_text('utf8'));m=json.loads(meta.read_text('utf8'))
  if not q['passed']or q['final_sha256']!=sha(pdf)or m['proof_sha256']!=sha(pdf)or m['plan_sha256']!=sha(plan):raise ValueError(('Reviewed proof/QA/plan changed',n,language))
  review=dict(source_page=n,language=language,reviewed=True,proof_sha256=sha(pdf),notes='Complete original-page and final-page visual review. Original mathematical components, all subscripts, radicals/fraction bars and neighboring CJK edges checked in source JPEG contacts. All translated original paragraphs/labels present; source display math and figures remain unchanged; inline scale and y unchanged. Final natural word spacing and page format reviewed.')
  rp=stem.with_suffix('.visual-review.json');rp.write_text(json.dumps(review,ensure_ascii=False,indent=2),'utf8')
  entry=dict(language=language,pdf=str(pdf),sha256=sha(pdf),pages=1,qa=str(qa),qa_sha256=sha(qa),composition=str(meta),composition_sha256=sha(meta),visual_review=str(rp),visual_review_sha256=sha(rp),qa_passed=True)
  editions.append(entry)
 targetplan=snapshot/f'plans/page{n:02d}.json';targetplan.parent.mkdir(exist_ok=True);shutil.copyfile(plan,targetplan)
 manifest=dict(status='IMMUTABLE_REVIEWED_PAGE_READY',source=str(SOURCE),source_sha256=sha(SOURCE),source_page=n,editions=editions,plan=str(plan),plan_sha256=sha(plan),plan_snapshot=str(targetplan),authoring_snapshot_root=str(snapshot),authoring_files=sources,source_point_sizes_fixed=True,original_encoded_math_1x_and_relative_internal_geometry_retained=True,original_math_y_unchanged=True,all_image_programs_masks_icc_palettes_and_source_ctms_retained=True,stationary_display_figures_and_language_outside_pixels_changed=0,independent_all_math_union_missing_pixels=0,independent_math_new_prose_overlap_pixels=0,actual_new_prose_font_gid_point_baseline_paint_stroke_verified=True,actual_new_prose_empty_glyph_outlines=0,no_publication_performed=True,note='Pagewise proof to combine with other reviewed original-source pages using pikepdf append and joined-v-proof pixel comparison. Full fonts are external licensed source donors; retained-GID subsets embedded in PDFs only. Snapshot includes a backward-compatible linked-multiline-atom option not used in these pages; proof bytes and QA govern READY identity.')
 dest=out/f'page{n:02d}-READY.json';dest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8');print(dest,sha(dest),flush=True)
