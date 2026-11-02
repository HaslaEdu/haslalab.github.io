from pathlib import Path
import sys,json,hashlib,shutil,subprocess,importlib.metadata
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');C=B/'figure-language';E=C/'engine';PUB=Path('D:/CodexBuilds/Hasla-publish-20261031');M=B/'master-v1';out=M/'figure-authoring-frozen';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text('utf8'))
def save(p,q):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(src,rel):
 src=Path(src);dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
def ref(p):return dict(path=str(p),sha256=sha(p))
body=load(B/'natural/editions/IZhO_2020_TS_KO.ready.json');current=next(r for r in load(PUB/'tools/original_style_publication.json')if r['file']=='IZhO_2020_TS_KO.pdf');item=current if current['audit_schema']=='natural-spacing-v2'else load(M/'IZhO_2020_TS_COMPLETE_READY.json')['editions'][0]['baseline_item'];assert item['audit_schema']=='natural-spacing-v2'and item['sha256']==body['sha256'];baseline=PUB/item['qa'];assert load(baseline)['sha256']==body['sha256'];pdf=M/'IZhO_2020_TS_KO.pdf';assembly=load(pdf.with_suffix('.assembly-qa.json'));assert assembly['passed']and assembly['sha256']==sha(pdf)and len(assembly['pages'])==13
for p in E.glob('*.py'):copy(p,Path('engine')/p.name)
for p in (C/'source-label-measurements').glob('*.json'):copy(p,Path('original-source-labels/measurements')/p.name)
for p in [B/'2020/source/IZhO_2020_TS.pdf',B/'2020/inspection/page01-source-figures-2x.png',C/'figure-fields.json']:copy(p,Path('original-source-labels')/p.name)
for p in (C/'analysis-only-negative').glob('*.json'):copy(p,Path('negative-controls')/p.name)
for p in [M/'source-word-component-review.json',M/'figure-negative-regression.json',baseline]:copy(p,Path('baseline-and-source-review')/p.name)
copy(B/'natural/2020/TS/page01.pdf','baseline-and-source-review/page01.pdf');copy(C/'2020/TS/page01.preview.png','visual-review/page01-figure-words.png')
for name in ['crop-izho2020-figure-source.py','measure-izho2020-source-figure-words.py','build-izho2020-figure-words.py','negative-izho2020-figure-words.py','prepare-izho2020-ts-final-assembly.py','freeze-izho2020-ts-figure-publication.py','assemble-scanned-proof-edition.py']:copy(Path('D:/CodexBuilds')/name,Path('scripts')/name)
contexts={};code="""from pathlib import Path
import sys,json,importlib,importlib.util
sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]]
stage=sys.argv[4]
if stage=='assembly':
 s=importlib.util.spec_from_file_location('actual_assembler',sys.argv[5]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
elif stage=='caption-build':importlib.import_module('pdf_original_style_fonts')
else:importlib.import_module('audit_figure_labels')
print(json.dumps({k:str(Path(v.__file__).resolve())for k,v in list(sys.modules.items())if getattr(v,'__file__',None)and str(v.__file__).lower().endswith('.py')and 'codexbuilds'in str(v.__file__).lower()}))
"""
for stage in ['caption-build','caption-audit','assembly']:
 paths=[str(B/'engine'),str(PUB/'tools'),str(E)]if stage=='caption-build'else[str(E),str(B/'engine'),str(PUB/'tools')]
 r=subprocess.run([sys.executable,'-X','utf8','-c',code,*paths,stage,'D:/CodexBuilds/assemble-scanned-proof-edition.py'],capture_output=True,text=True,encoding='utf8',check=True);rows={}
 for name,source in sorted(json.loads(r.stdout).items()):
  rel=Path('actual-loaded-modules')/stage/(name.replace('.','/')+'.py');copy(source,rel);rows[name]=dict(original_path=source,frozen_path=rel.as_posix(),sha256=sha(source))
 contexts[stage]=rows
save(out/'runtime-import-resolution.json',contexts);save(out/'runtime-versions.json',dict(python=sys.version,packages={p:importlib.metadata.version(p)for p in ['PyMuPDF','pikepdf','fonttools','numpy','Pillow']}));proofs=[]
for n in range(1,14):
 target=C/f'2020/TS/page{n:02}.pdf';a=C/f'2020/TS/qa/page{n:02}.audit.json';composition=target.with_suffix('.labels.json');q=load(a);assert q['passed']and q['proof_sha256']==sha(target)==assembly['pages'][n-1]['proof_sha256']and q['body_sha256']==body['page_audits'][n-1]['proof_sha256']
 row=dict(page=n,source_page=n,pdf=str(target),sha256=sha(target),body_sha256=q['body_sha256'],figure_language_qa=ref(a),composition=ref(composition))
 if n==1:
  overlay=target.with_name('page01.text-overlay.pdf');assert sha(overlay)==q['pixel_audit']['reference_sha256'];row['actual_font_reference_pdf']=ref(overlay)
 proofs.append(row)
edition=dict(file=pdf.name,language='ko',year=2020,kind='TS',pages=13,output=str(pdf),sha256=sha(pdf),bytes=pdf.stat().st_size,baseline_item=item,baseline_publication=ref(baseline),proofs=proofs,assembly_qa=ref(pdf.with_suffix('.assembly-qa.json')),visual_review=ref(M/'final-visual-review.json'))
save(out/'font-and-design-policy.json',dict(scope='Complete original13-page2020 solutions. Only six original bitmap-language words are replaced above the immutable, source-layout Korean body. All original fonts/math/figures/grades/counters retained.',figure_word_source_font_and_point_are_independent_source_raster_estimates=True,metadata_available_for_bitmap_words=False,target_translation_used_for_font_fitting=False,translated_label_role='NotoSansCJKkr-Regular at each independently measured original-source point/baseline',original_bitmap_caption_digits_1_and_2_retained=True,original_diagram_geometry_not_redrawn=True,all_body_Hangul_source_role_point_baseline_and_actual_donor_outlines_independently_verified=True,all15_original_bold_prose_headings_and_subtitles_centered_against_source=True,full_commercial_font_files_not_redistributed=True))
files={p.relative_to(out).as_posix():sha(p)for p in sorted(out.rglob('*'))if p.is_file()};ready=dict(status='READY',schema='reviewed-figure-language-v1',authoring_namespace='izho2020-ts-complete',editions=[edition],source_word_component_review=ref(M/'source-word-component-review.json'),negative_control=ref(M/'figure-negative-regression.json'),authoring_snapshot=dict(root=str(out),files=files),body_fonts_and_word_spacing_unchanged=True,original_equations_retyped=False,new_diagram_geometry=False,point_sizes_fitted=False,added_editorial_notes=0)
save(M/'IZhO_2020_TS_COMPLETE_READY.json',ready);print('COMPLETE_READY',pdf.name,13,sha(pdf),pdf.stat().st_size,len(files),flush=True)
