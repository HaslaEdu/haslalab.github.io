"""After exact root GO, add sidecars and PNGs without touching failed layout/PDF."""
import argparse
import json
import shutil
import sys
sys.dont_write_bytecode=True
import qa3_common as g
parser=argparse.ArgumentParser();parser.add_argument('--root-go-sha',required=True);args=parser.parse_args()
g.verify_go(args.root_go_sha)
assert g.sha(g.F/'page32.pdf')=='295d4bcd98d367c2cc0a140ba5d824fdf3345407500b03a127e04d1d2b159219'
assert g.sha(g.F/'page32.layout.json')=='1b5cdf8f40e8774344d024a5ccdbde997137be37a0f18027000619cfc2971eea'
assert g.sha(g.A/'actual-p32-external-pixel-KK-audit.json')==g.POSITIVE
assert g.sha(g.A/'actual-PDF-negative-regressions.json')==g.NEGATIVE
import pymupdf as fitz
for suffix in ['.pixel-KK-audit.json','.png','-source.png','.render.json']:assert not(g.F/('page32'+suffix)).exists()
q=g.read(g.F/'page32.layout.json')
with fitz.open(g.F/'page32.pdf')as doc,fitz.open(g.O/'frozen/source/IChO_2024_T_EN.pdf')as source:
    doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(g.F/'page32.png')
    source[31].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(g.F/'page32-source.png')
shutil.copyfile(g.A/'actual-p32-external-pixel-KK-audit.json',g.F/'page32.pixel-KK-audit.json')
metadata=dict(page=32,proof_sha256=g.sha(g.F/'page32.pdf'),layout_sha256=g.sha(g.F/'page32.layout.json'),
    composer_sha256=q['composer_sha256'],source_sha256=q['source_sha256'],render_scale=1.5,
    image_sha256=g.sha(g.F/'page32.png'),source_image_sha256=g.sha(g.F/'page32-source.png'),
    audit_program_sha256=g.AUDITOR,render_binding_program_sha256=g.sha(__file__),qa_amendment=g.lineage())
(g.F/'page32.render.json').write_text(json.dumps(metadata,indent=2)+'\n','utf8')
assert g.sha(g.F/'page32.layout.json')=='1b5cdf8f40e8774344d024a5ccdbde997137be37a0f18027000619cfc2971eea'
g.verify_code()
print('P32-EXTERNAL-SIDECAR-AND-PNG-BOUND-NO-LAYOUT-CHANGE',flush=True)
