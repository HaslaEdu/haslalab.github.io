from pathlib import Path
from collections import defaultdict
import sys,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
import pymupdf as f
from cpho2007_ts_initial_native_baseline import selected_glyphs
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
source=B/'inputs/CPhO_2007_Chinese_original.pdf';data=json.loads((B/'inputs/original-all20-source-slots.json').read_text('utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rules=[];evidence=[]
with page_worker(),f.open(source)as doc:
 for n in range(5,20):
  page=doc[n-1];plan=next(p for p in data['pages']if p['source_page']==n);raw=_traces(page);erased=selected_glyphs(plan);keys={glyph_key(g)for g in erased};native=[g for g in raw if g['c'].strip()and g['trace_gid']>=0 and glyph_key(g)not in keys]
  images=[list(f.Rect(i['bbox'])+(-4,0,4,0))for i in page.get_image_info()if i['width']>8 and i['height']>8]
  # Original beside-figure prose-column boundaries, measured from source.
  caps={5:(range(3,10),296.4),7:(range(3,11),303.12),12:(range(6,12),355.68)}
  anchors=[r for r in plan['rows']if any(s['row']==r['row']and not s.get('retain_native')for s in plan['slots'])];byrow=defaultdict(list)
  for g in native:
   if not 24<=g['origin'][0]<=508:continue
   if any(f.Rect(box).contains(f.Point(g['origin']))for box in images):continue
   row=min(anchors,key=lambda r:abs(r['baseline']-g['origin'][1]));rowid=row['row'];tol=max(s['size']for s in plan['slots']if s['row']==rowid)*1.02
   if abs(row['baseline']-g['origin'][1])>tol:continue
   if n in caps and rowid in caps[n][0]and g['origin'][0]>caps[n][1]+.02:continue
   byrow[rowid].append(g)
  inv=inspect_inline_groups(source,n)
  for rowid,gs in sorted(byrow.items()):
   row=next(r for r in anchors if r['row']==rowid);y=row['baseline'];barriers=[c['origin'][0]for c in erased if abs(c['origin'][1]-y)<.1];groups=[]
   for g in sorted(gs,key=lambda g:(g['origin'][0],g['origin'][1])):
    if groups and not any(groups[-1][-1]['origin'][0]+.001<x<g['origin'][0]-.001 for x in barriers):groups[-1].append(g)
    else:groups.append([g])
   for j,group in enumerate(groups):
    box=f.Rect(min(g['origin'][0]for g in group)-.002,min(g['origin'][1]for g in group)-.002,max(g['origin'][0]for g in group)+.002,max(g['origin'][1]for g in group)+.002)
    selected=[g for g in native if box.contains(f.Point(g['origin']))];assert {glyph_key(g)for g in selected}=={glyph_key(g)for g in group},(n,rowid,j)
    ink=f.Rect(group[0]['bbox'])
    for g in group[1:]:ink|=f.Rect(g['bbox'])
    # Word draws radicals and overbars as several separate native paths.
    # Their cap/diagonal can rise above a digit's font bbox. The source row's
    # complete math band, bounded by surrounding prose rows/display equations,
    # selects all those paths, rather than only its horizontal fraction bar.
    size=max(g['size']for g in group);graphic_band=f.Rect(ink.x0-1.1*size,y-1.5*size,ink.x1+.3*size,y+.5*size)
    vector=[p['rect']for p in inv['vector_paths']if graphic_band.contains(f.Rect(p['rect']))]
    label=f'Original complete inline expression {n}-{rowid}-{j}'
    rules.append(dict(page=n,label=label,rect=list(box),baseline=y,expected_physical_glyphs=len(group),vector_rects=vector,reason='Maximal complete original native expression between actually erased original Chinese prose glyphs; preserve exact original CID/font/GID/point/paint/Y and original internal two-dimensional geometry, including any original mathematical parentheses and fraction rules. Only a single common horizontal displacement is permitted.'))
    evidence.append(dict(page=n,row=rowid,label=label,text=''.join(g['c']for g in sorted(group,key=lambda g:(g['origin'][0],g['origin'][1]))),rect=list(box),baseline=y,physical_glyphs=group,vector_rects=vector))
path=B/'authoring/complete-inline-expressions-candidate.json';assert not path.exists();path.write_text(json.dumps(dict(source_sha256=sha(source),atoms=rules),ensure_ascii=False,indent=2)+'\n','utf8')
(B/'authoring/complete-inline-expressions-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n','utf8')
(B/'authoring/complete-inline-expressions-review.txt').write_text('\n'.join(f"{e['page']}-{e['row']} {e['text']!r} | {len(e['physical_glyphs'])} glyphs, {len(e['vector_rects'])} bars, {e['rect']}"for e in evidence)+'\n','utf8')
print('PRIVATE_COMPLETE_ORIGINAL_INLINE_CANDIDATES',len(rules),'source',sha(source),'plan',sha(path),flush=True)
