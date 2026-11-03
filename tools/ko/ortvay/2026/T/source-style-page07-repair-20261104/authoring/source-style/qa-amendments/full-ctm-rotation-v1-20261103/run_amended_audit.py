"""External QA only. Reads immutable R4 proofs; writes solely below this dir."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'common'))
sys.path.insert(0,str(HERE))
import pymupdf as f
import r4_guard as g
from amended_independent_qa import verify,expected_glyphs,match_expected
from amended_outline_qa import audit

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pin(path):
    return dict(path=str(path),sha256=sha(path))

def code_pins():
    return {str(p):sha(p) for p in sorted(HERE.glob('*.py'))}

def check_external_freeze():
    base=json.loads((HERE/'FROZEN-BASE-SOURCES.json').read_text('utf8'))
    assert base['frozen_runtime_sha256']==sha(ROOT/'PROTOTYPE-RUNTIME-FROZEN.json')
    for row in base['sources'].values():assert sha(row['path'])==row['sha256'],'Frozen base source mutated'
    freeze=HERE/'AMENDMENT-FROZEN.json'
    if freeze.exists():
        value=json.loads(freeze.read_text('utf8'))
        assert value['code_sha256']==code_pins()
        assert value['cases_sha256']==sha(HERE/'CASES.json')
        assert value['base_sources_sha256']==sha(HERE/'FROZEN-BASE-SOURCES.json')
    return pin(freeze) if freeze.exists() else None

def load_kernel(year):
    kernel=ROOT/str(year)/'composer'/('natural_plan_compose_ortvay2023_final.py' if year==2023 else f'natural_plan_compose_ortvay{year}_title_final.py')
    sys.path.insert(0,str(kernel.parent))
    spec=importlib.util.spec_from_file_location('external_readonly_kernel',kernel)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    vector_path=kernel.parent/('verify_native_vectors.py' if year==2026 else f'verify_native_vectors_ortvay{year}.py')
    spec=importlib.util.spec_from_file_location('external_readonly_native',vector_path)
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    return module,native,kernel,vector_path

def main():
    name=sys.argv[1];output=Path(sys.argv[2]).resolve()
    assert output.is_relative_to(HERE.resolve()) and not output.exists()
    cases=json.loads((HERE/'CASES.json').read_text('utf8'))['cases'];case=cases[name]
    target=Path(case['target']['path']);layout_path=Path(case['layout']['path'])
    assert sha(target)==case['target']['sha256'] and sha(layout_path)==case['layout']['sha256']
    output.mkdir(parents=True);before_codes=code_pins();freeze=check_external_freeze()
    snapshot=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),case=name,case_spec=case,
        code_sha256=before_codes,case_manifest=pin(HERE/'CASES.json'),base_sources=pin(HERE/'FROZEN-BASE-SOURCES.json'),
        original_runtime_freeze=pin(ROOT/'PROTOTYPE-RUNTIME-FROZEN.json'),original_preparation=pin(ROOT/'PREPARATION-FROZEN.json'),
        input_ledger=pin(ROOT/'input-ledger.json'),external_amendment_freeze=freeze)
    snap=output/'snapshot.json';snap.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n','utf8')
    stage='original_frozen_and_protected_input_guard';failed=None;value=None;original_runtime=None
    try:
        g.assert_runtime_frozen();g.assert_all_inputs();check_external_freeze()
        year,page=case['year'],case['page'];cfg=g.rules(ROOT/str(year))
        q=json.loads(layout_path.read_text('utf8'));assert cfg['year']==year and q['page']==page and q['source_sha256']==cfg['source_sha256']
        adjacent=target.with_suffix('.layout.json')
        assert adjacent.exists() and sha(adjacent)==case['layout']['sha256'],'Native verifier adjacent-layout contract differs'
        stage='retained_original_runtime_snapshot_binding'
        runtime_path=g.capture_runtime_snapshot(year,ROOT/'experiments/ctm-amendment-runtime-v1'/output.relative_to(HERE))
        original_runtime=pin(runtime_path)
        os.environ['R4_RUNTIME_SNAPSHOT']=str(runtime_path)
        os.environ['R4_OUTPUT_DIRECTORY']=str(target.parent)
        g.assert_runtime_snapshot()
        e,nv,kernel,vector_path=load_kernel(year)
        stage='unchanged_native_vector_audit';native=nv.verify(target)
        stage='original_full_master_glyph_geometry'
        with f.open(target) as doc:matched,geometry=match_expected(expected_glyphs(e,q,year),doc[0])
        # The complete original independent checks remain. Only source-bound
        # full CTM style classification and baseline-direction grouping differ.
        # Physical negatives fail here before any raster comparison is attempted.
        stage='amended_full_CTM_independent_audit';value=verify(e,q,target,cfg)
        stage='all_original_CID_W_TJ_master_outline_checks';outline=audit(target,matched,cfg)
        value['actual_outline_and_encoded_W_audit_pending']=False
        value['actual_outline_and_encoded_W_audit']=outline
        value['actual_native_vector_coordinate_audit']=native
        value['original_full_master_geometry']=geometry
        value.update(status='EXTERNAL_FULL_CTM_AMENDMENT_QA_PASS_NOT_PRODUCER_RESUME',case=name,
            year=year,page=page,target=pin(target),layout=pin(layout_path),snapshot=pin(snap),
            audit_runtime_snapshot=original_runtime['path'],audit_runtime_snapshot_sha256=original_runtime['sha256'],
            original_runtime_source_snapshot=original_runtime,
            audit_code_sha256={**{str(p):sha(p) for p in [ROOT/'audit_final_page.py',*sorted((ROOT/'common').glob('*.py'))]},**before_codes},
            original_runtime_freeze=pin(ROOT/'PROTOTYPE-RUNTIME-FROZEN.json'),preparation_sha256=sha(ROOT/'PREPARATION-FROZEN.json'),
            external_code_sha256=before_codes,external_amendment_freeze=freeze,
            frozen_bad_guard_failure_preserved=True,original_proof_layout_ready_logs_and_producer_unchanged=True,
            no_compositor_or_original_PNG_rerender=True)
    except Exception as error:
        failed=dict(status='EXTERNAL_AMENDMENT_QA_REJECTED_NOT_READY',case=name,year=case['year'],page=case['page'],
            stage=stage,exception_type=type(error).__name__,message=str(error),traceback=traceback.format_exc(),
            target=pin(target),layout=pin(layout_path),snapshot=pin(snap),external_code_sha256=before_codes,
            original_runtime_source_snapshot=original_runtime)
    finally:
        assert code_pins()==before_codes,'External checker changed during case'
        check_external_freeze();g.assert_runtime_frozen();g.assert_all_inputs()
        if original_runtime:g.assert_runtime_snapshot()
        assert sha(target)==case['target']['sha256'] and sha(layout_path)==case['layout']['sha256']
    result=failed if failed is not None else value
    result_path=output/('REJECTED.json' if failed else 'audit.json')
    result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(case=name,passed=failed is None,stage=failed.get('stage') if failed else 'all_checks',result=pin(result_path)),ensure_ascii=False),flush=True)
    if failed:raise SystemExit(1)

if __name__=='__main__':main()
