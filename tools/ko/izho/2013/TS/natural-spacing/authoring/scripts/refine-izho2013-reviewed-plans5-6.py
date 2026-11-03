from pathlib import Path
import json,hashlib,shutil,sys
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');sys.path.insert(0,str(B/'engine'))
from pdf_native_inline_reposition import _traces
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
folder=B/'natural/2013/TS'
for n in[5,6]:
 path=folder/f'plans/page{n:02}.json';d=json.loads(path.read_text('utf8'));history=folder/'history'/('plan-before-scope-refinement-'+sha(path)[:16]);history.mkdir(parents=True,exist_ok=True);shutil.copy2(path,history/path.name)
 if n==5:
  a=next(s for s in d['source_line_scopes']if s['source_at']==[26,0]);b=next(s for s in d['source_line_scopes']if s['source_at']==[26,6]);old=a['rect'][:];assert abs(a['baseline']-640.8699951171875)<.001 and abs(b['baseline']-643.8699951171875)<.001
  new=old[:];new[2]=b['rect'][0]-.25;assert old in d['allowed_line_rects'];d['allowed_line_rects'][d['allowed_line_rects'].index(old)]=new;a['rect']=new
  d['reviewed_source_offset_narrative_scopes']=[dict(first_source_at=[26,0],following_source_at=[26,6],first_original_baseline=a['baseline'],following_original_baseline=b['baseline'],first_scope_before=old,first_scope_after=new,following_scope=b['rect'],reason='Full source page5 and original raw runs show the trailing we-get-from-equations clause3pt below the initial-condition row. Preserve both exact original physical baselines and complete native conditions. Bound the initial horizontal scope before the source trailing clause, so neither selection claims the other row glyphs. No baseline tolerance or collision threshold changes.')]
 else:
  files=sorted(p for p in folder.glob('page06*')if p.is_file());saved=folder/'history'/('rejected-script-association-'+hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16]);saved.mkdir(parents=True,exist_ok=True)
  for p in files:
   target=saved/p.name;assert p.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(p);p.rename(target);assert sha(target)==digest
  with f.open(d['original_english_source'])as original:rows=_traces(original[n-1])
  with f.open(d['source_base'])as initial:input_rows=_traces(initial[n-1])
  groups=[]
  for label,rect in[('Original complete display equation(24)',[104,353,275,386]),('Original complete display equation(27)',[104,681,240,703])]:
   box=f.Rect(rect);glyphs=[g for g in rows if g['c'].strip()and box.contains(f.Point(g['origin']))];assert len(glyphs)>=8,(label,glyphs)
   keys={(g['c'],g['font'],g['trace_gid'],round(g['size'],4),tuple(round(v,3)for v in g['origin']))for g in glyphs}
   chosen=[g for g in input_rows if(g['c'],g['font'],g['trace_gid'],round(g['size'],4),tuple(round(v,3)for v in g['origin']))in keys];assert len(chosen)==len(glyphs)
   groups.append(dict(label=label,glyphs=chosen,reviewed=True,original_source_rect=rect,reason='Full original page6 visually read. These complete displayed equations remain stationary. Their small superscript2 belongs to its original B/a base inside this expression, not to an unrelated12pt prose-reference parenthesis on the preceding line. Constrain script/base pairing to the complete native expression and additionally require every member to retain one exact common dx. No native glyph is excluded from audit.'))
  d['reviewed_stationary_expression_groups']=groups
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('REVIEWED_SOURCE_SCOPE_OR_COMPLETE_NATIVE_EXPRESSION_PROFILE',n,flush=True)
