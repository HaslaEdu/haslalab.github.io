"""Stage exact reviewed PDF bytes and immutable cross-platform QA evidence."""
from pathlib import Path
import sys,json,hashlib,shutil

import os
ROOT=Path.cwd()
RELEASE=Path(os.environ['HASLALAB_RELEASE_DIRECTORY']);RELEASE.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
registry=json.loads((ROOT/'tools/original_style_publication.json').read_text('utf8'))
fonts=json.loads((ROOT/'tools/translation_font_validation.json').read_text('utf8'))

for argument in sys.argv[1:]:
    ready_path=Path(argument);q=json.loads(ready_path.read_text('utf8'));pdf=Path(q['output'])
    assert q['status']=='READY'and sha(pdf)==q['sha256']and pdf.stat().st_size==q['bytes']
    comp=pdf.name.split('_')[0].lower();year=q['year'];kind=q['kind'];language=q.get('language','ko')
    folder=Path(f'tools/ko/{comp}/{year}/{kind.lower() if comp=="cpho" else kind}/natural-spacing')
    if comp=='cpho':folder/=language.lower()
    dest=ROOT/folder
    modern='verified_original_native_ink_missing_pixels'in q
    snap=Path(q.get('authoring_snapshotroot',q.get('authoring_snapshot','')))
    hashes=q.get('authoring_snapshot_sha256',q.get('authoring_files'))
    for rel,digest in hashes.items():
        src=snap/rel;assert sha(src)==digest,(src,digest)
        copy(src,dest/'authoring'/rel)
        # Each PDF keeps its exact producing fork in its own authoring snapshot.
        # Shared engine upgrades are staged explicitly after their own checks.
        if str(rel).replace('\\','/').startswith('tools/'):
            assert src.stat().st_size>0,src
    copy(ready_path,dest/'source-ready.json')
    visual=Path(q['visual_review']);copy(visual,dest/'visual-review.json')
    reports=q['audit_reports']if modern else q['page_audits'];summaries=q['page_audits']if modern else q['page_proofs']
    pages=[];extra=[]
    for row in reports:
        number=row['page'];src=Path(row['path']);assert sha(src)==row['sha256']
        full=json.loads(src.read_text('utf8'));summary=next(r for r in summaries if r['page']==number)
        copy(src,dest/f'page{number:02}.qa.json')
        native=full.get('original_source_requested_dx_ink_audit',full.get('original_input_outline_native_ink_audit',full.get('native_ink')))
        if native is None:
            side=src.with_name(src.name.replace('.qa.json','.independent-moved-ink.json'));native=json.loads(side.read_text('utf8'))
        original=native.get('raw_svg_outline_audit',native)
        verified=full.get('verified_original_native_ink_missing_pixels',native.get('newly_missing_native_ink_pixels'))
        assert verified==0 and not original['missing_requested_source_glyphs']and not original['missing_final_native_glyphs']
        assert not original['source_outline_audit']['missing_source_outline_signatures']
        profile=full.get('native_ink_reference_profile');profile_copy=None
        if profile:
            p=Path(profile['witness']);assert sha(p)==profile['witness_sha256']
            copy(p,dest/f'witnesses/page{number:02}-native-cid.json')
            profile_copy=dict(profile,path=(folder/f'witnesses/page{number:02}-native-cid.json').as_posix())
            extra.append(dict(path=profile_copy['path'],sha256=sha(p)))
        ledger=dict(output_sha256=summary['proof_sha256'],verified_native_ink_missing_pixels=verified,raw_svg_audit=original,
            original_native_form_witnesses=native.get('source_native_program_witnesses',[]),original_native_cid_profile=profile_copy)
        save(dest/f'page{number:02}-native-ink.json',ledger)
        move=summary.get('native_move_qa',full.get('composition',{}).get('native_move_qa'))
        assert move['passed']and not move['native_glyph_mismatches']
        joined=summary.get('final_vs_reviewed_proof_changed_pixels',summary.get('joined_vs_reviewed_proof_changed_pixels'))
        assert joined==0 and full['passed']
        pages.append(dict(page=number,proof_sha256=summary['proof_sha256'],source_pdf_sha256=summary.get('source_pdf_sha256',q.get('original_source_sha256',full.get('original_source_sha256'))),
            final_vs_reviewed_proof_changed_pixels=joined,native_move_qa=move,
            qa=(folder/f'page{number:02}.qa.json').as_posix(),qa_sha256=sha(src),
            original_native_ink=(folder/f'page{number:02}-native-ink.json').as_posix(),original_native_ink_sha256=sha(dest/f'page{number:02}-native-ink.json')))
    assert len(pages)==q['pages']
    validation=dict(native_ink_missing_pixels=q.get('verified_original_native_ink_missing_pixels',q.get('native_actual_glyph_missing')),
        new_batang_empty_outlines=q['new_batang_empty_outlines'],hangul_visibility_loss_candidates=q['hangul_visibility_loss_candidates'],
        original_point_sizes_scaled=q['original_point_sizes_scaled'],
        outside_text_and_intended_math_motion=q.get('changed_pixels_outside_text_and_intended_native_math_motion',q.get('outside_motion_ink_pixels')),
        changed_figures=q.get('figure_and_locked_display_math_changed_pixels',q.get('figure_changed_pixels')),
        original_font_image_programs_and_page_groups_retained=q.get('original_font_image_palette_icc_mask_programs_and_page_groups_retained',q.get('original_fonts_and_image_programs_retained')and q.get('page_groups_preserved')),
        no_added_editorial_notes=q.get('no_added_pdf_editorial_notes',q.get('no_added_editorial_notes')))
    assert all(validation[k]==0 for k in ['native_ink_missing_pixels','new_batang_empty_outlines','hangul_visibility_loss_candidates','outside_text_and_intended_math_motion','changed_figures'])
    wrapper=dict(status='READY',file=pdf.name,year=year,kind=kind,language=language,pages=q['pages'],bytes=q['bytes'],sha256=q['sha256'],
        validation=validation,page_proofs=pages,source_ready=(folder/'source-ready.json').as_posix(),source_ready_sha256=sha(ready_path),
        visual_review=(folder/'visual-review.json').as_posix(),visual_review_sha256=sha(visual),
        authoring_snapshotroot=(folder/'authoring').as_posix(),authoring_snapshot_sha256=hashes,extra_evidence=extra)
    save(dest/'publication.json',wrapper)
    old=next((x for x in registry if x['file']==pdf.name),{})
    entry=dict(file=pdf.name,language=language,pages=q['pages'],bytes=q['bytes'],sha256=q['sha256'],qa=(folder/'publication.json').as_posix(),generated_file=str(pdf),audit_schema='natural-spacing-v2')
    if old.get('aliases'):entry['aliases']=old['aliases']
    registry=[x for x in registry if x['file']!=pdf.name]+[entry]
    for name in [pdf.name,*entry.get('aliases',[])]:
        record=next((f for f in fonts['files']if f['file']==name),None)
        if record is None:record=dict(file=name);fonts['files'].append(record)
        record.update(pages=q['pages'],bytes=q['bytes'],sha256=q['sha256'],missing_glyph_spans=[],original_style=True,natural_spacing=True)
        copy(pdf,RELEASE/name)
    print('Staged',pdf.name,q['pages'],q['sha256'],flush=True)

save(ROOT/'tools/original_style_publication.json',sorted(registry,key=lambda r:r['file']))
save(ROOT/'tools/translation_font_validation.json',fonts)
