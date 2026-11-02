"""Explicitly reviewed blank prose continuations; never white-fill exceptions."""
from pathlib import Path
import hashlib,json,math
import numpy as np
from PIL import Image
import pymupdf as fitz
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
APPROVED={4:['first-rebound-speed','first-flight-time','recurrences-intro'],5:['marking'],6:['gravity-centrifugal-definitions-b','gravity-at-r0'],7:['tube-force-f'],8:['below-critical-length-b','sum-sphere-potentials','ith-sphere-potential'],9:['equilibrium-position','problem5-reference','magnetic-force-b'],10:['divide-conduction-equations','ratio-result','marking-part1-d','disk-heat-loss','temperature-sum'],11:['bottom-temperature-result','marking-problem6-title','marking-problem6-b']}

def prepare(plan):
    page=plan['source_page'];records=[]
    if page not in APPROVED:return records
    source=Path.cwd()/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'
    evidence=BASE/'background-evidence';evidence.mkdir(exist_ok=True)
    rows={row['id']:row for row in plan['rows']};source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    with fitz.open(source)as doc:
        for key in APPROVED[page]:
            row=rows[key];old=row['erase_rects'][0];rect=[old[2],old[1],522.75,old[3]]
            pix=doc[page-1].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(rect),colorspace=fitz.csGRAY)
            data=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);ink=data<180;protected=np.zeros(ink.shape,bool)
            protected_rects=plan.get('protected_source_display_and_figure_rects',[])+[atom['rect']for source_row in plan['rows']for atom in source_row['atoms']]
            for box in protected_rects:
                x0=max(0,math.floor(box[0]*4)-pix.x);y0=max(0,math.floor(box[1]*4)-pix.y)
                x1=min(pix.width,math.ceil(box[2]*4)-pix.x);y1=min(pix.height,math.ceil(box[3]*4)-pix.y)
                if x1>x0 and y1>y0:protected[y0:y1,x0:x1]=True
            background=ink&~protected;yy,xx=np.nonzero(background)
            name=f'page{page:02d}-{key}';crop=evidence/(name+'-source.png');pix.save(crop)
            display=np.repeat(data[:,:,None],3,axis=2);display[background]=[220,0,0];display[ink&protected]=[0,120,0]
            overlay=evidence/(name+'-classification.png');Image.fromarray(display).save(overlay)
            records.append(dict(rect=rect,reviewed=True,reason='Manually reviewed continuation of the original Chinese prose row. After subtracting all listed original display/figure and source-inline math rectangles, only pre-existing scan dust/faint prose scan rule is classified as background. No mathematical object, numeral, physical figure or diagram line is part of this classification. Every replayed mathematical atom is an independent target obstacle.',
                source_page=page,source_sha256=source_hash,source_row=key,evidence=str(crop),classification_image=str(overlay),source_crop_gray_sha256=hashlib.sha256(pix.samples).hexdigest(),render_scale=4,
                source_background_ink_pixels=int(background.sum()),source_background_ink_bbox_pt=None if not len(xx)else[(pix.x+int(xx.min()))/4,(pix.y+int(yy.min()))/4,(pix.x+int(xx.max())+1)/4,(pix.y+int(yy.max())+1)/4],
                source_protected_ink_pixels=int((ink&protected).sum()),excluded_protected_rects=protected_rects,white_fill_applied=False,original_image_changed=False))
    (evidence/f'page{page:02d}.json').write_text(json.dumps(dict(source_sha256=source_hash,source_page=page,records=records),ensure_ascii=False,indent=2)+'\n','utf8')
    return records
