"""Stage immutable native-object translations, final label overlays, and raw QA."""
from pathlib import Path
import sys,json,hashlib,shutil
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(source,target):
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);assert sha(source)==sha(target)

def stage(manifest,root,release):
 q=json.loads(manifest.read_text('utf8'))
 assert q['status']=='READY'and q['schema']=='native-original-preserved-v1'
 for key in ['original_math_retyped','original_math_resampled','original_math_y_changed','translated_point_sizes_fitted']:assert q[key]is False
 assert q['added_editorial_notes']==0
 base=root/f"tools/ko/{q['competition']}/{q['year']}/{q['kind'].lower()}/natural-spacing/native-original"
 registry=json.loads((root/'tools/original_style_publication.json').read_text('utf8'))
 fonts=json.loads((root/'tools/translation_font_validation.json').read_text('utf8'))
 shared={}
 for snapshot in q['authoring_snapshots']:
  for rel,digest in snapshot['files'].items():
   source=Path(snapshot['root'])/rel;assert sha(source)==digest
   target=base/'authoring'/snapshot['name']/rel;copy(source,target)
   shared[target.relative_to(base).as_posix()]=digest
 for edition in q['editions']:
  pdf=Path(edition['output']);assert sha(pdf)==edition['sha256']and pdf.stat().st_size==edition['bytes']
  language=edition['language'];dest=base/language;frozen=dict(shared)
  def ref(source,name):
   source=Path(source);target=dest/name;copy(source,target)
   digest=sha(source);frozen[target.relative_to(base).as_posix()]=digest
   return dict(path=target.relative_to(root).as_posix(),sha256=digest)
  def pinned(row,name):
   assert sha(row['path'])==row['sha256'];return ref(row['path'],name)
  pages=[]
  for page in edition['proofs']:
   assert sha(page['pdf'])==page['sha256']
   row={k:page[k]for k in['page','source_page','body_sha256']};row['proof_sha256']=page['sha256']
   for key in ['body_qa','actual_style_qa','figure_language_qa','body_composition','figure_composition']:
    row[key]=pinned(page[key],f"page{page['page']:02}-{key}.json")
   pages.append(row)
  wrapper=dict(status='READY',file=pdf.name,year=q['year'],kind=q['kind'],language=language,pages=edition['pages'],bytes=edition['bytes'],sha256=edition['sha256'],source_original_sha256=q['source_original_sha256'],page_proofs=pages,source_ready=ref(manifest,'source-ready.json'),visual_review=pinned(edition['visual_review'],'visual-review.json'),assembly_qa=pinned(edition['assembly_qa'],'assembly-qa.json'),source_word_component_review=pinned(q['source_word_component_review'],'source-word-component-review.json'),caption_background_negative_control=pinned(q['caption_background_negative_control'],'caption-background-negative-control.json'),authoring_snapshotroot=base.relative_to(root).as_posix(),authoring_snapshot_sha256=frozen)
  for key in ['original_math_retyped','original_math_resampled','original_math_y_changed','translated_point_sizes_fitted','added_editorial_notes']:wrapper[key]=q[key]
  save(dest/'publication.json',wrapper)
  old=next((r for r in registry if r['file']==pdf.name),{})
  aliases=old.get('aliases',[])
  if language=='en':aliases=sorted(set([*aliases,f"CPhO_{q['year']}_{q['kind']}_BAUPC_EN.pdf"]))
  item=dict(file=pdf.name,language=language,pages=edition['pages'],bytes=edition['bytes'],sha256=edition['sha256'],qa=(dest/'publication.json').relative_to(root).as_posix(),generated_file=str(pdf),audit_schema=q['schema'])
  if aliases:item['aliases']=aliases
  registry=[r for r in registry if r['file']!=pdf.name]+[item]
  for name in [pdf.name,*aliases]:
   record=next((r for r in fonts['files']if r['file']==name),None)
   if record is None:record=dict(file=name);fonts['files'].append(record)
   record.update(pages=edition['pages'],bytes=edition['bytes'],sha256=edition['sha256'],missing_glyph_spans=[],original_style=True,natural_spacing=True,native_original_preserved=True)
   copy(pdf,release/name)
  print('Staged',pdf.name,edition['sha256'],flush=True)
 save(root/'tools/original_style_publication.json',sorted(registry,key=lambda r:r['file']))
 save(root/'tools/translation_font_validation.json',fonts)

if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: stage_native_original_publication.py READY.json RELEASE_DIRECTORY')
 stage(Path(sys.argv[1]),Path.cwd(),Path(sys.argv[2]))
