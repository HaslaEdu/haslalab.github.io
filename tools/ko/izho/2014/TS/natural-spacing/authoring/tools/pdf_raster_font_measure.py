"""Read-only glyph measurements for fixed-baseline scanned-text translation.

The source bitmap has no font program/size/baseline metadata. A manually
isolated, named glyph is compared with an explicit native or external font
outline. The result is an estimate made before translation, never a fit-to-box
font size. Original pixel data and PDF image drawing operators are untouched.
"""
from pathlib import Path
from io import BytesIO
import hashlib,re
import numpy as np
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from pdf_original_image_ink import resolved_images

def sha(data):return hashlib.sha256(data).hexdigest()
def family(value):return re.sub(r'^[A-Z]{6}\+','',value)

def reference_outline(char,*,reference_pdf=None,reference_page=1,font_alias=None,origin=None,font_path=None,face_index=0):
    if len(char)!=1:raise ValueError('One manually identified reference character is required')
    if reference_pdf is not None:
        if font_path is not None or not font_alias:raise ValueError('Native reference requires a font alias, not an external font')
        path=Path(reference_pdf)
        with fitz.open(path)as doc:
            page=doc[reference_page-1];records=[r for r in page.get_fonts(full=True)if r[4]==font_alias]
            if len(records)!=1:raise ValueError('Native reference font alias is not unique')
            record=records[0];raw=doc.extract_font(record[0])[3]
            if not raw:raise ValueError('Native reference font is unembedded; provide an explicit external reference instead')
            candidates=[]
            for span in page.get_texttrace():
                if family(span['font'])!=family(record[3]):continue
                for cp,gid,point,box in span['chars']:
                    if chr(cp)!=char or gid<0:continue
                    if origin is not None and any(abs(a-b)>.0001 for a,b in zip(point,origin)):continue
                    item=dict(gid=gid,size=span['size'],origin=list(point))
                    if item not in candidates:candidates.append(item)
            if not candidates:raise ValueError('Named reference glyph not found in the original trace')
            picked=candidates[0]
            if origin is not None and len(candidates)!=1:raise ValueError('Reference glyph origin is ambiguous')
        font=TTFont(BytesIO(raw),fontNumber=face_index)
        name=font.getGlyphOrder()[picked['gid']]
        provenance=dict(kind='embedded native source glyph',reference_pdf=str(path),reference_pdf_sha256=sha(path.read_bytes()),
            source_page=reference_page,font_alias=font_alias,font_name=record[3],font_program_sha256=sha(raw),
            native_gid=picked['gid'],native_size_pt=picked['size'],native_origin_pt=picked['origin'])
    else:
        if font_path is None:raise ValueError('An explicit native or external reference font is required')
        path=Path(font_path);raw=path.read_bytes();font=TTFont(BytesIO(raw),fontNumber=face_index)
        name=font.getBestCmap().get(ord(char))
        if name is None:raise ValueError('The external reference font has no requested glyph')
        provenance=dict(kind='explicit external reference font; original face is not recovered',font_path=str(path),
            font_file_sha256=sha(raw),face_index=face_index,font_name=font['name'].getDebugName(6))
    glyphs=font.getGlyphSet();pen=BoundsPen(glyphs);glyphs[name].draw(pen)
    if pen.bounds is None:raise ValueError('The reference glyph has no visible outline')
    provenance.update(character=char,glyph_name=name,units_per_em=font['head'].unitsPerEm,outline_bounds_units=list(pen.bounds),
        reference_weight_class=font['OS/2'].usWeightClass if'OS/2'in font else None)
    font.close();return provenance

def measure(source_path,source_page_1based,image_index,pixel_rect,reference_char,*,reference_pdf=None,reference_page=1,
            reference_font_alias=None,reference_origin=None,reference_font_path=None,face_index=0,threshold=180):
    if not 0<threshold<255:raise ValueError('Invalid source ink threshold')
    path=Path(source_path)
    with fitz.open(path)as doc:
        info=resolved_images(doc,doc[source_page_1based-1])[image_index]
        a,b,c,d,e,f=info['transform']
        if abs(b)>1e-6 or abs(c)>1e-6 or a<=0 or d<=0:raise ValueError('Rotated/skewed image measurement needs a reviewed axis profile')
        pix=fitz.Pixmap(doc,info['xref'])
        if pix.colorspace is None:raise ValueError('Source language image is not a colour/grey bitmap')
        if pix.colorspace.n not in [1,3]:pix=fitz.Pixmap(fitz.csRGB,pix)
        data=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)
        values=data[:,:,:pix.colorspace.n].min(axis=2)
        rect=list(pixel_rect)
        if len(rect)!=4 or any(type(v)is not int for v in rect):raise ValueError('Manual glyph ROI uses integer original-image pixel edges')
        x0,y0,x1,y1=rect
        if not 0<=x0<x1<=pix.width or not 0<=y0<y1<=pix.height:raise ValueError('Glyph ROI lies outside the original image')
        mask=values[y0:y1,x0:x1]<threshold
        smask=doc.extract_image(info['xref']).get('smask')
        if smask:
            alpha=fitz.Pixmap(doc,smask)
            if(alpha.width,alpha.height)!=(pix.width,pix.height):raise ValueError('Differently sized SMask needs a reviewed measurement profile')
            plane=np.frombuffer(alpha.samples,np.uint8).reshape(alpha.height,alpha.width,alpha.n)[:,:,0]
            mask&=plane[y0:y1,x0:x1]>127
        if not mask.any():raise ValueError('Manual source glyph ROI is empty')
        if mask[0].any()or mask[-1].any()or mask[:,0].any()or mask[:,-1].any():raise ValueError('Manual glyph ROI clips ink or includes a neighbouring glyph')
        yy,xx=np.nonzero(mask);ink=[x0+int(xx.min()),y0+int(yy.min()),x0+int(xx.max())+1,y0+int(yy.max())+1]
        physical=[e+a*ink[0]/pix.width,f+d*ink[1]/pix.height,e+a*ink[2]/pix.width,f+d*ink[3]/pix.height]
        image_sha=sha(doc.extract_image(info['xref'])['image'])
    reference=reference_outline(reference_char,reference_pdf=reference_pdf,reference_page=reference_page,font_alias=reference_font_alias,
        origin=reference_origin,font_path=reference_font_path,face_index=face_index)
    left,bottom,right,top=reference['outline_bounds_units'];units=reference['units_per_em']
    size=(physical[3]-physical[1])*units/(top-bottom)
    baseline=physical[3]+bottom*size/units
    origin_x=physical[0]-left*size/units
    return dict(method='manually isolated source bitmap glyph vs explicit font outline',is_estimate=True,
        source_pdf=str(path),source_pdf_sha256=sha(path.read_bytes()),source_page=source_page_1based,image_index=image_index,
        source_image_sha256=image_sha,source_image_dimensions_px=[pix.width,pix.height],source_image_ctm=list(info['transform']),
        reviewed_character=reference_char,manual_roi_pixels=rect,ink_threshold=threshold,source_ink_pixels=ink,
        source_ink_rect_pt=physical,reference=reference,inferred_size_pt_unrounded=size,size=round(size,2),
        inferred_baseline_pt=baseline,inferred_character_origin_pt=[origin_x,baseline],
        source_glyph_ink_density=float(mask.sum()/((ink[2]-ink[0])*(ink[3]-ink[1]))),
        limitations='Bitmap font face, weight, original point size and baseline metadata are unavailable; these values are measured estimates. No translation text enters this calculation.')
