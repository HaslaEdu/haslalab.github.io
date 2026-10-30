"""Independent Poppler comparison with explicit prose-suppressed controls."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,subprocess
import numpy as np
import cv2
import pymupdf as fitz
from PIL import Image
import cpho_2023_original_style as b
from pdf_original_text_ops import source_code_bytes,widths,cmap
from pdf_original_style_audit import glyphs,key
import pikepdf

def native_ink_changes(native,final,exceptions):
    actual=(native.min(axis=2)<250)&~exceptions.astype(bool)
    neighborhood=cv2.dilate((native.min(axis=2)<250).astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&~exceptions.astype(bool)
    difference=np.any(native!=final,axis=2)
    changed=difference&actual
    coarse=difference&neighborhood
    return changed,coarse,coarse&~actual

def audit(pdf,scratch,dpi=110):
    pdf=Path(pdf);scratch=Path(scratch);scratch.mkdir(parents=True,exist_ok=True)
    lang='ko'if pdf.stem.endswith('_KO')else'en'
    q=json.loads((b.ROOT/f'tools/ko/cpho/2023/original/qa-{lang}.json').read_text('utf8'))
    assert hashlib.sha256(pdf.read_bytes()).hexdigest()==q['sha256']
    data=json.loads((b.OUT/'slots.json').read_text('utf8'))
    t={k:dict(ko=ko,en=en)for k,ko,en in(x.split('\t')for x in(b.ROOT/'tools/ko/cpho/2023/original-style.tsv').read_text('utf8').splitlines())}
    report=dict(file=pdf.name,sha256=q['sha256'],renderer='Poppler pdftoppm',dpi=dpi,prose_antialias_guard_px=1,pages=[],passed=True,
        native_guard='Actually rendered prose-suppressed PDF, including original native math, clipping, Forms, image masks and Page Group; exclude only reviewed original figure-language regions.')
    def render(path,number,stem):
        out=scratch/stem
        result=subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-r',str(dpi),'-singlefile','-png',str(path),str(out)],capture_output=True,check=True)
        with Image.open(out.with_suffix('.png'))as image:return np.asarray(image.convert('RGB'))
    scale=dpi/72
    for page,row in zip(data['pages'],q['page_audits']):
        number=page['number'];control=scratch/f'{lang}-p{number}-control.pdf'
        selected=[g for s in page['slots']if t[s['id']][lang]!=s['source']for g in s['glyphs']if not g['c'].isspace()]
        raw,_=b.suppress_prose(b.SOURCE,number,selected)
        with fitz.open(stream=raw,filetype='pdf')as doc:
            for box in b.figure_language.audit_spec(number)['source_language_regions']:
                doc[0].draw_rect(fitz.Rect(box),color=None,fill=(1,1,1),overlay=True)
            doc.save(control,garbage=0,deflate=False)
        original=render(b.SOURCE,number,f'source-p{number}')
        native=render(control,1,f'{lang}-p{number}-native')
        final=render(pdf,number,f'{lang}-p{number}-final')
        assert original.shape==native.shape==final.shape
        allowed=np.zeros(original.shape[:2],np.uint8);exceptions=np.zeros_like(allowed)
        def fill(mask,r):
            x0,y0,x1,y1=r;mask[max(0,math.floor(y0*scale)):min(mask.shape[0],math.ceil(y1*scale)),max(0,math.floor(x0*scale)):min(mask.shape[1],math.ceil(x1*scale))]=1
        for box in row['audit_spec']['allowed_rects']:fill(allowed,box)
        # The photo prose is white text over original photographic ink.
        for s in page['slots']:
            if s['id']=='2-8-0':fill(exceptions,s['allowed_rect'])
        for box in b.figure_language.audit_spec(number)['source_language_regions']:fill(exceptions,box)
        changes=np.any(original!=final,axis=2)
        outside=changes&~cv2.dilate(allowed,np.ones((3,3),np.uint8)).astype(bool)
        native_changes,coarse_changes,fringe=native_ink_changes(native,final,exceptions)
        item=dict(page=number,changed_pixels_outside_prose=int(outside.sum()),changed_pixels_in_native_control_ink=int(native_changes.sum()),
            native_control_ink_threshold=250,coarse_one_pixel_neighborhood_changes=int(coarse_changes.sum()),
            coarse_fringe_control_pixels_at_least_250=bool(np.all(native.min(axis=2)[fringe]>=250)),
            raw_outside_prose_antialias_pixels=int((changes&~allowed.astype(bool)).sum()))
        for name,mask in [('native',native_changes),('outside',outside)]:
            if mask.any():
                y,x=np.nonzero(mask);item[name+'_bbox']=[float(x.min()/scale),float(y.min()/scale),float((x.max()+1)/scale),float((y.max()+1)/scale)]
        item['passed']=not outside.any()and not native_changes.any();report['pages'].append(item);report['passed']&=item['passed']
        (b.ROOT/f'tools/ko/cpho/2023/original/qa-poppler-{lang}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
        print(lang,number,'Poppler outside',item['changed_pixels_outside_prose'],'native',item['changed_pixels_in_native_control_ink'],flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf',type=Path);p.add_argument('--scratch',type=Path,required=True);a=p.parse_args();r=audit(a.pdf,a.scratch);raise SystemExit(not r['passed'])
