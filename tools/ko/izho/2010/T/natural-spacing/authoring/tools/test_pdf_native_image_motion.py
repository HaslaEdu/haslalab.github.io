"""Synthetic rendered-ink tests for original zero-glyph math instances."""
from io import BytesIO
from pathlib import Path
import json
import numpy as np
import pikepdf
import pymupdf as fitz
from pdf_native_inline_reposition import reposition_inline,inspect_inline_groups

OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/native-inline-prototype/image-regression')


def source(program,form=False):
    pdf=pikepdf.Pdf.new();p=pdf.add_blank_page(page_size=(200,200))
    alpha=np.zeros((12,12),np.uint8);alpha[2:10,2:4]=255;alpha[8:10,2:10]=255
    mask=pdf.make_stream(alpha.tobytes());mask.Type=pikepdf.Name.XObject;mask.Subtype=pikepdf.Name.Image
    mask.Width=12;mask.Height=12;mask.ColorSpace=pikepdf.Name.DeviceGray;mask.BitsPerComponent=8
    im=pdf.make_stream(bytes(4));im.Type=pikepdf.Name.XObject;im.Subtype=pikepdf.Name.Image
    im.Width=2;im.Height=2;im.ColorSpace=pikepdf.Name.DeviceGray;im.BitsPerComponent=8;im.SMask=mask
    p.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=im))
    if form:
        f=pdf.make_stream(b'q 12 0 0 12 0 0 cm /Im Do Q');f.Type=pikepdf.Name.XObject;f.Subtype=pikepdf.Name.Form
        f.BBox=pikepdf.Array([0,0,12,12]);f.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=im))
        p.Resources.XObject.F=f
    p.Contents=pdf.make_stream(program);s=BytesIO();pdf.save(s,compress_streams=False);pdf.close();return s.getvalue()


def pixels(raw):
    with fitz.open(stream=raw,filetype='pdf')as d:
        p=d[0].get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
        return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()


def main():
    OUT.mkdir(parents=True,exist_ok=True);reports=[]
    for name,program,form in[
        ('direct image',b'q 12 0 0 12 40 100 cm /Im Do Q q 12 0 0 12 120 100 cm /Im Do Q',False),
        ('complete image clip',b'q 39 99 14 14 re W n q 12 0 0 12 40 100 cm /Im Do Q Q q 12 0 0 12 120 100 cm /Im Do Q',False),
        ('pure bitmap Form',b'q 1 0 0 1 40 100 cm /F Do Q q 1 0 0 1 120 100 cm /F Do Q',True)]:
        raw=source(program,form);inv=inspect_inline_groups(raw,1)
        if form:
            target=next(f for f in inv['forms']if f['native_page_bbox'][0]<100);kwargs=dict(form_path=target['path'])
        else:
            target=next(i for i in inv['images']if i['bbox'][0]<100);kwargs=dict(image_path=target['path'])
        moved,qa=reposition_inline(raw,1,shifts=[dict(glyphs=[],dx=8,**kwargs)])
        a,b=pixels(raw),pixels(moved)
        delta=int(np.any(a[340:420,140:240]!=b[340:420,172:272],axis=2).sum())
        changed=np.any(a!=b,axis=2);changed[340:420,140:272]=False
        assert qa['passed']and qa['original_image_streams_unchanged']and delta==0 and not changed.any()
        reports.append(dict(case=name,qa=qa,translated_actual_pixels_differ=delta,other_pixels_changed=int(changed.sum())))
        (OUT/(name.replace(' ','-')+'.pdf')).write_bytes(moved)
        if form:
            nested=next(i for i in inv['images']if i['bbox'][0]<100)
            try:reposition_inline(raw,1,shifts=[dict(glyphs=[],image_path=nested['path'],dx=8)])
            except ValueError as e:assert 'complete original Form'in str(e)
            else:raise AssertionError('A partial nested math image bypassed its Form/BBox')
    raw=source(b'q 39 99 30 14 re W n q 12 0 0 12 40 100 cm /Im Do Q q 12 0 0 12 55 100 cm /Im Do Q Q')
    target=inspect_inline_groups(raw,1)['images'][0]
    try:reposition_inline(raw,1,shifts=[dict(glyphs=[],image_path=target['path'],dx=40)])
    except ValueError as e:assert 'unchanged source clip'in str(e)
    else:raise AssertionError('Partial image selection silently escaped its unchanged clip')
    reports.append(dict(case='partial image clip escape and partial nested Form rejected',passed=True))
    path=OUT/'report.json';path.write_text(json.dumps(dict(passed=True,cases=reports),indent=2),'utf8')
    print(json.dumps(dict(passed=True,cases=len(reports),report=str(path))))


if __name__=='__main__':main()
