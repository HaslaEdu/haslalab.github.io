"""Strict actual final-paper audit with exact frozen sources. No nested gate."""
from pathlib import Path
import importlib.util,json,os,sys
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'common'))
import r4_guard as g
from r4_independent_qa import verify,expected_glyphs,match_expected
from r4_outline_qa import audit
import pymupdf as f

def main():
    year,page=int(sys.argv[1]),int(sys.argv[2]);cfg=g.rules(ROOT/str(year))
    target=ROOT/str(year)/f'proofs/ortvay/{year}/page{page:02}.pdf';g.validate_output(year,page,target)
    output=target.with_suffix('.independent-qa.json');assert not output.exists()
    g.assert_runtime_frozen();g.assert_all_inputs()
    snapshot=g.capture_runtime_snapshot(year,ROOT/f'runtime-snapshots/final-{year}-{page:02}-audit')
    os.environ['R4_RUNTIME_SNAPSHOT']=str(snapshot);os.environ['R4_OUTPUT_DIRECTORY']=str(target.parent)
    kernel=ROOT/str(year)/'composer'/('natural_plan_compose_ortvay2023_final.py' if year==2023 else f'natural_plan_compose_ortvay{year}_title_final.py')
    sys.path.insert(0,str(kernel.parent));spec=importlib.util.spec_from_file_location('r4_kernel',kernel);e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
    nvpath=kernel.parent/('verify_native_vectors.py' if year==2026 else f'verify_native_vectors_ortvay{year}.py')
    nvspec=importlib.util.spec_from_file_location('r4_native_vectors',nvpath);nv=importlib.util.module_from_spec(nvspec);nvspec.loader.exec_module(nv)
    native=nv.verify(target);q=json.loads(target.with_suffix('.layout.json').read_text('utf8'))
    with f.open(target) as doc:
        matched,geometry=match_expected(expected_glyphs(e,q,year),doc[0])
        doc[0].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False).save(target.with_suffix('.png'))
    outline=audit(target,matched,cfg);value=verify(e,q,target,cfg)
    value['actual_outline_and_encoded_W_audit_pending']=False;value['actual_outline_and_encoded_W_audit']=outline
    value['actual_native_vector_coordinate_audit']=native
    value['audit_runtime_snapshot']=str(snapshot);value['audit_runtime_snapshot_sha256']=g.sha(snapshot)
    value['audit_code_sha256']={str(p):g.sha(p) for p in [Path(__file__),*sorted((ROOT/'common').glob('*.py'))]}
    value['preparation_sha256']=g.sha(ROOT/'PREPARATION-FROZEN.json')
    g.assert_runtime_snapshot();g.assert_runtime_frozen();g.assert_all_inputs()
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(passed=True,year=year,page=page,audit=str(output),sha256=g.sha(output),
        geometry_max=geometry['max_position_error_pt'],outline_max=outline['max_transformed_outline_error_pt']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
