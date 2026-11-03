"""Every original standalone displayed-equation number stays at source x/y."""
from pathlib import Path
import json,hashlib,re,pymupdf as f
from izho_initial_fixed_style import runs_of,characters
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
RANGES={1:range(1,8),2:range(1,6),3:[],4:range(1,11),5:range(11,25),6:range(25,38),7:range(38,43),8:range(1,7),9:range(7,14),10:range(14,16)}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_counters(plan):
 assert sha(plan['original_english_source'])==plan['original_english_source_sha256']=='ecc4a34a50fade6a08fd5f629480bebfa20ec418cdc19fa87915f6c0465ee008'
 with f.open(plan['original_english_source'])as doc:
  page=doc[plan['source_page']-1];runs=runs_of(page);physical={glyph_key(g):g for g in _traces(page)if g['c'].strip()};rows=[]
  for at,run in runs.items():
   m=re.fullmatch(r'\((\d+)\)',run['text'].strip())
   if not m:continue
   gs=[physical[glyph_key(g)]for g in characters(run)if g['c'].strip()];rows.append(dict(source_at=list(at),number=int(m[1]),glyphs=gs,reason='Original standalone displayed-equation label at its exact source font/GID/point/x/y, including the narrower left-column labels on source pages9/10. Not an inline prose reference.'))
  assert[n['number']for n in rows]==list(RANGES[plan['source_page']]),(plan['source_page'],[n['number']for n in rows])
  assert all(g['size']==12 and g['font']=='TimesNewRomanPSMT'for row in rows for g in row['glyphs'])
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
