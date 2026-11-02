"""Freeze shared readiness plus the early-edition independent extra checks."""
import argparse,json
from pathlib import Path
from izho_natural_spacing import BUILD,ROOT
from izho_natural_spacing_qa import sha
from izho_natural_spacing_ready import ready
from pdf_memory_gate import page_worker

def finalize(year):
    folder=BUILD/str(year)/'T';audits=[]
    for plan in sorted((folder/'plans').glob('page*.json')):
        proof=folder/(plan.stem+'.pdf');q=json.loads(proof.with_suffix('.audit.json').read_text('utf8'))
        assert q['output_sha256']==sha(proof)and q['passed']
        assert q['independent_new_hangul_native_graphics_overlap']['passed']
        assert q['independent_source_grading_columns']['passed'];audits.append(q)
    manifest=ready(year,'T');snapshot=Path(manifest['authoring_snapshot'])
    for name in['izho_early_natural_batch.py','izho_early_natural_extra_qa.py','izho_early_natural_ready.py',
                'pdf_new_hangul_graphics_overlap.py','test_pdf_new_hangul_graphics_overlap.py',
                'pdf_grading_columns_stationary.py','pdf_original_image_ink.py','pdf_original_graphics_ink.py',
                'pdf_original_text_ops.py','pdf_hangul_visibility.py','izho_new_prose_outline_qa.py',
                'izho_early_fixed_style.py','test_izho_native_image_atoms.py','test_pdf_native_image_motion.py']:
        source=ROOT/'tools'/name;target=snapshot/'tools'/name;target.write_bytes(source.read_bytes())
        manifest['authoring_files'][str(Path('tools')/name)]=sha(target)
    manifest['independent_new_hangul_native_graphics_overlap_pixels']=sum(q['independent_new_hangul_native_graphics_overlap']['new_hangul_dark_pixels_over_native_foreground']for q in audits)
    manifest['independent_stationary_original_grading_glyphs_checked']=sum(q['independent_source_grading_columns']['original_grading_glyphs_checked']for q in audits)
    manifest['supplementary_page_checks']=[dict(page=i+1,proof_sha256=q['output_sha256'],
        new_hangul_native_graphics_overlap=q['independent_new_hangul_native_graphics_overlap'],
        original_grading_columns=q['independent_source_grading_columns'])for i,q in enumerate(audits)]
    manifest['authoring_capture_note']='Current readiness source bytes are frozen after all exact final proofs pass independent audits; per-page supplementary QA source hashes are separately recorded in audit reports. Already frozen snapshots and editions are retained.'
    output=Path(manifest['output']);output.with_suffix('.ready.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')
    print('READY',year,manifest['pages'],manifest['sha256'],flush=True);return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);a=p.parse_args()
    with page_worker():finalize(a.year)
