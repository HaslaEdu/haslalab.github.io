from pathlib import Path
import sys,json,hashlib,shutil,subprocess,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-older-figure-language');E=B/'engine';PUB=Path('D:/CodexBuilds/Hasla-publish-20261031');OLD=B.parent/'izho-natural-spacing';out=B/'master-v1/authoring-frozen'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(src,rel):
 dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
def ref(p):return dict(path=str(p),sha256=sha(p))
registry=json.loads((PUB/'tools/original_style_publication.json').read_text('utf8'));editions=[]
for f in E.glob('*.py'):copy(f,Path('engine')/f.name)
for folder in ['source-label-measurements','source-label-roi-review']:
 for f in (B/folder).glob('*'):
  if f.is_file():copy(f,f.relative_to(B))
copy(B/'source-inventory.json','source-inventory.json')
for name in ['2010-p02-image03.png','2010-p02-image04.png','2010-p03-image01.png']:copy(B/name,Path('source-page-crops')/name)
for f in (B/'negative-controls').glob('*.json'):copy(f,Path('negative-controls')/f.name)
for name in ['prepare-izho-older-figure-editions.py','freeze-izho-older-figure-publication.py','assemble-scanned-proof-edition.py','inspect-older-izho-figure-language.py']:copy(Path('D:/CodexBuilds')/name,Path('scripts')/name)
contexts={}
for stage in ['measure_source_labels','build_figure_labels','audit_figure_labels','assembly']:
 code="""import sys,json,importlib,importlib.util
from pathlib import Path
sys.path.insert(0,sys.argv[1])
if sys.argv[2]=='assembly':
 s=importlib.util.spec_from_file_location('actual_assembler',sys.argv[3]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
else:importlib.import_module(sys.argv[2])
print(json.dumps({k:str(Path(v.__file__).resolve())for k,v in list(sys.modules.items())if getattr(v,'__file__',None)and str(v.__file__).lower().endswith('.py')and 'codexbuilds' in str(v.__file__).lower()}))
"""
 p=subprocess.run([sys.executable,'-X','utf8','-c',code,str(E),stage,'D:/CodexBuilds/assemble-scanned-proof-edition.py'],capture_output=True,text=True,encoding='utf8',check=True);rows={}
 for name,source in sorted(json.loads(p.stdout).items()):
  rel=Path('loaded-modules')/stage/(name.replace('.','/')+'.py');copy(source,rel);rows[name]=dict(original_path=source,frozen_path=rel.as_posix(),sha256=sha(source))
 contexts[stage]=rows
save(out/'runtime-import-resolution.json',contexts)
save(out/'runtime-versions.json',dict(python=sys.version,packages={p:importlib.metadata.version(p)for p in['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}))
for year,count in [(2010,5),(2011,6)]:
 saved_item=out/f'baseline/{year}-registry-item.json'
 item=json.loads(saved_item.read_text('utf8'))if saved_item.is_file()else next(r for r in registry if r['file']==f'IZhO_{year}_T_KO.pdf');assert item['audit_schema']=='natural-spacing-v2'
 baseline=PUB/item['qa'];copy(baseline,Path('baseline')/f'{year}-publication.json');save(out/f'baseline/{year}-registry-item.json',item)
 old_ready=json.loads((OLD/f'editions/IZhO_{year}_T_KO.ready.json').read_text('utf8'))
 english=old_ready['input_archives'][1];assert sha(english['path'])==english['sha256'];copy(english['path'],Path('baseline')/f'IZhO_{year}_T_EN.pdf')
 pages=[]
 pdf=B/f'master-v1/IZhO_{year}_T_KO.pdf';assembly=json.loads(pdf.with_suffix('.assembly-qa.json').read_text('utf8'));assert assembly['passed']and len(assembly['pages'])==count and assembly['sha256']==sha(pdf)
 for n in range(1,count+1):
  target=B/f'{year}/T/page{n:02}.pdf';audit=B/f'{year}/T/qa/page{n:02}.audit.json';composition=target.with_suffix('.labels.json');q=json.loads(audit.read_text('utf8'));assert q['passed']and q['proof_sha256']==sha(target)==assembly['pages'][n-1]['proof_sha256']
  body=OLD/f'{year}/T/page{n:02}.pdf';assert sha(body)==q['body_sha256'];copy(body,Path('baseline')/str(year)/f'page{n:02}.pdf')
  row=dict(page=n,source_page=n,pdf=str(target),sha256=sha(target),body_sha256=sha(body),figure_language_qa=ref(audit),composition=ref(composition))
  if q['labels']:
   overlay=B/f'{year}/T/page{n:02}.text-overlay.pdf';assert sha(overlay)==q['pixel_audit']['reference_sha256'];row['actual_font_reference_pdf']=ref(overlay)
   preview=B/f'inspection/final-label-previews/{year}-page{n:02}-review.png';copy(preview,Path('visual-review')/preview.name)
  pages.append(row)
 editions.append(dict(file=pdf.name,language='ko',year=year,kind='T',pages=count,output=str(pdf),sha256=sha(pdf),bytes=pdf.stat().st_size,baseline_item=item,baseline_publication=ref(baseline),proofs=pages,assembly_qa=ref(pdf.with_suffix('.assembly-qa.json')),visual_review=ref(B/f'master-v1/{year}-visual-review.json')))
save(out/'font-and-design-policy.json',dict(scope='Only remaining English figure words; previously reviewed natural Korean body and all native formulas are preserved.',korean_source_serif_role='Batang at exact source native point, or source-only measured bitmap point',korean_photo_bold_italic_role='NotoSansCJKkr-Bold with the measured source Verdana BoldItalic13degree basis; no scaling',source_bitmap_font_metadata_unavailable=True,source_only_ink_matching_used_for_bitmap_points=True,target_translation_not_used_for_font_fitting=True,original_bitmap_Fig1_Fig2_numerals_preserved=True,native_2011_caption_digit_original_font_GID_point_baseline_preserved=True,original_diagram_geometry_not_redrawn=True,full_commercial_font_files_not_redistributed=True))
files={f.relative_to(out).as_posix():sha(f)for f in sorted(out.rglob('*'))if f.is_file()}
ready=dict(status='READY',schema='reviewed-figure-language-v1',editions=editions,source_word_component_review=ref(B/'source-label-roi-review/source-components.json'),negative_control=ref(B/'negative-controls/regression.json'),authoring_snapshot=dict(root=str(out),files=files),body_fonts_and_word_spacing_unchanged=True,original_equations_retyped=False,new_diagram_geometry=False,point_sizes_fitted=False,added_editorial_notes=0)
save(B/'master-v1/IZhO_2010_2011_FIGURE_LANGUAGE_READY.json',ready)
print(json.dumps(dict(status='READY',frozen_files=len(files),frozen_bytes=sum((out/p).stat().st_size for p in files),editions=[{k:e[k]for k in['file','pages','sha256','bytes']}for e in editions])))
