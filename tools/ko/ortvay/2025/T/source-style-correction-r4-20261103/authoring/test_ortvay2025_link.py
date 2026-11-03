"""Check the real moved URL annotation independently of the final join."""
from pathlib import Path
import json,hashlib
import assemble_natural as join
import pikepdf
import pymupdf as fitz
BASE=Path(__file__).resolve().parents[1]
proof=BASE/'proofs/ortvay/2025/page10.pdf'
qa=json.loads(proof.with_suffix('.layout.json').read_text('utf8'))
source=join.resolve_source(qa['source'],qa['source_sha256'])
out=BASE/'experiments/ortvay2025-link/page10-link.pdf';out.parent.mkdir(parents=True,exist_ok=True)
with fitz.open(source)as original,pikepdf.open(proof)as single:
 audit=join.move_reviewed_url_link(single.pages[0],original[9],qa)
 single.save(out,compress_streams=False)
with fitz.open(proof)as a,fitz.open(out)as b:
 assert join.traces(a[0])==join.traces(b[0])
 changed=int((join.pixels(a[0])!=join.pixels(b[0])).any(axis=2).sum());assert changed==0
 links=[x for x in b[0].get_links()if x.get('uri')==audit['uri']];assert len(links)==1
 actual=list(links[0]['from']);assert max(abs(x-y)for x,y in zip(actual,audit['expected_target_rect_mupdf']))<.001
 audit.update(passed=True,actual_target_rect_mupdf=actual,changed_pixels=changed,all_visible_glyph_geometry_identical=True)
audit.update(proof_sha256=join.sha(proof),test_program_sha256=join.sha(__file__),assembler_sha256=join.sha(join.__file__))
(out.parent/'regression.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(audit,ensure_ascii=False))
