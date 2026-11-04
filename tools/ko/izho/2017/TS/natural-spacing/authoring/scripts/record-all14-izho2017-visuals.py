from pathlib import Path
import json,hashlib,datetime
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');F=B/'natural/2017/TS';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text('utf8'));q=load(F/'partial-visual-review.json');pin=sha(F/'page07.pdf')
assert pin=='685e9c601a8e1350244b39dc775a94e57a6b366c484ef6e092e0b95094033db4';a=load(F/'page07.native-prose-order.json');assert a['passed']and a['proof_sha256']==pin;v=load(F/'page07-preview.json');assert v['pdf_sha256']==pin
assert 7 not in [p['page']for p in q['pages']]
q['pages'].append(dict(page=7,proof_sha256=pin,reviewed=True,full_page_original_and_final_visually_read=True,preview_sha256=v['png_sha256'],notes='Full source/current144dpi independently read by root and agent. Correct source order and natural gaps: 식(10)과(11) before both complete equations; or analogous before math23/24. Six complete original native groups4/24/4/14/4/14 preserve all64 native CIDs/fonts/GIDs/points/paint/Y/Tf/Tm/ancestor clips/rules. Original92-CID lower displays/caption unchanged; outside3rows allPopplerpixels identical and other13proofSHA unchanged. Actual prior949 badPDF and one-bar-only damagedPDF rejected.'))
q['pages'].sort(key=lambda r:r['page']);assert len(q['pages'])==len({p['page']for p in q['pages']})==14
assert all(sha(F/('page%02d.pdf'%p['page']))==p['proof_sha256']for p in q['pages'])
q.update(reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),all14_pages_complete=True,all14_original_source_pages_and_grading_complete=True,pending_pages=[]);q.pop('pending_reason',None)
(F/'visual-review.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('ALL14_EXACT_SOURCE_AND_CURRENT_FULLPAGE_VISUALS_APPROVED',flush=True)
