"""One uniform final page. Caller holds the shared gate; fresh final48 GO required."""
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'common'))
import r4_guard as g

def main():
    year,page=int(sys.argv[1]),int(sys.argv[2]);cfg=g.rules(ROOT/str(year))
    target=ROOT/str(year)/f'proofs/ortvay/{year}/page{page:02}.pdf'
    g.validate_output(year,page,target);g.assert_all_inputs();g.assert_runtime_frozen()
    assert not target.exists(),'Never overwrite a final correction proof'
    target.parent.mkdir(parents=True,exist_ok=True)
    snapshot=g.capture_runtime_snapshot(year,ROOT/f'runtime-snapshots/final-{year}-{page:02}-build')
    env=dict(os.environ,R4_RUNTIME_SNAPSHOT=str(snapshot),R4_OUTPUT_DIRECTORY=str(target.parent),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    os.environ.update({k:env[k] for k in ('R4_RUNTIME_SNAPSHOT','R4_OUTPUT_DIRECTORY')})
    kernel=ROOT/str(year)/'composer'/('natural_plan_compose_ortvay2023_final.py' if year==2023 else f'natural_plan_compose_ortvay{year}_title_final.py')
    command=[sys.executable,str(kernel),cfg['base_plans'][str(page)]['path'],str(target)]
    if str(page) in cfg['overrides']:command+=['--overrides',cfg['overrides'][str(page)]['path']]
    run=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
    target.with_suffix('.build.log').write_text(run.stdout,'utf8');print(run.stdout,flush=True)
    assert run.returncode==0,('Final compositor failed; diagnostic outputs retained',run.returncode)
    g.assert_runtime_snapshot();g.assert_runtime_frozen();g.assert_all_inputs()
    # This subprocess reuses the already held gate; it must never nest a gate.
    audit=subprocess.run([sys.executable,str(ROOT/'audit_final_page.py'),str(year),str(page)],env=env,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
    target.with_suffix('.independent-audit.log').write_text(audit.stdout,'utf8');print(audit.stdout,flush=True)
    assert audit.returncode==0,('Final independent audit failed; proof retained',audit.returncode)
    g.assert_runtime_frozen();g.assert_all_inputs()
    result=dict(status='PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW',year=year,page=page,
        proof=dict(path=str(target),sha256=g.sha(target)),
        layout=dict(path=str(target.with_suffix('.layout.json')),sha256=g.sha(target.with_suffix('.layout.json'))),
        png=dict(path=str(target.with_suffix('.png')),sha256=g.sha(target.with_suffix('.png'))),
        independent_audit=dict(path=str(target.with_suffix('.independent-qa.json')),sha256=g.sha(target.with_suffix('.independent-qa.json'))),
        effective_plan=dict(path=str(target.with_suffix('.effective-plan.json')),sha256=g.sha(target.with_suffix('.effective-plan.json'))),
        runtime_snapshot=dict(path=str(snapshot),sha256=g.sha(snapshot)),human_read_pending=True)
    target.with_suffix('.result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
