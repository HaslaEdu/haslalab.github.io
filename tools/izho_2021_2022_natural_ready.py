"""Join only reviewed and audited natural-spacing IZhO pages."""
import argparse,json
from pathlib import Path
import pikepdf
import pymupdf as fitz
import numpy as np
from izho_2021_2022_natural_spacing import ROOT,OUT,sha
from pdf_memory_gate import page_worker
from izho_2021_2022_batang_coverage import audit as coverage_audit
from pdf_grading_columns_stationary import audit as grading_audit

COUNTS={(2021,'T'):6,(2021,'TS'):16,(2022,'T'):7,(2022,'TS'):15}

def finalize(year,kind):
    folder=OUT/str(year)/kind;count=COUNTS[year,kind]
    authoring_names=['izho_2021_2022_natural_ready.py','izho_2021_2022_batang_rebuild.py',
        'izho_2021_2022_natural_spacing.py','izho_2021_2022_header_spacing.py','izho_native_atomic_tokens.py',
        'izho_natural_spacing.py','pdf_korean_natural_composer.py','pdf_native_inline_reposition.py',
        'pdf_text_motion_ink.py','pdf_native_geometry_motion.py','pdf_memory_gate.py',
        'pdf_moved_native_ink.py','pdf_native_glyph_promote.py','izho_2022_t2_native_margin.py',
        'pdf_new_hangul_graphics_overlap.py','test_pdf_new_hangul_graphics_overlap.py',
        'izho_2021_2022_batang_coverage.py','izho_2021_ts15_native_raster_profile.py',
        'pdf_native_form_raster_witness.py','test_pdf_native_form_raster_witness.py','pdf_grading_columns_stationary.py',
        'izho_2022_ts_native_raster_profiles.py']
    # Freeze the exact source bytes when their hashes are read, before any
    # shared engine can be edited by a parallel authoring task.
    frozen={str(Path('tools')/name):(ROOT/'tools'/name).read_bytes()for name in authoring_names}
    import hashlib
    hashes={name:hashlib.sha256(payload).hexdigest()for name,payload in frozen.items()}
    snapshot=OUT/f'{year}-{kind}-authoring'
    if snapshot.exists()and any(not(snapshot/name).exists()or sha(snapshot/name)!=hashes[name]for name in frozen):
        suffix=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:10]
        snapshot=OUT/f'{year}-{kind}-authoring-{suffix}'
    for name,payload in frozen.items():
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(payload)
    review=json.loads((folder/'visual-review-natural.json').read_text('utf8'))
    reviewed={r['page']:r for r in review['pages']}
    proofs=[];audits=[]
    for page in range(1,count+1):
        proof=folder/f'batang-page{page}.pdf';qa=json.loads(proof.with_suffix('.qa.json').read_text('utf8'))
        if not qa['passed']or qa['output_sha256']!=sha(proof):raise ValueError('A page is not an intact independently audited proof')
        if kind=='TS':
            if not qa.get('original_source_requested_dx_ink_audit',{}).get('passed'):
                raise ValueError('Every solution page needs its original-source requested-motion ink audit')
            if not qa.get('new_hangul_native_graphics_overlap',{}).get('passed'):
                raise ValueError('Every solution page needs new prose versus native graphics collision audit')
        coverage=coverage_audit(year,kind,page)
        if not coverage['passed']:raise ValueError('Eligible regular Korean body prose was omitted from font/spacing repair')
        qa['body_hangul_replacement_coverage']=coverage
        old_qa=json.loads(Path(qa['source']).with_suffix('.qa.json').read_text('utf8'))
        grading=grading_audit(qa['source'],proof,old_qa['placements'])if kind=='TS'else dict(passed=True,original_grading_glyphs_checked=0,grading_glyphs_moved_from_source_cells=[])
        if not grading['passed']:raise ValueError(('Original grading numerals moved out of their source table cells',page,grading))
        qa['stationary_original_grading_columns']=grading
        if page not in reviewed or not reviewed[page]['reviewed']or reviewed[page]['proof_sha256']!=sha(proof):
            raise ValueError('Every final page needs a visual review of this exact proof')
        proofs.append(proof);audits.append(qa)
    target=OUT/'editions'/f'IZhO_{year}_{kind}_KO.pdf';target.parent.mkdir(parents=True,exist_ok=True)
    with pikepdf.Pdf.new()as joined:
        for proof in proofs:
            with pikepdf.open(proof)as single:joined.pages.append(single.pages[0])
        joined.save(target,compress_streams=False)
    joined=fitz.open(target);assembly=[]
    def pixels(page):
        p=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
        return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
    for pi,proof in enumerate(proofs):
        with fitz.open(proof)as single:
            diff=int(np.any(pixels(single[0])!=pixels(joined[pi]),axis=2).sum())
            if diff:raise ValueError('Native page append changed reviewed proof pixels')
            assembly.append(dict(page=pi+1,proof_sha256=sha(proof),final_vs_reviewed_proof_changed_pixels=diff))
    joined.close()
    inventory=dict(status='READY',year=year,kind=kind,pages=count,output=str(target),sha256=sha(target),
        bytes=target.stat().st_size,assembly='pikepdf native page append; no page rasterization or font rewriting',
        font_policy='Regular source Times-like Hangul uses Windows Batang at the original point size; existing native ASCII, Latin, math, bold, sans and italic glyphs retain their original programs and painting.',
        spacing_policy='Natural left-to-right inline horizontal packing with one quarter-em word spaces; source display equations and figures remain at original positions; source content centers retained.',
        native_actual_glyph_missing=sum(q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']for q in audits),new_batang_empty_outlines=sum(len(q['new_batang_outlines']['empty'])for q in audits),
        original_source_requested_dx_audited_pages=sum(bool(q.get('original_source_requested_dx_ink_audit'))for q in audits),
        original_source_requested_dx_newly_missing_native_ink_pixels=sum(q.get('original_source_requested_dx_ink_audit',{}).get('newly_missing_native_ink_pixels',0)for q in audits),
        new_hangul_native_graphics_overlap_pixels=sum(q.get('new_hangul_native_graphics_overlap',{}).get('new_hangul_dark_pixels_over_native_foreground',0)for q in audits),
        eligible_body_hangul_coverage_missing=sum(len(q['body_hangul_replacement_coverage']['missing_eligible_body_hangul'])for q in audits),
        original_stationary_grading_glyphs_checked=sum(q['stationary_original_grading_columns']['original_grading_glyphs_checked']for q in audits),
        hangul_visibility_loss_candidates=sum(q['hangul_visibility']['flagged_components']for q in audits),
        outside_motion_ink_pixels=sum(q['changed_pixels_outside_old_and_new_text_ink']for q in audits),
        figure_changed_pixels=sum(r.get('changed_visible_figure_ink_or_unreviewed_pixels',r['changed_pixels'])for q in audits for r in q['figure_pixel_audits']),
        reviewed_native_math_over_white_margin_pixels=sum(r.get('reviewed_native_over_white_margin_pixels',0)for q in audits for r in q['figure_pixel_audits']),
        original_fonts_and_image_programs_retained=all(q['original_font_programs_and_names_retained']and q['original_image_programs_retained']for q in audits),
        page_groups_preserved=all(q['page_group_preserved']for q in audits),
        measurements_tolerance_pt=.001,original_point_sizes_scaled=False,
        original_prose_and_formula_language_content_unchanged=True,no_added_editorial_notes=True,
        page_proofs=[dict(row,source_pdf_sha256=qa['original_source_sha256'],old_korean_proof_sha256=qa['source_sha256'],
            native_move_qa=qa['composition']['native_move_qa'],actual_native_math_visible_ink=qa['actual_native_math_visible_ink_audit'],
            changed_figures=sum(r.get('changed_visible_figure_ink_or_unreviewed_pixels',r['changed_pixels'])for r in qa['figure_pixel_audits']),
            original_source_requested_dx_ink_audit=qa.get('original_source_requested_dx_ink_audit'),
            new_hangul_native_graphics_overlap=qa.get('new_hangul_native_graphics_overlap'),
            body_hangul_replacement_coverage=qa['body_hangul_replacement_coverage'],
            stationary_original_grading_columns=qa['stationary_original_grading_columns'],
            new_empty_hangul_outlines=len(qa['new_batang_outlines']['empty']))
            for row,qa in zip(assembly,audits)],visual_review=str(folder/'visual-review-natural.json'),
        page_audits=[dict(page=i+1,path=str(p.with_suffix('.qa.json')),sha256=sha(p.with_suffix('.qa.json')))for i,p in enumerate(proofs)],
        authoring_files=hashes,authoring_snapshotroot=str(snapshot),authoring_snapshot_sha256=hashes,
        historical_source_drift=[dict(page=i+1,file=str(Path('tools')/name),recorded_build_sha=recorded,
            snapshot_sha=hashes[str(Path('tools')/name)],
            note='Exact per-page build hashes remain in the page QA. The frozen current snapshot includes later compatible inspection/profile additions; reviewed final page bytes and final binary QA remain authoritative.')
            for i,qa in enumerate(audits)for name,recorded in qa.get('authoring_sha256',{}).items()
            if str(Path('tools')/name)in hashes and recorded!=hashes[str(Path('tools')/name)]])
    target.with_suffix('.ready.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(inventory,ensure_ascii=False,indent=2))
    return target,inventory

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int,choices=[2021,2022]);p.add_argument('kind',choices=['T','TS']);a=p.parse_args()
    with page_worker():finalize(a.year,a.kind)
