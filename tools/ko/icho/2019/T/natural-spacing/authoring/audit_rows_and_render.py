"""Audit actual embedded Korean row ink and render one isolated 2019 proof."""
from pathlib import Path
from collections import defaultdict
import argparse,hashlib,json,math
import pymupdf as f,numpy as np
import natural_plan_compose_icho2019 as c
import icho2019_write_guard as guard
BASE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(n,render=True):
    path=guard.PROOFS/f'page{n:02}.pdf';guard.assert_output(path,n)
    q=json.loads(path.with_suffix('.layout.json').read_text('utf8'))
    assert q['page']==n and q['source_sha256']==guard.SOURCE_SHA
    assert sha(path)==q['output_sha256']
    doc=f.open(path);fontbuf={};metrics={}
    for item in doc[0].get_fonts():
        if item[4].startswith('KO_Natural_'):
            fontbuf[item[4].removeprefix('KO_Natural_').replace('_','-')]=doc.extract_font(item[0])[3]
    row_placements=list(q['placements']);font_paths=dict(q['new_font_paths'])
    for v in q.get('raster_labels',[])+q.get('outlined_vector_labels',[])+q.get('selected_graphic_labels',[]):
        if v.get('rotate',0):continue
        role='Raster-'+v.get('font_role','sans');font_paths[role]=str(c.FONTS[v.get('font_role','sans')])
        row_placements.append(dict(v,baseline=v['point'][1],font_role=role,angle=0))
    rows=[]
    for v in sorted(row_placements,key=lambda p:p['baseline']):
        if not rows or abs(rows[-1][0]['baseline']-v['baseline'])>.001:rows.append([])
        rows[-1].append(v)
    pairs=[];unions={}
    for i,upper in enumerate(rows):
        for j,lower in enumerate(rows[i+1:],i+1):
            gap=lower[0]['baseline']-upper[0]['baseline'];size=max(v['size']for v in upper+lower)
            if j!=i+1 and gap>=size*1.1:continue
            clip=f.Rect(0,math.floor(upper[0]['baseline']-size*1.5),doc[0].rect.width,math.ceil(lower[0]['baseline']+size*.5))
            pairs.append((i,j,gap,clip))
            for ri in[i,j]:unions[ri]=unions[ri]|clip if ri in unions else f.Rect(clip)
    cache={}
    for index,clip in sorted(unions.items()):
        row=rows[index];d=f.open();pg=d.new_page(width=doc[0].rect.width,height=doc[0].rect.height)
        for role in{v['font_role']for v in row}:
            pg.insert_font(fontname='KO_'+role.replace('-','_'),fontbuffer=fontbuf[role])
            full=font_paths[role]
            if full not in metrics:metrics[full]=c.font_metric(Path(full))
        for v in row:
            x,y=v['point'];metric=metrics[font_paths[v['font_role']]]
            for ch in v['text']:
                c.insert_prose_text(pg,f.Point(x,y),ch,'KO_'+v['font_role'].replace('-','_'),v['size'],(0,0,0),v['angle'])
                x+=c.word_space(metric,v['size'])if ch==' 'else metric.text_length(ch,fontsize=v['size'])
        pix=pg.get_pixmap(matrix=f.Matrix(2,2),colorspace=f.csGRAY,alpha=False,clip=clip)
        cache[index]=dict(pixels=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width).copy(),x=pix.x,y=pix.y,width=pix.width,height=pix.height)
        d.close()
    results=[];failures=[]
    for i,j,gap,clip in pairs:
        want=((clip&doc[0].rect)*f.Matrix(2,2)).irect;masks=[]
        for ri in[i,j]:
            im=cache[ri];x0,y0=want.x0-im['x'],want.y0-im['y'];x1,y1=want.x1-im['x'],want.y1-im['y']
            assert 0<=x0<=x1<=im['width']and 0<=y0<=y1<=im['height']
            masks.append(im['pixels'][y0:y1,x0:x1]<220)
        hits=masks[0]&masks[1];count=int(hits.sum())
        info=dict(upper_source_baseline=rows[i][0]['baseline'],lower_source_baseline=rows[j][0]['baseline'],gap_pt=gap,contact_pixels_2x=count);results.append(info)
        if count:
            ys,xs=np.nonzero(hits);failures.append(dict(info,contact_box_pt=[float((want.x0+xs.min())/2),float((want.y0+ys.min())/2),float((want.x0+xs.max()+1)/2),float((want.y0+ys.max()+1)/2)]))
    report=dict(page=n,proof_sha256=sha(path),passed=not failures,tested_row_pairs=len(results),pairs=results,failures=failures,measurement_code_sha256=sha(__file__),method='Exact embedded subset buffers paint glyphs at full-precision positions and angles, original point sizes and baselines; every adjacent row pair plus nonadjacent pairs below1.1em tested at2x threshold220. Cache each row over the union of exact pair clips on the unchanged global pixel grid.')
    (guard.PROOFS/f'page{n:02}.inter-row-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    q['actual_new_korean_inter_row_ink_audit']=report
    path.with_suffix('.layout.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
    if render:
        png=guard.PROOFS/f'page{n:02}.png';doc[0].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False).save(png)
        metadata=dict(page=n,proof_sha256=sha(path),png_sha256=sha(png),layout_sha256=sha(path.with_suffix('.layout.json')),scale=1.5)
        png.with_suffix('.render.json').write_text(json.dumps(metadata,indent=2)+'\n','utf8')
    doc.close();assert report['passed'],report['failures'];return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pages',nargs='+',type=int);a=p.parse_args()
    for n in a.pages:
        r=run(n);print(json.dumps(dict(page=n,passed=r['passed'],pairs=r['tested_row_pairs'])),flush=True)
