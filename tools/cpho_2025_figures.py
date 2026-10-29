"""Rebuild CPhO 2025's six diagrams as monochrome vector line drawings.

Geometry follows the printed figures. Thin black rules, serif mathematical
labels, arrowheads and white backgrounds follow the BAUPC problem sheets.
Both language editions share exactly the same physical geometry.
"""
from pathlib import Path
import math
import re
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "tools/ko/cpho/2025/figures"
HEAD = '''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
<defs><marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 Z" fill="black"/></marker></defs>
<g fill="none" stroke="black" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'''

def arrow_head(x,y,dx,dy,size=8,width=6):
    length=math.hypot(dx,dy)
    if length==0:return ''
    ux,uy=dx/length,dy/length;bx,by=x-size*ux,y-size*uy
    px,py=-uy*width/2,ux*width/2
    return (f'<path d="M{x:.3f} {y:.3f} L{bx+px:.3f} {by+py:.3f} '
            f'L{bx-px:.3f} {by-py:.3f} Z" fill="black" stroke="none"/>')

def line(x1,y1,x2,y2,arrow=False,extra=""):
    # MuPDF's SVG renderer does not draw marker arrowheads. Real triangles
    # preserve every physical direction in the exported vector PDF.
    end=arrow or 'marker-end=' in extra;start='marker-start=' in extra
    attrs=re.sub(r'\s*marker-(?:start|end)="[^"]*"','',extra)
    svg=f'<path d="M{x1} {y1} L{x2} {y2}" {attrs}/>'
    if end:svg+=arrow_head(x2,y2,x2-x1,y2-y1)
    if start:svg+=arrow_head(x1,y1,x1-x2,y1-y2)
    return svg

def text(x,y,s,size=25,italic=True,anchor="start"):
    return f'</g><text x="{x}" y="{y}" font-family="Times New Roman,serif" font-size="{size}" font-style="'+('italic' if italic else 'normal')+f'" fill="black" text-anchor="{anchor}">{s}</text><g fill="none" stroke="black" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'

def figure(n,lang):
    s=HEAD
    caption=lambda k:('그림 ' if lang=='ko' else 'Fig. ')+k
    if n==0:
        s+=line(65,290,540,290,True)+line(160,330,160,50,True)+line(65,110,485,110)
        s+=line(410,110,410,290,False,'stroke-dasharray="5 5"')
        s+=line(160,290,160,245,True)+line(375,132,456,83,True)
        s+='<path d="M410 75 A35 35 0 0 1 441 91"/>'
        for x,y,t in [(548,300,'x'),(172,48,'y'),(132,317,'O'),(130,275,'A'),(420,137,'B'),(398,318,'x'),(470,87,'p₂'),(173,251,'p₁'),(421,72,'θ'),(61,136,'y = b')]:s+=text(x,y,t)
        s+=text(300,375,caption('1a'),23,False,'middle')
    elif n in (1,2,3,4):
        # The source panels have a wide aspect ratio; ample whitespace in the
        # drawing is cropped before insertion, so axis labels keep their size.
        s+=line(65,215,545,215,True)+line(210,265,210,105,True)
        s+=text(552,223,'x')+text(222,108,'y')+text(181,246,'O')
        if n==1:
            s+=line(78,215,512,215,False,'stroke-width="4"')+text(389,176,'ρ, τ')
        elif n==2:
            s+=line(78,215,512,215,False,'stroke-width="4"')+text(130,178,'1')+text(333,178,'2')
        else:
            s+=line(78,215,515,215,False,'stroke-width="4"')
            if n==3:
                for x,t in [(160,'2'),(250,'1'),(335,'2'),(405,'1'),(474,'2')]:s+=text(x,178,t)
                for x,t in [(250,'a'),(335,'b'),(405,'a')]:s+=text(x,250,t)
            else:
                for x,t in [(108,'1'),(168,'2'),(255,'1'),(325,'2'),(398,'1'),(470,'2')]:s+=text(x,178,t)
                s+=text(252,250,'a')+text(325,250,'b')+text(510,208,'⋯')
        s+=text(300,315,caption('2'+chr(ord('a')+n-1)),23,False,'middle')
    elif n==5:
        s+='<circle cx="340" cy="145" r="98"/>'
        s+=line(205,145,67,145,True)
        s+=line(340,145,340,243,False,'stroke-dasharray="5 5"')
        s+=line(340,145,406,218)+line(340,145,428,102,False,'stroke-dasharray="5 5"')
        s+='<path d="M390 82 A82 82 0 0 0 285 84"/>'+arrow_head(285,84,-.7,.4)
        s+='<path d="M340 197 A52 52 0 0 0 375 183"/><path d="M368 173 A40 40 0 0 0 376 127"/>'
        s+=text(353,205,'ωt',22)+text(383,158,'φ',23)+text(412,238,'0',22,False)
        for x in [230,285,340,395,450]:s+=line(x,337,x,269,True)
        s+=text(340,110,'자전 방향' if lang=='ko' else 'spin',22,False,'middle')
        s+=text(139,179,'공전속도' if lang=='ko' else 'orbital velocity',20,False,'middle')
        s+=text(340,367,'태양 복사' if lang=='ko' else 'solar radiation',22,False,'middle')
        s+=text(340,397,caption('6a'),20,False,'middle')
    return s+'</g></svg>'

def replace(path,lang):
    doc=fitz.open(path)
    panels=[(1,0),(2,1),(2,2),(3,3),(3,4),(7,5)]
    counts={}
    for pi,n in panels:
        page=doc[pi];ii=counts.get(pi,0);counts[pi]=ii+1
        images=page.get_images(full=True)
        # Newly inserted formula crops also occur in the KO file. Original
        # figure image rectangles are identified using the source geometry.
        source=fitz.open(ROOT/'tmp/source-audit/CPhO_2025_T_EN.pdf')
        original=source[pi];xref=original.get_images(full=True)[ii][0]
        rect=original.get_image_rects(xref)[0]
        page.draw_rect(rect,color=None,fill=(1,1,1),overlay=True)
        svg=figure(n,lang)
        FIG.mkdir(parents=True,exist_ok=True)
        (FIG/f'figure-{n+1}-{lang}.svg').write_text(svg,encoding='utf8')
        vector=fitz.open(stream=svg.encode(),filetype='svg')
        pdf=fitz.open(stream=vector.convert_to_pdf(),filetype='pdf')
        clip=fitz.Rect(48,90,565,335) if n in (1,2,3,4) else fitz.Rect(40,35,570,400)
        if n==5:clip=fitz.Rect(45,35,470,400)
        page.show_pdf_page(rect,pdf,0,clip=clip,keep_proportion=True,overlay=True)
    result=path.with_name(path.stem+'.redrawn.pdf')
    doc.save(result,garbage=4,deflate=True)
    doc.close();result.replace(path)
    print(path)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('lang',choices=['en','ko']);a=p.parse_args();replace(a.path,a.lang)
