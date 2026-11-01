"""Read-only source-CJK comparison of actual vector stroke at a fixed source size."""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
import pymupdf as fitz
cv2.setNumThreads(1)
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
SOURCE=Path('tmp/original-style-sources/CPhO_2013_Chinese_original.pdf')
RUNS=[dict(id='p4-first-ten',page=4,rect=[75,135,184,150],text='设小球每次落地反弹时',size=9.78),
      dict(id='p4-speed-clause',page=4,rect=[178,135,333,150.2],text='反弹后的竖直速度大小是反弹前的',size=9.78),
      dict(id='p6-tight-prose',page=6,rect=[78,120,214.2,132],text='由于地球自转引起的惯性离心力',size=9.68)]
RUNS += [dict(id='p4-reference-bold',page=4,rect=[76,123,119.5,135],text='参考解答',size=9.78),
         dict(id='p4-marking-bold',page=4,rect=[80.5,660,124.8,672],text='评分标准',size=10.215)]

def calibrate(run):
    scale=4
    with fitz.open(SOURCE)as doc:
        pix=doc[run['page']-1].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=fitz.Rect(run['rect']),colorspace=fitz.csGRAY)
        source=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<160).astype(np.float32)
    rows=[];doc=fitz.open();page=doc.new_page(width=run['size']*len(run['text'])+12,height=35)
    page.insert_font(fontname='SourceFace',fontfile='C:/Windows/Fonts/simsun.ttc')
    for stroke in[0,.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.7,.8,.9,1.0,1.1]:
        content=doc.get_new_xref();doc.update_object(content,'<<>>');doc.update_stream(content,b'');page.set_contents(content)
        page.insert_text((3,23),run['text'],fontname='SourceFace',fontsize=run['size'],render_mode=2 if stroke else 0,
            border_width=stroke/run['size'],color=(0,0,0),fill=(0,0,0))
        pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
        mask=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<160).astype(np.uint8)
        best=None
        for angle in([0]if run['page']==4 else[-.3,0,.3]):
            candidate=mask if not angle else cv2.warpAffine(mask,cv2.getRotationMatrix2D((mask.shape[1]/2,mask.shape[0]/2),angle,1),mask.shape[::-1],flags=cv2.INTER_NEAREST,borderValue=0)
            yy,xx=np.nonzero(candidate);template=candidate[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
            if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
            _,intersection,_,point=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));union=float(source.sum()+template.sum()-intersection)
            item=dict(line_width_pt=stroke,render_mode=2 if stroke else 0,size_unchanged_pt=run['size'],border_width_argument=stroke/run['size'],rotation_degrees=-angle,iou=intersection/union,point=point,intersection=round(intersection),union=round(union),template_pixels=int(template.sum()))
            if best is None or item['iou']>best['iou']:best=item
        if best:rows.append(best)
    doc.close()
    rows.sort(key=lambda x:-x['iou'])
    report=dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_run=run,source_font='SimSun5.24 face0',render_scale=4,mask_threshold=160,
        no_size_or_width_fitting=True,no_dilation=True,actual_PDF_Tr2_stroke=True,results=rows,scope='Estimate printed raster weight from original known CJK only, before applying any translated prose.')
    path=BASE/'font-calibration'/(run['id']+'-actual-stroke.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print(run['id'],json.dumps(rows[:3]),'Tr0',next(r for r in rows if not r['line_width_pt'])['iou'],flush=True)

if __name__=='__main__':
    for run in RUNS:
        path=BASE/'font-calibration'/(run['id']+'-actual-stroke.json')
        if path.exists()and json.loads(path.read_text('utf8'))['source_run']==run:continue
        calibrate(run)
