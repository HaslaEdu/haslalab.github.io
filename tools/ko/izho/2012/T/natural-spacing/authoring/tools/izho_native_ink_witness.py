"""Narrow diagnostic for one SVG/native-font raster phase sample; no proof edits."""
from pathlib import Path
import json,hashlib
import numpy as np
import pikepdf
import pymupdf as fitz
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import reposition_inline,_traces
from pdf_native_glyph_promote import promote_native_glyphs
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_original_text_ops import glyph_key
from izho_natural_spacing import BUILD

def rgb(path,scale=4):
    with fitz.open(path)as d:
        p=d[0].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
        return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()

def main():
    folder=BUILD/'2026/T';old=folder/'page08.old-source.pdf';target=folder/'page08.pdf';out=folder/'e-phase-witness';out.mkdir(exist_ok=True)
    with fitz.open(old)as src,fitz.open(target)as dst:
        assert not src[0].get_image_info()and not dst[0].get_image_info()
        assert not any(d['rect'].intersects(fitz.Rect(375,294,395,309))for d in src[0].get_drawings())
        assert not any(d['rect'].intersects(fitz.Rect(360,294,378,309))for d in dst[0].get_drawings())
        glyph=next(g for g in _traces(src[0])if g['c']=='e'and g['trace_gid']==135 and abs(g['origin'][1]-304.37)<.01)
        new=next(g for g in _traces(dst[0])if g['c']=='e'and g['trace_gid']==135 and abs(g['origin'][1]-304.37)<.01)
    dx=new['origin'][0]-glyph['origin'][0]
    moved,moveqa=reposition_inline(old,1,shifts=[dict(glyphs=[glyph],dx=dx)]);moved_path=out/'source-native-e-requested-x.pdf';moved_path.write_bytes(moved)
    promoted,promoteqa=promote_native_glyphs(moved,1,[dict(glyph,origin=new['origin'])])
    with fitz.open(stream=promoted,filetype='pdf')as doc:
        unwanted=[g for g in _traces(doc[0])if g['c'].strip()and not(g['c']=='e'and g['trace_gid']==135 and abs(g['origin'][0]-new['origin'][0])<.001 and abs(g['origin'][1]-new['origin'][1])<.001)]
    reference,eraseqa=reposition_inline(promoted,1,erased_glyphs=unwanted)
    reference_path=out/'source-native-cid-e-only.pdf';reference_path.write_bytes(reference)
    a=rgb(reference_path);b=rgb(target);area=np.zeros(a.shape[:2],bool)
    area[294*4:309*4,360*4:378*4]=True;dark=area&(a.min(axis=2)<32)
    missing=int((dark&(b.min(axis=2)>=220)).sum())
    crop_old=out/'source-crop.pdf';crop_final=out/'final-crop.pdf'
    for source,dest in[(old,crop_old),(target,crop_final)]:
        with pikepdf.open(source)as pdf:
            h=float(pdf.pages[0].MediaBox[3]);pdf.pages[0].CropBox=pikepdf.Array([350,h-315,400,h-290]);pdf.save(dest,compress_streams=False)
    with fitz.open(crop_old)as doc:
        cropped=next(g for g in _traces(doc[0])if g['c']=='e'and g['trace_gid']==135 and abs(g['origin'][1]-14.37)<.01)
    scales={}
    for scale in[4,8,12]:
        scales[str(scale)]=audit_moved_native_ink(crop_old,1,crop_final,shifts=[dict(glyphs=[cropped],dx=dx)],protected_glyphs=[cropped],scale=scale)
    report=dict(proof_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),proof_unmodified=True,
        scope='CambriaMath original native e, GID135, unit mole; no source/final images and no non-text vector paint near either glyph position.',
        source_glyph=glyph,actual_target_glyph=new,requested_dx=dx,original_encoded_cid_reference=promoteqa,
        reference_sha256=hashlib.sha256(reference).hexdigest(),native_reference_dark_pixels=int(dark.sum()),
        native_cid_reference_missing_pixels=missing,svg_reference_scales=scales,
        passed=missing==0 and promoteqa['passed']and moveqa['passed']and eraseqa['passed'])
    path=out/'witness.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(dict(path=str(path),native_cid_missing=missing,scales={k:v.get('newly_missing_native_ink_pixels')for k,v in scales.items()},passed=report['passed']),ensure_ascii=False))

if __name__=='__main__':
    with page_worker():main()
