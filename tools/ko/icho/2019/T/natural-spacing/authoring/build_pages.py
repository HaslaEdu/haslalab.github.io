from pathlib import Path
import json,subprocess,sys,hashlib,argparse,shutil,time,os
BASE=Path(__file__).resolve().parent
import icho2019_write_guard as year_guard
PY=Path(sys.executable)
GATE=Path('D:/CodexBuilds/Hasla-publish-20261031/tools/pdf_memory_gate.py')
parser=argparse.ArgumentParser();parser.add_argument('pages',nargs='*',type=int);parser.add_argument('--proof-dir',type=Path,default=year_guard.PROOFS);parser.add_argument('--metadata-copy-dir',type=Path,default=year_guard.METADATA);args=parser.parse_args()
for name in ['proof_dir','metadata_copy_dir']:
    output=getattr(args,name)
    if output is None:continue
    if not output.is_absolute():parser.error('--'+name.replace('_','-')+' requires an absolute path; child cwd must not reinterpret it')
    setattr(args,name,output.resolve())
if args.proof_dir!=year_guard.PROOFS or args.metadata_copy_dir!=year_guard.METADATA:parser.error('IChO2019 output/metadata roots must match the isolated year guard')
year_guard.assert_protected_2024()
pages=args.pages or list(range(1,61));args.proof_dir.mkdir(parents=True,exist_ok=True)
child_env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for page in pages:
    if(BASE/'HOLD-OUTPUT').exists():print('2019 output held for root publication disk space',flush=True);break
    if(BASE/'STOP-AFTER-CURRENT').exists():print('STOP-AFTER-CURRENT marker found; no new page launched.',flush=True);break
    for location in[BASE,args.proof_dir,args.metadata_copy_dir,year_guard.CACHE]:
        location.mkdir(parents=True,exist_ok=True)
        if shutil.disk_usage(location).free<year_guard.MIN_FREE:raise SystemExit('256MiB free-disk minimum reached: '+str(location))
    started=time.time_ns()
    (BASE/'ACTIVE-RUN.json').write_text(json.dumps(dict(pid=__import__('os').getpid(),page=page,proof_dir=str(args.proof_dir),status='running',stop_marker=str(BASE/'STOP-AFTER-CURRENT')),indent=2)+'\n','utf8')
    result=subprocess.run([str(PY),'-X','utf8',str(GATE),'--',str(PY),'-X','utf8',str(BASE/'diagnose_page.py'),str(page),str(args.proof_dir)],capture_output=True,text=True,encoding='utf8',cwd=BASE,env=child_env)
    diagnostic=BASE/f'page{page:02}.diagnostic.json'
    report=json.loads(diagnostic.read_text('utf8'))if diagnostic.exists()and diagnostic.stat().st_mtime_ns>=started else{}
    if args.metadata_copy_dir:
        args.metadata_copy_dir.mkdir(parents=True,exist_ok=True)
        for suffix in['.layout.json','.effective-plan.json']:
            sidecar=args.proof_dir/f'page{page:02}{suffix}'
            if sidecar.exists():
                destination=args.metadata_copy_dir/sidecar.name
                if destination.resolve()!=sidecar.resolve():shutil.copyfile(sidecar,destination)
    print(json.dumps(dict(page=page,returncode=result.returncode,passed=report.get('passed'),error=report.get('error'),elapsed_seconds=report.get('elapsed_seconds')),ensure_ascii=False),flush=True)
    if result.returncode and not report:
        print(result.stderr[-1200:],flush=True)
(BASE/'ACTIVE-RUN.json').write_text(json.dumps(dict(pid=__import__('os').getpid(),status='finished',proof_dir=str(args.proof_dir)),indent=2)+'\n','utf8')
