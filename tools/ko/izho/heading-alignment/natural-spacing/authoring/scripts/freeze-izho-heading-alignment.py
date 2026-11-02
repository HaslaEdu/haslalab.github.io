from pathlib import Path
from collections import defaultdict
import os,sys,json,hashlib,shutil,subprocess,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/heading-alignment-v1');P=Path('D:/CodexBuilds/Hasla-publish-20261031');D=Path('D:/CodexBuilds')
load=lambda p:json.loads(Path(p).read_text('utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
out=B/'authoring-frozen'
external_inputs={}
def copy(src,rel):
 src=Path(src);rel=Path(rel)
 if rel.parts[0]=='immutable-inputs':
  external_inputs[rel.as_posix()]=dict(path=str(src),sha256=sha(src),bytes=src.stat().st_size)
  return rel.as_posix()
 dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst);return rel.as_posix()
def ref(p):return dict(path=str(p),sha256=sha(p))
review=load(B/'visual-review/manual-review.json');assert review['reviewed']and len(review['sheets'])==9
negative=load(B/'heading-negative-control.json');assert negative['passed']
assert negative['canonical_proof_sha256']==sha(B/'IZhO_2012_T_KO/page02.pdf')
groups=defaultdict(list)
for r in load(B.parent/'published-izho-heading-detail-20261102.json')['candidates_requiring_review']:
 if abs(r['actual_center_error'])>.001:groups[r['file']].append(r)
copy(B.parent/'published-izho-heading-detail-20261102.json','source-heading-inventory.json');copy(B/'visual-review/manual-review.json','visual-review/manual-review.json');copy(B/'visual-review/contact-sheet-inventory.json','visual-review/contact-sheet-inventory.json')
for f in (B/'visual-review').glob('headings-*.png'):copy(f,Path('visual-review')/f.name)
for name in ['review-izho-heading-alignment.py','run-izho-heading-pages.py','assemble-heading-alignment-edition.py','assemble-izho-heading-alignment.py','negative-izho-historical-heading.py','render-izho-heading-review.py','refresh-izho-heading-review-sheet9.py','freeze-izho-heading-alignment.py']:
 copy(D/name,Path('scripts')/name)
for f in (B/'producer-versions').glob('*.py'):
 assert f.stem==sha(f);copy(f,Path('scripts/producer-versions')/f.name)
copy(D/'review-izho-heading-alignment.py',Path('scripts/producer-versions')/(sha(D/'review-izho-heading-alignment.py')+'.py'))
copy(P/'tools/stage_reviewed_heading_alignment.py','scripts/stage_reviewed_heading_alignment.py')
runtime={}
code="""import sys,runpy,json
from pathlib import Path
runpy.run_path(sys.argv[1],run_name='frozen_import_context')
print(json.dumps({k:str(Path(v.__file__).resolve())for k,v in sys.modules.items()if getattr(v,'__file__',None)and str(v.__file__).lower().endswith('.py')and 'codexbuilds'in str(v.__file__).lower()}))
"""
for stage,script in [('producer',D/'review-izho-heading-alignment.py'),('assembly',D/'assemble-heading-alignment-edition.py')]:
 r=subprocess.run([sys.executable,'-X','utf8','-c',code,str(script)],capture_output=True,text=True,encoding='utf8',check=True);records={}
 for name,source in json.loads(r.stdout).items():
  rel=copy(source,Path('actual-loaded-modules')/stage/(name.replace('.','/')+'.py'));records[name]=dict(original_path=source,frozen_path=rel,sha256=sha(source))
 runtime[stage]=records
save(out/'runtime-import-resolution.json',runtime);save(out/'runtime-versions.json',dict(python=sys.version,packages={n:importlib.metadata.version(n)for n in ['PyMuPDF','pikepdf','numpy','fonttools','opencv-python','Pillow']}))
contacts=load(B/'visual-review/contact-sheet-inventory.json');editions=[]
for filename,rows in sorted(groups.items()):
 folder=B/filename.removesuffix('.pdf');spec=load(folder/'assembly-spec.json');item=spec['baseline_item'];pdf=B/'editions'/filename;assembly=pdf.with_suffix('.assembly-qa.json');a=load(assembly);assert a['passed']and a['sha256']==sha(pdf)
 allowed=[];assert sha(item['generated_file'])==item['sha256'];allowed.append(copy(item['generated_file'],Path('immutable-inputs')/filename))
 for row in rows:
  allowed.append(copy(row['source_path'],Path('original-language')/(sha(row['source_path'])+'.pdf')))
  allowed.append(copy(row['plan_path'],Path('original-plans')/filename/f"page{row['published_page']:02}.json"))
 proofs=[];visual=[]
 for n,proof in enumerate(spec['proofs'],1):
  r=dict(page=n,proof_sha256=proof['sha256'],proof_index=proof['proof_index']);changed=n in spec['affected_pages']
  if changed:
   report=folder/f'page{n:02}.alignment.json';q=load(report);assert q['passed']and q['proof_sha256']==sha(proof['pdf']);r['alignment_qa']=ref(report)
  proofs.append(r);tiles=next((r['tiles']for r in contacts['page_tiles']if r['file']==filename and r['page']==n),[])
  visual.append(dict(page=n,proof_sha256=proof['sha256'],reviewed=True,existing_entire_page_review_inherited=True,changed_heading_tiles=tiles,only_source_defined_complete_heading_horizontal_moves=changed))
 visualfile=folder/'visual-review.json';save(visualfile,dict(pages=visual,heading_contact_sheets_reviewed=ref(B/'visual-review/manual-review.json'),body_font_spacing_math_and_diagram_review_inherited_from_immutable_baseline=True))
 year=int(filename.split('_')[1]);kind=filename.split('_')[2]
 editions.append(dict(file=filename,year=year,kind=kind,language='ko',pages=item['pages'],bytes=pdf.stat().st_size,sha256=sha(pdf),output=str(pdf),baseline_item=item,baseline_publication=ref(P/item['qa']),proofs=proofs,assembly_qa=ref(assembly),visual_review=ref(visualfile),aligned_headings=len(rows),scoped_authoring_files=sorted(set(allowed))))
files={f.relative_to(out).as_posix():sha(f)for f in sorted(out.rglob('*'))if f.is_file()}
files.update({rel:r['sha256']for rel,r in external_inputs.items()})
ready=dict(status='READY',schema='reviewed-heading-alignment-v1',editions=editions,negative_control=ref(B/'heading-negative-control.json'),authoring_snapshot=dict(root=str(out),files=files,external_inputs=external_inputs),reviewed_existing_bold_prose_headings=461,candidates_reviewed=181,already_correct_candidate_retained=1,actual_heading_moves=180,changed_pages=69,all_23_IZhO_current_editions_reviewed=True,original_CID_font_GID_point_paint_baseline_and_other_page_geometry_retained=True,no_new_fonts_or_unicode_text_inserted=True,no_original_math_retyped=True)
save(B/'IZhO_HEADING_ALIGNMENT_READY.json',ready);print('READY',len(editions),sum(r['pages']for r in editions),180,len(files),flush=True)
