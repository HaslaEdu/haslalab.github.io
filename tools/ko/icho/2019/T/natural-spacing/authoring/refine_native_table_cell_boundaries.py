"""Split detected merged cells only at independently repeated original grid rules."""
from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;doc=f.open(g.SOURCE);journal=[]
for n in range(1,61):
    p=B/f'page{n:02}.overrides.json';q=json.loads(p.read_text('utf8'));sc=q['__layout_scope__'];cells=sc.get('fixed_table_cells',[])
    if not cells:continue
    edges=[list(d['rect'])for d in doc[n-1].get_drawings()if d['fill']==(0.,0.,0.)and 0<d['rect'].width<1 and d['rect'].height>2];new=[];review=[]
    for r in cells:
        inside=[e for e in edges if r[0]+1<(e[0]+e[2])/2<r[2]-1 and e[1]<=r[1]+.75 and e[3]>=r[3]-.75]
        repeated=[]
        for e in inside:
            x=(e[0]+e[2])/2;siblings=[v for v in edges if abs((v[0]+v[2])/2-x)<.05 and any(t[0]-.5<=x<=t[2]+.5 and t[1]-.5<=v[1]<=t[3]+.5 and t[1]-.5<=v[3]<=t[3]+.5 for t in sc.get('fixed_table_rects',[]))]
            if len({(round(v[1],2),round(v[3],2))for v in siblings})>=2:repeated.append(e)
        xx=sorted({r[0],r[2]}|{(e[0]+e[2])/2 for e in repeated});parts=[[a,r[1],b,r[3]]for a,b in zip(xx,xx[1:])];new+=parts
        if len(parts)>1:review.append(dict(detected_merged_cell=r,source_repeated_black_grid_rects=repeated,refined_cells=parts))
    if review:
        sc['fixed_table_cells']=new;sc['source_native_grid_cell_refinement_review']=review;p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');journal.append(dict(page=n,rows=review));print(n,len(review),flush=True)
(B/'source-native-grid-cell-refinement-review.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,pages=journal,source_only_classification=True,review='Source table detector merged cells across a real original black native vertical grid rule. Split only where the same exact black vertical grid x repeats in at least two original table rows and spans the full source cell interior. All original vector construction, coordinates, colour, thickness and native glyphs remain unchanged; no output tolerance is widened.'),ensure_ascii=False,indent=2)+'\n','utf8')
