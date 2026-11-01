"""Layer audited figure translations over immutable reviewed natural editions."""
from pathlib import Path
import sys,json,hashlib,shutil,re
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
def stage(manifest,root,release):
 q=json.loads(manifest.read_text('utf8'));assert q['status']=='READY'and q['schema']=='reviewed-figure-language-v1'
 assert q['body_fonts_and_word_spacing_unchanged']and not q['original_equations_retyped']and not q['new_diagram_geometry']and not q['point_sizes_fitted']and q['added_editorial_notes']==0
 snapshot=q['authoring_snapshot'];common=root/'tools/ko/izho';shared={};namespace=q.get('authoring_namespace','')
 assert not namespace or re.fullmatch('[a-z0-9-]+',namespace)
 for rel,digest in snapshot['files'].items():
  source=Path(snapshot['root'])/rel;assert sha(source)==digest;target=common/'figure-language/natural-spacing/authoring'/namespace/rel;copy(source,target);shared[target.relative_to(common).as_posix()]=digest
 registry=json.loads((root/'tools/original_style_publication.json').read_text('utf8'));fonts=json.loads((root/'tools/translation_font_validation.json').read_text('utf8'))
 for edition in q['editions']:
  pdf=Path(edition['output']);assert sha(pdf)==edition['sha256']and pdf.stat().st_size==edition['bytes']
  dest=common/f"{edition['year']}/{edition['kind']}/natural-spacing/figure-language";files=dict(shared)
  def ref(source,name):
   target=dest/name;copy(source,target);digest=sha(source);files[target.relative_to(common).as_posix()]=digest;return dict(path=target.relative_to(root).as_posix(),sha256=digest)
  def pinned(row,name):assert sha(row['path'])==row['sha256'];return ref(row['path'],name)
  pages=[]
  for page in edition['proofs']:
   assert sha(page['pdf'])==page['sha256'];row={k:page[k]for k in ['page','source_page','body_sha256']};row['proof_sha256']=page['sha256']
   for key in ['figure_language_qa','composition']:row[key]=pinned(page[key],f"page{page['page']:02}-{key}.json")
   if 'actual_font_reference_pdf'in page:row['actual_font_reference_pdf']=pinned(page['actual_font_reference_pdf'],f"page{page['page']:02}-actual-font-reference.pdf")
   pages.append(row)
  wrapper=dict(status='READY',file=pdf.name,year=edition['year'],kind=edition['kind'],language=edition['language'],pages=edition['pages'],sha256=edition['sha256'],bytes=edition['bytes'],baseline_item=edition['baseline_item'],baseline_publication=pinned(edition['baseline_publication'],'baseline-publication.json'),source_ready=ref(manifest,'source-ready.json'),visual_review=pinned(edition['visual_review'],'visual-review.json'),assembly_qa=pinned(edition['assembly_qa'],'assembly-qa.json'),source_word_component_review=pinned(q['source_word_component_review'],'source-word-component-review.json'),negative_control=pinned(q['negative_control'],'real-drawing-negative-controls.json'),page_proofs=pages,authoring_snapshotroot=common.relative_to(root).as_posix(),authoring_snapshot_sha256=files)
  for key in ['body_fonts_and_word_spacing_unchanged','original_equations_retyped','new_diagram_geometry','point_sizes_fitted','added_editorial_notes']:wrapper[key]=q[key]
  save(dest/'publication.json',wrapper)
  item=dict(file=pdf.name,year=edition['year'],language=edition['language'],pages=edition['pages'],bytes=edition['bytes'],sha256=edition['sha256'],qa=(dest/'publication.json').relative_to(root).as_posix(),generated_file=str(pdf),audit_schema=q['schema'])
  registry=[r for r in registry if r['file']!=pdf.name]+[item]
  record=next(r for r in fonts['files']if r['file']==pdf.name);record.update(pages=edition['pages'],bytes=edition['bytes'],sha256=edition['sha256'],missing_glyph_spans=[],original_style=True,natural_spacing=True,figure_language_complete=True)
  copy(pdf,release/pdf.name);print('Staged',pdf.name,edition['sha256'],flush=True)
 save(root/'tools/original_style_publication.json',sorted(registry,key=lambda r:r['file']));save(root/'tools/translation_font_validation.json',fonts)
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: stage_reviewed_figure_language.py READY.json RELEASE_DIRECTORY')
 stage(Path(sys.argv[1]),Path.cwd(),Path(sys.argv[2]))
