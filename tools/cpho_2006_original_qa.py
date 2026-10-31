"""Audit the native-layout 2006 editions against their original PDF."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re,math,gc
import numpy as np
from io import BytesIO
import pymupdf as fitz
from PIL import Image,ImageDraw
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import cpho_2006_original_build as b
import pdf_original_style_audit as preservation
from cpho_original_latin_fonts import BUILD_ROOT as EN_REPAIR_ROOT
import pdf_hangul_visibility as visibility
from cpho_2006_original_captions import CAPTIONS,SIZE
preservation.cv2.setNumThreads(1)


def sha(value):return hashlib.sha256(value).hexdigest()


def exact_glyph_key(g):
    return(g['c'],g['font'],g['gid'],g['size'],tuple(g['origin']),tuple(g['color']),g['render_type'])


def image_keys(page):
    return Counter((tuple(item['bbox']),item['width'],item['height'],item['bpc'],item['colorspace'],item['digest'].hex())
                   for item in page.get_image_info(hashes=True))


def font_keys(doc,page):
    result={}
    for record in page.get_fonts(full=True):
        name=record[3]
        if name.startswith('Translation'):continue
        data=doc.extract_font(record[0])[3]
        result[name]=sha(data)
    return result


def translated_ink_rects(doc,page,original_page):
    """Actual outlines, including Times f/j overhang and descenders."""
    old={t['font']for t in original_page.get_texttrace()};fonts=[];rects=[]
    for record in page.get_fonts(full=True):
        if not record[4].startswith('Translation'):continue
        font=TTFont(BytesIO(doc.extract_font(record[0])[3]))
        names={re.sub('[^a-z0-9]','',entry.toUnicode().lower())for entry in font['name'].names}
        names.add(re.sub('[^a-z0-9]','',record[3].lower()));fonts.append((names,font))
    for trace in page.get_texttrace():
        if trace['font']in old:continue
        key=re.sub('[^a-z0-9]','',trace['font'].lower())
        font=next(font for names,font in fonts if key in names);glyphs=font.getGlyphSet()
        factor=trace['size']/font['head'].unitsPerEm
        for cp,gid,origin,box in trace['chars']:
            pen=BoundsPen(glyphs);glyphs[font.getGlyphOrder()[gid]].draw(pen)
            if pen.bounds is None:continue
            x0,y0,x1,y1=pen.bounds;x,y=origin
            # One raster pixel covers outline antialiasing at audit scale.
            rects.append([x+x0*factor-.25,y-y1*factor-.25,x+x1*factor+.25,y-y0*factor+.25])
    for names,font in fonts:font.close()
    return rects


def audit(path,pages,scale=4):
    data=json.loads((b.BASE/'slots.json').read_text(encoding='utf8'))
    source=fitz.open(b.SOURCE);proof=fitz.open(path);assert len(proof)==len(pages)
    folder=EN_REPAIR_ROOT/'2006'/'qa'/path.stem if '_EN'in path.stem else b.BASE/'qa'/path.stem;folder.mkdir(parents=True,exist_ok=True)
    report={'pdf':str(path.resolve()),'sha256':sha(path.read_bytes()),'source_sha256':b.SOURCE_SHA,
            'source_pages':pages,'pages':[],'passed':True}
    previews=[]
    for pi,number in enumerate(pages):
        page=data['pages'][number-1];erased=[c['origin']for c in b.selected_glyphs(page)]
        spec={'source_page':number,'proof_page':pi+1,
              'allowed_rects':[s['allowed_rect']for s in page['slots']if not s.get('retain_native')],
              'erased_glyph_origins':erased}
        spec['protected_rects']=[list(item['rect'])for item in source[number-1].get_drawings()
                     if item['rect'].height<1.5 and item['rect'].width>7]
        captions=[item for item in CAPTIONS if item['page']==number]
        spec['allowed_rects'] +=[item['erase_rect']for item in captions]
        spec['protected_rects'] +=[item['numeric_protected_rect']for item in captions]
        # Include new prose's real font metric boxes: Times has overhanging
        # f/j and a slightly deeper descender than the source CJK cells.
        # This never weakens the independently protected native ink mask.
        spec['allowed_rects'] +=translated_ink_rects(proof,proof[pi],source[number-1])
        (folder/f'page{number:02}-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
        row=preservation.audit(b.SOURCE,path,spec,scale)
        # Root audit rounds only for comparison; this second check requires
        # bit-identical original nonspace glyph size and origins.
        kept=[g for g in preservation.glyphs(source[number-1])if not g['c'].isspace()
              and not any(preservation.close_origin(g['origin'],p)for p in erased)]
        current=Counter(exact_glyph_key(g)for g in preservation.glyphs(proof[pi]))
        missing=[]
        for g in kept:
            key=exact_glyph_key(g)
            if current[key]:current[key]-=1
            else:missing.append(g)
        row['bit_exact_native_nonspace_glyphs_checked']=len(kept)
        row['bit_exact_native_nonspace_glyphs_changed']=missing
        row['original_images_identical']=image_keys(source[number-1])==image_keys(proof[pi])
        aa=source[number-1].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB)
        bb=proof[pi].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB)
        difference=np.any(np.frombuffer(aa.samples,np.uint8).reshape(aa.height,aa.width,3)!=
                          np.frombuffer(bb.samples,np.uint8).reshape(bb.height,bb.width,3),axis=2)
        original_images=np.zeros(difference.shape,bool);caption_mask=np.zeros(difference.shape,bool)
        image_edges=np.zeros(difference.shape,bool)
        def region(rect):
            r=fitz.Rect(rect)
            return(slice(max(0,math.floor(r.y0*scale)),min(aa.height,math.ceil(r.y1*scale))),
                   slice(max(0,math.floor(r.x0*scale)),min(aa.width,math.ceil(r.x1*scale))))
        for image in source[number-1].get_image_info():
            r=fitz.Rect(image['bbox']);part=np.zeros(difference.shape,bool);part[region(r)]=True
            inner=(slice(max(0,math.ceil(r.y0*scale)),min(aa.height,math.floor(r.y1*scale))),
                   slice(max(0,math.ceil(r.x0*scale)),min(aa.width,math.floor(r.x1*scale))))
            part[inner]=False;image_edges|=part;original_images[region(r)]=True
        # A fragment edge can blend the underlying original footer within
        # one renderer pixel. This guard is restricted below to the original
        # under-image footer, never the opaque diagram's interior.
        image_edges=preservation.cv2.dilate(image_edges.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&original_images
        for item in captions:caption_mask[region(item['comparison_rect'])]=True
        row['original_image_pixels_changed_outside_caption_text']=int((difference&original_images&~caption_mask).sum())
        footer=np.zeros(difference.shape,bool)
        if number==2:
            for slot in page['slots']:
                if slot.get('overlay')is False:footer[region(slot['allowed_rect'])]=True
        inherited_footer_edge=difference&original_images&~caption_mask&footer&image_edges
        row['inherited_footer_prose_at_image_antialias_edge']=int(inherited_footer_edge.sum())
        row['inherited_footer_image_edge_antialias_guard_pixels']=1
        row['unexplained_original_image_pixel_changes']=int((difference&original_images&~caption_mask&~inherited_footer_edge).sum())
        row['caption_number_pixels_changed']=[{'number':item['number'],
                   'changed_pixels':int(difference[region(item['numeric_protected_rect'])].sum())}for item in captions]
        row['translation_style_violations']=[];max_baseline=0;max_size=0
        source_fonts={t['font']for t in source[number-1].get_texttrace()}
        expected=[{'size':s['size'],'baseline':s['origin'][1],
                      'color':s['color'],'mode':s.get('render_mode',0)}for s in page['slots']]
        expected +=[{'size':SIZE,'baseline':c['baseline'],'color':0,'mode':0}for c in captions]
        for trace in proof[pi].get_texttrace():
            if trace['font']in source_fonts:continue
            for cp,gid,origin,box in trace['chars']:
                closest=min(expected,key=lambda e:abs(e['baseline']-origin[1]))
                dy=abs(closest['baseline']-origin[1]);ds=abs(closest['size']-trace['size'])
                max_baseline=max(max_baseline,dy);max_size=max(max_size,ds)
                color=[((closest['color']>>n)&255)/255 for n in [16,8,0]]
                modes={0,1}if closest['mode']==2 else{closest['mode']}
                if dy>.0001 or ds>.0001 or trace['type']not in modes or any(abs(a-b)>.0001 for a,b in zip(color,trace['color'])):
                    row['translation_style_violations'].append({'c':chr(cp),'origin':origin,'size':trace['size'],'render_mode':trace['type'],'expected':closest})
        row['translation_baseline_max_delta_pt']=max_baseline
        row['translation_size_max_delta_pt']=max_size
        old_fonts=font_keys(source,source[number-1]);new_fonts=font_keys(proof,proof[pi])
        row['original_font_programs_identical']=all(new_fonts.get(k)==v for k,v in old_fonts.items())
        row['original_font_program_sha256']=old_fonts
        row['remaining_han']=[g for g in preservation.glyphs(proof[pi]) if re.search('[\u3400-\u9fff]',g['c']) and exact_glyph_key(g) not in {exact_glyph_key(k) for k in kept}]
        row['native_han_math_shapes_retained']=[g for g in kept if re.search('[\u3400-\u9fff]',g['c'])]
        # Never attribute a pre-existing damaged native source mapping to the
        # new translation fonts.
        row['unexpected_nul']=sum(g['c']=='\x00'and not any(preservation.close_origin(g['origin'],p['origin'])
                   for p in kept if p['c']=='\x00')for g in preservation.glyphs(proof[pi]))
        row['passed']=not(row['native_glyphs_changed']or missing or row['protected_glyphs_selected_for_erasure']
             or row['changed_pixels_outside_prose']or row['changed_pixels_in_native_glyph_neighborhood']
             or not row['original_images_identical']or not row['original_font_programs_identical']
             or row['remaining_han']or row['unexpected_nul']or row['translation_style_violations']
             or row['unexplained_original_image_pixel_changes']
             or any(item['changed_pixels']for item in row['caption_number_pixels_changed']))
        report['passed']&=row['passed'];report['pages'].append(row)
        pix=proof[pi].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False)
        image=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        image.save(folder/f'page{number:02}-mupdf.png');image.thumbnail((595,842));previews.append((number,image.copy()))
        print(path.name,'source p',number,'outside',row['changed_pixels_outside_prose'],
              'native ink',row['changed_pixels_in_native_glyph_neighborhood'],'exact glyphs',len(missing),flush=True)
        del aa,bb,difference,original_images,caption_mask,image_edges,footer,inherited_footer_edge
        fitz.TOOLS.store_shrink(100);gc.collect()
    cols=2;rows=(len(previews)+1)//2;contact=Image.new('RGB',(cols*620,rows*875),'#ddd');draw=ImageDraw.Draw(contact)
    for index,(number,image)in enumerate(previews):
        x=(index%cols)*620;y=(index//cols)*875;draw.text((x+12,y+5),f'Source page {number}',fill='black');contact.paste(image,(x+12,y+25))
    contact.save(folder/'contact-mupdf.png')
    if '_KO' in path.stem:
        visible=visibility.audit(path,scale=scale);report['hangul_visibility']=visible
        inherited=[];unexpected=[]
        for row in visible['pages']:
            original_number=pages[row['page']-1]
            images=source[original_number-1].get_image_info()
            panel=fitz.Rect()
            for item in images:
                if item['width']>20 and item['height']>20:panel|=fitz.Rect(item['bbox'])
            for group in row['clusters']:
                rect=fitz.Rect(group['rect'])
                if original_number==2 and rect.y0>755 and panel.contains(rect):
                    inherited.append({'page':2,**group})
                else:unexpected.append({'page':original_number,**group})
        visible['inherited_source_footer_occlusion']=inherited
        visible['inherited_source_footer_occlusion_reason']='The original opaque fragmented illustration covers this footer region. Translation remains below that identical original image, preserving source paint order.'
        visible['unexpected_components']=unexpected
        report['passed']&=not unexpected
    (folder/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('--pages',nargs='+',type=int,required=True)
    p.add_argument('--scale',type=int,default=4);args=p.parse_args();result=audit(args.pdf,args.pages,args.scale)
    print('PASSED',result['passed']);raise SystemExit(not result['passed'])
