"""Independent Poppler actual-control-ink check for the original2005 T.

Raw prose antialias fringes are recorded separately from actual native ink.
No native/math/figure pixels or explicit exceptions are excluded.
"""
from pathlib import Path
import json,hashlib,math,subprocess,os
import cv2,numpy as np,pymupdf as fitz
from PIL import Image
import cpho_2005_original_build as b
import cpho_2005_original_qa as q


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit():
    root=b.BASE/'poppler';rows=[];source=fitz.open(b.source.SOURCE)
    for number in [1,2,3]:
        prefix=root/f'control-{number}'
        subprocess.run(['pdftoppm','-png','-r','144','-singlefile',str(b.BASE/'ko'/f'page{number:02}.control.pdf'),str(prefix)],
            check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
    for lang in ['ko','en']:
        path=b.BASE.parent/f'CPhO_2005_T_{lang.upper()}.pdf'
        with fitz.open(path)as final:
            for i in range(3):
                with Image.open(root/f'source-{i+1:02}.png')as image:original=np.array(image.convert('RGB'))
                with Image.open(root/f'control-{i+1}.png')as image:native=np.array(image.convert('RGB'))
                with Image.open(root/lang/f'page-{i+1}.png')as image:current=np.array(image.convert('RGB'))
                if original.shape!=native.shape or native.shape!=current.shape:raise ValueError('Poppler page size changed')
                picked=q.selected(b.data()['pages'][i]);allowed=np.zeros(original.shape[:2],np.uint8)
                rects=[[g['bbox'][0]-.25,g['bbox'][1]-.25,g['bbox'][2]+.25,g['bbox'][3]+.25]for g in picked]
                rects+=q.translation_ink_rects(final,final[i],q.extra_glyphs(source[i],final[i]))
                for box in rects:
                    r=fitz.Rect(box);allowed[max(0,math.floor(r.y0*2)):min(allowed.shape[0],math.ceil(r.y1*2)),
                        max(0,math.floor(r.x0*2)):min(allowed.shape[1],math.ceil(r.x1*2))]=1
                diff=np.any(original!=current,axis=2);suppressed=np.any(original!=native,axis=2);new=np.any(native!=current,axis=2)
                actual=native.min(axis=2)<250
                guard=cv2.dilate(actual.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
                raw_outside=diff&~allowed.astype(bool)
                outside=diff&~cv2.dilate(allowed,np.ones((3,3),np.uint8)).astype(bool)
                row=dict(language=lang,page=i+1,source_sha256=b.source.SOURCE_SHA,final_sha256=sha(path),
                    suppression_control_sha256=sha(b.BASE/'ko'/f'page{i+1:02}.control.pdf'),
                    raw_changed_pixels_outside_prose=int(raw_outside.sum()),prose_antialias_guard_px=1,
                    changed_pixels_outside_prose_aa_guard=int(outside.sum()),
                    changed_original_actual_control_ink_pixels=int((diff&actual).sum()),
                    source_to_control_actual_native_ink_changes=int((suppressed&actual).sum()),
                    new_translation_on_actual_native_ink_pixels=int((new&actual).sum()),
                    coarse_control_one_pixel_neighborhood_changes=int((new&guard).sum()),
                    explicit_native_pixel_exclusions=[])
                for name,mask in [('outside',outside),('native',new&actual),('suppression',suppressed&actual)]:
                    if mask.any():
                        yy,xx=np.nonzero(mask);row[name+'_bbox']=[float(xx.min()/2),float(yy.min()/2),float((xx.max()+1)/2),float((yy.max()+1)/2)]
                row['passed']=not(outside.any()or(diff&actual).any()or(suppressed&actual).any()or(new&actual).any())
                rows.append(row);print(json.dumps(row),flush=True)
    source.close()
    report=dict(renderer='Poppler pdftoppm,144dpi',actual_native_ink_threshold=250,
        method='Actually rendered prose-suppressed PDF including original math, fonts, clipping, Form/Image masks and Page Group; no native exceptions.',
        pages=rows,passed=all(r['passed']for r in rows))
    (b.AUTHOR/'T-poppler-control-ink-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    return report


if __name__=='__main__':raise SystemExit(not audit()['passed'])
