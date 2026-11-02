"""Original-only fixed-family size/stroke survey for a visibly distinct scan run."""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
import pymupdf as fitz
cv2.setNumThreads(1)
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
SOURCE=Path('tmp/original-style-sources/CPhO_2013_Chinese_original.pdf')

def compare():
    run=dict(id='p4-marking-prefix-joint',page=4,rect=[80.5,660,124.8,672],text='评分标准')
    with fitz.open(SOURCE)as original:
        pix=original[3].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(run['rect']),colorspace=fitz.csGRAY)
        source=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<160).astype(np.float32)
    rows=[];doc=fitz.open();page=doc.new_page(width=60,height=35);page.insert_font(fontname='SourceFace',fontfile='C:/Windows/Fonts/simsun.ttc')
    for size in np.arange(9.1,10.401,.04):
        for stroke in [.3,.4,.45,.5,.55,.6,.65,.7,.8]:
            content=doc.get_new_xref();doc.update_object(content,'<<>>');doc.update_stream(content,b'');page.set_contents(content)
            page.insert_text((3,23),run['text'],fontname='SourceFace',fontsize=float(size),render_mode=2,border_width=stroke/size,color=(0,0,0),fill=(0,0,0))
            p=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csGRAY);mask=(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<160).astype(np.float32)
            yy,xx=np.nonzero(mask);template=mask[yy.min():yy.max()+1,xx.min():xx.max()+1]
            if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
            _,intersection,_,point=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));union=float(source.sum()+template.sum()-intersection)
            rows.append(dict(size=round(float(size),3),line_width=stroke,iou=intersection/union,point=point,baseline=23-int(yy.min())/4+pix.y/4+point[1]/4))
    doc.close();rows.sort(key=lambda v:-v['iou'])
    report=dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_run=run,font='SimSun5.24',mask_threshold=160,scale=4,top20=rows[:20],translated_text_used=False,no_character_width_adjustment=True)
    path=BASE/'font-calibration'/(run['id']+'.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(rows[:4]),flush=True)

if __name__=='__main__':compare()
