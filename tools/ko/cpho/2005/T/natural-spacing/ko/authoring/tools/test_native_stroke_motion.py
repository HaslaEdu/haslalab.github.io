"""Actual-PDF regression: stroke AA stays inside its exact native path scope."""
from pathlib import Path
import json
import pymupdf as fitz
import pikepdf,os
from pdf_native_inline_reposition import _traces,inspect_inline_groups,reposition_inline
from pdf_native_geometry_motion import audit as old_audit
from pdf_native_geometry_stroke_motion import audit
from pdf_memory_gate import page_worker

BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho-early-natural')
def run():
 folder=BASE/'stroke-audit-regression';folder.mkdir(exist_ok=True)
 source=folder/'source.pdf';target=folder/'moved.pdf';bad=folder/'bad-unselected-line.pdf'
 with fitz.open()as d:
  p=d.new_page(width=594.96,height=842.04);p.insert_text((94.8,444.91),'v',fontname='tiro',fontsize=10.56)
  p.draw_line((93.384,434.82997802734377),(98.064,434.82997802734377),width=.72)
  p.draw_line((200,500),(215,500),width=.72);d.save(source,garbage=0,deflate=False)
 # Synthetic source uses the Word path profile: style before path construction.
 # MuPDF draw_line emits width/color between l and S, which this reviewed
 # native path mover intentionally does not claim. No original PDF is edited.
 with pikepdf.open(source)as pdf:
  for stream in pdf.pages[0].Contents:
   raw=stream.read_bytes()
   if b'.72 w\n0 G S'in raw:
    raw=raw.replace(b'q\n',b'q\n.72 w\n0 G\n',1).replace(b'.72 w\n0 G S',b'S');stream.write(raw)
  tmp=source.with_suffix('.tmp.pdf');pdf.save(tmp,compress_streams=False)
 os.replace(tmp,source)
 with fitz.open(source)as d:g=next(g for g in _traces(d[0])if g['c']=='v')
 inv=inspect_inline_groups(source,1);path=next(p for p in inv['vector_paths']if abs(p['rect'][1]-434.829978)<.01)
 shifts=[dict(glyphs=[{k:g[k]for k in('c','font','size','origin')}],dx=.0959937572479248,vector_paths=[path])]
 raw,moved=reposition_inline(source,1,shifts=shifts);target.write_bytes(raw)
 _,good=audit(source,target,shifts)
 assert good['changed_nonselected_native_graphical_pixels']==0,good
 with fitz.open(target)as d:d[0].draw_line((200,503),(215,503),width=.72);d.save(bad,garbage=0,deflate=False)
 _,tampered=audit(source,bad,shifts)
 assert tampered['changed_nonselected_native_graphical_pixels']>0,tampered
 src=BASE/'output/2013/en/page03-immutable-input.pdf';dst=BASE/'output/2013/en/page03.pdf'
 journal=json.loads(dst.with_suffix('.qa.json').read_text('utf8'))
 _,historical=old_audit(src,dst,journal['native_shifts']);_,repaired=audit(src,dst,journal['native_shifts'])
 assert historical['changed_nonselected_native_graphical_pixels']==2,historical
 assert repaired['changed_nonselected_native_graphical_pixels']==0,repaired
 report=dict(passed=True,fixture_native_move_qa=moved,fixture_geometry=good,unexpected_nonselected_line=tampered,
  actual_2013_EN3_old_geometry=historical,actual_2013_EN3_correct_stroke_geometry=repaired)
 (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
 print(json.dumps(dict(passed=True,actual_source_old=2,actual_source_fixed=0,unexpected_line_detected=tampered['changed_nonselected_native_graphical_pixels']),ensure_ascii=False),flush=True)
 return report
if __name__=='__main__':
 with page_worker():run()
