"""Independent native-type, vector, bitmap and prose QA for 2022 T."""
from pathlib import Path
from collections import Counter
from io import BytesIO
import argparse,gc,hashlib,json,math,re
import pikepdf
import numpy as np
import cv2
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image,ImageDraw
import cpho_2022_original_build as b
import cpho_2022_original_labels as labels
import pdf_original_style_audit as preservation
from cpho_original_latin_fonts import BUILD_ROOT as EN_REPAIR_ROOT
import pdf_hangul_visibility as visibility
from pdf_original_image_ink import image_ink_mask,image_programs
cv2.setNumThreads(1)


def sha(value):return hashlib.sha256(value).hexdigest()
def exact(g):return(g['c'],g['font'],g['gid'],g['size'],tuple(g['origin']),tuple(g['color']),g['render_type'])


def extra_glyphs(source,page):
    original=Counter(exact(g)for g in preservation.glyphs(source));result=[]
    for trace in page.get_texttrace():
        for cp,gid,origin,bbox in trace['chars']:
            g=dict(c=chr(cp),font=re.sub(r'^[A-Z]{6}\+','',trace['font']),gid=gid,size=trace['size'],origin=list(origin),
                   bbox=list(bbox),color=list(trace['color']),render_type=trace['type'],direction=list(trace['dir']))
            key=exact(g)
            if original[key]:original[key]-=1
            else:result.append(g)
    return result


def translation_ink_rects(doc,page,glyphs):
    fonts=[];rects=[]
    for record in page.get_fonts(full=True):
        if not record[4].startswith('Translation'):continue
        font=TTFont(BytesIO(doc.extract_font(record[0])[3]));names={re.sub('[^a-z0-9]','',n.toUnicode().lower())for n in font['name'].names}
        names.add(re.sub('[^a-z0-9]','',record[3].lower()));fonts.append((names,font))
    for g in glyphs:
        if g['c'].isspace():continue
        key=re.sub('[^a-z0-9]','',g['font'].lower());candidates=[font for names,font in fonts if key in names]
        if not candidates:raise ValueError('Unknown additional nonspace glyph '+repr(g))
        font=candidates[0];glyphset=font.getGlyphSet();pen=BoundsPen(glyphset);glyphset[font.getGlyphOrder()[g['gid']]].draw(pen)
        if pen.bounds is None:continue
        x0,y0,x1,y1=pen.bounds;factor=g['size']/font['head'].unitsPerEm;dx,dy=g['direction'];x,y=g['origin']
        points=[(x+(gx*dx+gy*dy)*factor,y+(gx*dy-gy*dx)*factor)for gx in(x0,x1)for gy in(y0,y1)]
        rects.append([min(x for x,y in points)-.25,min(y for x,y in points)-.25,max(x for x,y in points)+.25,max(y for x,y in points)+.25])
    for names,font in fonts:font.close()
    return rects


def vector_ink_mask(page,scale):
    # Native text glyphs have a separate exact-glyph/outline test. Keep only
    # the source's non-text paths here; bitmaps/SMask have their own reader.
    svg=page.get_svg_image(text_as_path=True)
    svg=re.sub(r'<use\b[^>]*data-text=[^>]*?/?>','',svg)
    svg=re.sub(r'<image\b[^>]*?/?>','',svg)
    svg=re.sub(r'<use\b[^>]*xlink:href="#image_[^"]*"[^>]*?/?>','',svg)
    source=fitz.open(stream=svg.encode('utf8'),filetype='svg');vector=fitz.open(stream=source.convert_to_pdf(),filetype='pdf')
    pix=vector[0].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
    result=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<245).astype(np.uint8)
    result=cv2.dilate(result,np.ones((3,3),np.uint8)).astype(bool);vector.close();source.close();return result


def original_font_programs(doc,page):
    # Follow all native Form resource dictionaries; MuPDF's get_fonts can
    # omit fonts in an imported nested mathematical Form.
    programs={};visited=set();path=doc.name if doc.name else BytesIO(doc.tobytes(garbage=0))
    with pikepdf.Pdf.open(path)as pdf:
        def walk(resources):
            for name,font in resources.get('/Font',{}).items():
                if str(name).startswith('/Translation'):continue
                descriptor=font.get('/FontDescriptor')
                if descriptor is None and '/DescendantFonts'in font:descriptor=font['/DescendantFonts'][0].get('/FontDescriptor')
                raw=[]
                if descriptor is not None:
                    for key in ['/FontFile','/FontFile2','/FontFile3']:
                        if key in descriptor:raw.append(sha(descriptor[key].read_bytes()))
                key='|'.join([bytes(font.get('/BaseFont')).decode('latin1'),str(font.get('/Subtype')),str(font.get('/Encoding'))])
                programs.setdefault(key,set()).add(tuple(raw))
            for child in resources.get('/XObject',{}).values():
                if str(child.get('/Subtype'))!='/Form'or child.objgen in visited:continue
                visited.add(child.objgen)
                if '/Resources'in child:walk(child['/Resources'])
        walk(pdf.pages[page.number].Resources)
    return {key:sorted(values)for key,values in programs.items()}


def label_mask(shape,scale,items):
    mask=np.zeros(shape,np.uint8)
    for item in items:
        if 'erase_polygon'in item:
            points=np.round(np.asarray(item['erase_polygon'])*scale).astype(np.int32);cv2.fillPoly(mask,[points],1)
        else:
            r=fitz.Rect(item['erase_rect']);mask[max(0,math.floor(r.y0*scale)):math.ceil(r.y1*scale),max(0,math.floor(r.x0*scale)):math.ceil(r.x1*scale)]=1
    # The bitmap mask carries the same one-pixel antialiasing guard.
    # Exclude that guard around the explicitly translated language too.
    return cv2.dilate(mask,np.ones((3,3),np.uint8)).astype(bool)


def style_checks(additional,page,raster):
    expected=[]
    for slot in page['slots']:
        if slot.get('retain_native'):continue
        expected.append(dict(size=slot['size'],origin=slot['origin'],angle=0,kind='native-prose',font_family=slot['family']))
    for label in raster:
        for run in label['runs']:expected.append(dict(size=label['size'],origin=run['origin'],angle=run['angle'],kind='raster-prose',font_family='serif'))
    failures=[];max_size=0;max_baseline=0
    for g in additional:
        if g['c'].isspace():continue
        distances=[]
        for e in expected:
            angle=math.radians(e['angle']);x,y=g['origin'];xx,yy=e['origin']
            distance=abs((x-xx)*math.sin(angle)+(y-yy)*math.cos(angle));ds=abs(e['size']-g['size'])
            distances.append((distance+10*ds,distance,ds,e))
        _,distance,ds,e=min(distances,key=lambda a:a[0]);max_size=max(max_size,ds);max_baseline=max(max_baseline,distance)
        tolerance=.005 if e['kind']=='raster-prose'else.0001
        if ds>.001 or distance>tolerance or g['render_type']!=0 or any(g['color']):failures.append({'glyph':g,'expected':e,'baseline_delta_pt':distance,'size_delta_pt':ds})
    return dict(translation_style_violations=failures,translation_size_max_delta_pt=max_size,translation_baseline_max_delta_pt=max_baseline)


def audit(path,scale=4):
    data=json.loads((b.BASE/'slots.json').read_text(encoding='utf8'));source=fitz.open(b.SOURCE);proof=fitz.open(path)
    build=json.loads(path.with_suffix('.build.json').read_text(encoding='utf8'));folder=EN_REPAIR_ROOT/'2022'/'qa'/path.stem if '_EN'in path.stem else b.BASE/'qa'/path.stem;folder.mkdir(parents=True,exist_ok=True)
    report=dict(pdf=str(path.resolve()),sha256=sha(path.read_bytes()),source_sha256=b.SOURCE_SHA,pages=[],passed=True)
    previews=[]
    for pi,page in enumerate(data['pages']):
        original=source[pi];current=proof[pi];erased=[g['origin']for g in b.selected_glyphs(page)];raster=[l for l in build['raster_label_translation']if l['page']==pi+1]
        added=extra_glyphs(original,current);ink=translation_ink_rects(proof,current,added)
        allowed=[[r[0]-.25,r[1]-.25,r[2]+.25,r[3]+.25]for g in b.selected_glyphs(page)for r in[g['bbox']]]+ink
        for label in raster:
            if 'erase_rect'in label:allowed.append(label['erase_rect'])
            else:
                pts=label['erase_polygon'];allowed.append([min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)])
        spec=dict(source_page=pi+1,proof_page=pi+1,allowed_rects=allowed,erased_glyph_origins=erased,
                  protected_glyph_origins=[g['origin']for g in page['native_form_glyphs']])
        (folder/f'page{pi+1:02}-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
        row=preservation.audit(b.SOURCE,path,spec,scale)
        kept=[g for g in preservation.glyphs(original)if not g['c'].isspace()and not any(preservation.close_origin(g['origin'],p)for p in erased)]
        counts=Counter(exact(g)for g in preservation.glyphs(current));missing=[]
        for g in kept:
            if counts[exact(g)]:counts[exact(g)]-=1
            else:missing.append(g)
        row['bit_exact_native_nonspace_glyphs_checked']=len(kept);row['bit_exact_native_nonspace_glyphs_changed']=missing
        old_fonts=original_font_programs(source,original);row['original_font_programs_identical']=old_fonts==original_font_programs(proof,current)
        row['original_font_program_sha256']=old_fonts
        row['original_images_and_smask_streams_identical']=image_programs(source,original)==image_programs(proof,current)
        aa=original.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB);bb=current.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB)
        before=np.frombuffer(aa.samples,np.uint8).reshape(aa.height,aa.width,3);after=np.frombuffer(bb.samples,np.uint8).reshape(bb.height,bb.width,3);difference=np.any(before!=after,axis=2)
        source_labels=label_mask(difference.shape,scale,raster);bitmap=image_ink_mask(source,original,scale=scale)&~source_labels;vectors=vector_ink_mask(original,scale)
        row['changed_pixels_in_native_bitmap_ink_outside_language']=int((difference&bitmap).sum())
        row['changed_pixels_in_native_vector_graphics']=int((difference&vectors).sum())
        changed=(difference&(bitmap|vectors)).astype(np.uint8)
        n,components,stats,centres=cv2.connectedComponentsWithStats(changed,8)
        row['graphic_collision_components']=[dict(rect=[x/scale,y/scale,(x+w)/scale,(y+h)/scale],pixels=int(count))for x,y,w,h,count in stats[1:]]
        row.update(style_checks(added,page,raster))
        row['new_prose_glyphs_checked']=len([g for g in added if not g['c'].isspace()])
        row['unexpected_han']=[g for g in added if re.search('[\u3400-\u9fff]',g['c'])]
        row['native_han_math_labels_retained']=[g for g in kept if re.search('[\u3400-\u9fff]',g['c'])]
        row['unexpected_nul']=[g for g in added if g['c']=='\x00']
        row['passed']=not(row['native_glyphs_changed']or missing or row['protected_glyphs_selected_for_erasure']or row['changed_pixels_outside_prose']
            or row['changed_pixels_in_native_glyph_neighborhood']or row['changed_pixels_in_native_bitmap_ink_outside_language']or row['changed_pixels_in_native_vector_graphics']
            or not row['original_font_programs_identical']or not row['original_images_and_smask_streams_identical']or row['translation_style_violations']or row['unexpected_han']or row['unexpected_nul'])
        report['pages'].append(row);report['passed']&=row['passed']
        (folder/'audit.partial.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        pix=current.get_pixmap(matrix=fitz.Matrix(1.8,1.8),colorspace=fitz.csRGB);image=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);image.save(folder/f'page{pi+1:02}.png');image.thumbnail((595,842));previews.append(image.copy())
        print(path.name,pi+1,'outside',row['changed_pixels_outside_prose'],'native glyph ink',row['changed_pixels_in_native_glyph_neighborhood'],'bitmap',row['changed_pixels_in_native_bitmap_ink_outside_language'],'vector',row['changed_pixels_in_native_vector_graphics'],'exact',len(missing),flush=True)
        del aa,bb,before,after,difference,bitmap,vectors,source_labels,changed,components
        gc.collect();fitz.TOOLS.store_shrink(100)
    contact=Image.new('RGB',(1220,1740),'#ddd')
    for i,image in enumerate(previews):contact.paste(image,((i%2)*610+8,(i//2)*870+20))
    contact.save(folder/'contact.png')
    if '_KO'in path.stem:
        report['hangul_visibility']=visibility.audit(path,scale=scale)
        report['passed']&=not report['hangul_visibility']['unexpected_components']if 'unexpected_components'in report['hangul_visibility']else report['hangul_visibility']['flagged_components']==0
    (folder/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pdf',type=Path);parser.add_argument('--scale',type=int,default=4);args=parser.parse_args();r=audit(args.pdf,args.scale);print('PASSED',r['passed']);raise SystemExit(not r['passed'])
