"""Independent original-source-to-final native ink, not baseline-only QA."""
from pathlib import Path
import sys,json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
from cpho2003_initial_native_baseline import selected_glyphs
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_moved_native_ink import audit_moved_native_ink
import pymupdf as f
source=B/'inputs/CPhO_2003_Chinese_original.pdf';data=json.loads((B/'inputs/original-all10-source-slots.json').read_text('utf8'))
with page_worker(),f.open(source)as doc:
 for lang in ['ko','en']:
  for n in [1,2,3]:
   proof=B/f'natural/2003/{lang}/page{n:02}.pdf';out=B/f'evidence/source-native-ink/{lang}-page{n:02}.json'
   if out.exists():
    old=json.loads(out.read_text('utf8'));assert old['passed']and old['output_sha256']==hashlib.sha256(proof.read_bytes()).hexdigest();continue
   composition=json.loads(proof.with_suffix('.qa.json').read_text('utf8'));erased={glyph_key(g)for g in selected_glyphs(data['pages'][n-1])};native=[g for g in _traces(doc[n-1])if g['c'].strip()and glyph_key(g)not in erased]
   q=audit_moved_native_ink(source,n,proof,protected_glyphs=native,shifts=composition['native_shifts']);assert q['passed'],q
   out=B/f'evidence/source-native-ink/{lang}-page{n:02}.json';out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists();out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('CPHO2003_ORIGINAL_SOURCE_NATIVE_INK_PASS',lang,n,q['protected_native_glyphs'],q['newly_missing_native_ink_pixels'],flush=True)
