"""CPhO 2006 diagrams in a thin black vector style."""
from pathlib import Path
import math
import pymupdf as fitz
from cpho_2025_figures import HEAD,line,text
ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'tools/ko/cpho/2006/figures'

def circle(x,y,r,fill='white'):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'

def figure(n,lang):
    s=HEAD
    if n==0:
        s+=circle(330,175,140)+line(220,80,330,35)+line(220,360,330,315)+circle(220,220,140)
        offset=math.sqrt(3)*70
        s+=f'<path d="M{220-offset} 290 L{330-offset} 245 H{330+offset} L{220+offset} 290 Z" fill="white"/>'
        s+=line(220-offset,290,330-offset,245,False,'stroke-width="4"')
        s+=line(220+offset,290,330+offset,245,False,'stroke-width="4"')
        s+=line(220,85,220,355,True,'marker-start="url(#arrow)"')
        s+=text(183,202,'2R',24)+text(110,280,'A',24)+text(341,308,'B',24)+text(214,316,'l',25)
        s=s.replace('viewBox="0 0 600 400"','viewBox="65 20 420 355"')
    elif n==1:
        s+=line(35,145,540,145,False,'stroke-dasharray="7 5"')
        s+='<rect x="20" y="133" width="22" height="24" fill="white"/>'
        for x in [100,210]:s+=line(x,119,x,176,False,'stroke-width="3"')
        s+=line(320,105,430,105,False,'stroke-width="4"')+line(320,195,430,195,False,'stroke-width="4"')
        s+=line(430,105,448,105)+line(448,105,448,116)
        s+=line(438,116,458,116)+line(442,121,454,121)+line(446,126,450,126)
        s+=line(540,55,540,235,False,'stroke-width="4"')+line(540,55,540,28,True)
        for x1,x2 in [(100,210),(210,320),(320,430),(430,540)]:
            s+=line(x1,228,x2,228,True,'marker-start="url(#arrow)"')+text((x1+x2)/2,221,'l',20,False,'middle')
        for x,y,t in [(22,122,'K'),(47,170,'O′'),(83,118,'A'),(104,185,'a'),(192,118,'B'),(214,185,'b'),(293,105,'M'),(290,202,'M′'),(548,151,'O'),(521,60,'N'),(518,252,'N′'),(550,28,'Y')]:s+=text(x,y,t,20)
        s+=text(300,280,'그림 1' if lang=='ko' else 'Fig. 1',20,False,'middle')
        # Exact square wave: +2U on each even half-period, -U on each odd one.
        s+=line(65,455,570,455,True)+line(65,530,65,330,True)
        for j in range(12):
            x=65+j*39;y=365 if j%2==0 else 500
            s+=line(x,y,x+39,y,False,'stroke-width="3"')
            if j<11:s+=line(x+39,365,x+39,500,False,'stroke-dasharray="4 4"')
        for j in range(0,13,2):s+=text(65+j*39,477,str(j),19,False,'middle')
        for x,y,t in [(35,365,'2U'),(35,506,'−U'),(72,333,'u'),(550,495,'t/T')]:s+=text(x,y,t,20,False,'middle')
        s+=text(300,558,'그림 2' if lang=='ko' else 'Fig. 2',20,False,'middle')
        s=s.replace('viewBox="0 0 600 400"','viewBox="10 10 580 560"')
    else:
        s+=line(150,95,150,360,False,'stroke-width="4"')+line(405,95,405,360,False,'stroke-width="4"')
        s+=line(277.5,250,535,250,True)+line(277.5,250,277.5,28,True)+line(277.5,250,355,90,True)
        s+='<path d="M277.5 180 A70 70 0 0 1 308 187"/>'
        s+=line(150,342,405,342,True,'marker-start="url(#arrow)"')
        for x,y,t in [(120,97,'P'),(420,97,'Q'),(263,277,'O'),(541,260,'x'),(281,22,'z'),(360,87,'B'),(288,170,'α'),(271,334,'2d')]:s+=text(x,y,t,24)
        s=s.replace('viewBox="0 0 600 400"','viewBox="110 10 455 365"')
    return s+'</g></svg>'

def stamp(doc,source,lang):
    for n,pi in [(0,0),(1,1),(2,3)]:
        if n==1:rect=fitz.Rect(258.9,570.9,536.9,818)
        else:rect=source[pi].get_image_rects(source[pi].get_images(full=True)[0][0])[0]
        svg=figure(n,lang);FIG.mkdir(parents=True,exist_ok=True);(FIG/f'figure-{n+1}-{lang}.svg').write_text(svg,encoding='utf8')
        image=fitz.open(stream=svg.encode(),filetype='svg');vector=fitz.open(stream=image.convert_to_pdf(),filetype='pdf')
        doc[pi].draw_rect(rect,color=None,fill=(1,1,1))
        # The source's fragmented page-2 picture covers its own red footer.
        # Keep both panels above the footer inside the same original column.
        target=fitz.Rect(rect.x0,rect.y0,rect.x1,755) if n==1 else rect
        doc[pi].show_pdf_page(target,vector,0)
        if n==1:
            for drawing in source[pi].get_drawings():
                r=drawing['rect']
                if r.y0>760 and r.width>300 and r.height<2:
                    for item in drawing['items']:
                        if item[0]=='l':doc[pi].draw_line(item[1],item[2],color=drawing['color'],width=drawing['width'])
