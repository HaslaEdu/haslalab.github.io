"""Frozen continuation guards. No rendering or writes at import time."""
from pathlib import Path
import hashlib
import json
C=Path(__file__).resolve().parent
A=C.parent
O=A.parents[1]
R=O/'revisions/final62-v3'
F=O/'final/2024-v3'
PRODUCTION='fd600ecbd54dc70bf25033bf9eebf4a065ac3256175ecfdf3ff70954361625e4'
AUDITOR_FREEZE='cf9cbf12fc44e398d55869c8d0be416c85c6ec347a962567e14376fd406f4ffe'
POSITIVE='1badd547ccd6b1a0a8a624819469da05b5b28376389ae41a9df81c91e77ee382'
NEGATIVE='ad132f31de1cb85bddfe3631efa3d12876084fc4a5eae216dc3e06399a5a6445'
AUDITOR='71a4437ddf0a99abc9585ef3585c26c668e42fc891ee0148f7cf6e44f153f21b'


def sha(p):
    with Path(p).open('rb')as h:return hashlib.file_digest(h,'sha256').hexdigest()


def read(p):return json.loads(Path(p).read_text('utf8'))
def pin(p):return dict(path=str(p),sha256=sha(p))


def verify_code():
    for p,s in read(C/'CODE-INPUT-FREEZE.json')['program_and_input_sha256'].items():assert sha(p)==s,p
    assert sha(R/'FINAL-CODE-INPUT-FREEZE.json')==PRODUCTION
    assert sha(A/'AUDITOR-CODE-INPUT-FREEZE.json')==AUDITOR_FREEZE
    for p,s in read(A/'AUDITOR-CODE-INPUT-FREEZE.json')['program_and_input_sha256'].items():assert sha(p)==s,p


def verify_go(expected):
    verify_code()
    p=C/'ROOT-GO-CONTINUATION.json';assert sha(p)==expected
    go=read(p)
    assert go['status']=='ROOT_GO_QA3_CONTINUATION_OF_FROZEN_FINAL62_V3'
    assert go['production_freeze_sha256']==PRODUCTION
    assert go['auditor_code_input_freeze_sha256']==AUDITOR_FREEZE
    assert go['continuation_code_input_freeze_sha256']==sha(C/'CODE-INPUT-FREEZE.json')
    assert go['actual_positive_sha256']==POSITIVE and go['actual_negative_regressions_sha256']==NEGATIVE
    return go


def complete_pages():
    old=read(F/'driver-progress.json');assert old['complete']==list(range(1,32))
    extra=read(A/'continuation-progress.json')['complete']if(A/'continuation-progress.json').exists()else[]
    return sorted(old['complete']+extra)


def lineage():
    return dict(auditor_code_input_freeze=pin(A/'AUDITOR-CODE-INPUT-FREEZE.json'),
        root_GO=pin(C/'ROOT-GO-CONTINUATION.json'),actual_positive=pin(A/'actual-p32-external-pixel-KK-audit.json'),
        actual_negative_regressions=pin(A/'actual-PDF-negative-regressions.json'),
        auditor_program=pin(A/'audit_p32_source_stroke_support.py'),continuation_code_input_freeze=pin(C/'CODE-INPUT-FREEZE.json'))


def verify_originals():
    prod=read(R/'FINAL-CODE-INPUT-FREEZE.json')
    for table in ['preserved_input_sha256','preserved_prior_output_sha256']:
        for p,s in prod[table].items():assert sha(p)==s,p
    originals=[]
    for name in ['protection-pins.json','supplementary-path-pins.json','visual-reference-pins.json']:originals.extend(read(O/name)['original_files'])
    assert len(originals)==910
    for v in originals:assert sha(v['source'])==sha(v['copy'])==v['sha256'],v['source']
    working=read(O/'protection-pins.json')['working_copies'];assert len(working)==171
    for v in working:assert sha(v['path'])==sha(v['frozen'])==v['sha256'],v['path']
