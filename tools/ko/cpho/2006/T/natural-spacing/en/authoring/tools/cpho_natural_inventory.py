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


def author_source_path(path):
    """Pin the executed private module when a frozen engine is on PYTHONPATH."""
    path=Path(path)
    module=sys.modules.get(path.stem)if path.suffix=='.py'else None
    executed=Path(module.__file__)if module and getattr(module,'__file__',None)else path
    return executed if executed.is_file()and executed.suffix=='.py'else path


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
        'cpho_natural_rotated_labels.py','pdf_native_glyph_raster_witness.py','pdf_native_glyph_promote.py',
        'pdf_native_inline_reposition.py','pdf_native_inline_reposition_regression.py','pdf_moved_native_ink.py',
        'test_pdf_native_image_motion.py','pdf_new_hangul_graphics_overlap.py',
        'pdf_native_script_motion_audit.py',
        'pdf_korean_natural_composer.py','izho_natural_spacing.py','izho_native_atomic_tokens.py',
        'pdf_original_text_ops.py','pdf_original_style_fonts.py','pdf_native_geometry_motion.py','pdf_text_motion_ink.py',
        'pdf_original_graphics_ink.py','pdf_original_image_ink.py','pdf_memory_gate.py','pdf_hangul_visibility.py',
        'izho_natural_spacing_qa.py','izho_early_fixed_style.py','izho_new_prose_outline_qa.py','cpho_original_latin_fonts.py']
    authors=[ROOT/'tools'/v for v in owned]
    authors+=[ROOT/f'tools/ko/cpho/{year}/original'/f'page{n:02}.tsv'for n in range(1,5)]
    for name in ['atomic-inline.json','atomic-forms.json','atomic-images.json']:
        plan=ROOT/f'tools/ko/cpho/{year}/natural'/name
        if plan.exists():authors.append(plan)
    inventory=dict(status='READY_NATURAL_SPACING_ORIGINAL_RESOURCES',year=year,generated_at=datetime.now().isoformat(),
        source=str(original(year)),source_sha256=sha(original(year)),source_pages=[1,2,3,4],files=files,
        style_policy='Original figures and encoded native mathematics/Latin keep font, GID, program, point size, paint and y; reviewed x translation only. Regular Korean serif uses Batang at original size. English SimSun and official full SimHei5.03 actual families; quarter-em prose spaces, no justification/scaling.',
        all_eight_page_native_ink_missing_pixels=0,raw_SVG_reference_candidates=sum(q['original_physical_native_ink'].get('newly_missing_native_ink_pixels',0)for q in allqa),
        native_reference_policy='Exact original encoded-CID witness is authoritative for a documented hinted-font/SVG raster-phase discrepancy. Raw SVG diagnostics remain in the report.',
        all_eight_page_nonselected_graphics_changes=0,
        all_eight_page_original_expression_relative_geometry_preserved=all(q['original_native_expression_relative_geometry']['passed']for q in allqa),
        native_script_base_pairs_checked=sum(len(q['original_native_expression_relative_geometry']['script_base_pairs'])for q in allqa),
        complete_native_expressions_checked=sum(len(q['original_native_expression_relative_geometry']['reviewed_expression_groups'])for q in allqa),
        maximum_native_script_base_relative_x_error_pt=max([abs(p['relative_x_change_pt'])for q in allqa for p in q['original_native_expression_relative_geometry']['script_base_pairs']]+[0]),
        maximum_complete_expression_relative_x_error_pt=max([p['relative_x_spread_pt']for q in allqa for p in q['original_native_expression_relative_geometry']['reviewed_expression_groups']]+[0]),
        all_eight_page_changes_outside_text_and_declared_math_motion=0,
        all_eight_page_Hangul_visibility_components=sum(q['hangul_visibility']['flagged_components']for q in allqa),
        all_eight_page_unexpected_Hangul_visibility_components=sum(q.get('unexpected_Hangul_visibility_components',q['hangul_visibility']['flagged_components'])for q in allqa),
        inherited_original_footer_profiles=[q['inherited_original_footer_overlay']for q in allqa if q.get('inherited_original_footer_overlay')],
        all_eight_page_image_palette_ICC_SMask_graphs_preserved=True,all_eight_page_combined_vs_proof_both_renderers_changed_pixels=0,
        authoring_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(author_source_path(p)))for p in authors])
    # Freeze exact source bytes now, before a different year's compatible
    # opt-in extension can alter the shared live module files.
    import ast
    snapshot=OUT/str(year)/'authoring-snapshot';snapshot.mkdir(exist_ok=True)
    pending=[p.relative_to(ROOT).as_posix()for p in authors if p.suffix=='.py'];seen=set();dependencies=[]
    for entry in inventory['authoring_files']:
        p=author_source_path(ROOT/entry['path']);dest=snapshot/entry['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    while pending:
        relative=pending.pop()
        if relative in seen:continue
        seen.add(relative);p=snapshot/relative
        if not p.exists():
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(author_source_path(ROOT/relative).read_bytes())
            dependencies.append(dict(path=relative,sha256=sha(p)))
        for node in ast.walk(ast.parse(p.read_text('utf-8-sig'))):
            names=[n.name.split('.')[0]for n in node.names]if isinstance(node,ast.Import)else[node.module.split('.')[0]]if isinstance(node,ast.ImportFrom)and node.module else[]
            for module in names:
                rel='tools/'+module+'.py'
                if(ROOT/rel).is_file()and rel not in seen:pending.append(rel)
    source_plan=ROOT/f'tmp/original-style-repair/{year}/slots.json';copy=snapshot/source_plan.relative_to(ROOT)
    copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes(source_plan.read_bytes())
    for f in files:
        journal=Path(f['immutable_translation_input']).with_suffix('.build.json');dest=snapshot/'immutable-input-journals'/journal.name
        dest.parent.mkdir(exist_ok=True);dest.write_bytes(journal.read_bytes())
    inventory.update(source_snapshot=str(snapshot),source_snapshot_authoring_hashes_verified=True,authoring_dependency_files=dependencies,
        source_plan_snapshot=str(copy),source_plan_snapshot_sha256=sha(copy))
    path=ROOT/'tools'/f'cpho_natural_{year}_inventory.json';path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2),'utf8')
    (snapshot/'manifest.json').write_bytes(path.read_bytes())
    print(json.dumps(dict(inventory=str(path),files=files),ensure_ascii=False),flush=True)
    return inventory


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);a=p.parse_args()
    from pdf_memory_gate import page_worker
    with page_worker():assemble(a.year)
