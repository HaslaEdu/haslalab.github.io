"""Freeze the implemented runtime and approved operands before five final cases."""
from pathlib import Path
import ast,datetime,json,shutil,sys
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'common'))
import r4_guard as g
def main():
    output=ROOT/'PROTOTYPE-RUNTIME-FROZEN.json';assert not output.exists()
    g.assert_all_inputs()
    code=set(p for y in (2023,2024,2025,2026) for p in g.runtime_files(y))
    code.update(ROOT/p for p in ['run_prototype.py','audit_prototype.py','run_final_page.py','audit_final_page.py',
        'test_prototype_negatives_v2_final.py','freeze_r4_runtime.py','run_frozen_five.py','finalize_preparation.py','generate_final48.py'])
    for path in code:ast.parse(path.read_text('utf8'),filename=str(path))
    extra=[ROOT/p for p in ['input-ledger.json','EXPERIMENT-GO.json','EXPERIMENT-BATANG-PAINT-ADDENDUM-GO.json',
        'APPROVED-2026-P1-EXISTING-AA-CONTACT-ROW.json','candidates/2026-Batang-glyph-origin-reset.patch',
        'FINAL48-CONDITIONAL-AUTHORIZATION.json','experiments/ROOT-THREE-PROTOTYPE-REVIEW.json',
        'experiments/ROOT-2026-TWO-PROTOTYPE-REVIEW.json']]
    row=json.loads((ROOT/'APPROVED-2026-P1-EXISTING-AA-CONTACT-ROW.json').read_text('utf8'))
    extra.extend(Path(row[k]['path']) for k in ('precontact_proof','precontact_layout','diagnosis','source_comparison'))
    extra.extend(ROOT/p for p in ['experiments/attempt-proto06/2026/page01.pdf','experiments/attempt-proto06/2026/page01.layout.json',
        'experiments/attempt-proto06/2026/page01.renderer-W-diagnosis-v2.json'])
    retained=ROOT/'frozen-runtime-sources';retained.mkdir(exist_ok=False)
    codehash={};extrahash={};copies={}
    for path in sorted(set(code)|set(extra)):
        target=retained/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        digest=g.sha(path);assert g.sha(target)==digest
        (codehash if path in code else extrahash)[str(path)]=digest;copies[str(path)]=dict(path=str(target),sha256=digest)
    value=dict(status='ROOT_AUTHORIZED_FIVE_PROTOTYPES_RUNTIME_AND_APPROVED_INPUTS_FROZEN',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtime_code_sha256=codehash,
        runtime_input_sha256=extrahash,runtime_sha256=dict(codehash,**extrahash),retained_source_copies=copies,
        input_ledger_sha256=g.sha(ROOT/'input-ledger.json'),allowed_cases=sorted(g.FIVE),final48_generation_authorized=False)
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8');g.assert_all_inputs()
    print(json.dumps(dict(path=str(output),sha256=g.sha(output),code_files=len(codehash),approved_inputs=len(extrahash))))
if __name__=='__main__':main()
