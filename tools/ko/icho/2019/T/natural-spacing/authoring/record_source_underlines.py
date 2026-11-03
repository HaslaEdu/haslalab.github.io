"""Bind the visually reviewed source prose underlines to Korean counterparts."""
from pathlib import Path
import hashlib,json,sys
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'engine'))
import latex_native_motion as motion
import icho2019_write_guard as g
data=json.loads((B/'source-prose-underline-candidates.json').read_text('utf8'))
assert data['source_sha256']==g.SOURCE_SHA
chosen={8:{'p8:b14:l0:s8-8':'각각의','p8:b14:l1:s0-0':'모형'}}
pages=sorted({r['page']for r in data['rows']})
for n in pages:
    q=json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'));q.setdefault('__slot_edits__',{})
    if n==8:q['__slot_edits__'].setdefault('p8:b14:l0:s8-8',{})['text']='각각의'
    inventory=motion.inspect_inline_groups(g.SOURCE,n);specs=[]
    for r in data['rows']:
        if r['page']!=n:continue
        # MuPDF exposes binary32 drawing coordinates; select one source path
        # across that serialization boundary, then pin exact native decimals.
        paths=[v for v in inventory['vector_paths']if max(abs(a-b)for a,b in zip(v['rect'],r['source_rect']))<.001]
        assert len(paths)==1,(n,r,paths)
        v=paths[0];target=chosen.get(n,{}).get(r['slot_id'],r['target'].strip().rstrip(':'))
        assert target
        specs.append(dict(id=f'p{n}-source-underline-{r["slot_id"]}',slot_id=r['slot_id'],target_text=target,source_baseline=r['source_baseline'],operator_indices=v['operator_indices'],paint_operator=v['paint_operator'],source_rect=v['rect'],source_text=r['source'],review='Source-bound underline and its Korean counterpart reviewed; exact original vector program, colour, physical width and vertical coordinates remain unchanged; only horizontal placement follows the corresponding Korean emphasis.'))
    q['__prose_vector_decorations__']=specs
    (B/f'page{n:02}.overrides.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(page=n,reviewed_underlines=len(specs))),flush=True)
