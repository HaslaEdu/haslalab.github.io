"""Bind plain, source-centered table labels to their measured original centers."""
from pathlib import Path
import argparse,json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('pages',nargs='+',type=int);args=ap.parse_args();doc=f.open(g.SOURCE);rows=[]
LABELS={'Problem','Question','Points','Score','Total','Hydrogen type','Vibrational mode','Intensity','Compound','Anode','Stages','Picture','Index','Peak','Area','Peak Area','Approximate','fraction','strong','weak','weak; strong','variable','medium'}
for n in args.pages:
    plan=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'));p=B/f'page{n:02}.overrides.json';q=json.loads(p.read_text('utf8'));blocks=doc[n-1].get_text('rawdict')['blocks'];scope=q['__layout_scope__'];cells=scope.get('fixed_table_cells',[]);page_rows=[]
    for previous in scope.get('source_centered_table_label_review',[]):q.get('__slot_edits__',{}).get(previous['slot_id'],{}).pop('source_word_centered_label',None)
    vertical=[list(d['rect'])for d in doc[n-1].get_drawings()if d['fill']==(0.,0.,0.)and 0<d['rect'].width<1 and d['rect'].height>2]
    for original in plan['slots']+q.get('__extra_slots__',[]):
        s=dict(original,**q.get('__slot_edits__',{}).get(original['id'],{}))
        if s.get('skip')or s['source'].strip()not in LABELS:continue
        b,l,a,z=s['at'];line=blocks[b]['lines'][l];whole=''.join(c['c']for span in line['spans']for c in span['chars'])
        if whole.strip()!=s['source'].strip():continue
        chars=[c for span in line['spans']for c in span['chars']if c['c'].strip()];left=min(c['bbox'][0]for c in chars);right=max(c['bbox'][2]for c in chars);baseline=chars[0]['origin'][1];center=(left+right)/2
        matching=[(i,c)for i,c in enumerate(cells)if all(c[0]-.05<=v['origin'][0]<c[2]-.05 and c[1]-.05<=v['origin'][1]<=c[3]+.05 for v in chars)]
        if len(matching)!=1:continue
        ci,cell=matching[0];native_edges=[]
        for edge in[cell[0],cell[2]]:
            nearby=[v for v in vertical if v[1]-.05<=baseline<=v[3]+.05 and abs((v[0]+v[2])/2-edge)<6]
            if not nearby:break
            native_edges.append(min(nearby,key=lambda v:abs((v[0]+v[2])/2-edge)))
        if len(native_edges)!=2:continue
        cellcenter=sum((v[0]+v[2])/2 for v in native_edges)/2
        if abs(center-cellcenter)>2:continue
        q.setdefault('__slot_edits__',{}).setdefault(s['id'],{})['source_word_centered_label']=True
        page_rows.append(dict(slot_id=s['id'],source_text=s['source'],source_line=[b,l],source_baseline=baseline,source_nonspace_word_bounds=[left,right],source_word_center_x=center,source_cell_index=ci,source_detected_cell_rect=cell,exact_original_native_vertical_border_rects=native_edges,source_native_grid_cell_center_x=cellcenter,source_word_vs_cell_center_delta_pt=center-cellcenter,review='Plain source table label occupies the complete original source line. Its source center matches the exact original black native grid border centers within the original trailing-space allowance; detected table snap coordinates are not used as actual grid coordinates. Preserve the measured original nonspace word center, point size/baseline/weight and native grid/number columns.'))
    scope['source_centered_table_label_review']=page_rows;p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');rows+=list(dict(v,page=n)for v in page_rows)
    print(json.dumps(dict(page=n,source_centered_plain_labels=len(page_rows))),flush=True)
(B/('source-centered-table-labels-'+','.join(map(str,args.pages))+'.json')).write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,rows=rows,center_detection_bound_pt=2,full_source_line_only=True,no_scientific_glyphs_or_columns_retyped=True),ensure_ascii=False,indent=2)+'\n','utf8')
