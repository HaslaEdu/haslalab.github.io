from pathlib import Path
import math,re,json,hashlib
import pymupdf as f,numpy as np
import natural_plan_compose_icho2024_style as c
ROOT=Path('D:/CodexBuilds/Hasla-poi-natural-20261102/style-corrections/icho2024-20261103')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def interrow_ink(e,q,document):
    """Actual proof subsets, unchanged word paints,2x grayscale threshold220."""
    import pymupdf as f,numpy as np
    pg=document[0];fontbuf={v[4]:document.extract_font(v[0])[3] for v in pg.get_fonts() if v[4].startswith('KO_Natural_')}
    metrics=e._correction_qa_metrics;rows=[]
    items=[dict(p,_kind='body') for p in q['placements'] if p['text']]
    orthogonal=[]
    for p in q.get('raster_labels',[]):
        if not p['text']:continue
        if p.get('rotate',0):orthogonal.append(dict(text=p['text'],rotate=p['rotate']));continue
        items.append(dict(p,_kind='label',baseline=p['point'][1],font_role=p.get('font_role','sans')))
    for p in sorted(items,key=lambda v:v['baseline']):
        if not rows or abs(rows[-1][0]['baseline']-p['baseline'])>.001:rows.append([])
        rows[-1].append(p)
    pairs=[];unions={}
    for i,upper in enumerate(rows):
        for j in range(i+1,len(rows)):
            lower=rows[j];gap=lower[0]['baseline']-upper[0]['baseline'];size=max(v['size'] for v in upper+lower)
            if gap>=size*2.0:continue
            clip=f.Rect(0,math.floor(upper[0]['baseline']-size*1.5),pg.rect.width,math.ceil(lower[0]['baseline']+size*.5))
            pairs.append((i,j,gap,clip))
            for index in [i,j]:unions[index]=unions[index]|clip if index in unions else f.Rect(clip)
    def paint(page,point,text,name,size,angle):
        if hasattr(e,'insert_prose_text'):e.insert_prose_text(page,point,text,name,size,(0,0,0),angle)
        else:
            morph=(point,f.Matrix(1,0,math.tan(math.radians(angle)),1,0,0)) if angle else None
            page.insert_text(point,text,fontname=name,fontsize=size,color=(0,0,0),morph=morph)
    def raster(index,clip):
        d=f.open();page=d.new_page(width=pg.rect.width,height=pg.rect.height)
        for p in rows[index]:
            role=p['font_role'];metric=metrics[role]
            name=('KO_Natural_Raster_' if p['_kind']=='label' else 'KO_Natural_')+role.replace('-','_')
            page.insert_font(fontname=name,fontbuffer=fontbuf[name])
            if p['_kind']=='label':
                x,y=p['point']
                if p.get('align')=='right':x-=metric.text_length(p['text'],fontsize=p['size'])
                paint(page,f.Point(x,y),p['text'],name,p['size'],p.get('angle',0));continue
            x,y=p.get('draw_point',p['point']);parts=re.split('( +)',p.get('draw_text',p['text']))
            for ii,part in enumerate(parts):
                if not part:continue
                if part.isspace():x+=e.word_space(metric,p['size'])*len(part);continue
                emitted=part+(' ' if ii+1<len(parts) and parts[ii+1].isspace() else '')
                paint(page,f.Point(x,y),emitted,name,p['size'],p['angle']);x+=metric.text_length(part,fontsize=p['size'])
        pix=page.get_pixmap(matrix=f.Matrix(2,2),colorspace=f.csGRAY,alpha=False,clip=clip)
        result=dict(pixels=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width).copy(),x=pix.x,y=pix.y,width=pix.width,height=pix.height)
        d.close();return result
    def crop(image,rect):
        a=rect.x0-image['x'];b=rect.y0-image['y'];c=rect.x1-image['x'];d=rect.y1-image['y']
        assert 0<=a<=c<=image['width'] and 0<=b<=d<=image['height']
        return image['pixels'][b:d,a:c]
    cache={i:raster(i,clip) for i,clip in unions.items()};results=[];failures=[];regression=0
    for upper,lower,gap,clip in pairs:
        rect=((clip&pg.rect)*f.Matrix(2,2)).irect;up=crop(cache[upper],rect);down=crop(cache[lower],rect)
        if q['page']==1:
            for index,pixels in [(upper,up),(lower,down)]:
                reference=raster(index,clip)
                assert (reference['x'],reference['y'],reference['width'],reference['height'])==(rect.x0,rect.y0,rect.width,rect.height)
                assert np.array_equal(reference['pixels'],pixels),'Cached row raster changed grayscale bytes'
                regression+=1
        count=int(((up<220)&(down<220)).sum())
        row=dict(upper_source_baseline=rows[upper][0]['baseline'],lower_source_baseline=rows[lower][0]['baseline'],gap_pt=gap,contact_pixels_2x=count)
        results.append(row)
        if count:failures.append(row)
    negative=None
    if cache:
        first=next(iter(cache.values()))['pixels'];negative=int((first<220).sum());assert negative>0
    report=dict(passed=not failures,page=q['page'],proof_sha256=q['output_sha256'],scale=2,threshold=220,
                same_row_grouping_tolerance_pt=.001,close_row_selection_em=2.0,tested_close_row_pairs=len(results),
                pairs=results,failures=failures,actual_embedded_subset_fonts=True,unchanged_word_space_size_shear_paints=True,
                cached_row_renders=len(cache),old_pair_specific_row_renders=len(pairs)*2,
                cache_regression_grayscale_byte_comparisons=regression,
                intentional_same_row_overlap_negative_control_pixels=negative,orthogonal_labels_excluded=orthogonal)
    assert report['passed'],report
    return report
def run(n,folder):
 path=Path(folder)/f'page{n:02}.pdf';q=json.loads(path.with_suffix('.layout.json').read_text('utf8'));oldq=json.loads((ROOT/f'frozen/publication/page{n:02}.qa.json').read_text('utf8'));m=json.loads((ROOT/'semantic-underline-mapping-68-v2.json').read_text('utf8'))
 approved=json.loads(c.style_rules.APP.read_text('utf8'));edit_ids={id for id,d in approved['edits'].items()if d['page']==n};changed_y={p['baseline']for zz in [q,oldq]for p in zz['placements']if p.get('original_source_slot_id',p['id'])in edit_ids};baselines=sorted({r['source_guard']['source_prose_baseline']for r in m['rows']if r['page']==n}|{r['baseline']for r in m['new_Korean_italic_placements']if r['page']==n}|changed_y)
 affected=lambda y:any(abs(y-v)<.001 for v in baselines)
 c._correction_qa_metrics=c.FontMetrics({role:Path(p)for role,p in q['new_font_paths'].items()})
 with f.open(path)as new,f.open(ROOT/f'frozen/reference-proofs/page{n:02}.pdf')as old,f.open(ROOT/'frozen/source/IChO_2024_T_EN.pdf')as source:
  op=old[0];np_=new[0];assert list(op.rect)==list(np_.rect)
  kk=interrow_ink(c,q,new)
  assert c.original_helpers.font_programs(source,source[n-1])<=c.original_helpers.font_programs(new,np_)
  assert c.original_helpers.encoded_images(source,source[n-1])==c.original_helpers.encoded_images(new,np_)
  assert c.original_helpers.native_images(source[n-1])==c.original_helpers.native_images(np_)
  rects=[]
  for y in baselines:
   lines=[v for z in [q,oldq]for v in z['line_reports']if abs(v['baseline']-y)<.001];assert lines
   x0=min(v['left']for v in lines);x1=max(v['right']for v in lines);y0=min(v['source_bounds'][1]for v in lines);y1=max(v['source_bounds'][3]for v in lines)
   for z in [q,oldq]:
    for dec in z['prose_vector_decorations']:
     if abs(dec['source_baseline']-y)<.001:
      rr=dec.get('target_rect',[v+(dec['dx']if i%2==0 else 0)for i,v in enumerate(dec['source_rect'])]);x0=min(x0,rr[0]);x1=max(x1,rr[2]);y0=min(y0,rr[1]-.3);y1=max(y1,rr[3]+.3)
   if n==39 and abs(y-391.5249938964844)<.001:
    atom=json.loads(c.style_rules.ATOM_FILE.read_text('utf8'))
    for vector in atom['source_paths']:
     r=vector['rect'];y0=min(y0,r[1]-.2);y1=max(y1,r[3]+.2)
   rects.append([x0-.5,y0-.5,x1+.5,y1+.5])
  def raster(pg):
   pm=pg.get_pixmap(matrix=f.Matrix(2,2),alpha=False);return np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,3).copy()
  a,b=raster(op),raster(np_);assert a.shape==b.shape;mask=np.zeros(a.shape[:2],bool)
  for r in rects:
   x0=max(0,math.floor(r[0]*2));x1=min(mask.shape[1],math.ceil(r[2]*2));y0=max(0,math.floor(r[1]*2));y1=min(mask.shape[0],math.ceil(r[3]*2));mask[y0:y1,x0:x1]=True
  changed=np.any(a!=b,axis=2);outside=int((changed&~mask).sum());assert outside==0,('Unexpected pixels outside named original rows',n,outside)
  def outside_glyphs(pg):
   result=[]
   for t in pg.get_texttrace():
    if t['type']==3:continue
    for cp,gid,origin,box in t['chars']:
     if not chr(cp).strip()or affected(origin[1]):continue
     if any((f.Rect(r)&f.Rect(box)).get_area()>0 for r in rects):continue
     result.append((cp,gid,t['font'],t['size'],t['type'],list(origin),list(box),t['color'],t['opacity']))
   return result
  assert outside_glyphs(op)==outside_glyphs(np_),'Visible glyph geometry outside source-bound changed rows changed'
  result=dict(page=n,passed=True,proof_sha256=sha(path),reference_proof_sha256=sha(ROOT/f'frozen/reference-proofs/page{n:02}.pdf'),protected_source_sha256=q['source_sha256'],source_bound_changed_row_baselines=baselines,source_bound_row_rects=rects,anti_alias_support_pad_pt=.5,pixel_scale=2,changed_pixels_total=int(changed.sum()),changed_pixels_outside_named_source_rows=outside,visible_glyph_geometry_outside_rows_exactly_equal=True,source_font_programs_images_and_image_placements_preserved=True,kk=kk,program_sha256=sha(__file__))
  q['style_experiment_pixel_and_KK_audit']=result;path.with_suffix('.layout.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');path.with_suffix('.pixel-KK-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
  png=path.with_suffix('.png');assert not png.exists();np_.get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False).save(png)
  srcpng=path.with_name(path.stem+'-source.png');assert not srcpng.exists();source[n-1].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False).save(srcpng)
  metadata=dict(page=n,proof_sha256=sha(path),layout_sha256=sha(path.with_suffix('.layout.json')),composer_sha256=q['composer_sha256'],source_sha256=q['source_sha256'],render_scale=1.5,image_sha256=sha(png),source_image_sha256=sha(srcpng),audit_program_sha256=sha(__file__))
  png.with_suffix('.render.json').write_text(json.dumps(metadata,indent=2)+'\n','utf8')
 return result
