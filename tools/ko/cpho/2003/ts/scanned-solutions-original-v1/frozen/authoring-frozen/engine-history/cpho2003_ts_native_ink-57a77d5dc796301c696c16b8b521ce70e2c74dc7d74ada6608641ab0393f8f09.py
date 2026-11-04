"""Actual original native math/scripts and folio ink; no translated baseline."""
from pathlib import Path
import json,hashlib
import pymupdf as f
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_moved_native_ink import audit_moved_native_ink
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
T=B/'TS';SOURCE=B/'inputs/CPhO_2003_Chinese_original.pdf'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(number,lang,proof_override=None,output_override=None):
 reference=T/f'proofs/{lang}/page{number:02}.pdf'
 proof=Path(proof_override)if proof_override else reference
 output=Path(output_override)if output_override else proof.with_suffix('.original-source-native-ink-v2.json')
 if output.exists():
  old=json.loads(output.read_text('utf8'));assert old['passed']and old['output_sha256']==sha(proof);return old
 assert sha(SOURCE)=='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
 composition=json.loads(reference.with_suffix('.composition.json').read_text('utf8'))
 assert composition['output_sha256']==sha(reference)
 erased={glyph_key(g)for g in composition['header']['erased_original_prose']}
 with f.open(SOURCE)as original:
  native=[g for g in _traces(original[number-1])if g['c'].strip()and glyph_key(g)not in erased]
 assert native
 q=audit_moved_native_ink(SOURCE,number,proof,protected_glyphs=native,shifts=composition['header']['native_shifts'])
 q.update(schema='cpho2003-ts-actual-original-native-ink-v2',source_page=number,language=lang,no_initial_baseline_or_other_translated_control_used=True,current_positive_reference_sha256=sha(reference),actual_original_native_nonspace_glyphs=len(native),hybrid_complete_condition_and_original_scripts_checked=number==10)
 assert not output.exists();output.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 assert q['passed'],('Actual source-native ink missing',q['newly_missing_native_ink_pixels'])
 print('C03_TS_ACTUAL_ORIGINAL_NATIVE_INK_PASS',number,lang,len(native),q['newly_missing_native_ink_pixels'],flush=True)
 return q
