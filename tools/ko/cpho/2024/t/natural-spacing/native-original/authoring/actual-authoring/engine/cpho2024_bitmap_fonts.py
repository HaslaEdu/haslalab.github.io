"""Measure original Chinese bitmap labels against actual font programs.

The source Chinese text alone determines point size/family/stroke. Target
translation strings are never used to size a font or fit a label box.
"""
from pathlib import Path
import json,hashlib,time
import pymupdf as fitz
import numpy as np,cv2
from PIL import Image
from cpho2024_events import BASE
from cpho2024_natural import FACE_ROOT
from pdf_memory_gate import page_worker

FONTS=[
('SimSun',FACE_ROOT/'english-face-repair/font-faces/SimSun-5.24.ttf'),
('SimHei',FACE_ROOT/'official-hans-fonts/faces/simhei.ttf'),
('DengXian',BASE/'fonts/DENG.TTF'),
('DengXian-Bold',BASE/'fonts/DENGB.TTF'),
('KaiTi',FACE_ROOT/'official-hans-fonts/faces/simkai.ttf'),
('FangSong',FACE_ROOT/'official-hans-fonts/faces/simfang.ttf'),
('MicrosoftYaHei',Path(r'C:/Windows/Fonts/msyh.ttc')),
('MicrosoftYaHei-Bold',Path(r'C:/Windows/Fonts/msyhbd.ttc')),
]
FIELDS=[
dict(id='spectrum-x',page=1,image=0,text='电子动能',rect=[152,369,268,398],point_range=[7.,10.5]),
dict(id='spectrum-y',page=1,image=0,text='电子的相对数目',rect=[0,77,32,266],point_range=[7.,10.5],rotation=90),
dict(id='beam-splitter',page=2,image=2,text='分束器',rect=[279,198,413,240],point_range=[9.,12.]),
dict(id='mz-incident',page=2,image=4,text='入射光',rect=[45,33,153,70],point_range=[9.,11.5]),
dict(id='mz-mirror',page=2,image=4,text='全反镜',rect=[272,5,376,39],point_range=[9.,11.5]),
dict(id='optics-slow',page=2,image=7,text='慢轴',rect=[465,49,560,101],point_range=[9.,12.]),
dict(id='quadrature-mirror',page=3,image=1,text='全反镜',rect=[1,5,41,24],point_range=[7.,10.]),
dict(id='wheel-torque',page=4,image=1,text='扭矩',rect=[137,423,231,478],point_range=[9.,12.]),
]

def calibrate(field):
    inv=json.loads((BASE/'inspection/image-ink-inventory.json').read_text('utf8'))
    meta=next(i for i in inv if i['page']==field['page']and i['index']==field['image'])
    original=np.asarray(Image.open(BASE/f"inspection/image-p{field['page']}-{field['image']}.png").convert('L'))
    scale=meta['dimensions'][0]/(meta['bbox'][2]-meta['bbox'][0]);x0,y0,x1,y1=field['rect']
    source=(original[y0:y1,x0:x1]<160).astype('float32');results=[]
    if field.get('rotation')==90:source=np.rot90(source,k=-1).copy()
    for name,path in FONTS:
        if not path.exists():continue
        font_digest=hashlib.sha256(path.read_bytes()).hexdigest()
        doc=fitz.open();page=doc.new_page(width=150,height=35);page.insert_font(fontname='MeasureSource',fontfile=str(path))
        for size in np.arange(field['point_range'][0],field['point_range'][1]+.001,.05):
            xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'');page.set_contents(xref)
            page.insert_text((2,25),field['text'],fontname='MeasureSource',fontsize=float(size))
            pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
            gray=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);mask=(gray<128).astype('uint8')
            for expand in[0,1]:
                m=cv2.dilate(mask,np.ones((1+2*expand,1+2*expand),np.uint8));yy,xx=np.nonzero(m)
                if not len(xx):continue
                box=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
                template=m[box[1]:box[3],box[0]:box[2]].astype('float32')
                if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
                _,inter,_,location=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR))
                union=float(source.sum()+template.sum()-inter)
                local_x=location[0]+2*scale-box[0];local_y=location[1]+25*scale-box[1]
                if field.get('rotation')==90:origin=[meta['bbox'][0]+(x0+local_y)/scale,meta['bbox'][1]+(y1-local_x)/scale]
                else:origin=[meta['bbox'][0]+(x0+local_x)/scale,meta['bbox'][1]+(y0+local_y)/scale]
                results.append(dict(face=name,font_file=str(path),size=round(float(size),3),pixel_spread=expand,
                    iou=inter/union,origin=origin,template_bbox=box,location=location,
                    font_sha256=font_digest))
        doc.close()
    results.sort(key=lambda r:-r['iou'])
    return dict(field=field,source=meta,scale_px_per_pt=scale,
        source_text_only_no_translated_box_fit=True,metadata_available=False,
        method='Named source Chinese word, actual face raster at fixed candidate point sizes; maximize black-ink IoU',
        top20=results[:20],best_by_face={name:next(r for r in results if r['face']==name)for name,_ in FONTS if any(r['face']==name for r in results)})

if __name__=='__main__':
    import sys
    for field in FIELDS:
        if len(sys.argv)>1 and field['id']not in sys.argv[1:]:continue
        with page_worker():report=calibrate(field)
        path=BASE/f"inspection/font-{field['id']}.json";path.write_text(json.dumps(report,ensure_ascii=False,indent=1),'utf8')
        print(field['id'],report['top20'][0],flush=True);time.sleep(.6)
