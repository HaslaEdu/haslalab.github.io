"""Optical source-vs-Hangul stem comparison; pointsize/advance stay fixed."""
from pathlib import Path
from io import BytesIO
import json,hashlib,re
import cv2,numpy as np
from PIL import Image,ImageDraw
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools import subset
cv2.setNumThreads(1)
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
SOURCE=Path('tmp/original-style-sources/CPhO_2013_Chinese_original.pdf')
SCALE=8;SIZE=9.78;TEXT='처음 튄 직후의 수직 속력'

def stems(gray,size):
    mask=(gray<160).astype(np.uint8);length=round(size*SCALE*.28);maximum=round(size*SCALE*.17)
    result={}
    for direction in['vertical','horizontal']:
        selected=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((length,1)if direction=='vertical'else(1,length),np.uint8))
        if direction=='horizontal':selected=selected.T
        values=[]
        for row in selected:
            changes=np.diff(np.pad(row.astype(np.int16),(1,1)));beg=np.where(changes==1)[0];end=np.where(changes==-1)[0]
            values.extend(int(v)for v in end-beg if 1<=v<=maximum)
        if not values:raise ValueError('No primary stem samples')
        counts=np.bincount(values);mode=int(np.argmax(counts))
        result[direction]=dict(mode_pt=mode/SCALE,median_pt=float(np.median(values)/SCALE),quartiles_pt=(np.percentile(values,[25,75])/SCALE).tolist(),samples=len(values),histogram_px={str(i):int(n)for i,n in enumerate(counts)if n})
    result['vertical_horizontal_mode_ratio']=result['vertical']['mode_pt']/result['horizontal']['mode_pt']
    return result

def compare():
    out=BASE/'font-calibration';samples=[];source_rows=[]
    with fitz.open(SOURCE)as doc:
        for name,rect in[('first-ten',[75,135,184,150]),('speed-clause',[178,135,333,150.2]),('reference-bold',[76,123,119.5,135])]:
            p=doc[3].get_pixmap(matrix=fitz.Matrix(SCALE,SCALE),clip=fitz.Rect(rect),colorspace=fitz.csGRAY)
            gray=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width).copy();source_rows.append(dict(id=name,rect=rect,role='bold'if name=='reference-bold'else'regular',metrics=stems(gray,SIZE)))
            samples.append(('Original SimSun '+name,gray))
    font=TTFont('C:/Windows/Fonts/batang.ttc',fontNumber=0,recalcTimestamp=False);options=subset.Options();options.retain_gids=True
    worker=subset.Subsetter(options=options);worker.populate(text=TEXT);worker.subset(font);stream=BytesIO();font.save(stream);font.close();raw=stream.getvalue();metric=fitz.Font(fontbuffer=raw)
    doc=fitz.open();page=doc.new_page(width=160,height=25);page.insert_font(fontname='Body',fontbuffer=raw);rows=[]
    for stroke in[0,.05,.1,.15,.2,.25,.3,.35,.4,.45]:
        content=doc.get_new_xref();doc.update_object(content,'<<>>');doc.update_stream(content,b'');page.set_contents(content);x=3
        for word in TEXT.split(' '):
            page.insert_text((x,17),word,fontname='Body',fontsize=SIZE,render_mode=2 if stroke else 0,border_width=stroke/SIZE,color=(0,0,0),fill=(0,0,0));x+=metric.text_length(word,fontsize=SIZE)+SIZE/4
        p=page.get_pixmap(matrix=fitz.Matrix(SCALE,SCALE),clip=fitz.Rect(0,6,155,21),colorspace=fitz.csGRAY)
        gray=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width).copy();measured=stems(gray,SIZE)
        error=sum(abs(measured[d]['median_pt']-source['metrics'][d]['median_pt'])for source in source_rows if source['role']=='regular'for d in['vertical','horizontal'])/2
        bold_error=sum(abs(measured[d]['median_pt']-source_rows[-1]['metrics'][d]['median_pt'])for d in['vertical','horizontal'])
        rows.append(dict(stroke_pt=stroke,pointsize=SIZE,metrics=measured,stem_median_absolute_error_pt=error,bold_stem_median_absolute_error_pt=bold_error));samples.append((f'Batang {SIZE}pt stroke {stroke:g}pt',gray))
    doc.close();width=max(a.shape[1]for _,a in samples);height=sum(a.shape[0]+25 for _,a in samples);canvas=Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(canvas);y=0
    for label,gray in samples:draw.text((2,y+2),label,fill='black');canvas.paste(Image.fromarray(gray),(0,y+20));y+=gray.shape[0]+25
    chart=out/'source-vs-Batang-stems.png';canvas.save(chart)
    report=dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_page=4,source_runs=source_rows,korean_font='Batang face0',font_sha256=hashlib.sha256(Path('C:/Windows/Fonts/batang.ttc').read_bytes()).hexdigest(),sample_text=TEXT,
        source_pointsize_fixed=SIZE,quarter_em_spaces=True,scale=SCALE,threshold=160,method='Long primary stem openings (.28em); cross-sections above .17em excluded as junction/serif rather than stems. Horizontal/vertical widths and contrast compared independently. No whole-ink-density target or glyph-width fitting.',results=rows,comparison_image=str(chart))
    (out/'source-vs-Batang-stems.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print('source',[(r['id'],r['metrics']['vertical']['median_pt'],r['metrics']['horizontal']['median_pt'])for r in source_rows])
    print('Korean',[(r['stroke_pt'],r['metrics']['vertical']['median_pt'],r['metrics']['horizontal']['median_pt'],r['stem_median_absolute_error_pt'])for r in rows])

if __name__=='__main__':compare()
