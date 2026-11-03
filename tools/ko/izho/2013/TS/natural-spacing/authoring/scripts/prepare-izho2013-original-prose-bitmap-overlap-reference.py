from pathlib import Path
import hashlib,json,sys,shutil
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces,reposition_inline
from izho_initial_fixed_style import runs_of
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=B/'2013/source/IZhO_2013_TS.pdf';assert sha(source)=='2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1'
author=json.loads((B/'2013/original_style/page2.json').read_text('utf8'));selected=[s for s in author['slots']if s['at']==[5,1,2]];assert len(selected)==1 and 'vaporized'in selected[0]['source_text']
with page_worker():
 with f.open(source)as doc:
  run=runs_of(doc[1])[(5,1,2)];assert run['text']==selected[0]['source_text'];box=f.Rect(run['bbox']);glyphs=[g for g in _traces(doc[1])if g['c']=='p'and g['font']=='TimesNewRomanPSMT'and abs(g['size']-12)<.001 and abs(g['origin'][1]-run['origin'][1])<.001 and box.contains(f.Point(g['origin']))]
 assert len(glyphs)==1,glyphs
 raw,qa=reposition_inline(source,2,erased_glyphs=glyphs)
 folder=B/'2013/reviewed-original-prose-bitmap-overlap';folder.mkdir(exist_ok=True);control=folder/'page02-only-original-selected-English-p-erased.pdf';assert not control.exists();control.write_bytes(raw)
 report=dict(original_source=str(source),original_source_sha256=sha(source),source_page=2,original_prose_at=[5,1,2],original_prose_text=run['text'],exact_erased_original_English_prose_glyph=glyphs[0],control=str(control),control_sha256=sha(control),shared_native_guard_sha256=sha(B/'engine/pdf_native_inline_reposition.py'),native_erasure_verification=qa,reason='The descender of the selected English prose p in vaporized lies inside the transparent white top padding of the following original bitmap. Erase only that exact original English prose glyph in this independent reference control. All original bitmap programs/CTMs, font programs and every other original native glyph remain unchanged. Figure comparison must prove all13 affected source pixels become pure white in the control and every remaining bitmap-region pixel agrees exactly with the translated final PDF.')
 (folder/'reference-provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 plan=B/'natural/2013/TS/plans/page02.json';d=json.loads(plan.read_text('utf8'));history=plan.parent.parent/'history'/('plan-before-original-prose-overlap-'+sha(plan)[:16]);history.mkdir(parents=True,exist_ok=True);shutil.copy2(plan,history/plan.name)
 d['reviewed_original_prose_bitmap_overlap_references']=[dict(rect=[238.10000610351562,156.8499755859375,413.6500244140625,183.8499755859375],reference_provenance=str(folder/'reference-provenance.json'),reference_provenance_sha256=sha(folder/'reference-provenance.json'),control=str(control),control_sha256=sha(control),expected_original_prose_only_pixels_inside_bitmap_rectangle=13)]
 plan.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('ORIGINAL_SELECTED_ENGLISH_P_ONLY_REFERENCE_PREPARED',sha(control),flush=True)
