"""Stage an immutable, source-aware scanned translation after full edition QA."""
from pathlib import Path
import sys,json,hashlib,shutil

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)

def stage(manifest,root,release):
 q=json.loads(manifest.read_text('utf8'));assert q['status']=='READY'
 registry=json.loads((root/'tools/original_style_publication.json').read_text('utf8'))
 fonts=json.loads((root/'tools/translation_font_validation.json').read_text('utf8'))
 for edition in q['editions']:
  pdf=Path(edition['output']);assert sha(pdf)==edition['sha256']and pdf.stat().st_size==edition['bytes']
  language=edition['language'];year=q['year'];kind=q['kind'];folder=Path(f'tools/ko/cpho/{year}/{kind.lower()}/source-scan');dest=root/folder/language
  copied={}
  def ref(src,name,selector=None):
   source=Path(src)
   if str(source) in copied:result=dict(copied[str(source)])
   else:
    target=dest/name;copy(source,target);result=dict(path=target.relative_to(root).as_posix(),sha256=sha(source));copied[str(source)]=dict(result)
   if selector:result['selector']=selector
   return result
  snapshots=[]
  for snapshot in q['authoring_snapshots']:
   out=root/folder/'authoring'/snapshot['name'];files=snapshot['files']
   for rel,digest in files.items():
    src=Path(snapshot['root'])/rel;assert sha(src)==digest;copy(src,out/rel)
   snapshots.append(dict(root=out.relative_to(root).as_posix(),files=files))
  pages=[]
  for page in edition['proofs']:
   assert sha(page['pdf'])==page['sha256'];number=page['page'];row=dict(page=number,source_page=page['source_page'],proof_sha256=page['sha256'])
   for key in ['source_scan_qa','actual_style_qa','actual_outline_qa','independent_math_union_qa']+(['hangul_visibility_qa']if language=='ko'else[]):
    source=page[key];assert sha(source['path'])==source['sha256'];row[key]=ref(source['path'],f'page{number:02}-{key}.json',source.get('selector'))
   pages.append(row)
  ready=ref(manifest,'source-ready.json');visual=ref(edition['visual_review'],'visual-review.json');assembly=ref(edition['assembly_qa'],'assembly-qa.json')
  wrapper=dict(status='READY',file=pdf.name,year=year,kind=kind,language=language,pages=edition['pages'],bytes=edition['bytes'],sha256=edition['sha256'],source_original_sha256=q['source_original_sha256'],source_audited_sha256=q['source_audited_sha256'],original_math_retyped=False,original_math_resampled=False,original_math_y_changed=False,translated_point_sizes_fitted=False,added_editorial_notes=0,source_ready=ready,visual_review=visual,assembly_qa=assembly,page_proofs=pages,authoring_snapshots=snapshots)
  if q['source_original_sha256']!=q['source_audited_sha256']:
   source=q['source_normalization_qa'];assert sha(source['path'])==source['sha256'];wrapper['source_normalization_qa']=ref(source['path'],'source-normalization-qa.json')
  for key in ['original_math_retyped','original_math_resampled','original_math_y_changed','translated_point_sizes_fitted']:assert q[key]is False
  assert q['added_editorial_notes']==0
  save(dest/'publication.json',wrapper)
  old=next((r for r in registry if r['file']==pdf.name),{})
  aliases=old.get('aliases',[])
  if language=='en':aliases=sorted(set(aliases+[f'CPhO_{year}_{kind}_BAUPC_EN.pdf']))
  item=dict(file=pdf.name,language=language,pages=edition['pages'],bytes=edition['bytes'],sha256=edition['sha256'],qa=(dest/'publication.json').relative_to(root).as_posix(),generated_file=str(pdf),audit_schema='source-scan-preserved-v1')
  if aliases:item['aliases']=aliases
  registry=[r for r in registry if r['file']!=pdf.name]+[item]
  for name in [pdf.name,*aliases]:
   record=next((r for r in fonts['files']if r['file']==name),None)
   if record is None:record=dict(file=name);fonts['files'].append(record)
   record.update(pages=edition['pages'],bytes=edition['bytes'],sha256=edition['sha256'],missing_glyph_spans=[],original_style=True,natural_spacing=True,source_scan_preserved=True)
   copy(pdf,release/name)
  print('Staged reviewed source-scan edition',pdf.name,edition['pages'],edition['sha256'],flush=True)
 save(root/'tools/original_style_publication.json',sorted(registry,key=lambda r:r['file']));save(root/'tools/translation_font_validation.json',fonts)

if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: stage_source_scan_publication.py READY.json RELEASE_DIRECTORY')
 stage(Path(sys.argv[1]),Path.cwd(),Path(sys.argv[2]))
