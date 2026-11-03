"""Run exactly five final representatives and current-runtime invalid controls."""
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'common'))
import r4_guard as g
GATE=Path('D:/CodexBuilds/Hasla-publish-20261031/tools/pdf_memory_gate.py')
ATTEMPT='attempt-frozen-final01'
def frozen():
    value=json.loads((ROOT/'PROTOTYPE-RUNTIME-FROZEN.json').read_text('utf8'))
    for name,digest in value['runtime_sha256'].items():assert g.sha(name)==digest,('Frozen source/operand changed',name)
    return value
def gated(command,log):
    frozen();run=subprocess.run([sys.executable,str(GATE),'--',sys.executable,*map(str,command)],
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
    log.parent.mkdir(parents=True,exist_ok=True);log.write_text(run.stdout,'utf8');print(run.stdout,flush=True)
    assert run.returncode==0,('Frozen representative failed; diagnostics retained',str(log));frozen()
def main():
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['PYTHONIOENCODING']='utf-8'
    frozen();g.assert_all_inputs();rows=[]
    for year,page in sorted(g.FIVE):
        prefix=ROOT/'experiments'/ATTEMPT/str(year)/f'page{page:02}'
        gated([ROOT/'run_prototype.py',year,page,ATTEMPT],prefix.with_suffix('.frozen-compose.log'))
        gated([ROOT/'audit_prototype.py',year,page,ATTEMPT,'frozen'],prefix.with_suffix('.frozen-audit.log'))
        rows.append(dict(year=year,page=page,**{key:dict(path=str(prefix.with_suffix(suffix)),sha256=g.sha(prefix.with_suffix(suffix)))
            for key,suffix in [('proof','.pdf'),('layout','.layout.json'),('png','.png'),('effective_plan','.effective-plan.json'),
                ('independent_audit','.independent-qa-frozen.json')]}))
    gated([ROOT/'test_prototype_negatives_v2_final.py'],ROOT/'experiments/prototype-negative-controls-v2-final.log')
    g.assert_all_inputs();frozen()
    output=ROOT/'FIVE-FROZEN-PROTOTYPE-RESULTS.json';assert not output.exists()
    value=dict(status='FIVE_SAME_FROZEN_RUNTIME_STRICT_REPRESENTATIVES_PASS',
        runtime_freeze=dict(path=str(ROOT/'PROTOTYPE-RUNTIME-FROZEN.json'),sha256=g.sha(ROOT/'PROTOTYPE-RUNTIME-FROZEN.json')),
        page_results=rows,negative_controls=dict(path=str(ROOT/'experiments/prototype-negative-controls-v2-final.json'),
            sha256=g.sha(ROOT/'experiments/prototype-negative-controls-v2-final.json')),root_visual_rebinding_pending=True,final48_started=False)
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(path=str(output),sha256=g.sha(output),passed=True)),flush=True)
if __name__=='__main__':main()
