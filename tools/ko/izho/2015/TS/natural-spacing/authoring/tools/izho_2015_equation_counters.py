"""Every source2015 display label, including the original leading-period(16), stays native at source x/y."""
from pathlib import Path
import json,hashlib,re,pymupdf as f
from izho_initial_fixed_style import runs_of,characters
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
SOURCE='c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde'
RANGES={1:[],2:range(1,5),3:[],4:range(1,16),5:[16,17,1,2],6:range(3,11),7:range(11,19),8:range(19,25),9:range(25,29),10:[],11:[]}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_counters(plan):
 assert sha(plan['original_english_source'])==plan['original_english_source_sha256']==SOURCE
 with f.open(plan['original_english_source'])as doc:
  page=doc[plan['source_page']-1];runs=runs_of(page);physical={glyph_key(g):g for g in _traces(page)if g['c'].strip()};rows=[]
  for at,run in runs.items():
   m=re.fullmatch(r'\s*\.?\s*(\((\d+)\))\s*',run['text'])
   if not m or run['font']!='Times New Roman'or run['size']!=12:continue
   chars=characters(run);assert ''.join(c['c']for c in chars)==run['text'];gs=[physical[glyph_key(g)]for g in chars[m.start(1):m.end(1)]if g['c'].strip()]
   rows.append(dict(source_at=list(at),number=int(m[2]),glyphs=gs,reason='Full original2015 source visually read: exact displayed-equation label, retaining its original Times New Roman12pt encoded glyphs and physical source x/y. Source leading prose/formula period before(16) is separate and remains unchanged. Inline references and grades are not display labels.'))
  assert[n['number']for n in rows]==list(RANGES[plan['source_page']]),(plan['source_page'],[n['number']for n in rows])
  assert all(g['size']==12 and g['font']=='Times New Roman'for row in rows for g in row['glyphs'])
  return rows
def apply_reviewed_counters(plan):plan['reviewed_stationary_native_equation_counters']=source_counters(plan)
def audit(plan_path,*,final_override=None,report_override=None):
 plan_path=Path(plan_path);plan=json.loads(plan_path.read_text('utf8'));proof=Path(final_override)if final_override else plan_path.parents[1]/(plan_path.stem+'.pdf');expected=source_counters(plan)
 with f.open(proof)as doc:actual=_traces(doc[0])
 rows=[]
 for counter in expected:
  errors=[]
  for g in counter['glyphs']:
   hits=[a for a in actual if a['c']==g['c']and a['font']==g['font']and a['trace_gid']==g['trace_gid']and abs(a['size']-g['size'])<.001 and abs(a['origin'][1]-g['origin'][1])<.001 and a['render_mode']==g['render_mode']]
   closest=min(hits,key=lambda a:abs(a['origin'][0]-g['origin'][0]))if hits else None
   if closest is None or abs(closest['origin'][0]-g['origin'][0])>=.001:errors.append(dict(source=g,actual=closest,source_x_difference=None if closest is None else closest['origin'][0]-g['origin'][0]))
  rows.append(dict(number=counter['number'],original_source_at=counter['source_at'],native_glyphs=len(counter['glyphs']),font_gid_point_x_y_and_paint_errors=errors,passed=not errors))
 q=dict(source_sha256=plan['original_english_source_sha256'],proof_sha256=sha(proof),source_page=plan['source_page'],method='Independent original English PDF inventory of every standalone displayed-equation number; actual final native glyph font/GID/point/paint AND original x/y must remain exact within0.001pt. No motion-journal exception for equation numbers.',equation_counters_checked=len(rows),native_counter_glyphs_checked=sum(r['native_glyphs']for r in rows),rows=rows,passed=all(r['passed']for r in rows));report=Path(report_override)if report_override else proof.with_suffix('.equation-counters.json');report.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return q
