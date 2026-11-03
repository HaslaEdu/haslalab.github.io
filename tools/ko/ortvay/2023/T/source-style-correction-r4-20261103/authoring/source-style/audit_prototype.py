"""Read one already generated representative proof under the shared gate."""
from pathlib import Path
import importlib.util,json,os,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'common'))
from r4_guard import rules,sha,assert_all_inputs,capture_runtime_snapshot,assert_runtime_snapshot
from r4_independent_qa import verify,expected_glyphs,match_expected
from r4_outline_qa import audit
import pymupdf as f

def main():
    year,page=int(sys.argv[1]),int(sys.argv[2]);folder=ROOT/'experiments'/sys.argv[3]/str(year)
    target=folder/f'page{page:02}.pdf';tag=sys.argv[4] if len(sys.argv)>4 else 'v2'
    output=target.with_suffix(f'.independent-qa-{tag}.json');assert not output.exists()
    kernel=ROOT/str(year)/'composer'/('natural_plan_compose_ortvay2023_final.py' if year==2023 else f'natural_plan_compose_ortvay{year}_title_final.py')
    cfg=rules(ROOT/str(year))
    snapshot=capture_runtime_snapshot(year,folder/f'page{page:02}-audit-runtime-{tag}')
    os.environ['R4_RUNTIME_SNAPSHOT']=str(snapshot);os.environ['R4_OUTPUT_DIRECTORY']=str(folder)
    sys.path.insert(0,str(kernel.parent))
    spec=importlib.util.spec_from_file_location('r4_kernel',kernel);e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
    assert_all_inputs()
    nvpath=kernel.parent/('verify_native_vectors.py' if year==2026 else f'verify_native_vectors_ortvay{year}.py')
    nvspec=importlib.util.spec_from_file_location('r4_native_vectors',nvpath);nv=importlib.util.module_from_spec(nvspec);nvspec.loader.exec_module(nv)
    native=nv.verify(target)
    q=json.loads(target.with_suffix('.layout.json').read_text('utf8'))
    with f.open(target) as doc:matched,geometry=match_expected(expected_glyphs(e,q,year),doc[0])
    outline=audit(target,matched,cfg)
    value=verify(e,q,target,cfg);value['actual_outline_and_encoded_W_audit_pending']=False
    value['actual_outline_and_encoded_W_audit']=outline
    value['actual_native_vector_coordinate_audit']=native
    value['audit_runtime_snapshot']=str(snapshot);value['audit_runtime_snapshot_sha256']=sha(snapshot)
    value['audit_code_sha256']={str(p):sha(p) for p in [Path(__file__),*sorted((ROOT/'common').glob('*.py'))]}
    assert_all_inputs();assert_runtime_snapshot();output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(audit=str(output),sha256=sha(output),passed=True,
        geometry_max=geometry['max_position_error_pt'],outline_max=outline['max_transformed_outline_error_pt'],
        actual_W_TJ_origin_max=outline['actual_W_TJ_replay_max_origin_error_pt'],
        kk_pairs=value['actual_stream_interrow_ink']['tested_close_row_pairs'],
        references=[dict(lineage=v['lineage'],outside_pixels=v['changed_pixels_outside_explicit_glyph_union']) for v in value['direct_reference_comparisons']]),ensure_ascii=False))

if __name__=='__main__':main()
