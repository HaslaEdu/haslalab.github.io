from pathlib import Path
from collections import defaultdict
import json,sys,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
from cpho2003_initial_native_baseline import selected_glyphs
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
import pymupdf as f
source=B/'inputs/CPhO_2003_Chinese_original.pdf';data=json.loads((B/'inputs/original-all10-source-slots.json').read_text('utf8'));rules=[];evidence=[]
with page_worker(),f.open(source)as doc:
 for n in [1,2,3]:
  page=doc[n-1];plan=data['pages'][n-1];raw=_traces(page);erased=selected_glyphs(plan);keys={glyph_key(g)for g in erased};native=[g for g in raw if g['c'].strip()and g['trace_gid']>=0 and glyph_key(g)not in keys]
  images=[list(f.Rect(i['bbox'])+(-4,0,4,0))for i in page.get_image_info()if i['width']>8 and i['height']>8]
  anchors=[r for r in plan['rows']if any(s['row']==r['row']and not s.get('retain_native')for s in plan['slots'])];byrow=defaultdict(list)
  for g in native:
   if not 24<=g['origin'][0]<=524.3 or any(f.Rect(b).contains(f.Point(g['origin']))for b in images):continue
   row=min(anchors,key=lambda r:abs(r['baseline']-g['origin'][1]));tol=max(s['size']for s in plan['slots']if s['row']==row['row'])*1.02
   if abs(row['baseline']-g['origin'][1])<=tol:byrow[row['row']].append(g)
  inv=inspect_inline_groups(source,n)
  for rowid,gs in sorted(byrow.items()):
   row=next(r for r in anchors if r['row']==rowid);y=row['baseline'];barriers=[c['origin'][0]for c in erased if abs(c['origin'][1]-y)<.1];groups=[]
   for g in sorted(gs,key=lambda g:(g['origin'][0],g['origin'][1])):
    if groups and not any(groups[-1][-1]['origin'][0]+.001<x<g['origin'][0]-.001 for x in barriers):groups[-1].append(g)
    else:groups.append([g])
   for j,group in enumerate(groups):
    box=f.Rect(min(g['origin'][0]for g in group)-.002,min(g['origin'][1]for g in group)-.002,max(g['origin'][0]for g in group)+.002,max(g['origin'][1]for g in group)+.002)
    selected=[g for g in native if box.contains(f.Point(g['origin']))];assert {glyph_key(g)for g in selected}=={glyph_key(g)for g in group}
    ink=f.Rect(group[0]['bbox'])
    for g in group[1:]:ink|=f.Rect(g['bbox'])
    size=max(g['size']for g in group);band=f.Rect(ink.x0-1.1*size,y-1.5*size,ink.x1+.3*size,y+.5*size)
    vector=[p['rect']for p in inv['vector_paths']if band.contains(f.Rect(p['rect']))]
    label=f'Original complete inline expression {n}-{rowid}-{j}'
    rules.append(dict(page=n,label=label,rect=list(box),baseline=y,expected_physical_glyphs=len(group),vector_rects=vector,reason='Complete original native expression between actually erased Chinese prose; keep original font/GID/point/paint/Y and all original internal script geometry. Only common horizontal displacement is allowed.'))
    evidence.append(dict(page=n,row=rowid,label=label,text=''.join(g['c']for g in sorted(group,key=lambda g:(g['origin'][0],g['origin'][1]))),rect=list(box),baseline=y,physical_glyphs=group,vector_rects=vector))
for name,q in [('complete-inline-expressions-candidate.json',dict(source_sha256=data['source_sha256'],atoms=rules)),('complete-inline-expressions-evidence.json',evidence)]:
 p=B/'authoring/native'/name;assert not p.exists();p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
(B/'authoring/native/complete-inline-expressions-review.txt').write_text('\n'.join(f"{e['page']}-{e['row']} {e['text']!r} | {len(e['physical_glyphs'])} glyphs, {len(e['vector_rects'])} vectors, {e['rect']}"for e in evidence)+'\n','utf8')
print('CPHO2003_NATIVE_ATOM_CANDIDATES',len(rules),flush=True)
