"""Actual original whitespace GIDs, not assumptions from Unicode/strip()."""
from pathlib import Path
from io import BytesIO
import sys,json,re,hashlib,collections
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import pymupdf as f
B=Path(__file__).resolve().parents[1];sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools');from pdf_memory_gate import page_worker
S=B/'source/CPhO_2008_original_combined_ZH.pdf';counts=collections.Counter();rows=[];seen=set()
with page_worker(),f.open(S)as doc:
 for n in range(1,22):
  inv=json.loads((B/f'inspection/page{n:02}-original-native-programs.json').read_text('utf8'))
  for g in inv['actual_original_glyphs']:
   if g['c'].isspace():counts[(g['c'],g['font'],g['trace_gid'])]+=1
 for (c,face,gid),count in sorted(counts.items()):
  hits={r[0]:r for page in doc for r in page.get_fonts(full=True)if re.sub(r'^[A-Z]{6}\+','',r[3])==face};assert hits,(face,'No exact original font resource')
  programmes=[]
  for xref,record in hits.items():
   raw=doc.extract_font(xref)[3];font=TTFont(BytesIO(raw),recalcTimestamp=False);glyphs=font.getGlyphSet();name=font.getGlyphOrder()[gid];pen=BoundsPen(glyphs);glyphs[name].draw(pen)
   programmes.append(dict(actual_original_font_xref=xref,original_font_name=record[3],original_font_program_sha256=hashlib.sha256(raw).hexdigest(),original_GID=gid,original_glyph_name=name,original_actual_outline_bounds=pen.bounds,actual_original_outline_is_empty=pen.bounds is None));assert pen.bounds is None,(face,gid,pen.bounds);font.close()
  rows.append(dict(literal_original_character=c,original_trace_font=face,original_GID=gid,occurrences=count,all_actual_original_embedded_programmes_checked=programmes,all_actual_original_outlines_empty=True))
result=dict(original_source_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),source_pages=21,original_whitespace_GID_profiles=len(rows),all_original_actual_whitespace_outlines_empty=True,Unicode_and_GIDs_and_font_programs_not_modified=True,profiles=rows,passed=True)
(B/'inspection/all21-original-whitespace-GID-outline-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print('C08_ALL_ORIGINAL_WHITESPACE_OUTLINES_ACTUALLY_EMPTY',[(r['original_trace_font'],r['original_GID'],r['occurrences'])for r in rows],flush=True)
