"""Publish source-defined heading moves above immutable reviewed editions."""
from pathlib import Path
import sys,json,hashlib,shutil,re
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text('utf8'))
def save(p,q):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(source,target):
 source=Path(source)
 if source.resolve()==target.resolve():return
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);assert sha(source)==sha(target)
def stage(manifest,root,release):
 q=load(manifest);assert q['status']=='READY'and q['schema']=='reviewed-heading-alignment-v1'
 common=root/'tools/ko/izho';author=common/'heading-alignment/natural-spacing/authoring';shared={}
 for rel,digest in q['authoring_snapshot']['files'].items():
  external=q['authoring_snapshot'].get('external_inputs',{}).get(rel)
  src=Path(external['path'])if external else Path(q['authoring_snapshot']['root'])/rel
  assert sha(src)==digest;target=author/rel;copy(src,target);shared[target.relative_to(common).as_posix()]=digest
 registry=load(root/'tools/original_style_publication.json');fonts=load(root/'tools/translation_font_validation.json')
 for edition in q['editions']:
  pdf=Path(edition['output']);assert sha(pdf)==edition['sha256']and pdf.stat().st_size==edition['bytes']
  prior=next(r for r in registry if r['file']==pdf.name);assert prior==edition['baseline_item']
  dest=common/f"{edition['year']}/{edition['kind']}/natural-spacing/heading-alignment"
  allowed=set(edition['scoped_authoring_files'])
  files={k:v for k,v in shared.items()if not any('/'+name+'/'in k for name in ['immutable-inputs','original-language','original-plans'])or k.removeprefix('heading-alignment/natural-spacing/authoring/')in allowed}
  def pinned(row,name):
   assert sha(row['path'])==row['sha256'];target=dest/name;copy(row['path'],target);files[target.relative_to(common).as_posix()]=row['sha256'];return dict(path=target.relative_to(root).as_posix(),sha256=row['sha256'])
  pages=[]
  for page in edition['proofs']:
   row={k:page[k]for k in ['page','proof_sha256','proof_index']}
   if 'alignment_qa'in page:row['alignment_qa']=pinned(page['alignment_qa'],f"page{page['page']:02}-alignment.json")
   pages.append(row)
  wrapper=dict(status='READY',file=pdf.name,year=edition['year'],kind=edition['kind'],language='ko',pages=edition['pages'],sha256=edition['sha256'],bytes=edition['bytes'],aligned_headings=edition['aligned_headings'],baseline_item=prior,baseline_publication=pinned(edition['baseline_publication'],'baseline-publication.json'),source_ready=pinned(dict(path=str(manifest),sha256=sha(manifest)),'source-ready.json'),assembly_qa=pinned(edition['assembly_qa'],'assembly-qa.json'),visual_review=pinned(edition['visual_review'],'visual-review.json'),negative_control=pinned(q['negative_control'],'negative-control.json'),page_proofs=pages,authoring_snapshotroot=common.relative_to(root).as_posix(),authoring_snapshot_sha256=files,complete_existing_headings_moved_horizontally_only=True,fonts_points_paint_baselines_math_images_and_other_page_content_retained=True)
  save(dest/'publication.json',wrapper)
  item=dict(prior,sha256=edition['sha256'],bytes=edition['bytes'],generated_file=str(pdf),qa=(dest/'publication.json').relative_to(root).as_posix(),audit_schema=q['schema'])
  registry=[r for r in registry if r['file']!=pdf.name]+[item]
  record=next(r for r in fonts['files']if r['file']==pdf.name);record.update(bytes=edition['bytes'],sha256=edition['sha256'],source_heading_alignment_reviewed=True)
  copy(pdf,release/pdf.name);print('STAGED',pdf.name,edition['aligned_headings'],edition['sha256'],flush=True)
 save(root/'tools/original_style_publication.json',sorted(registry,key=lambda r:r['file']));save(root/'tools/translation_font_validation.json',fonts)
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: stage_reviewed_heading_alignment.py READY.json RELEASE_DIRECTORY')
 stage(Path(sys.argv[1]),Path.cwd(),Path(sys.argv[2]))
