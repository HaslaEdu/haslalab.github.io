from pathlib import Path
from collections import Counter
import sys,json,hashlib,pymupdf as f,pikepdf
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');E=B/'engine';F=B/'natural/2019/TS';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import reposition_inline,_traces,_font_programs
from pdf_native_glyph_raster_witness import audit
source=B/'2019/source/IZhO_2019_TS.pdf';proof=F/'page06.pdf';before=sha(proof);assert before=='18316acf25994fb13e39381a168363d7238191103c79a5f2d38a3485de46b71a';wpath=B/'natural/2019-page06-independent-native-digit3-witness/witness.json';w=json.loads(wpath.read_text('utf8'));assert sha(wpath)=='99942cab28db7fb97aec48058372a9da1fc439af8cd2997a5b8603e90cfec8e4';out=wpath.parent/'negative-controls';out.mkdir(exist_ok=True)
with page_worker():
 with f.open(proof)as doc:
  rows=_traces(doc[0]);gs=[g for g in rows if g['c']=='3'and g['font']=='TimesNewRomanPSMT'and g['trace_gid']==20 and abs(g['origin'][0]-136.8560028076172)<.001 and abs(g['origin'][1]-770.3759765625)<.001];assert len(gs)==1;g=gs[0]
 raw,qa=reposition_inline(str(proof),1,erased_glyphs=[g],shifts=[]);bad=out/'page06-only-original-native-digit3-removed.pdf';bad.write_bytes(raw)
 with pikepdf.open(proof)as a,pikepdf.open(bad)as b:assert _font_programs(a.pages[0])==_font_programs(b.pages[0])
 checks={str(scale):audit(source,6,bad,w['source_glyph'],w['requested_dx'],scale)for scale in[4,8,12]};assert all(not r['passed']and r['missing_native_CID_reference_pixels']>0 for r in checks.values())
 assert sha(proof)==before;report=dict(positive_proof_sha256=before,positive_witness_sha256=sha(wpath),positive_proof_unmodified=True,bad_PDF_sha256=sha(bad),only_one_original_native_digit3_CID_removed=True,original_font_programs_unchanged=True,native_CID_reference_negative_checks=checks,all_native_CID_raster_scales_rejected_bad_PDF=True,passed=True);(out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE2019_EXACT_ORIGINAL_DIGIT3_CID_REFERENCE_REJECTS_REMOVAL_AT_ALL_4_8_12_SCALES',{s:r['missing_native_CID_reference_pixels']for s,r in checks.items()},flush=True)
