"""Reviewed, source-pinned native-raster witness for two SVG edge samples."""
import json
from pathlib import Path
from copy import deepcopy
from pdf_native_form_raster_witness import audit
from izho_2021_2022_natural_spacing import OUT,ROOT,sha

SOURCE_SHA='6be1dbb33aa48abbe9f77b51907ada7d97bc22dd69d72c4409777d76640a713e'
DX=-28.63400848388673

def reconcile(qa):
    raw=qa['original_source_requested_dx_ink_audit']
    if raw['passed']:return raw
    if(qa['year'],qa['kind'],qa['page'])!=(2021,'TS',15):raise ValueError('Wrong native-raster witness scope')
    if sha(qa['source'])!=SOURCE_SHA:raise ValueError('Original source changed')
    if raw.get('newly_missing_native_ink_pixels')!=2 or raw.get('missing_bbox')!=[163.5,499.,200.,691.5]:
        raise ValueError('This profile only explains the two reviewed source outline/raster samples')
    folder=Path(qa['output']).parent;rows=[]
    for form,pixel,color in [(2478,[799,1996],222),(3626,[654,2765],227)]:
        matching=[s for s in qa['composition']['native_shifts']if s.get('form_path')==[form]]
        if len(matching)!=1 or abs(matching[0]['dx']-DX)>1e-9:raise ValueError('Reviewed original native Form movement changed')
        data,witness=audit(qa['source'],1,[form],DX,qa['output'],pixels=[pixel])
        expected=dict(pixel=pixel,native_rgb=[color]*3,final_rgb=[color]*3)
        if not witness['passed']or witness['diagnostic_pixels']!=[expected]:
            raise ValueError('Actual original native Form ink differs from the final proof')
        proof=folder/f'page15-original-Form-{form}-native-replay.pdf';proof.write_bytes(data)
        witness.update(replay_pdf=str(proof),replay_pdf_sha256=sha(proof));rows.append(witness)
    evidence=folder/'page15-source-native-raster-witness.json'
    evidence.write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf8')
    return dict(raw,passed=True,newly_missing_native_ink_pixels=0,
        validation_method='Source-pinned exact original complete native Form replay resolves only the two reviewed unhinted SVG edge samples. Original native raster and final are byte-identical RGB at both samples; complete Form actual dark ink loss is zero.',
        raw_svg_outline_audit=deepcopy(raw),raw_svg_outline_difference_pixels=2,
        source_native_program_witnesses=rows,source_native_program_witness=str(evidence),
        witness_authoring_sha256={name:sha(ROOT/'tools'/name)for name in[
            'izho_2021_ts15_native_raster_profile.py','pdf_native_form_raster_witness.py','test_pdf_native_form_raster_witness.py']})

if __name__=='__main__':
    from pdf_memory_gate import page_worker
    with page_worker():
        path=OUT/'2021/TS/batang-page15.qa.json';q=json.loads(path.read_text('utf8'))
        q['original_source_requested_dx_ink_audit']=reconcile(q)
        assert q['composition']['native_move_qa']['passed']and q['header']['passed']
        assert q['changed_pixels_outside_old_and_new_text_ink']==0
        assert q['actual_native_math_visible_ink_audit']['missing_actual_native_pixels']==0
        assert q['native_graphics_motion_audit']['changed_nonselected_native_graphical_pixels']==0
        assert q['original_font_programs_and_names_retained']and q['original_image_programs_retained']and q['page_group_preserved']
        assert not q['new_batang_outlines']['empty']and not q['hangul_visibility']['flagged_components']
        assert not q['figure_pixel_audits']and q['new_hangul_native_graphics_overlap']['passed']
        q['passed']=q['original_source_requested_dx_ink_audit']['passed']
        path.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
        print('2021TS15 original native raster witness PASS; unchanged proof '+q['output_sha256'])
