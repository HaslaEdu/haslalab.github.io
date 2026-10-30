"""Translate only language ink within the three original 2022 bitmap figures.

Every original image/SMask byte, mathematical label and diagram shape stays
in the PDF. White vector overlays cover measured Chinese-language regions
only. Raster typography has no font metadata: nominal Song-family sizes are
inferred against the same document's native Song outlines and recorded.
"""
from pathlib import Path
import json,math
import numpy as np
import cv2
import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
AUTHOR=ROOT/'tools/ko/cpho/2022/original'
BASE=ROOT/'tmp/original-style-repair/2022/labels'
SOURCE=ROOT/'tmp/source-audit/CPhO_2022_T_ZH.pdf'
RECIPES=[
 ('fel-accelerator',2,'fel',[122,14,379,68],'电子束加速器','전자빔 가속기','Electron-beam accelerator',10.15,'left'),
 ('fel-collector',2,'fel',[853,14,1063,68],'电子束收集','전자빔 수집기','Electron-beam collector',10.15,'right'),
 ('fel-beam-left',2,'fel',[148,150,279,205],'电子束','전자빔','e-beam',10.15,'center'),
 ('fel-beam-right',2,'fel',[928,150,1057,205],'电子束','전자빔','e-beam',10.15,'center'),
 ('fel-bender-left',2,'fel',[129,292,302,343],'弯曲磁体','편향자석','Bend mag',10.15,'right'),
 ('fel-bender-right',2,'fel',[941,292,1110,343],'弯曲磁体','편향자석','Bend mag',10.15,'center'),
 ('fel-mirror-left',2,'fel',[18,370,196,421],'谐振腔镜','공진기 거울','Cavity mirror',10.15,'center'),
 ('fel-mirror-right',2,'fel',[1090,370,1270,421],'谐振腔镜','공진기 거울','Cavity mirror',10.15,'center'),
 ('fel-undulator',2,'fel',[563,407,698,455],'扭摆器','언듈레이터','Undulator',10.15,'center'),
 ('fel-laser',2,'fel',[1192,216,1287,268],'激光','레이저','Laser',10.15,'center'),
 ('diffraction-laser',3,'diffraction',[24,241,79,352],'激光','레이저','Laser',11.6,'vertical'),
 ('crystal-air',3,'crystal',[690,142,789,193],'空气','공기','Air',10.67,'right'),
 ('crystal-body',3,'crystal',[690,204,789,255],'晶体','결정','Crystal',10.67,'right'),
 ('crystal-axis',3,'crystal',[65,365,160,414],'光轴','광축','Opt. ax.',10.67,'right'),
]
PANELS={'fel':(2,[132.3,375.15,459.3,537.15]),
        'diffraction':(3,[364.05,44.4,555.45,189]),
        'crystal':(3,[360.9,368.7,561.3,510.9])}


def prepare():
    cv2.setNumThreads(1);doc=fitz.open(SOURCE);panels={};labels=[];BASE.mkdir(parents=True,exist_ok=True)
    for name,(number,rect)in PANELS.items():
        pix=doc[number-1].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(rect),colorspace=fitz.csRGB)
        pixels=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        panels[name]=(pixels,np.array([pix.x/4,pix.y/4]))
    for name,number,panel,roi,source,ko,en,size,align in RECIPES:
        pixels,origin=panels[panel];x0,y0,x1,y1=roi;yy,xx=np.nonzero(pixels[y0:y1,x0:x1].min(axis=2)<180)
        if not len(xx):raise ValueError('Empty source language ink: '+name)
        ink=np.array([x0+xx.min(),y0+yy.min(),x0+xx.max()+1,y0+yy.max()+1])/4+np.tile(origin,2)
        erase=ink+np.array([-.5,-.5,.5,.5]);baseline=float(ink[3]-.7*size/10.15)
        labels.append(dict(id=name,page=number,source=source,ko=ko,en=en,size=size,align=align,
            source_ink_rect=ink.tolist(),erase_rect=erase.tolist(),baseline=baseline,
            inferred_font_family='Song/SimSun serif',font_metadata_available=False))
    # The diagonal word is isolated from the adjacent ray and lattice.
    pixels,origin=panels['diffraction'];polygon=np.array([[530,156],[610,28],[653,63],[573,180]],np.int32)
    mask=np.zeros(pixels.shape[:2],np.uint8);cv2.fillPoly(mask,[polygon],1)
    yy,xx=np.nonzero((pixels.min(axis=2)<180)&mask.astype(bool));points=np.column_stack([xx,yy]).astype(np.float32)
    rotated=cv2.minAreaRect(points);corners=cv2.boxPoints(rotated);edges=[corners[(i+1)%4]-corners[i]for i in range(4)]
    vector=max(edges,key=np.linalg.norm)
    if vector[0]<0:vector=-vector
    unit=vector/np.linalg.norm(vector);down=np.array([-unit[1],unit[0]])
    along=points@unit;across=points@down
    lo,hi=along.min(),along.max();top,bottom=across.min(),across.max()
    erase=np.array([unit*(lo-1.6)+down*(top-1.6),unit*(hi+1.6)+down*(top-1.6),
                    unit*(hi+1.6)+down*(bottom+1.6),unit*(lo-1.6)+down*(bottom+1.6)])/4+origin
    anchor=(unit*(lo-.8)+down*(bottom-2.8))/4+origin
    labels.append(dict(id='diffraction-outgoing',page=3,source='衍射光',ko='회절광',en='Diffracted light',size=11.6,
        align='rotated',angle=float(math.degrees(math.atan2(-unit[1],unit[0]))),origin=anchor.tolist(),
        erase_polygon=erase.tolist(),source_ink_rect=[float(xx.min()/4+origin[0]),float(yy.min()/4+origin[1]),float((xx.max()+1)/4+origin[0]),float((yy.max()+1)/4+origin[1])],
        inferred_font_family='Song/SimSun serif',font_metadata_available=False))
    data={'source':'CPhO_2022_T_ZH.pdf','labels':labels,'font_inference':[
        {'panel':'fel','native_comparison':'Same-document Song 电 at 10.56 pt: actual outline height 9.36375 pt. Raster 电 is 9.00 pt at 4x; inferred 10.14978 pt, used 10.15 pt.'},
        {'panel':'diffraction','native_comparison':'Same-document Song 光 at 10.56 pt: actual outline height 9.57000 pt. Raster 光 is 10.50 pt at 4x; inferred 11.58621 pt, used 11.60 pt.'},
        {'panel':'crystal','native_comparison':'Same-document Song 空 at 10.56 pt: actual outline height 9.15750 pt. Raster 空 is 9.25 pt at 4x; inferred 10.66667 pt, used 10.67 pt.'}],
        'limits':'Raster fonts have no recoverable font program/size/baseline metadata; matching uses source ink, serif structure and measured orientation. No diagram geometry or image stream is edited.'}
    (AUTHOR/'raster-labels.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');doc.close();return data


def data():return json.loads((AUTHOR/'raster-labels.json').read_text(encoding='utf8'))


def apply(doc,lang,font_file,pages):
    labels=data()['labels'];font=fitz.Font(fontfile=str(font_file));report=[]
    for label in labels:
        if label['page']not in pages:continue
        page=doc[pages.index(label['page'])];text=label[lang];size=label['size'];name='TranslationRasterSerif'
        alignment='center'if lang=='en'and label['id']=='fel-bender-left'else label['align']
        if 'erase_polygon'in label:
            points=[fitz.Point(*p)for p in label['erase_polygon']];page.draw_polyline(points+[points[0]],color=None,fill=(1,1,1),width=0,closePath=True)
        else:page.draw_rect(fitz.Rect(label['erase_rect']),color=None,fill=(1,1,1),width=0)
        runs=[]
        if alignment=='rotated':
            x,y=label['origin'];angle=label['angle'];runs=[dict(text=text,origin=[x,y],angle=angle)]
        elif alignment=='vertical':
            box=fitz.Rect(label['source_ink_rect']);cx=(box.x0+box.x1)/2;cy=(box.y0+box.y1)/2
            if lang=='en':
                width=font.text_length(text,fontsize=size);runs=[dict(text=text,origin=[cx+size*.3,cy+width/2],angle=90)]
            else:
                leading=size*1.04;top=cy-(len(text)-1)*leading/2+size*.36
                runs=[dict(text=c,origin=[cx-font.text_length(c,fontsize=size)/2,top+i*leading],angle=0)for i,c in enumerate(text)]
        else:
            box=fitz.Rect(label['source_ink_rect']);width=font.text_length(text,fontsize=size)
            if alignment=='left':x=box.x0
            elif alignment=='right':x=box.x1-width
            else:x=(box.x0+box.x1-width)/2
            runs=[dict(text=text,origin=[x,label['baseline']],angle=0)]
        for run in runs:
            point=fitz.Point(*run['origin']);angle=run['angle'];kwargs={'morph':(point,fitz.Matrix(angle))}if angle else{}
            page.insert_text(point,run['text'],fontname=name,fontfile=str(font_file),fontsize=size,color=(0,0,0),**kwargs)
        report.append({**label,'language':lang,'text':text,'runs':runs,'effective_alignment':alignment})
    return report


if __name__=='__main__':print('Prepared',len(prepare()['labels']),'raster-language labels')
