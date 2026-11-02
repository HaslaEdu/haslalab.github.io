"""Source-aware scan/native-program and new-prose collision audit; read-only PDFs."""
from pathlib import Path
from io import BytesIO
import argparse,json,hashlib,math,re
import cv2,numpy as np
import pikepdf,pymupdf as fitz
from pdf_native_inline_reposition import _multiply
from pdf_original_raster_math import replay,original_image_instances,program,program_sha
from cpho_2013_ts_compose import BASE,ROOT,SOURCE,SOURCE_SHA,new_font,font_path,write_words,write_row_token,row_layout,width,sha

def image(page,scale=4):
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False)
    return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width).copy()

def include(mask,rect,scale=4,pad=0):
    x0,y0,x1,y1=rect;x0=max(0,math.floor(x0*scale)-pad);y0=max(0,math.floor(y0*scale)-pad)
    x1=min(mask.shape[1],math.ceil(x1*scale)+pad);y1=min(mask.shape[0],math.ceil(y1*scale)+pad)
    mask[y0:y1,x0:x1]=True

def summary(mask,scale=4):
    yy,xx=np.nonzero(mask)
    return dict(pixels=int(mask.sum()),bbox=None if not len(xx)else[int(xx.min())/scale,int(yy.min())/scale,(int(xx.max())+1)/scale,(int(yy.max())+1)/scale])

def body_style_audit(target,layout,lang,metric,expected_font_sha):
    from collections import Counter,defaultdict
    from izho_new_prose_outline_qa import trace_font_resources
    errors=[];counts=defaultdict(Counter);checked=0
    with pikepdf.open(target)as pdf,fitz.open(target)as doc:
        page=doc[0];mapped,_=trace_font_resources(pdf,page);traces=page.get_texttrace();rows=[]
        for row in layout['rows']:
            tokens,_=row_layout(row,lang,metric)
            for token in tokens:
                if token['kind']=='prose'and token['text'].strip():rows.append((row,token))
        for glyph in mapped:
            if glyph['font_alias']!='/TSScanBody'or glyph['c'].isspace():continue
            checked+=1
            candidates=[(row,token)for row,token in rows if abs(row['size']-glyph['size'])<.001 and abs(row['baseline']-glyph['origin'][1])<.001 and token['x']-.001<=glyph['origin'][0]<token['x']+token['width']+.001]
            if len(candidates)!=1:errors.append(dict(reason='No unique unchanged-size/baseline authored prose token',glyph=glyph));continue
            row,token=candidates[0]
            if glyph['render_type']==2:counts[row['id']].update([0,1])
            else:counts[row['id']][glyph['render_type']]+=1
            if glyph['font_program_sha256']!=expected_font_sha:errors.append(dict(reason='New prose actual font program differs',glyph=glyph))
            styles=row.get('printed_stroke_by_language',{}).get(lang,dict(regular=row['printed_regular_stroke'],bold=row['printed_bold_stroke']))
            stroke=styles['bold']if row.get('role')=='serif-bold'else styles['regular']
            if row.get('role')=='mixed-bold'and token['index']==0 and ':'in token['text']:
                end=token['text'].index(':')+1;boundary=token['x']+width(metric,token['text'][:end],row['size'])
                if glyph['origin'][0]<boundary-.001:stroke=styles['bold']
            if glyph['render_type']!=2:errors.append(dict(reason='Actual new prose fill/stroke paint mode changed',glyph=glyph))
            if glyph['render_type']in[1,2]:
                matching=[t for t in traces if t['type']==1 and abs(t['size']-glyph['size'])<.001 and any(cp==ord(glyph['c'])and gid==glyph['gid']and abs(point[0]-glyph['origin'][0])<.001 and abs(point[1]-glyph['origin'][1])<.001 for cp,gid,point,bbox in t['chars'])]
                if not matching or any(abs(t['linewidth']-stroke)>1e-5 for t in matching):errors.append(dict(reason='Actual source-estimated stroke width changed',glyph=glyph,expected_stroke=stroke,actual_strokes=[t['linewidth']for t in matching]))
        for row in layout['rows']:
            count=sum(not c.isspace()for c in re.sub(r'\[\[[^\]]+\]\]','',row[lang]))
            if counts[row['id']]!=Counter({0:count,1:count}):errors.append(dict(reason='New prose fill/stroke count differs',row=row['id'],actual=dict(counts[row['id']]),expected_per_paint=count))
    return dict(actual_new_prose_glyph_paints_checked=checked,style_font_size_baseline_or_stroke_failures=errors,passed=not errors)

def audit(number,lang):
    out=BASE/'proofs'/lang;target=out/f'page{number:02d}.pdf';stem=target.with_suffix('')
    composition=json.loads(target.with_suffix('.composition.json').read_text('utf8'))
    layout=json.loads((BASE/'authoring'/f'page{number:02d}-layout.json').read_text('utf8'))
    if sha(SOURCE)!=SOURCE_SHA or composition['output_sha256']!=sha(target):raise ValueError('Pinned PDF changed')
    with pikepdf.open(SOURCE)as a,pikepdf.open(target)as b:
        source_page=a.pages[number-1];page=b.pages[0]
        old=original_image_instances(source_page,source_page.Resources);new=original_image_instances(page,page.Resources)
        expected=old.copy()
        with fitz.open(SOURCE)as original_doc:inverse=~original_doc[number-1].transformation_matrix
        for atom in composition['inline_math_replay']['atoms']:
            delta=fitz.Point(atom['dx'],0)*inverse-fitz.Point(0,0)*inverse
            ctm=_multiply(tuple(atom['source_image_ctm']),(1,0,0,1,delta.x,delta.y))
            expected[(atom['image_program_sha256'],tuple(round(v,8)for v in ctm))]+=1
        original_images_unchanged=new==expected
        font_changes=[str(name)for name,font in source_page.Resources.Font.items()if program_sha(font)!=program_sha(page.Resources.Font[name])]
        pagegroup_same=program(source_page.obj.get('/Group'))==program(page.obj.get('/Group'))
    with fitz.open(SOURCE)as a,fitz.open(target)as b:
        before=image(a[number-1]);after=image(b[0])
        allowed=np.zeros(before.shape,bool);old_language=np.zeros(before.shape,bool);old_inline=np.zeros(before.shape,bool)
        for row in layout['rows']:
            for rect in row['erase_rects']:include(allowed,rect,pad=1);include(old_language,rect,pad=1)
            for atom in row['atoms']:include(old_inline,atom['rect'],pad=1);include(allowed,atom['rect'],pad=1)
        for row in composition['body_placements']:
            include(allowed,[row['left']-1,row['baseline']-row['size']*1.3,row['right']+1,row['baseline']+row['size']*.4],pad=1)
            for token in row['tokens']:
                if token['kind']=='math':
                    r=token['atom']['rect'];dx=token['x']-r[0];include(allowed,[r[0]+dx,r[1],r[2]+dx,r[3]],pad=1)
        source_slots=json.loads((ROOT/'tools/ko/cpho/2013/original/native-slots.json').read_text('utf8'))['pages'][number-1]['slots']
        for slot in source_slots:
            for c in slot['source_characters']:include(allowed,c['bbox'],pad=3)
        for row in composition['header']['placements']:
            include(allowed,[row['left']-1,row['baseline']-row['size']*1.4,row['right']+1,row['baseline']+row['size']*.4],pad=3)
        for restored in layout.get('source_background_restore_atoms',[]):
            if restored.get('reviewed')is not True or restored.get('source_sha256')!=SOURCE_SHA or float(restored.get('dx',0))!=0:raise ValueError('Only reviewed exact-source stationary background replay may extend declared image-program regions')
            include(allowed,restored['rect'],pad=1)
        outside=(before!=after)&~allowed
        # Any genuinely stationary old dark pixel may not turn white. Black
        # overprinting is checked independently below against a prose-free control.
        stationary_loss=(before<160)&(after>240)&~old_language&~old_inline
        for slot in source_slots:
            for c in slot['source_characters']:
                r=np.zeros(before.shape,bool);include(r,c['bbox'],pad=3);stationary_loss[r]=False
        protected=np.zeros(before.shape,bool)
        for rect in layout.get('protected_source_display_and_figure_rects',[]):include(protected,rect)
        # This independent source mask is not weakened by a prose erase ROI.
        # It catches a mistaken language box erasing a nearby original bar,
        # fraction component, equation tag or diagram.
        protected_loss=(before<160)&(after>240)&protected
    atoms=[]
    for row in composition['body_placements']:
        for token in row['tokens']:
            if token['kind']=='math':
                atom=token['atom'];atoms.append(dict(id=row['id']+'-'+atom['id'],rect=atom['rect'],image_path=atom['image_path'],dx=token['x']-atom['rect'][0],reviewed=True,reason='Same reviewed source math replay as final composition; independent no-prose collision control.'))
    mathcontrol=out/f'page{number:02d}.math-control.pdf'
    raw,control_qa=replay(SOURCE,number,out/f'page{number:02d}.control.pdf',atoms);mathcontrol.write_bytes(raw)
    text=''.join(t['text']for row in composition['body_placements']for t in row['tokens']if t['kind']=='prose')
    raw_font,metric,_=new_font(font_path(lang),text)
    with fitz.open(SOURCE)as source_doc:bounds=source_doc[number-1].rect
    prose=fitz.open();p=prose.new_page(width=bounds.width,height=bounds.height);p.insert_font(fontname='TSScanBody',fontbuffer=raw_font)
    for row in layout['rows']:
        tokens,_=row_layout(row,lang,metric)
        for token in tokens:
            if token['kind']=='prose':write_row_token(p,row,token,metric,'TSScanBody',lang)
    new_ink=image(p)<180;prose.close()
    new_prose_missing=new_ink&(after>240)
    with fitz.open(mathcontrol)as control:existing_ink=image(control[0])<180
    if existing_ink.shape!=new_ink.shape:raise ValueError(('Control/prose geometry mismatch',existing_ink.shape,new_ink.shape))
    # No exclusions are silently inferred. Reviewed blank-language background
    # exceptions must carry an explicit source crop/meaningful-ink separation.
    collision=existing_ink&new_ink;blank=np.zeros(collision.shape,bool)
    applicable_blank_records=[r for r in layout.get('reviewed_blank_background_rects',[])if lang in r.get('languages',['ko','en'])]
    for record in applicable_blank_records:
        if record.get('reviewed')is not True or not record.get('evidence'):raise ValueError('Blank background needs reviewed source evidence')
        include(blank,record['rect'])
    protected_rects=layout.get('protected_math_and_figure_rects',[])+layout.get('protected_source_display_and_figure_rects',[])
    protected_rects+=[atom['rect']for row in layout['rows']for atom in row['atoms']]
    for atom in atoms:
        rect=atom['rect'];dx=atom['dx'];protected_rects.append([rect[0]+dx,rect[1],rect[2]+dx,rect[3]])
    for rect in protected_rects:
        protected=np.zeros(blank.shape,bool);include(protected,rect);blank[protected]=False
    collision_after=collision&~blank
    import pdf_new_prose_outlines as outlines
    old_prefixes=outlines.PREFIXES
    try:outlines.PREFIXES=('/TSHeader','/TSScanBody');outline_qa=outlines.audit(target)
    finally:outlines.PREFIXES=old_prefixes
    style_qa=body_style_audit(target,layout,lang,metric,composition['body_font']['subset_sha256'])
    hangul_qa=None
    if lang=='ko':
        from pdf_hangul_visibility import audit as visibility
        hangul_qa=visibility(target)
    report=dict(source=str(SOURCE),source_sha256=SOURCE_SHA,source_page=number,language=lang,proof=str(target),proof_sha256=sha(target),
        original_encoded_images_mask_icc_palette_and_ctm_unchanged=original_images_unchanged,original_native_font_program_changes=font_changes,
        original_pagegroup_unchanged=pagegroup_same,outside_declared_translation_and_moved_math=summary(outside),stationary_original_dark_ink_lost=summary(stationary_loss),
        independent_protected_source_display_and_figure_dark_ink_lost=summary(protected_loss),protected_source_display_and_figure_rects=layout.get('protected_source_display_and_figure_rects',[]),
        new_prose_overlap_original_or_replayed_nonlanguage_ink=summary(collision_after),raw_collision_including_reviewed_scan_background=summary(collision),
        reviewed_blank_background_records=applicable_blank_records,new_actual_outline_audit=outline_qa,
        new_prose_expected_dark_pixels_missing=summary(new_prose_missing),actual_new_prose_style_audit=style_qa,independent_hangul_visibility=hangul_qa,
        source_math_replay=composition['inline_math_replay'],passed=not outside.any()and not stationary_loss.any()and not protected_loss.any()and not collision_after.any()and not new_prose_missing.any()and original_images_unchanged and not font_changes and pagegroup_same and outline_qa['passed']and style_qa['passed']and(hangul_qa is None or not hangul_qa['flagged_components']),
        visual_review_required=True,publication_ready=False)
    target.with_suffix('.source-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    from PIL import Image
    Image.fromarray(after).resize((after.shape[1]//2,after.shape[0]//2),Image.Resampling.LANCZOS).save(target.with_suffix('.png'))
    if protected_loss.any():
        ys=np.nonzero(protected_loss.any(axis=1))[0];groups=[]
        for y in ys:
            if not groups or y-groups[-1][-1]>16:groups.append([int(y)])
            else:groups[-1].append(int(y))
        strips=[]
        for group in groups:
            y0=max(0,group[0]-24);y1=min(before.shape[0],group[-1]+25)
            xx=np.nonzero(protected_loss[y0:y1].any(axis=0))[0];x0=max(0,int(xx.min())-28);x1=min(before.shape[1],int(xx.max())+29)
            old=Image.fromarray(before[y0:y1,x0:x1]).convert('RGB');new=Image.fromarray(after[y0:y1,x0:x1]).convert('RGB')
            strip=Image.new('RGB',(old.width*2+10,old.height+20),'white');strip.paste(old,(0,20));strip.paste(new,(old.width+10,20))
            from PIL import ImageDraw
            draw=ImageDraw.Draw(strip);draw.text((1,2),f'source x{x0/4:g} y{y0/4:g}; original / translation',fill='black');strips.append(strip)
        witness=Image.new('RGB',(max(s.width for s in strips),sum(s.height+8 for s in strips)),'white');y=0
        for strip in strips:witness.paste(strip,(0,y));y+=strip.height+8
        witness.save(target.with_suffix('.protected-loss-witness.png'))
    if collision_after.any():
        debug=np.full((*collision.shape,3),255,np.uint8);debug[existing_ink]=[170,170,170];debug[new_ink]=[0,0,180];debug[collision_after]=[255,0,0]
        Image.fromarray(debug).save(target.with_suffix('.collision.png'))
    print(lang,number,'outside',summary(outside),'stationary',summary(stationary_loss),'collision',summary(collision_after),'pass',report['passed'],flush=True)
    return report

if __name__=='__main__':
    from pdf_memory_gate import page_worker
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('page',type=int);p.add_argument('language',choices=['ko','en']);a=p.parse_args()
    with page_worker():audit(a.page,a.language)
