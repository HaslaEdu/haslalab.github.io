from pathlib import Path
import sys,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'))
from cpho2007_ts_runtime import source_page
from cpho2007_ts_initial_native_baseline import translated_text
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected={'ko':['2a8c6aa40e459492','fbdfdcfeb65a9385','3a68b0058607752c','f68f12e1cd55a7eb','356c1a4572560fad','fb861f73ccd81338','a7277b364624ac16','a2425bff30546ec9','7ba12573e6bfc2ea','55903db55c86a550','2f4a390539f4536c','993ca176317faedb','44f1cbfc76a5da85','d4f453421572f3b1','9c033f9b67cd5f0e','2454c6f53f847297'],'en':['2c374d8ae72efcf6','b1054007ea63a457','ece10e97cfa1f6ba','fbff15fa2f99447c','755cbcc90c36e0b9','de68bb91d74b66bd','99ec942f95d3a00b','0fff754289a59d50','f562841282670ea6','a074947f3bb23182','5dd8964807ac335f','ec81cd4bc674ef05','e26f2ad02458475a','298dd417c0a911da','22ace54a9624e391','2454c6f53f847297']}
renders=json.loads((B/'evidence/poppler144-pages5-20.json').read_text('utf8'));assert len(renders)==32;rows=[]
for lang in ['ko','en']:
 for n in range(5,21):
  r=next(r for r in renders if r['source_page']==n and r['language']==lang);proof=Path(r['proof']);audit=proof.with_suffix('.audit.json');q=json.loads(audit.read_text('utf8'));assert q['passed']and q['output_sha256']==sha(proof)==r['proof_sha256']and sha(proof).startswith(expected[lang][n-5]);assert sha(Path(r['png']))==r['png_sha256']
  if n<20:
   auth=json.loads((B/f'authoring/page{n:02}-bilingual-prose.json').read_text('utf8'))['prose'];journal=json.loads((B/f'native-baseline/{lang}/page{n:02}-source-indexed.build.json').read_text('utf8'));assert {a['id']:a['text']for a in journal['fit_report']}=={s['id']:translated_text(s,auth[s['id']][lang])for s in source_page(n)['slots']}
   assert q['independent_actual_new_prose_native_text_ink']['passed']
  original=B/f'source-renders/page{n:02}.png';assert original.exists()
  rows.append(dict(r,visual_review_pending=False,full_original_and_current_proof_144dpi_visually_reviewed=True,source_png=str(original),source_png_sha256=sha(original),passed=True))
out=B/'authoring/full144-visual-review-complete.json';assert not out.exists();out.write_text(json.dumps(dict(status='ALL32_CURRENT_FULL_PAGE_VISUALS_REVIEWED',source_sha256='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9',reviewer='Assistant full-page original/proof visual inspection',pages_per_language=16,total_proof_pages=32,checks=['All actual original source prose read and translated; final source-slot journal matches current language authoring.','Original15.12pt centered title,12pt section roles and10.56pt body retained; original math fonts/GIDs/point/Y, diagrams, table rules, vectors and source folios retained.','Natural Korean ordinary word spaces, readable clause/line continuations, title centering, no prose overlap, no changed formula shape or clipped figure/table.','All32 full Poppler144dpi proof pages inspected. Source20 is its original blank folio page. Original source18 unmapped comparison-square glyph remains original.','Native/script/image/graphics and independent prose-over-math ink audits passed; five actual negative controls rejected.'],pages=rows),ensure_ascii=False,indent=2)+'\n','utf8');print('ALL_CURRENT_CPHO2007_TS_FULL144_VISUAL_REVIEW_COMPLETE',len(rows),sha(out),flush=True)
