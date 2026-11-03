"""One root-authorized representative render. Caller holds shared memory gate."""
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'common'))
import r4_guard as guard

def main():
    year,page=int(sys.argv[1]),int(sys.argv[2]);attempt=sys.argv[3]
    assert (year,page) in guard.FIVE
    folder=ROOT/'experiments'/attempt/str(year)
    folder.mkdir(parents=True,exist_ok=True)
    output=folder/f'page{page:02}.pdf'
    assert not output.exists(),'Never overwrite an experimental proof'
    cfg=guard.rules(ROOT/str(year));guard.assert_all_inputs()
    snapshot=guard.capture_runtime_snapshot(year,folder/f'page{page:02}-runtime')
    env=dict(os.environ,R4_RUNTIME_SNAPSHOT=str(snapshot),R4_OUTPUT_DIRECTORY=str(folder),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    os.environ['R4_RUNTIME_SNAPSHOT']=str(snapshot);os.environ['R4_OUTPUT_DIRECTORY']=str(folder)
    kernel=ROOT/str(year)/'composer'/('natural_plan_compose_ortvay2023_final.py' if year==2023 else f'natural_plan_compose_ortvay{year}_title_final.py')
    command=[sys.executable,str(kernel),cfg['base_plans'][str(page)]['path'],str(output)]
    if str(page) in cfg['overrides']:command+=['--overrides',cfg['overrides'][str(page)]['path']]
    run=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
    (folder/f'page{page:02}.render.log').write_text(run.stdout,'utf8')
    print(run.stdout,flush=True)
    if output.exists():
        import pymupdf as fitz
        with fitz.open(output) as doc:doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(output.with_suffix('.png'))
    guard.assert_all_inputs();guard.assert_runtime_snapshot()
    result=dict(year=year,page=page,render_returncode=run.returncode,output=str(output),
        output_sha256=guard.sha(output) if output.exists() else None,runtime_snapshot=str(snapshot),
        runtime_snapshot_sha256=guard.sha(snapshot),independent_audit_pending=True)
    (folder/f'page{page:02}.render-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    raise SystemExit(run.returncode)

if __name__=='__main__':main()
