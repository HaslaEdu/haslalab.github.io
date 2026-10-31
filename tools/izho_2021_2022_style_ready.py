"""Rebuild assigned original-style editions; finalize only visually reviewed proofs.

    python tools/izho_2021_2022_style_ready.py 2021 T
    python tools/izho_2021_2022_style_ready.py 2021 T --ready

The --ready operation requires current per-page proof hashes in the edition's
visual-review.json. Originals and the previous published layout remain intact.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import izho_legacy_style_rebuild as pipeline
from pdf_hangul_visibility import audit as hangul_audit

ROOT=pipeline.ROOT
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rebuild(year,kind,ready=False,move_final=False):
    if move_final and not ready:raise ValueError('--move-final requires --ready')
    pipeline.rebuild(year,kind)
    folder=ROOT/f'tools/ko/izho/{year}/{kind}/original_style'
    report=json.loads((folder/'audit.json').read_text('utf8'))
    final=ROOT/report['output'];scratch=final.parent
    if not ready:
        print('Built and audited; visual review is required before --ready.',flush=True)
        return report
    review_path=folder/'visual-review.json'
    review=json.loads(review_path.read_text('utf8'))
    if review.get('source_sha256')!=report['source_sha256']:raise ValueError('Visual review names a different original')
    reviews={entry['page']:entry for entry in review['pages']}
    if set(reviews)!=set(range(1,report['pages']+1)):raise ValueError('Every output page needs a visual review')
    for number,qa in enumerate(report['page_audits'],1):
        proof=scratch/f'page{number}.pdf'
        if not pipeline.valid(proof,folder/f'page{number}.json'):raise ValueError('Stale reviewed proof')
        if not reviews[number].get('reviewed')or reviews[number].get('proof_sha256')!=sha(proof):raise ValueError('The current proof has not been visually reviewed')
        if qa['final_vs_reviewed_proof_changed_pixels']!=0:raise ValueError('Final assembly differs from the reviewed proof')
    visibility=hangul_audit(final)
    if visibility['flagged_components']:raise ValueError('Final Korean glyphs are hidden')
    target=ROOT/f'pdfx/izho/original-style/IZhO_{year}_{kind}_KO.pdf'
    target.parent.mkdir(parents=True,exist_ok=True)
    if move_final:
        # The complete, audited assembly is on the same workspace volume.
        # Rename it into its canonical location rather than retaining a
        # second large PDF. Existing canonical versions are never replaced
        # by this opt-in path.
        if target.exists():raise ValueError('--move-final requires a new canonical target')
        final.rename(target)
        report['output']=str(target.relative_to(ROOT)).replace('\\','/')
        (folder/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    else:shutil.copyfile(final,target)
    record=dict(year=year,kind=kind,status='READY',file=str(target.relative_to(ROOT)).replace('\\','/'),
        sha256=sha(target),bytes=target.stat().st_size,pages=report['pages'],
        source_sha256=report['source_sha256'],source_pages_1based=report['source_pages_1based'],
        autoshrink=False,reflow=False,equation_images=0,added_titles_or_errata=False,
        native_glyphs_checked=sum(qa['native_glyphs_checked']for qa in report['page_audits']),
        protected_glyph_origins_checked=sum(qa['protected_glyph_origins_checked']for qa in report['page_audits']),
        native_glyphs_changed=0,protected_glyphs_selected_for_erasure=0,
        selected_prose_actual_whitespace_glyphs_checked=sum(qa.get('selected_prose_actual_whitespace_glyphs_checked',0)for qa in report['page_audits']),
        selected_prose_whitespace_scope=[dict(page=qa['source_page'],glyphs=qa['mutable_prose_whitespace_glyphs'])for qa in report['page_audits']if qa.get('mutable_prose_whitespace_glyphs')],
        changed_pixels_in_native_glyph_neighborhood=0,changed_pixels_outside_prose=0,
        final_vs_reviewed_proof_changed_pixels=0,new_native_ascii_nonpositive_widths=report['new_native_ascii_nonpositive_widths'],
        hangul_visibility_candidates=0,visual_reviewed_pages=sorted(reviews),
        visual_review_completed=True,visual_review_proofs=[reviews[n]for n in sorted(reviews)],
        raster_language_regions_translated=sum(qa.get('raster_language_region_count',0)for qa in report['page_audits']),
        changed_pixels_outside_raster_language_regions=sum(qa.get('changed_pixels_outside_raster_language_regions',0)for qa in report['page_audits']),
        changed_pixels_in_visible_raster_graphics=sum(qa.get('changed_pixels_in_visible_raster_graphics',0)for qa in report['page_audits']),
        plans=[str((folder/f'page{i}.json').relative_to(ROOT)).replace('\\','/')for i in sorted(reviews)],
        visual_review_file=str(review_path.relative_to(ROOT)).replace('\\','/'),
        source_audit=report,hangul_visibility=visibility)
    target.with_suffix('.qa.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf8')
    registry=ROOT/'tools/izho_2021_2022_original_style_ready.json'
    records=json.loads(registry.read_text('utf8'))if registry.exists()else[]
    records=[entry for entry in records if(entry['year'],entry['kind'])!=(year,kind)]+[record]
    records.sort(key=lambda entry:(entry['year'],entry['kind']))
    registry.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps({key:value for key,value in record.items()if key not in ['source_audit','hangul_visibility']},ensure_ascii=False),flush=True)
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('year',type=int,choices=[2021,2022]);p.add_argument('kind',choices=['T','TS'])
    p.add_argument('--ready',action='store_true')
    p.add_argument('--move-final',action='store_true',help='Rename a newly audited assembly into a new canonical target, avoiding a duplicate PDF')
    a=p.parse_args();rebuild(a.year,a.kind,a.ready,a.move_final)
