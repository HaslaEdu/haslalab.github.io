"""Small read-only source CJK-run typeface/physical-size/spread comparison."""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
import pymupdf as fitz
cv2.setNumThreads(1)
SOURCE=Path('tmp/original-style-sources/CPhO_2013_Chinese_original.pdf')
OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/font-calibration')
FONTROOT=Path('D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces')
FONTS=[('SimSun',Path('C:/Windows/Fonts/simsun.ttc')),('KaiTi',FONTROOT/'simkai.ttf'),('FangSong',FONTROOT/'simfang.ttf')]
RUNS=[dict(id='p4-first-ten',page=4,rect=[75,135,184,150],text='设小球每次落地反弹时'),
      dict(id='p4-speed-clause',page=4,rect=[178,135,333,150.2],text='反弹后的竖直速度大小是反弹前的'),
      dict(id='p6-centrifugal-clause',page=6,rect=[76,118,257,133],text='由于地球自转引起的惯性离心力'),
      dict(id='p10-temperature-clause',page=10,rect=[75,520,339,539],text='可见金属盘上、下表面温度的和为常量。由题给数据，有'),
      dict(id='p6-tight-prose',page=6,rect=[78,120,214.2,132],text='由于地球自转引起的惯性离心力',size_range=[9.4,10.01],angles=[-.3,0,.3]),
      dict(id='p10-tilted-prose',page=10,rect=[75,520,339,539],text='可见金属盘上、下表面温度的和为常量。由题给数据，有',size_range=[10.0,10.501],angles=[-.4,-.2,0,.2,.4]),
      dict(id='p10-tight-CJK',page=10,rect=[150,523,258,538],text='下表面温度的和为常量',size_range=[10.0,10.501],angles=[-.3,0,.3])]

def calibrate(run):
    scale=4;OUT.mkdir(parents=True,exist_ok=True)
    with fitz.open(SOURCE)as doc:
        pix=doc[run['page']-1].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=fitz.Rect(run['rect']),colorspace=fitz.csGRAY,alpha=False)
        image=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);source=(image<160).astype(np.float32)
        pix.save(OUT/(run['id']+'-source.png'))
    rows=[]
    for name,font in FONTS:
        doc=fitz.open();page=doc.new_page(width=max(220,len(run['text'])*11.3+10),height=35);page.insert_font(fontname='CompareFace',fontfile=str(font))
        for size in np.arange(*run.get('size_range',[8.8,11.201]),.02):
            xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'');page.set_contents(xref)
            page.insert_text((3,23),run['text'],fontname='CompareFace',fontsize=float(size))
            p=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False)
            mask=(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<128).astype(np.uint8)
            for sx,sy in[(0,0),(1,0),(0,1),(1,1)]:
                grown=cv2.dilate(mask,np.ones((2*sy+1,2*sx+1),np.uint8))
                for angle in run.get('angles',[0]):
                    candidate=grown if not angle else cv2.warpAffine(grown,cv2.getRotationMatrix2D((grown.shape[1]/2,grown.shape[0]/2),angle,1),grown.shape[::-1],flags=cv2.INTER_NEAREST,borderValue=0)
                    yy,xx=np.nonzero(candidate)
                    if not len(xx):continue
                    template=candidate[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
                    if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
                    score=cv2.matchTemplate(source,template,cv2.TM_CCORR);_,intersection,_,point=cv2.minMaxLoc(score)
                    union=float(source.sum()+template.sum()-intersection)
                    rows.append(dict(font=name,size=round(float(size),3),spread_x=sx,spread_y=sy,baseline_angle_degrees=-angle,iou=intersection/union,point=point,
                        template_pixels=[template.shape[1],template.shape[0]],intersection=round(intersection),union=round(union)))
        doc.close()
    rows.sort(key=lambda r:-r['iou']);result=dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        source_run=run,render_scale=scale,source_foreground_pixels=int(source.sum()),top20=rows[:20],best_by_font={name:next(r for r in rows if r['font']==name)for name,_ in FONTS},
        font_files={name:dict(path=str(font),sha256=hashlib.sha256(font.read_bytes()).hexdigest())for name,font in FONTS},
        scope='Only manually verified consecutive original CJK prose. No translated text, mathematical recognition/retyping, resizing, or character-spacing adjustment. Physical source size/spread estimates; not fit-to-translation.')
    (OUT/(run['id']+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(run['id'],json.dumps(result['best_by_font'],ensure_ascii=False),flush=True)
    return result

if __name__=='__main__':
    for run in RUNS:
        report=OUT/(run['id']+'.json')
        if report.exists()and json.loads(report.read_text('utf8'))['source_run']==run:
            print('Verified calibration retained',run['id'],flush=True)
        else:calibrate(run)
