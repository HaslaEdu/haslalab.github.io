"""Root-authorized p32 QA binding and unmodified frozen workers33-62."""
import argparse
import json
import shutil
import subprocess
import sys
import time
sys.dont_write_bytecode=True
import qa3_common as g
GATE='D:/CodexBuilds/Hasla-publish-20261031/tools/pdf_memory_gate.py'
p=argparse.ArgumentParser();p.add_argument('--root-go-sha',required=True);args=p.parse_args()
g.verify_go(args.root_go_sha);g.verify_originals()
old=g.read(g.F/'driver-progress.json');assert old['complete']==list(range(1,32))
old_artifacts=old['completed_page_artifact_sha256']
for table in old_artifacts.values():
    for path,s in table.items():assert g.sha(path)==s,path
progress=g.A/'continuation-progress.json'
state=g.read(progress)if progress.exists()else dict(complete=[],completed_page_artifact_sha256={})
for table in state['completed_page_artifact_sha256'].values():
    for path,s in table.items():assert g.sha(path)==s,path


def stop():
    if not(g.A/'STOP-AFTER-CURRENT-PAGE').exists():return False
    g.verify_code();g.verify_originals()
    print('QA3-SAFE-STOP-COMPLETED-PAGE-BOUNDARY',state['complete'],flush=True)
    return True


for n in range(32,63):
    if stop():sys.exit(0)
    if n in state['complete']:continue
    g.verify_go(args.root_go_sha)
    assert shutil.disk_usage(g.F).free>=256*1024*1024
    worker=[str(g.C/'render_and_bind_p32.py'),'--root-go-sha',args.root_go_sha]if n==32 else[str(g.R/'run_page.py'),str(n)]
    print('QA3-START',n,flush=True)
    subprocess.run([sys.executable,'-X','utf8',GATE,'--',sys.executable,'-X','utf8',*worker],cwd=g.C,check=True)
    g.verify_code()
    q=g.read(g.F/f'page{n:02}.layout.json')
    for field in ['source','plan','overrides','effective_plan','composer']:
        path=q[field if field=='source'else field+'_path'];assert g.sha(path)==q[field+'_sha256'],(n,field)
    assert q['output_sha256']==g.sha(g.F/f'page{n:02}.pdf')
    audit=g.read(g.F/f'page{n:02}.pixel-KK-audit.json');assert audit['passed']and audit['changed_pixels_outside_named_source_rows']==0
    state['complete'].append(n)
    state['completed_page_artifact_sha256'][str(n)]={str(v):g.sha(v)for v in sorted(g.F.glob(f'page{n:02}*'))if v.is_file()}
    state.update(status='QA3_CONTINUATION_IN_PROGRESS_PENDING_ALL62_MANUAL_READ',
        production_code_input_freeze_sha256=g.PRODUCTION,continuation_code_input_freeze_sha256=g.sha(g.C/'CODE-INPUT-FREEZE.json'),
        old_completed_pages=list(range(1,32)),qa_amendment=g.lineage(),program_sha256=g.sha(__file__))
    progress.write_text(json.dumps(state,indent=2)+'\n','utf8')
    print('QA3-PAGE-PASS',n,flush=True)
    if stop():sys.exit(0)
    if n<62:print('OUTSIDE-GATE-YIELD-SECONDS',8,flush=True);time.sleep(8)
g.verify_code();g.verify_originals()
assert state['complete']==list(range(32,63))
all_artifacts={**old_artifacts,**state['completed_page_artifact_sha256']}
for table in all_artifacts.values():
    for path,s in table.items():assert g.sha(path)==s,path
out=g.F/'ALL62-MACHINE-QA-PASS.json';assert not out.exists()
out.write_text(json.dumps(dict(status='ALL62_MACHINE_QA_PASS_PENDING_ALL62_MANUAL_PNG_REVIEW',pages=list(range(1,63)),
    all910_originals_and_frozen_copies_unchanged=True,all171_initial_working_copies_unchanged=True,
    all_frozen_runtime_and_inputs_unchanged=True,code_input_freeze_sha256=g.PRODUCTION,qa_amendment=g.lineage(),
    final_page_artifact_sha256=all_artifacts,program_sha256=g.sha(__file__)),indent=2)+'\n','utf8')
print('QA3-ALL62-MACHINE-PASS',out,g.sha(out),flush=True)
