"""Reviewed bitmap language overlays. Original images and nonlanguage ink stay native.

Each source rectangle is a manually isolated bitmap WORD, never a formula or
diagram area. White erasure is restricted to those word rectangles; comparison
masks contain actual old language ink and actual new glyph outlines only.
"""
from pathlib import Path
import hashlib,json,shutil,math
import numpy as np
import pikepdf,pymupdf as fitz
from pdf_original_style_fonts import korean_font
from pdf_text_motion_ink import ink_envelope
from pdf_original_graphics_ink import graphics_control

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def specifications(plan):
    labels=plan.get('reviewed_bitmap_language_labels',[])
    if not labels:return []
    if sha(plan['original_english_source'])!=plan['original_english_source_sha256']:raise ValueError('Original label source changed')
    with fitz.open(plan['original_english_source'])as source:
        images=source[plan['source_page']-1].get_image_info()
        result=[]
        for label in labels:
            if not label.get('reviewed')or label['source_sha256']!=plan['original_english_source_sha256']:raise ValueError('Unreviewed bitmap label')
            info=images[label['image_index']];box=fitz.Rect(info['bbox']);w,h=info['width'],info['height'];px=label['source_word_ink_rect_px']
            xref=source[plan['source_page']-1].get_images(full=True)[label['image_index']][0];pix=fitz.Pixmap(source,xref)
            if pix.colorspace.n!=3:pix=fitz.Pixmap(fitz.csRGB,pix)
            sx,sy=label['source_background_sample_px'];sample=list(pix.pixel(sx,sy))[:3]
            if sample!=label['source_background_rgb']:raise ValueError('Original measured label background does not match source image')
            rect=[box.x0+(px[0]-1)*box.width/w,box.y0+(px[1]-1)*box.height/h,box.x0+(px[2]+1)*box.width/w,box.y0+(px[3]+1)*box.height/h]
            center=box.x0+(px[0]+px[2])/2*box.width/w
            result.append(dict(label,erase_rect_pt=rect,original_word_center_pt=center,image_bbox=list(box),image_dimensions_px=[w,h]))
        return result

def apply(plan,target):
    target=Path(target);labels=specifications(plan)
    if not labels:return None
    before=target.with_suffix('.before-language.pdf');shutil.copyfile(target,before)
    role,path=korean_font('',0,''.join(l['text']for l in labels),override='serif-bold',cache_dir=target.parent/'label-fonts')
    metric=fitz.Font(fontfile=str(path));overlay=fitz.open()
    with fitz.open(before)as body:p=overlay.new_page(width=body[0].rect.width,height=body[0].rect.height)
    alias='KO_Original_Bitmap_Label_Bold';p.insert_font(fontname=alias,fontfile=str(path));placements=[]
    for label in labels:
        p.draw_rect(fitz.Rect(label['erase_rect_pt']),color=None,fill=tuple(c/255 for c in label['source_background_rgb']),width=0)
        size=label['measured_source_size_pt'];x=label['original_word_center_pt']-metric.text_length(label['text'],fontsize=size)/2;y=label['measured_source_baseline_pt']
        p.insert_text((x,y),label['text'],fontname=alias,fontsize=size,color=(0,0,0))
        placements.append(dict(label,origin=[x,y],font_role=role,replacement_font_path=str(path),replacement_font_sha256=sha(path),point_size_fitted=False))
    overlay_path=target.with_suffix('.language-overlay.pdf');overlay.save(overlay_path,garbage=0,deflate=False);overlay.close()
    with pikepdf.open(before)as body,pikepdf.open(overlay_path)as over:
        body.pages[0].add_overlay(over.pages[0]);body.save(target,compress_streams=False)
    report=dict(source_sha256=plan['original_english_source_sha256'],input_body_sha256=sha(before),output_sha256=sha(target),overlay_sha256=sha(overlay_path),placements=placements,source_image_bytes_modified=False,method='White PDF rectangles only over manually reviewed isolated original language words; measured original bold-serif size/baseline and matching Korean bold-serif fallback, original word center retained.')
    target.with_suffix('.language-overlay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report

def masks(plan,target,original_rgb,scale=4):
    labels=specifications(plan);shape=original_rgb.shape[:2];old=np.zeros(shape,bool)
    if not labels:return old,old.copy(),dict(labels=0)
    for label in labels:
        x0,y0,x1,y1=label['erase_rect_pt'];x0=max(0,math.floor(x0*scale));y0=max(0,math.floor(y0*scale));x1=min(shape[1],math.ceil(x1*scale));y1=min(shape[0],math.ceil(y1*scale))
        old[y0:y1,x0:x1]|=np.any(original_rgb[y0:y1,x0:x1]!=np.array(label['source_background_rgb']),axis=2)
    report=json.loads(Path(target).with_suffix('.language-overlay.json').read_text('utf8'));new=np.zeros(shape,bool);collision=0
    with fitz.open(target)as final:
        for row in report['placements']:
            hits=[]
            for trace in final[0].get_texttrace():
                for cp,gid,point,bbox in trace['chars']:
                    if row['origin'][0]-.02<=point[0]<=row['origin'][0]+len(row['text'])*row['measured_source_size_pt']+.02 and abs(point[1]-row['origin'][1])<.02 and abs(trace['size']-row['measured_source_size_pt'])<.001 and 'NotoSerif'in trace['font']:
                        if not chr(cp).isspace():hits.append((chr(cp),point))
            if ''.join(c for c,_ in hits)!=row['text']:raise ValueError(('Final label glyphs missing',row,hits))
            item_mask,_=ink_envelope(final[0],[list(point)for _,point in hits],scale)
            collision+=int((item_mask&np.any(original_rgb!=np.array(row['source_background_rgb']),axis=2)&~old).sum())
            new|=item_mask
    result=dict(labels=len(labels),source_original_language_ink_pixels=int(old.sum()),new_label_outline_pixels=int(new.sum()),new_label_over_original_nonlanguage_foreground_pixels=collision,
                original_language_regions=[l['erase_rect_pt']for l in labels],actual_ink_only_masks=True,source_background_restored_exactly=True,source_background_rgb_samples=[dict(label=l['source_label'],source_pixel=l['source_background_sample_px'],rgb=l['source_background_rgb'])for l in labels],source_nonlanguage_geometry_within_and_outside_language_regions_protected=True)
    if collision:raise ValueError(('New label covers original nonlanguage picture ink',result))
    return old,new,result

def adjust_geometry(plan,old,target,motion,report,old_language_mask,fresh_render,folder):
    """Recheck complete non-text controls with only OLD language ink excluded."""
    controls=[]
    for name,path in [('old',old),('new',target)]:
        dest=Path(folder)/('bitmap-label-graphics-'+name+'.pdf')
        with fitz.open(path)as doc:dest.write_bytes(graphics_control(doc,doc[0]))
        controls.append(fresh_render(dest,1,Path(folder)/('bitmap-label-graphics-'+name+'.png')))
    changed=np.any(controls[0]!=controls[1],axis=2)
    result=dict(report,coarse_changed_nonselected_native_graphical_pixels=report['changed_nonselected_native_graphical_pixels'],
                explicitly_translated_original_bitmap_language_pixels=int((changed&old_language_mask&~motion).sum()),
                changed_nonselected_native_graphical_pixels=int((changed&~motion&~old_language_mask).sum()),
                bitmap_language_profile='Only reviewed source language ink is excluded; original background, lines, variables and picture surfaces remain protected.')
    return result
