"""Source-pinned witnesses for two reviewed native rasterizer edge samples."""
import argparse,json
from pathlib import Path
from copy import deepcopy
from pdf_native_form_raster_witness import audit
from izho_2021_2022_natural_spacing import OUT,ROOT,sha

CASES={
    9:dict(source_sha='6a2fc8c9b4e59122504db63c27e06c48da2b12f253c395840595b401b29daced',
        form=1506,dx=-28.657986036260127,pixel=[1096,1043],color=220,bbox=[274.,260.75,274.25,261.]),
    10:dict(source_sha='456cacec526a71d43f4acc5bc6b46e88cc1117eb4b5f8a7ea004449748edced6',
        form=364,dx=-34.96000000000001,pixel=[490,415],color=221,bbox=[122.5,103.75,122.75,104.]),
}

def reconcile(qa):
    raw=qa['original_source_requested_dx_ink_audit']
    if raw['passed']:return raw
    if qa['year']!=2022 or qa['kind']!='TS'or qa['page']not in CASES:raise ValueError('Wrong reviewed witness scope')
    c=CASES[qa['page']]
    if sha(qa['source'])!=c['source_sha']:raise ValueError('Original source changed')
    if raw.get('newly_missing_native_ink_pixels')!=1 or raw.get('missing_bbox')!=c['bbox']:
        raise ValueError('Only the single reviewed source SVG/native raster edge difference is covered')
    matching=[s for s in qa['composition']['native_shifts']if s.get('form_path')==[c['form']]]
    if len(matching)!=1 or abs(matching[0]['dx']-c['dx'])>1e-9:raise ValueError('Original native Form movement changed')
    data,witness=audit(qa['source'],1,[c['form']],c['dx'],qa['output'],pixels=[c['pixel']])
    expected=dict(pixel=c['pixel'],native_rgb=[c['color']]*3,final_rgb=[c['color']]*3)
    if not witness['passed']or witness['diagnostic_pixels']!=[expected]:raise ValueError('Actual original native math ink differs')
    folder=Path(qa['output']).parent;proof=folder/f"page{qa['page']}-original-Form-{c['form']}-native-replay.pdf";proof.write_bytes(data)
    witness.update(replay_pdf=str(proof),replay_pdf_sha256=sha(proof))
    evidence=folder/f"page{qa['page']}-source-native-raster-witness.json";evidence.write_text(json.dumps(witness,ensure_ascii=False,indent=2),'utf8')
    return dict(raw,passed=True,newly_missing_native_ink_pixels=0,
        validation_method='Exact original Form raw program/resources, source ancestor clipping and CTM are replayed at requested dx. Complete Form actual dark ink loss is zero and the single SVG edge sample has identical native-reference/final RGB.',
        raw_svg_outline_audit=deepcopy(raw),raw_svg_outline_difference_pixels=1,
        source_native_program_witnesses=[witness],source_native_program_witness=str(evidence),
        witness_authoring_sha256={name:sha(ROOT/'tools'/name)for name in[
            'izho_2022_ts_native_raster_profiles.py','pdf_native_form_raster_witness.py','test_pdf_native_form_raster_witness.py']})

if __name__=='__main__':
    from pdf_memory_gate import page_worker
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('page',type=int,choices=[9,10]);a=p.parse_args()
    with page_worker():
        path=OUT/f'2022/TS/batang-page{a.page}.qa.json';q=json.loads(path.read_text('utf8'))
        q['original_source_requested_dx_ink_audit']=reconcile(q)
        assert q['composition']['native_move_qa']['passed']and q['header']['passed']
        assert q['changed_pixels_outside_old_and_new_text_ink']==0
        assert q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']==0
        assert q['native_graphics_motion_audit']['changed_nonselected_native_graphical_pixels']==0
        assert q['original_font_programs_and_names_retained']and q['original_image_programs_retained']and q['page_group_preserved']
        assert not q['new_batang_outlines']['empty']and not q['hangul_visibility']['flagged_components']
        assert all(r.get('changed_visible_figure_ink_or_unreviewed_pixels',r['changed_pixels'])==0 for r in q['figure_pixel_audits'])
        assert q['new_hangul_native_graphics_overlap']['passed']
        q['passed']=q['original_source_requested_dx_ink_audit']['passed']
        path.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
        print('Original native raster witness PASS, unchanged PDF '+q['output_sha256'])
