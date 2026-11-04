"""Prove the real fraction-bar control changed no original encoded glyph state."""
from pathlib import Path
import sys,json,hashlib
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from cpho2008_original_CID_states import audit
from pdf_native_inline_reposition import inspect_inline_groups
from cpho2008_atomic_authoring import atomic_text
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))
source=B/'source/CPhO_2008_original_combined_ZH.pdf';summary=read(B/'actual-negative-PDF-controls/all7-actual-source-native-design-negatives.json');row=summary['actual_unique_bad_PDFs'][0];assert row['kind']=='single-original-fraction-bar-dx'
bad=Path(row['actual_bad_PDF_path']);assert sha(bad)==row['actual_bad_PDF_sha256'];positive=B/'proofs/ko/page15.pdf';pin=sha(positive);assert pin==row['positive_proof_sha256'];c=read(positive.with_suffix('.composition.json'))
with page_worker():
    result=audit(source,15,bad,read(B/'inspection/page15-original-native-programs.json'),inspect_inline_groups(bad,1,include_text_shows=True),c['erased_original_language_glyphs'])
assert result['passed']and not result['errors'];assert sha(positive)==pin
out=B/'actual-negative-PDF-controls/single-fraction-bar-all-original-encoded-CIDs-unchanged.json'
atomic_text(out,json.dumps(dict(original_source_sha256=sha(source),positive_proof_sha256=pin,actual_bar_only_bad_PDF_sha256=sha(bad),positive_proof_unmodified=True,actual_original_encoded_CID_state_audit=result,all_original_encoded_CIDs_fonts_GIDs_Tf_full_Tm_fractional_points_paint_ancestor_clips_unchanged=True,only_original_fraction_rule_changed_and_independent_native_geometry_rejects=True,passed=True),ensure_ascii=False,indent=2)+'\n');print('C08_REAL_BAR_NEGATIVE_ORIGINAL_CID_IDENTITY_PASS',result['actual_original_encoded_CIDs_checked'])
