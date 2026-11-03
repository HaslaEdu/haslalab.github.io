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
        images=source[plan['source_page']-1].get_image_info(xrefs=True)
        result=[]
        for label in labels:
            if not label.get('reviewed')or label['source_sha256']!=plan['original_english_source_sha256']:raise ValueError('Unreviewed bitmap label')
            info=images[label['image_index']];box=fitz.Rect(info['bbox']);w,h=info['width'],info['height'];px=label['source_word_ink_rect_px']
            if plan['original_english_source_sha256']=='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49':
                policy=Path(plan['reviewed_bitmap_source_measurements']);assert sha(policy)==plan['reviewed_bitmap_source_measurements_sha256'];measured=json.loads(policy.read_text('utf8'));assert plan['source_page']==10 and label in measured['reviewed_bitmap_language_labels'] and measured['source_sha256']==plan['original_english_source_sha256'];xref=info['xref']
            else:xref=source[plan['source_page']-1].get_images(full=True)[label['image_index']][0]
            pix=fitz.Pixmap(source,xref)
            if pix.colorspace.n!=3:pix=fitz.Pixmap(fitz.csRGB,pix)
            sx,sy=label['source_background_sample_px'];sample=list(pix.pixel(sx,sy))[:3]
            if sample!=label['source_background_rgb']:raise ValueError('Original measured label background does not match source image')
            rect=[box.x0+(px[0]-1)*box.width/w,box.y0+(px[1]-1)*box.height/h,box.x0+(px[2]+1)*box.width/w,box.y0+(px[3]+1)*box.height/h]
            center=box.x0+(px[0]+px[2])/2*box.width/w
            if label.get('rotation',0)not in[0,90]:raise ValueError('Unreviewed original bitmap label orientation')
            center_y=box.y0+(px[1]+px[3])/2*box.height/h
            dx=0.
            if plan.get('reviewed_bitmap_label_translation_clearance'):
                clearance=Path(plan['reviewed_bitmap_label_translation_clearance']);assert sha(clearance)==plan['reviewed_bitmap_label_translation_clearance_sha256'];review=json.loads(clearance.read_text('utf8'));assert review['source_sha256']==plan['original_english_source_sha256']and review['source_measurements_sha256']==plan['reviewed_bitmap_source_measurements_sha256']and review['passed'];r=next(r for r in review['rows']if r['source_label']==label['source_label']);dx=r['horizontal_dx_pt'];assert(label['source_label']=='Sun'and dx==-1.25)or(label['source_label']in['Star','Earth']and dx==0)
            result.append(dict(label,erase_rect_pt=rect,original_word_center_pt=center,actual_word_center_pt=center+dx,translation_width_clearance_dx_pt=dx,original_word_center_y_pt=center_y,image_bbox=list(box),image_dimensions_px=[w,h]))
        return result

def apply(plan,target):
    target=Path(target);labels=specifications(plan)
    if not labels:return None
    before=target.with_suffix('.before-language.pdf');shutil.copyfile(target,before)
    roles={l.get('measured_source_font_role','serif-bold')for l in labels}
    allowed={'serif-bold','sans-bold'}
    if plan['original_english_source_sha256']=='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49'and plan['source_page']==10:allowed.add('serif')
    if not roles<=allowed:raise ValueError('Unreviewed bitmap source font role')
    fonts={role:korean_font('',0,''.join(l['text']for l in labels if l.get('measured_source_font_role','serif-bold')==role),override=role,cache_dir=target.parent/'label-fonts')[1]for role in roles}
    overlay=fitz.open()
    with fitz.open(before)as body:p=overlay.new_page(width=body[0].rect.width,height=body[0].rect.height)
    for role,path in fonts.items():p.insert_font(fontname='KO_Original_Bitmap_Label_'+role.replace('-','_'),fontfile=str(path))
    placements=[]
    for label in labels:
        role=label.get('measured_source_font_role','serif-bold');path=fonts[role];metric=fitz.Font(fontfile=str(path));alias='KO_Original_Bitmap_Label_'+role.replace('-','_')
        p.draw_rect(fitz.Rect(label['erase_rect_pt']),color=None,fill=tuple(c/255 for c in label['source_background_rgb']),width=0)
        size=label['measured_source_size_pt'];rotation=label.get('rotation',0);width=metric.text_length(label['text'],fontsize=size)
        if rotation==90:x=label['measured_source_baseline_pt'];y=label['original_word_center_y_pt']+width/2
        else:x=label['actual_word_center_pt']-width/2;y=label['measured_source_baseline_pt']
        angle=label.get('measured_source_italic_slant_degrees',0.)
        if angle and (plan['original_english_source_sha256']!='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49'or rotation or role!='serif'):raise ValueError('Unreviewed source bitmap italic role')
        morph=(fitz.Point(x,y),fitz.Matrix(1,0,math.tan(math.radians(angle)),1,0,0))if angle else None
        p.insert_text((x,y),label['text'],fontname=alias,fontsize=size,color=(0,0,0),rotate=rotation,morph=morph)
        placements.append(dict(label,origin=[x,y],font_role=role,replacement_font_path=str(path),replacement_font_sha256=sha(path),point_size_fitted=False,writing_direction=[0,-1]if rotation else[1,0]))
    overlay_path=target.with_suffix('.language-overlay.pdf');overlay.save(overlay_path,garbage=0,deflate=False);overlay.close()
    with pikepdf.open(before)as body,pikepdf.open(overlay_path)as over:
        body.pages[0].add_overlay(over.pages[0]);body.save(target,compress_streams=False)
    report=dict(source_sha256=plan['original_english_source_sha256'],input_body_sha256=sha(before),output_sha256=sha(target),overlay_sha256=sha(overlay_path),placements=placements,source_image_bytes_modified=False,method='White PDF rectangles only over manually reviewed isolated original language words; measured original source font role, size and baseline with matching Korean role fallback, original word center retained.')
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
            hits=[];metric=fitz.Font(fontfile=row['replacement_font_path']);offset=0.;expected=[];rotation=row.get('rotation',0)
            for c in row['text']:
                point=[row['origin'][0],row['origin'][1]-offset]if rotation else[row['origin'][0]+offset,row['origin'][1]]
                if not c.isspace():expected.append((c,point))
                offset+=metric.text_length(c,fontsize=row['measured_source_size_pt'])
            for trace in final[0].get_texttrace():
                for cp,gid,point,bbox in trace['chars']:
                    expected_family='NotoSans'if row.get('measured_source_font_role','serif-bold')=='sans-bold'else'NotoSerif'
                    if any(chr(cp)==c and max(abs(a-b)for a,b in zip(point,wanted))<.02 for c,wanted in expected) and abs(trace['size']-row['measured_source_size_pt'])<.001 and expected_family in trace['font'] and max(abs(a-b)for a,b in zip(trace['dir'],row['writing_direction']))<.001:
                        if not chr(cp).isspace():hits.append((chr(cp),point))
            if ''.join(c for c,_ in hits)!=''.join(c for c,_ in expected)or len(hits)!=len(expected):raise ValueError(('Final label glyphs missing or wrong original orientation',row,hits))
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
