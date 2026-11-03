from pathlib import Path
import json,sys
import pymupdf as f
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'engine'))
import latex_native_motion as m
import icho2019_write_guard as g
regions={57:[[260,280,358,304]],52:[[175,260,400,278]],58:[[100,150,185,178],[345,138,440,177],[180,322,235,340],[100,368,210,387],[420,330,520,352],[95,458,530,482]],60:[[250,410,350,430]]}
out=B/'source-vector-labels';out.mkdir(exist_ok=True);doc=f.open(g.SOURCE)
for n,rects in regions.items():
    inv=m.inspect_inline_groups(g.SOURCE,n);forms=[];rows=[]
    for form in inv['forms']:
        hits=[v for v in form['own_vector_paths']if any(f.Rect(v['rect']).intersects(f.Rect(r))for r in rects)]
        if hits:forms.append(form);rows+=[dict(form_path=form['path'],raw_sha256=form['original_raw_sha256'],**v)for v in hits]
    top=[v for v in inv['vector_paths']if any(f.Rect(v['rect']).intersects(f.Rect(r))for r in rects)]
    (out/f'page{n:02}-language-profile.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,forms=forms,paths_in_regions=rows,top_level_paths=top),ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(page=n,forms=[dict(path=v['path'],sha=v['original_raw_sha256'],bbox=v['native_page_bbox'],glyphs=len(v['glyphs']),paths=len(v['own_vector_paths']))for v in forms],paths=[dict(form=v['form_path'],ops=[v['operator_indices'][0],v['operator_indices'][-1]],rect=v['rect'],paint=v['paint_operator'])for v in rows],top=top),ensure_ascii=False),flush=True)
    for i,r in enumerate(rects):doc[n-1].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(r),alpha=False).save(out/f'page{n:02}-language-region{i}.png')
