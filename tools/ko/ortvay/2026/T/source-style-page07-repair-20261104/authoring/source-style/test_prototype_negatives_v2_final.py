"""Meaningful invalid-source and actual bad-render controls, no source mutations."""
from pathlib import Path
import copy,importlib.util,json,sys,re
import pymupdf as f
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'common'))
from r4_guard import rules,sha,validate_output,assert_all_inputs
from r4_runtime import source_style_angle
from r4_independent_qa import expected_glyphs,match_expected
from r4_outline_qa import audit as outline_audit
from r4_font_widths import desired_widths,to_unicode,ref

def kernel(year):
    p=ROOT/str(year)/'composer'/('natural_plan_compose_ortvay2023_final.py' if year==2023 else f'natural_plan_compose_ortvay{year}_title_final.py')
    sys.path.insert(0,str(p.parent));s=importlib.util.spec_from_file_location('test_kernel_'+str(year),p);e=importlib.util.module_from_spec(s);s.loader.exec_module(e);return e

def main():
    results=[]
    def rejected(name,callback):
        try:callback()
        except (AssertionError,ValueError) as exc:results.append(dict(name=name,rejected=True,reason=str(exc)[:3500]))
        else:raise AssertionError('Invalid control accepted: '+name)
    assert_all_inputs()
    cfg=rules(ROOT/'2024');entry=next(v for v in cfg['source_style_entries'] if not v['source_style_reference'])
    slot=entry['original_source_slot'];anchor=entry['source_anchor'];plan=dict(source_sha256=cfg['source_sha256'])
    args=[ROOT/'2024',plan,slot,anchor,anchor,entry['font_role'],slot['text'],entry['old_descriptor_angle']]
    assert source_style_angle(*args)==14
    bad=list(args);bad[-1]=14;rejected('wrong_positive_source_descriptor_angle',lambda:source_style_angle(*bad))
    bad=list(args);bad[5]='sans';rejected('wrong_source_style_font_role',lambda:source_style_angle(*bad))
    bad=list(args);bad[2]=dict(slot,source=slot['source']+' altered');rejected('original_source_slot_changed',lambda:source_style_angle(*bad))
    bad=list(args);bad[1]=dict(source_sha256='0'*64);rejected('wrong_original_source_SHA',lambda:source_style_angle(*bad))
    rejected('unapproved_sixth_experiment_case',lambda:validate_output(2024,1,ROOT/'experiments/attempt-negative/2024/page01.pdf'))
    rejected('final48_without_fresh_root_GO',lambda:validate_output(2024,3,ROOT/'2024/proofs/ortvay/2024/page03.pdf'))
    target=ROOT/'experiments/attempt-proto04/2024/page03.pdf';q=json.loads(target.with_suffix('.layout.json').read_text('utf8'));e=kernel(2024)
    p0=next(v['P0'] for v in cfg['reference_pages'] if v['page']==3)
    with f.open(p0['proof_path']) as d:
        matched,_=match_expected(expected_glyphs(e,q,2024),d[0])
    rejected('actual_P0_negative_physical_shear_rejected_by_master_outline',lambda:outline_audit(p0['proof_path'],matched,cfg))
    with f.open(target) as d:
        expected=expected_glyphs(e,q,2024);bad=copy.deepcopy(expected);bad[0]['gid']+=1
        rejected('wrong_full_master_GID',lambda:match_expected(bad,d[0]))
        bad=copy.deepcopy(expected);bad[0]['origin'][0]+=.002
        rejected('new_glyph_origin_over_0_001pt',lambda:match_expected(bad,d[0]))
    cfg26=rules(ROOT/'2026');target=ROOT/'experiments/attempt-proto06/2026/page01.pdf';q=json.loads(target.with_suffix('.layout.json').read_text('utf8'));e26=kernel(2026)
    with f.open(target) as d:
        rejected('exact_W_only_still_fails_actual_master_geometry',lambda:match_expected(expected_glyphs(e26,q,2026),d[0]))
        xref=next(v[0] for v in d[0].get_fonts() if v[4]=='KO_Natural_serif');program=d.extract_font(xref)[3]
        umap=to_unicode(d.xref_stream(ref(d.xref_get_key(xref,'ToUnicode')[1])))
        approved=cfg26['new_Batang_W_precision']
        desired,used=desired_widths(q,'serif',program,umap,lambda cid:cid,approved)
        assert desired and used
        rejected('wrong_bound_CID_to_GID_mapping',lambda:desired_widths(q,'serif',program,umap,lambda cid:cid+1,approved))
        bad=dict(approved,units_per_em=2048)
        rejected('wrong_master_UPEM_2048',lambda:desired_widths(q,'serif',program,umap,lambda cid:cid,bad))
        bad=dict(approved,sha256='0'*64)
        rejected('wrong_approved_master_SHA',lambda:desired_widths(q,'serif',program,umap,lambda cid:cid,bad))
    # Actual no-offset paper must fail the source-master origins of the approved row.
    good=ROOT/'experiments/attempt-proto08/2026/page01.pdf'
    goodq=json.loads(good.with_suffix('.layout.json').read_text('utf8'))
    with f.open(ROOT/'experiments/attempt-proto07/2026/page01.pdf') as d:
        rejected('actual_missing_approved_contact_row_dx',lambda:match_expected(expected_glyphs(e26,goodq,2026),d[0]))
    # Mutate an actual upright glyph paint, retaining all actual resources.
    from r4_actual_paint import streams
    src=ROOT/'experiments/attempt-proto04/2024/page03.pdf'
    srcq=json.loads(src.with_suffix('.layout.json').read_text('utf8'))
    folder=ROOT/'experiments/negative-actual-origin-v2';folder.mkdir(exist_ok=False)
    with f.open(src) as d:
        s=next(v for v in streams(d[0]) if v['font_alias']=='KO_Natural_serif')
        tm=s['text_matrix'];num=rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
        raw,count=re.subn(rb'1 0 0 1 '+num+rb' '+num+rb' Tm',f'1 0 0 1 {tm[4]+.01:.12f} {tm[5]:.12f} Tm'.encode(),s['data']);assert count==1
        d.update_stream(s['xref'],raw);badpdf=folder/'one-actual-glyph-origin-plus0.01.pdf';d.save(badpdf,garbage=0,deflate=False)
    with f.open(badpdf) as d:
        rejected('actual_out_of_scope_origin_movement_0_01pt',lambda:match_expected(expected_glyphs(e,srcq,2024),d[0]))
    assert_all_inputs()
    output=ROOT/'experiments/prototype-negative-controls-v2-final.json';assert not output.exists()
    value=dict(passed=True,negative_controls=len(results),results=results,actual_bad_render_controls_not_synthetic_bounds=True,
        source_and_existing_proofs_unchanged=True,all_original_pins_verified=True,code_sha256=sha(__file__))
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(path=str(output),sha256=sha(output),negative_controls=len(results),passed=True)))

if __name__=='__main__':main()
