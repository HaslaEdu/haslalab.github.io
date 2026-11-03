"""Generate48 strictly uniform pages sequentially, one shared gate per page."""
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'common'))
import r4_guard as g
GATE=Path('D:/CodexBuilds/Hasla-publish-20261031/tools/pdf_memory_gate.py')
def main():
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['PYTHONIOENCODING']='utf-8'
    g.assert_runtime_frozen();g.assert_all_inputs()
    for year in (2023,2024,2025,2026):
        cfg=g.rules(ROOT/str(year));rows=[]
        for page in range(1,cfg['pages']+1):
            prefix=ROOT/str(year)/f'proofs/ortvay/{year}/page{page:02}'
            result_path=prefix.with_suffix('.result.json')
            if result_path.exists():
                row=json.loads(result_path.read_text('utf8'))
                for key in ('proof','layout','png','independent_audit','effective_plan'):assert g.sha(row[key]['path'])==row[key]['sha256']
                audit=json.loads(Path(row['independent_audit']['path']).read_text('utf8'));assert audit['passed'] and audit['preparation_sha256']==g.sha(ROOT/'PREPARATION-FROZEN.json')
            else:
                run=subprocess.run([sys.executable,str(GATE),'--',sys.executable,str(ROOT/'run_final_page.py'),str(year),str(page)],
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
                log=ROOT/f'final-generation-logs/{year}-page{page:02}.log';log.parent.mkdir(exist_ok=True);log.write_text(run.stdout,'utf8')
                if run.returncode:print(run.stdout,flush=True);raise SystemExit(run.returncode)
                row=json.loads(result_path.read_text('utf8'))
            rows.append(row);print(json.dumps(dict(year=year,page=page,strict_actual_QA_pass=True,png=row['png']['path'],human_read_pending=True)),flush=True)
        output=ROOT/str(year)/'PAGES-GENERATED-STRICT-PASS.json';assert not output.exists()
        value=dict(status='ALL_YEAR_PAGES_STRICT_PASS_HUMAN_READ_REQUIRED',year=year,pages=cfg['pages'],source=dict(path=cfg['source_path'],sha256=cfg['source_sha256']),
            preparation_sha256=g.sha(ROOT/'PREPARATION-FROZEN.json'),page_results=rows,human_read_pending=True)
        output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(dict(year=year,generated_pages=cfg['pages'],manifest_sha256=g.sha(output),human_read_pending=True)),flush=True)
    g.assert_runtime_frozen();g.assert_all_inputs()
if __name__=='__main__':main()
