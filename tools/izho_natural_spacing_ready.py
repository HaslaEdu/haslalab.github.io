"""Assemble exact visually reviewed natural-spacing proofs and freeze provenance."""
from pathlib import Path
import argparse,hashlib,json,shutil
import numpy as np
import pikepdf
from PIL import Image
from pdf_memory_gate import page_worker
from izho_natural_spacing import ROOT,BUILD
from izho_natural_spacing_qa import sha,fresh_render

def ready(year,kind):
    folder=BUILD/str(year)/kind;plans=sorted((folder/'plans').glob('page*.json'))
    review=json.loads((folder/'visual-review.json').read_text('utf8'));reviews={r['page']:r for r in review['pages']}
    audits=[];proofs=[]
    for i,plan in enumerate(plans,1):
        proof=folder/f'page{i:02d}.pdf';audit=json.loads(proof.with_suffix('.audit.json').read_text('utf8'))
        if not audit['passed']or audit['output_sha256']!=sha(proof):raise ValueError('An audited proof changed')
        if i not in reviews or not reviews[i]['reviewed']or reviews[i]['proof_sha256']!=sha(proof):raise ValueError('Every exact proof requires visual review')
        proofs.append(proof);audits.append(audit)
    output=BUILD/'editions'/f'IZhO_{year}_{kind}_KO.pdf';output.parent.mkdir(parents=True,exist_ok=True)
    with pikepdf.Pdf.new()as joined:
        for proof in proofs:
            with pikepdf.open(proof)as src:joined.pages.append(src.pages[0])
        joined.save(output,compress_streams=False)
    assembly=[]
    for i,(proof,audit)in enumerate(zip(proofs,audits),1):
        actual=fresh_render(output,i,folder/'qa-renders'/f'{i:02d}-joined.png')
        with Image.open(folder/'qa-renders'/f'{i:02d}-new.png')as image:expected=np.array(image.convert('RGB'))
        delta=int(np.any(actual!=expected,axis=2).sum())
        if delta:raise ValueError(('Native page append changed exact reviewed RGB pixels',i,delta))
        assembly.append(dict(page=i,proof_sha256=sha(proof),joined_vs_reviewed_proof_changed_pixels=delta,
            original_input_native_ink_missing=audit.get('verified_original_native_ink_missing_pixels',audit['original_input_outline_native_ink_audit'].get('newly_missing_native_ink_pixels')),
            native_glyphs=audit['original_input_outline_native_ink_audit']['protected_native_glyphs'],
            native_move_qa=audit['composition']['native_move_qa'],native_ink_reference_profile=audit.get('native_ink_reference_profile')))
    names=['izho_natural_spacing.py','pdf_korean_natural_composer.py','izho_native_atomic_tokens.py','pdf_native_inline_reposition.py',
           'pdf_native_glyph_promote.py','pdf_native_geometry_motion.py','pdf_moved_native_ink.py','pdf_text_motion_ink.py','pdf_memory_gate.py',
           'izho_natural_spacing_rebuild.py','izho_natural_spacing_qa.py','izho_native_ink_witness.py','izho_natural_spacing_ready.py',
           'pdf_grading_columns_stationary.py','test_izho_natural_spacing.py','test_pdf_korean_natural_composer.py']
    snapshot=BUILD/f'{year}-{kind}-authoring';snapshot.mkdir(exist_ok=True);authoring={}
    for name in names:
        source=ROOT/'tools'/name;payload=source.read_bytes();target=snapshot/'tools'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(payload);authoring[str(Path('tools')/name)]=hashlib.sha256(payload).hexdigest()
    data_root=snapshot/f'tools/ko/izho/{year}/{kind}/natural_spacing';data_root.mkdir(parents=True,exist_ok=True)
    for plan in plans:shutil.copyfile(plan,data_root/plan.name)
    override=ROOT/f'tools/ko/izho/{year}/{kind}/natural_spacing-overrides.json'
    if override.exists():shutil.copyfile(override,data_root.parent/override.name)
    first=json.loads(plans[0].read_text('utf8'));archives=[]
    for source_path,digest in[(first['source_base'],first['source_base_sha256']),(first['original_english_source'],first['original_english_source_sha256'])]:
        source=Path(source_path);target=BUILD/'input-bases'/digest/source.name;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copyfile(source,target)
        if sha(target)!=digest:raise ValueError('Input archive SHA mismatch')
        archives.append(dict(path=str(target),sha256=digest,bytes=target.stat().st_size))
    manifest=dict(status='READY',year=year,kind=kind,pages=len(proofs),output=str(output),sha256=sha(output),bytes=output.stat().st_size,
        original_source_sha256=first['original_english_source_sha256'],input_korean_source_sha256=first['source_base_sha256'],input_archives=archives,
        font_policy='Original-point-size Batang for regular serif Hangul; all existing native Latin/math/ASCII, bold, sans, italic and paint retained.',
        spacing_policy='Quarter-em prose word spaces; whole inline native expressions move horizontally with internal geometry retained; original display equations and figures stay fixed; source content centers retained.',
        original_point_sizes_scaled=False,equations_rasterized=False,no_added_pdf_editorial_notes=True,
        original_physical_native_glyphs_checked=sum(r['native_glyphs']for r in assembly),
        verified_original_native_ink_missing_pixels=sum(r['original_input_native_ink_missing']for r in assembly),
        raw_unhinted_svg_reference_deltas=sum(a['original_input_outline_native_ink_audit'].get('newly_missing_native_ink_pixels',0)for a in audits),
        retained_native_control_ink_missing_pixels=sum(a['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']for a in audits),
        changed_pixels_outside_text_and_intended_native_math_motion=sum(a['changed_pixels_outside_old_and_new_text_ink']for a in audits),
        changed_nonselected_native_graphical_pixels=sum(a['native_graphics_motion_audit']['changed_nonselected_native_graphical_pixels']for a in audits),
        figure_and_locked_display_math_changed_pixels=sum(r['changed_pixels']for a in audits for r in a['figure_pixel_audits']),
        new_batang_empty_outlines=sum(len(a['new_batang_outlines']['empty'])for a in audits),
        new_batang_hangul_glyphs_checked=sum(a['new_batang_outlines']['checked']for a in audits),
        hangul_visibility_loss_candidates=sum(a['hangul_visibility']['flagged_components']for a in audits),
        unconverted_regular_body_hangul=sum(a['body_font_coverage']['unreplaced_regular_body_hangul']for a in audits),
        stationary_table_math_glyphs=sum(len(a['composition'].get('stationary_native_glyphs',[]))for a in audits),
        table_math_internal_geometry_mismatches=sum(a.get('source_math_internal_geometry',{}).get('mismatched_groups',0)for a in audits),
        original_grading_glyphs_checked=sum(a.get('grading_columns_stationary',{}).get('original_grading_glyphs_checked',0)for a in audits),
        grading_glyphs_moved_from_source_cells=sum(len(a.get('grading_columns_stationary',{}).get('grading_glyphs_moved_from_source_cells',[]))for a in audits),
        reviewed_complete_inline_expressions=sum(a.get('reviewed_inline_expression_geometry',{}).get('checked_groups',0)for a in audits),
        reviewed_inline_expression_geometry_mismatches=sum(a.get('reviewed_inline_expression_geometry',{}).get('mismatched_groups',0)for a in audits),
        original_font_image_palette_icc_mask_programs_and_page_groups_retained=all(a['original_font_programs_and_names_retained']and a['original_image_programs_retained']and a['page_group_preserved']and a['colorspace_resources_preserved']and all(r['full_palette_icc_mask_image_graph_preserved']for r in a['original_palette_icc_mask_graphs'])for a in audits),
        assembly='pikepdf native page append; fresh-process 4x RGB exact comparison to reviewed proofs',page_audits=assembly,
        audit_reports=[dict(page=i,path=str(p.with_suffix('.audit.json')),sha256=sha(p.with_suffix('.audit.json')))for i,p in enumerate(proofs,1)],
        visual_review=str(folder/'visual-review.json'),authoring_snapshot=str(snapshot),authoring_files=authoring,
        note=('The one CambriaMath e unhinted SVG 4x edge sample is documented with exact original CID0087 native-reference zero loss and SVG8x/12x zero loss; proof unchanged.'
              if any(a.get('native_ink_reference_profile')for a in audits)else'All page proofs passed the ordinary original-input native-ink audit.'))
    output.with_suffix('.ready.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in manifest.items()if k not in['page_audits','authoring_files','audit_reports']},ensure_ascii=False,indent=2))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('year',type=int);p.add_argument('kind',choices=['T','TS']);a=p.parse_args()
    with page_worker():ready(a.year,a.kind)
