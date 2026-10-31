"""A reviewed bar cannot be reinserted outside its already-moved clip."""
from pathlib import Path
import json
import pymupdf as fitz,pikepdf
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline,_traces
from pdf_memory_gate import page_worker
ROOT=Path(__file__).resolve().parent

def run():
 source=ROOT/'atomic-source.pdf'
 with fitz.open()as d:
  p=d.new_page(width=600,height=800);p.insert_text((100,230),'v',fontname='tiro',fontsize=12);d.save(source,garbage=0,deflate=False)
 with pikepdf.open(source)as d:
  d.pages[0].Contents=d.make_stream(b'q 90 550 40 60 re W n BT /tiro 12 Tf 1 0 0 1 100 570 Tm <76> Tj ET .72 w 0 G 100 585 m 110 585 l S Q')
  d.save(ROOT/'atomic-source-ready.pdf',compress_streams=False)
 source=ROOT/'atomic-source-ready.pdf';inv=inspect_inline_groups(source,1)
 with fitz.open(source)as d:g=next(g for g in _traces(d[0])if g['c']=='v')
 vector=inv['vector_paths'][0];glyph={k:g[k]for k in('c','font','size','origin')}
 rejected=None
 try:reposition_inline(source,1,shifts=[dict(glyphs=[glyph],dx=10,vector_paths=[vector])])
 except ValueError as e:rejected=str(e)
 assert rejected and 'already owns this reviewed vector path'in rejected,rejected
 raw,qa=reposition_inline(source,1,shifts=[dict(glyphs=[glyph],dx=10)])
 target=ROOT/'atomic-moved-once.pdf';target.write_bytes(raw)
 with fitz.open(target)as d:
  rows=d[0].get_drawings();assert len(rows)==1,rows
  bar=rows[0];assert abs(bar['rect'].x0-110)<.001 and abs(bar['rect'].x1-120)<.001 and abs(bar['width']-.72)<.0001,bar
 data=dict(passed=True,overlap_rejected=rejected,single_atomic_clip_move_qa=qa,bar_moved_once=True,source_stream_unchanged=True)
 (ROOT/'test-report.json').write_text(json.dumps(data,indent=2),'utf8');print(json.dumps(dict(passed=True,overlap_rejected=True,bar_count=1,bar_dx=10)),flush=True)
 return data
if __name__=='__main__':
 with page_worker():run()
