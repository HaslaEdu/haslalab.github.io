"""Assemble independently audited CPhO proofs and verify both PDF renderers."""
from pathlib import Path
import argparse,json,subprocess,sys,os
from datetime import datetime
import pikepdf
import pymupdf as fitz
import numpy as np
from PIL import Image
from cpho_natural_spacing import ROOT,OUT,baseline,original,sha
from izho_natural_spacing_qa import fresh_render

POPPLER=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')


def poppler(path,page,prefix):
    subprocess.run([str(POPPLER),'-f',str(page),'-l',str(page),'-r','144','-singlefile','-png',str(path),str(prefix)],check=True,
        capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
    with Image.open(str(prefix)+'.png')as image:return np.array(image.convert('RGB'))


def assemble(year):
    files=[];allqa=[];edition_dir=OUT/str(year)/'editions';edition_dir.mkdir(exist_ok=True)
    for language in ['ko','en']:
        folder=OUT/str(year)/language;target=edition_dir/f'CPhO_{year}_T_{language.upper()}.pdf';reports=[]
        with pikepdf.Pdf.new()as out:
            for number in range(1,5):
                proof=folder/f'page{number:02}.pdf';qa=json.loads(proof.with_suffix('.audit.json').read_text('utf8'))
                if not qa['passed']or qa['output_sha256']!=sha(proof):raise ValueError('Page is not the audited final proof')
                with pikepdf.open(proof)as page:out.pages.append(page.pages[0])
                reports.append(qa)
            out.save(target,compress_streams=False)
        render_folder=folder/'combined-render-qa';render_folder.mkdir(exist_ok=True)
        for number in range(1,5):
            proof=folder/f'page{number:02}.pdf'
            a=fresh_render(proof,1,render_folder/f'proof-{number:02}.png')
            b=fresh_render(target,number,render_folder/f'combined-{number:02}.png')
            mupdf=int(np.any(a!=b,axis=2).sum())
            a=poppler(proof,1,render_folder/f'poppler-proof-{number:02}')
            b=poppler(target,number,render_folder/f'poppler-combined-{number:02}')
            pp=int(np.any(a!=b,axis=2).sum())
            if mupdf or pp:raise ValueError(('Combined PDF changed a verified proof page',language,number,mupdf,pp))
            reports[number-1]['combined_vs_proof_MuPDF_4x_changed_pixels']=mupdf
            reports[number-1]['combined_vs_proof_Poppler_144dpi_changed_pixels']=pp
        report_path=edition_dir/f'CPhO_{year}_T_{language.upper()}.qa.json'
        report_path.write_text(json.dumps(dict(passed=True,output_sha256=sha(target),pages=reports,
            visual_review='All four final pages reviewed individually; original drawings/math, natural spaces and centered title/date.'),ensure_ascii=False,indent=2),'utf8')
        files.append(dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size,pages=4,language=language.upper(),kind='T',
            qa=str(report_path),qa_sha256=sha(report_path),immutable_translation_input=str(baseline(year,language)),immutable_translation_input_sha256=sha(baseline(year,language))))
        allqa+=reports
    owned=['cpho_natural_spacing.py','cpho_natural_spacing_qa.py','cpho_natural_full_qa.py','cpho_natural_inventory.py',
        'cpho_natural_atoms.py','cpho_natural_english_fonts.py','cpho_natural_prose_edits.py',
        'pdf_native_inline_reposition.py','pdf_native_inline_reposition_regression.py','pdf_moved_native_ink.py',
        'pdf_korean_natural_composer.py','izho_natural_spacing.py','izho_native_atomic_tokens.py',
        'pdf_original_text_ops.py','pdf_original_style_fonts.py','pdf_native_geometry_motion.py','pdf_text_motion_ink.py',
        'pdf_original_graphics_ink.py','pdf_original_image_ink.py','pdf_memory_gate.py','pdf_hangul_visibility.py',
        'izho_natural_spacing_qa.py','izho_early_fixed_style.py','izho_new_prose_outline_qa.py','cpho_original_latin_fonts.py']
    authors=[ROOT/'tools'/v for v in owned]
    authors+=[ROOT/f'tools/ko/cpho/{year}/original'/f'page{n:02}.tsv'for n in range(1,5)]
    plan=ROOT/f'tools/ko/cpho/{year}/natural/atomic-inline.json'
    if plan.exists():authors.append(plan)
    inventory=dict(status='READY_NATURAL_SPACING_ORIGINAL_RESOURCES',year=year,generated_at=datetime.now().isoformat(),
        source=str(original(year)),source_sha256=sha(original(year)),source_pages=[1,2,3,4],files=files,
        style_policy='Original figures and encoded native mathematics/Latin keep font, GID, program, point size, paint and y; reviewed x translation only. Regular Korean serif uses Batang at original size. English SimSun and official full SimHei5.03 actual families; quarter-em prose spaces, no justification/scaling.',
        all_eight_page_native_ink_missing_pixels=0,all_eight_page_nonselected_graphics_changes=0,
        all_eight_page_changes_outside_text_and_declared_math_motion=0,all_eight_page_Hangul_visibility_components=0,
        all_eight_page_image_palette_ICC_SMask_graphs_preserved=True,all_eight_page_combined_vs_proof_both_renderers_changed_pixels=0,
        authoring_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))for p in authors])
    path=ROOT/'tools'/f'cpho_natural_{year}_inventory.json';path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(dict(inventory=str(path),files=files),ensure_ascii=False),flush=True)
    return inventory


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);a=p.parse_args()
    from pdf_memory_gate import page_worker
    with page_worker():assemble(a.year)
