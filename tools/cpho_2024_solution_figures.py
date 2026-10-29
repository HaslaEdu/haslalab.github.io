"""Seven CPhO 2024 solution figures, bilingual BAUPC-style vector line art."""
from pathlib import Path
import math
import pymupdf as fitz
from cpho_2025_figures import HEAD,text

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools/ko/cpho/2024/solution-figures'
PAGES=[8,10,15,16,17,23,25]

def arrowhead(x,y,dx,dy,size=8):
    length=math.hypot(dx,dy);ux,uy=dx/length,dy/length
    ax,ay=x-size*ux,y-size*uy
    return f'<path d="M{x} {y} L{ax-uy*size*.38} {ay+ux*size*.38} L{ax+uy*size*.38} {ay-ux*size*.38} Z" fill="black" stroke="none"/>'

def line(x1,y1,x2,y2,arrow=False,extra=''):
    # MuPDF's SVG importer ignores SVG markers and dash arrays.
    # Use explicit path segments/triangles so the PDF matches the SVG.
    if 'stroke-dasharray' in extra:
        length=math.hypot(x2-x1,y2-y1);dx=(x2-x1)/length;dy=(y2-y1)/length
        s=''
        for start in range(0,int(length),11):
            end=min(length,start+6);s+=f'<path d="M{x1+dx*start} {y1+dy*start} L{x1+dx*end} {y1+dy*end}"/>'
    else:s=f'<path d="M{x1} {y1} L{x2} {y2}" {extra}/>'
    return s+(arrowhead(x2,y2,x2-x1,y2-y1) if arrow else '')

def label(x,y,ko,en,lang,size=22,anchor='middle'):
    return text(x,y,ko if lang=='ko' else en,size,False,anchor)

def figure(n,lang):
    s=HEAD
    caption=lambda name:('그림 ' if lang=='ko' else 'Fig. ')+name
    if n==0:
        s+='<rect x="20" y="25" width="560" height="330" stroke-dasharray="6 5"/>'
        s+=line(100,105,180,195,True)
        for a,b,c,d in [(180,195,300,80),(300,80,440,195),
                        (180,195,300,305),(300,305,440,195)]:s+=line(a,b,c,d,True)
        # Both output ports exist; one is destructive and one constructive.
        for a,b,c,d in [(440,195,522,107),(448,202,530,114),
                        (440,195,522,285),(448,188,530,278)]:s+=line(a,b,c,d,True)
        for x,y in [(180,195),(440,195)]:s+=line(x-36,y,x+36,y,False,'stroke-width="5"')
        for y in (75,310):s+=line(270,y,330,y,False,'stroke-width="3"')
        s+='<rect x="522" y="75" width="34" height="34"/><path d="M531 286 l24 24 -24 24 -24 -24 Z"/>'
        s+=label(96,81,'입사광','incident light',lang,20)
        s+=label(300,54,'전반사 거울','mirror',lang,20)
        s+=label(300,339,'전반사 거울','mirror',lang,20)
        s+=label(104,224,'빔분할기 1','splitter 1',lang,18)
        s+=label(484,224,'빔분할기 2','splitter 2',lang,18)
        s+=label(500,61,'검출기 B','detector B',lang,19)
        s+=label(497,349,'검출기 A','detector A',lang,19)
        s+=text(300,388,caption('S3a'),22,False,'middle')
    elif n==1:
        s+=line(165,205,440,205,True)+line(300,350,300,50,True)
        s+=line(186,319,414,91,True,'stroke-dasharray="6 5"')
        s+=line(186,91,414,319,True,'stroke-dasharray="6 5"')
        s+=text(451,215,'P',26)+text(282,50,'S',26)
        s+=label(423,78,'느린축','slow',lang,24)
        s+=label(428,348,'빠른축','fast',lang,24)
        s+=text(300,397,caption('S3b'),24,False,'middle')
        s=s.replace('viewBox="0 0 600 400"','viewBox="140 20 340 390"')
    elif n==2:
        s+='<circle cx="300" cy="215" r="110" stroke-dasharray="3 4"/>'
        s+=line(155,215,470,215,True)+line(300,355,300,55,True)
        s+=line(300,215,377.8,137.2,True,'stroke-width="2.5"')
        s+='<path d="M343 215 A43 43 0 0 0 330.4 184.6"/>'
        s+=text(344,197,'Δφ',26)
        s+=text(451,253,'I',27)+text(461,262,'A',17)+text(462,239,'int',15)
        s+=text(262,66,'−I',27)+text(285,75,'B',17)+text(285,51,'int',15)
        s+=text(300,395,caption('S3c'),24,False,'middle')
        s=s.replace('viewBox="0 0 600 400"','viewBox="140 15 360 395"')
    elif n in (3,4):
        cx,cy,r=300,190,120
        theta=math.radians(160);px=cx+r*math.cos(theta);py=cy-r*math.sin(theta)
        s+=f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'
        s+=line(cx-r,cy,cx,cy,False,'stroke-dasharray="5 4"')
        s+=line(cx,cy,px,py,False,'stroke-dasharray="5 4"')
        s+='<path d="M175 157 A133 133 0 0 1 225 80"/>'+arrowhead(225,80,1,-.6)
        s+='<path d="M250 190 A50 50 0 0 1 253 173"/>'
        s+=text(201,104,'Ω',26)+text(219,214,'Ωt',24)
        s+=f'</g><circle cx="{px}" cy="{py}" r="3" fill="black"/><circle cx="300" cy="190" r="3" fill="black"/><g fill="none" stroke="black" stroke-width="1.6">'
        if n==3:
            s+=text(px-9,py-10,'C',26)+text(311,205,'D',26)
            s+=text(300,367,caption('S1a'),24,False,'middle')
            s=s.replace('viewBox="0 0 600 400"','viewBox="155 40 300 345"')
        else:
            s+=line(300,190,457,190,True)+line(300,190,300,34,True)
            s+=line(300,190,413,231,True)+line(300,190,341,77,True)
            s+=text(px-22,py-7,'C′',26)+text(302,216,'D′',26)
            s+=text(466,195,'X',26)+text(306,33,'Y',26)
            s+=text(420,242,'x',26)+text(344,75,'y',26)
            s+=text(300,367,caption('S1b'),24,False,'middle')
            s=s.replace('viewBox="0 0 600 400"','viewBox="145 15 345 370"')
    elif n==5:
        s+='<path d="M60 300 L373 85 Q420 139 435 230 Z"/>'
        s+='<path d="M350 100 Q395 145 410 235"/>'
        def bezier(p0,p1,p2,t):return tuple((1-t)**2*a+2*t*(1-t)*b+t*t*c for a,b,c in zip(p0,p1,p2))
        for j in range(1,12):
            t=j/12;a=bezier((350,100),(395,145),(410,235),t)
            b=bezier((373,85),(420,139),(435,230),t)
            s+=line(*a,*b,False,'stroke-width=".9"')
        s+=line(60,300,410,235)+text(37,307,'O',29)
        s+=line(260,80,365,133,True)+text(218,74,'dS',27)
        s+=text(276,191,'p(r)',27)+text(427,139,'p(r)+dp(r)',26)
        s+=text(242,281,'r',28)
        s+=line(383,271,406,242,True)+line(466,267,437,236,True)
        s+=text(420,300,'dr',26)
        s+=text(300,386,caption('S5a'),26,False,'middle')
    else:
        s+='<ellipse cx="340" cy="100" rx="130" ry="38"/>'
        s+=line(210,100,100,320)+line(470,100,360,320)
        s+='<ellipse cx="230" cy="320" rx="130" ry="38"/>'
        s+=line(100,320,100,61)
        s+='<path d="M100 252 A68 68 0 0 1 130 259"/>'
        for x in (300,360,420):s+=line(x,157,x-64,285,True,'stroke-width="1.3"')
        s+=text(114,236,'θ',29)+text(427,238,'c dt',28)+text(230,333,'dS',29,False,'middle')
        s+=text(290,397,caption('S5b'),26,False,'middle')
        s=s.replace('viewBox="0 0 600 400"','viewBox="70 35 450 380"')
    return s+'</g></svg>'

def replace(path,lang):
    original=fitz.open(ROOT/'tmp/source-audit/CPhO_2024_TS.pdf');doc=fitz.open(path)
    OUT.mkdir(parents=True,exist_ok=True)
    for n,pi in enumerate(PAGES):
        sp=original[pi];rect=sp.get_image_rects(sp.get_images(full=True)[0][0])[0]
        svg=figure(n,lang);(OUT/f'figure-{n+1}-{lang}.svg').write_text(svg,encoding='utf8')
        drawing=fitz.open(stream=svg.encode(),filetype='svg')
        vector=fitz.open(stream=drawing.convert_to_pdf(),filetype='pdf')
        doc[pi].draw_rect(rect,color=None,fill=(1,1,1))
        doc[pi].show_pdf_page(rect,vector,0,keep_proportion=True)
    if lang=='en':
        # Keep the source's attribution accurate after replacing its figures.
        for rect in doc[0].search_for('cropped'):
            spans=[sp for b in doc[0].get_text('dict')['blocks'] if b['type']==0
                   for ln in b['lines'] for sp in ln['spans']
                   if not (fitz.Rect(sp['bbox'])&rect).is_empty]
            baseline=spans[0]['origin'][1];size=spans[0]['size']
            doc[0].add_redact_annot(rect,fill=(1,1,1));doc[0].apply_redactions(images=0,graphics=0)
            doc[0].insert_text((rect.x0,baseline),'redrawn',fontname='tiit',fontsize=size)
    revised=path.with_name(path.stem+'.figures.pdf');doc.save(revised,garbage=4,deflate=True)
    doc.close();revised.replace(path)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('lang',choices=['en','ko'])
    a=p.parse_args();replace(a.path,a.lang)
