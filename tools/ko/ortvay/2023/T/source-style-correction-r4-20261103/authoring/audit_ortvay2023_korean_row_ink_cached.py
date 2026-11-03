"""One2023 page per gate; cache each row raster over its exact pair-clip union."""
from pathlib import Path
import argparse,hashlib,json,math,time
import pymupdf as f,numpy as np
import natural_plan_compose_ortvay2023_final as c
import ortvay2023_write_guard as g
p=argparse.ArgumentParser();p.add_argument('page',type=int,choices=range(1,14));p.add_argument('--allow-partial',action='store_true');p.add_argument('--regression',action='store_true');a=p.parse_args()
B=g.B;F=g.PROOF_ROOT;sha=g.sha;n=a.page
g.assert_protected_editions()
nominal=F/f'page{n:02}.pdf';q=json.loads(nominal.with_suffix('.layout.json').read_text('utf8'))
g.validate_paths(n,Path(q['plan_path']),nominal,B/'composer/natural_plan_compose_ortvay2023_final.py',q.get('overrides_path'))
assert sha(nominal)==q['output_sha256']
doc=f.open(nominal);fontbuf={};metrics={}
for item in doc[0].get_fonts():
    if item[4].startswith('KO_Natural_'):
        fontbuf[item[4].removeprefix('KO_Natural_').replace('_','-')]=doc.extract_font(item[0])[3]
rows=[]
for v in sorted(q['placements'],key=lambda v:v['baseline']):
    if not rows or abs(rows[-1][0]['baseline']-v['baseline'])>.001:rows.append([])
    rows[-1].append(v)
pairs=[];unions={}
for i,(upper,lower) in enumerate(zip(rows,rows[1:])):
    gap=lower[0]['baseline']-upper[0]['baseline'];size=max(v['size'] for v in upper+lower)
    if gap>=size*1.1:continue
    clip=f.Rect(0,math.floor(upper[0]['baseline']-size*1.5),doc[0].rect.width,math.ceil(lower[0]['baseline']+size*.5))
    pairs.append((i,i+1,gap,clip))
    for ri in [i,i+1]:unions[ri]=unions[ri]|clip if ri in unions else f.Rect(clip)

def render_row(index,clip):
    # Same glyph/space/morph operations as the original2023 checker. Only the
    # render clip and reuse count change. Union clips contain every old clip.
    row=rows[index];d=f.open();pg=d.new_page(width=doc[0].rect.width,height=doc[0].rect.height)
    for role in {v['font_role'] for v in row}:
        pg.insert_font(fontname='KO_'+role.replace('-','_'),fontbuffer=fontbuf[role])
        fontpath=q['new_font_paths'][role]
        if fontpath not in metrics:metrics[fontpath]=c.font_metric(Path(fontpath))
    for v in row:
        x,y=v['point'];metric=metrics[q['new_font_paths'][v['font_role']]]
        for ch in v['text']:
            c.insert_prose_text(pg,f.Point(x,y),ch,'KO_'+v['font_role'].replace('-','_'),v['size'],(0,0,0),v['angle'])
            x+=c.word_space(metric,v['size']) if ch==' ' else metric.text_length(ch,fontsize=v['size'])
    pix=pg.get_pixmap(matrix=f.Matrix(2,2),colorspace=f.csGRAY,alpha=False,clip=clip)
    result={'pixels':np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width).copy(),'x':pix.x,'y':pix.y,'width':pix.width,'height':pix.height}
    d.close();return result

def crop(image,rect):
    x0=rect.x0-image['x'];y0=rect.y0-image['y'];x1=rect.x1-image['x'];y1=rect.y1-image['y']
    assert 0<=x0<=x1<=image['width'] and 0<=y0<=y1<=image['height']
    return image['pixels'][y0:y1,x0:x1]

cache_started=time.perf_counter();cache={i:render_row(i,clip) for i,clip in sorted(unions.items())};cache_seconds=time.perf_counter()-cache_started
results=[];failures=[];regression_comparisons=0;reference_seconds=0.
for upper,lower,gap,clip in pairs:
    # Clip edges are whole PDF points, so the2x global raster grid is unchanged.
    want=((clip & doc[0].rect)*f.Matrix(2,2)).irect
    up=crop(cache[upper],want);down=crop(cache[lower],want)
    if a.regression:
        started=time.perf_counter()
        for index,pixels in [(upper,up),(lower,down)]:
            reference=render_row(index,clip)
            assert (reference['x'],reference['y'],reference['x']+reference['width'],reference['y']+reference['height'])==tuple(want)
            assert np.array_equal(reference['pixels'],pixels),('Cached grayscale raster differs from old pair-specific render',n,index,clip)
            regression_comparisons+=1
        reference_seconds+=time.perf_counter()-started
    hits=(up<220)&(down<220);count=int(hits.sum())
    info={'upper_source_baseline':rows[upper][0]['baseline'],'lower_source_baseline':rows[lower][0]['baseline'],'gap_pt':gap,'contact_pixels_2x':count}
    results.append(info)
    if count:
        ys,xs=np.nonzero(hits)
        failures.append(dict(info,contact_box_pt=[float((want.x0+xs.min())/2),float((want.y0+ys.min())/2),float((want.x0+xs.max()+1)/2),float((want.y0+ys.max()+1)/2)]))
doc.close()
page={'page':n,'proof_sha256':sha(nominal),'measurement_code_sha256':sha(__file__),'tested_close_row_pairs':len(results),'pairs':results,'failures':failures,'passed':not failures,'raster_cache':{'row_renders':len(cache),'old_pair_specific_row_renders':len(pairs)*2,'union_contains_each_original_pair_clip':True,'same_global2x_raster_grid':True,'cache_render_seconds':cache_seconds}}
if a.regression:
    regression={'status':'PASS_EXACT_CACHED_ROW_GRAYSCALE_REGRESSION','page':n,'proof_sha256':sha(nominal),'reference_checker_sha256':sha(B/'composer/audit_ortvay2023_korean_row_ink.py'),'cached_checker_sha256':sha(__file__),'grayscale_crop_byte_comparisons':regression_comparisons,'changed_grayscale_pixels':0,'threshold':220,'scale':2,'same_row_baseline_grouping_tolerance_pt':.001,'same_close_row_selection_em':1.1,'cached_row_renders':len(cache),'old_pair_specific_row_renders':len(pairs)*2,'cached_render_seconds':cache_seconds,'old_pair_render_seconds':reference_seconds,'all_contact_counts_identical':True}
    out=g.PROFILE_ROOT/'row-cache-regression';out.mkdir(parents=True,exist_ok=True);(out/f'page{n:02}.json').write_text(json.dumps(regression,indent=2),'utf8')
aggregate=F/'korean-inter-row-ink-audit.json'
previous={v['page']:v for v in json.loads(aggregate.read_text('utf8'))['pages']} if aggregate.exists() else {}
previous[n]=page;pages=sorted(previous.values(),key=lambda v:v['page']);stale=[]
for v in pages:
    current=json.loads((F/f"page{v['page']:02}.layout.json").read_text('utf8'))
    if current['output_sha256']!=v['proof_sha256']:stale.append(v['page'])
report={'schema':'actual-subset-font-korean-inter-row-ink-2x-v1','passed':len(pages)==13 and not stale and all(v['passed'] for v in pages),'pages':pages,'stale_pages':stale,'method':'Exact same embedded subset glyph paints/full-precision metrics/source baselines,2x grayscale threshold220,.001pt same-row grouping and1.1em close-row selection. Cache each row over the union of all old pair clips; crop exact original common clips on the unchanged global pixel grid. Pixel-byte regression compares these crops to independent old pair-specific renders; unchanged proof SHA results are reused between single-page gated calls.'}
g.assert_protected_editions();aggregate.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
assert page['passed'],{'page':n,'failures':failures}
if not a.allow_partial:assert report['passed'],{'stale':stale,'failed':[v['page'] for v in pages if not v['passed']]}
print(json.dumps({'page':n,'passed':page['passed'],'aggregate_passed':report['passed'],'tested_close_row_pairs':len(results),'cached_row_renders':len(cache),'old_pair_specific_row_renders':len(pairs)*2,'cache_render_seconds':cache_seconds,'regression_pixel_comparisons':regression_comparisons,'reference_render_seconds':reference_seconds}),flush=True)
