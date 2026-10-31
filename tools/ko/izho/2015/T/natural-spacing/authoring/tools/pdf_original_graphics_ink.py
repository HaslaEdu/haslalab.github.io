"""Check original non-text vector and bitmap ink after prose translation."""
from pathlib import Path
from io import BytesIO
import hashlib,json,math,re
import numpy as np
import cv2
import pymupdf as fitz
import pikepdf
from pdf_original_image_ink import image_programs
from pdf_original_text_ops import replace_show_regions

def graphics_control(doc,page):
    """Read-only non-text control retaining original image clipping and masks.

    A raw SMask can contain ink outside the PDF image's active clip. Projecting
    that alpha plane alone incorrectly protects phantom ink over nearby prose.
    Remove text-show ink in an analysis copy instead, leaving every graphic
    token, nested Form, clipping path and image resource as it was painted.
    """
    source=doc.name if doc.name and Path(doc.name).is_file()else BytesIO(doc.tobytes(garbage=0))
    with pikepdf.Pdf.open(source)as original:
        control=pikepdf.Pdf.new();control.pages.append(original.pages[page.number]);seen=set()
        def strip(node,resources,is_page=False):
            identity=node.obj.objgen if is_page else node.objgen
            if identity in seen:return
            seen.add(identity);replacements={}
            for index,instruction in enumerate(pikepdf.parse_content_stream(node)):
                op=str(instruction.operator)
                if op=='Tr'and int(instruction.operands[0])>=4:raise ValueError('Text clipping requires a separate non-text control profile')
                if op in["'",'"']:raise ValueError('Quoted text-show requires a separate non-text control profile')
                if op in['Tj','TJ']:replacements[index]=pikepdf.ContentStreamInstruction([pikepdf.Array([])],pikepdf.Operator('TJ'))
                if op=='Do':
                    child=resources.get('/XObject',{}).get(instruction.operands[0])
                    if child is not None and str(child.get('/Subtype'))=='/Form':strip(child,child.get('/Resources',resources))
            if is_page:
                raw=replace_show_regions(node,replacements);node.Contents=control.make_stream(raw)
            else:
                # The raw token filter is a Page API. A temporary wrapper
                # exposes this Form stream without rewriting any operands.
                wrapper=control.add_blank_page(page_size=(3,3));wrapper.Contents=node
                raw=replace_show_regions(wrapper,replacements);del control.pages[-1]
                node.write(raw)
        strip(control.pages[0],control.pages[0].Resources,True)
        data=BytesIO();control.save(data,compress_streams=False);control.close()
    return data.getvalue()

def graphics_ink_mask(doc,page,scale=4):
    flat=fitz.open(stream=graphics_control(doc,page),filetype='pdf')
    pix=flat[0].get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
    rgb=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
    mask=cv2.dilate((rgb.min(axis=2)<250).astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    flat.close();return mask

def audit(source_path,proof_path,source_page,proof_page=1,language_regions=(),scale=4):
    source_path=Path(source_path);proof_path=Path(proof_path)
    with fitz.open(source_path)as source,fitz.open(proof_path)as proof:
        a=source[source_page-1];b=proof[proof_page-1]
        if a.rect!=b.rect:raise ValueError('Page boxes changed')
        mask=graphics_ink_mask(source,a,scale)
        for box in language_regions:
            x0,y0,x1,y1=box
            mask[max(0,math.floor(y0*scale)):min(mask.shape[0],math.ceil(y1*scale)),max(0,math.floor(x0*scale)):min(mask.shape[1],math.ceil(x1*scale))]=False
        def pixels(page):
            pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
            return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        changed=np.any(pixels(a)!=pixels(b),axis=2)&mask
        result=dict(source=source_path.name,proof=proof_path.name,source_page=source_page,proof_page=proof_page,scale=scale,
            proof_sha256=hashlib.sha256(proof_path.read_bytes()).hexdigest(),original_graphics_ink_changed_pixels=int(changed.sum()),
            graphics_mask_method='raw-token non-text PDF control; original Form/image clipping and SMask rendering',
            protected_graphics_pixels=int(mask.sum()),explicit_language_regions=[list(r)for r in language_regions],
            original_image_and_smask_programs_and_positions_identical=image_programs(source,a)==image_programs(proof,b))
        if changed.any():
            yy,xx=np.nonzero(changed);result['changed_graphics_bbox']=[float(xx.min()/scale),float(yy.min()/scale),float((xx.max()+1)/scale),float((yy.max()+1)/scale)]
    return result
