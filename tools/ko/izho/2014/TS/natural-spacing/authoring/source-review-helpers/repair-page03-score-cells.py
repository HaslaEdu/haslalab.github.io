from pathlib import Path
import json,hashlib,shutil,sys,re,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2014-complete-solutions');F=B/'natural/2014/TS';sys.path.insert(0,str(B/'engine'))
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
progress=json.loads((B/'natural/2014-private-page-progress.json').read_text('utf8'));assert any(r['page']==3 for r in progress),'Initial root page3 process must have finished'
plan=F/'plans/page03.json';d=json.loads(plan.read_text('utf8'));assert d['original_english_source_sha256']=='1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c'
prior=F/'page03.audit.json';audit=json.loads(prior.read_text('utf8'));assert not audit['passed'];assert len(audit['grading_columns_stationary']['grading_glyphs_moved_from_source_cells'])==6
history=F/'history'/('page03-plan-before-score-cell-repair-'+sha(plan)[:16]);history.mkdir(parents=True,exist_ok=True);shutil.copy2(plan,history/plan.name)
with f.open(d['original_english_source'])as source:original=[g for g in _traces(source[2])if g['c'].strip()and re.fullmatch(r'[0-9.,]',g['c'])and 480<=g['origin'][0]<=520 and 170<=g['origin'][1]<=641]
with f.open(d['source_base'])as source:initial=_traces(source[2])
assert len(original)==33,len(original);keys={glyph_key(g)for g in original};scores=[g for g in initial if glyph_key(g)in keys];assert len(scores)==33
locked=list(d.get('stationary_table_math',[]));locked.append(dict(rect=[480,170,520,641],native_glyphs=scores,reviewed=True,reason='Full original2014 page3 and rejected proof visually read. All33 original score/total glyphs in the two right grading columns must retain exact source fonts/GIDs/points/paint/x/y. Two1.0 scores in the tall merged second-table cell had been incorrectly packed into the content column. Freeze every original score in these columns; no equation/prose reference is frozen or excluded from audits. Independent grading_columns_stationary must report33 checked and zero moved.'))
d['stationary_table_math']=locked
repairs=[]
for scope in d['source_line_scopes']:
 if scope['source_at'][0]!=12:continue
 before=scope['rect'][:];after=before[:];after[2]=min(after[2],470.28050842285154)
 if before!=after:
  assert before in d['allowed_line_rects'];d['allowed_line_rects'][d['allowed_line_rects'].index(before)]=after
  scope['rect']=after;repairs.append(dict(source_at=scope['source_at'],before=before,after=after,reason='The source tall merged grading-content cell ends at the same original vertical grid x470.530508pt as the neighboring content rows. Its content scope ends0.25pt before that exact grid; the original score column is separate. Original y/baselines/points and every grid primitive stay unchanged.'))
assert len(repairs)>=6,len(repairs);d['reviewed_original_merged_grading_content_cell_bounds']=repairs
files=sorted(p for p in F.glob('page03*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];archive=F/'history'/f'page03-rejected-before-score-cell-repair-{version}';archive.mkdir(parents=True,exist_ok=True)
for item in files:
 target=archive/item.name;assert item.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(item);item.rename(target);assert sha(target)==digest
plan.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
print('PRIVATE2014_PAGE3_SCORE_CELLS_REPAIRED',len(scores),len(repairs),flush=True)
