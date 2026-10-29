"""Vector redraws of the six original CPhO 2005 problem illustrations."""
from pathlib import Path
import pymupdf as fitz
from svg_pdf import explicit_strokes
from cpho_2025_figures import HEAD,line,text,arrow_head
ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'tools/ko/cpho/2005/figures'

def zigzag(x1,y1,x2,y2,turns=8,amplitude=12):
    dx,dy=x2-x1,y2-y1;length=(dx*dx+dy*dy)**.5;nx,ny=-dy/length,dx/length
    points=[(x1,y1)]
    for j in range(1,2*turns):
        t=j/(2*turns);a=amplitude*(-1 if j%2 else 1)
        points.append((x1+t*dx+a*nx,y1+t*dy+a*ny))
    points.append((x2,y2))
    return '<polyline points="'+' '.join(f'{x:g},{y:g}' for x,y in points)+'"/>'

def ellipse(x,y,rx,ry,fill='white'):
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}"/>'

def hatch(x1,y1,x2,y2,gap=12):
    return ''.join(line(x,y1,x+min(18,x2-x),y2) for x in range(int(x1),int(x2),gap))

def figure(n,lang):
    s=HEAD
    if n==0:
        s+='<path d="M100 190 H500 M100 310 H500 M100 190 C85 210 115 230 100 250 S115 290 100 310 M500 190 C485 210 515 230 500 250 S515 290 500 310"/>'
        s+=line(260,190,260,65,False,'stroke-dasharray="6 5"')+line(150,70,260,190,True)
        s+='<path d="M260 143 A47 47 0 0 0 228 155"/>'+text(239,127,'i',24)
    elif n==1:
        s+=line(70,80,70,225)+line(70,225,440,225)+line(440,225,440,330)
        s+=hatch(55,80,70,225,15)+hatch(70,225,430,240,16)
        s+=line(70,180,95,180)+zigzag(95,180,210,180,7,12)+line(210,180,235,180)
        s+='<rect x="235" y="150" width="58" height="75" fill="white"/>'
        s+=line(293,178,440,178)+ellipse(440,195,17,17)+line(457,195,457,280)
        s+='<path d="M457 280 v17 c0 18 24 18 24 0"/><rect x="449" y="311" width="54" height="62" fill="white"/>'
        s+=text(258,140,'A',23)+text(514,350,'B',23)+text(136,147,'k',23)
    elif n==2:
        for x,label in [(150,'A'),(380,'B')]:
            s+='<path d="M'+str(x-65)+' 70 V330 H'+str(x+65)+' V70"/>'
            s+=f'<rect x="{x-65}" y="190" width="130" height="12" fill="white"/>'
            for yy in range(225,325,23):
                for xx in range(x-50,x+60,23):s+=f'<circle cx="{xx}" cy="{yy}" r="1.3" fill="black" stroke="none"/>'
            s+=text(x,365,label,24,False,'middle')
        s+=line(315,70,445,70)+line(380,70,380,90)+zigzag(380,90,380,175,7,12)+line(380,175,380,190)
    elif n==3:
        # The spring box has sloped seats for the upper and lower wedges.
        s+='<path d="M100 25 H560 V375 H100 V300 L270 265 V325 H510 V75 H270 V135 L100 100 Z" fill="#fff"/>'
        s+=hatch(110,28,548,65,16)+hatch(110,337,548,372,16)
        for yy in range(80,330,18):s+=line(525,yy,550,yy+12)
        s+='<path d="M140 108 L278 137 V160 H140 Z M140 240 H278 V263 L140 292 Z" fill="white"/>'
        s+='<rect x="120" y="145" width="16" height="110" fill="white"/><rect x="282" y="122" width="16" height="156" fill="white"/>'
        s+=line(210,160,210,173)+zigzag(210,173,210,227,5,10)+line(210,227,210,240)
        s+=line(298,200,322,200)+zigzag(322,200,490,200,9,24)+line(490,200,510,200)
        s+=line(30,200,119,200,True)
        for x,y,t in [(57,182,'F'),(112,287,'P'),(301,299,'Q'),(160,132,'C'),(161,275,'D'),(151,200,'k₁'),(250,204,'A'),(392,150,'k₂'),(388,254,'B'),(161,70,'N')]:s+=text(x,y,t,23)
    elif n==4:
        # Shaft, conducting disk, rim brush, and the two parallel source branches.
        s+='<path d="M230 215 V355 C230 375 290 375 290 355 V215" fill="white"/>'
        s+=ellipse(260,215,180,42)
        s+='<path d="M80 215 V228 C80 284 440 284 440 228 V215 M230 130 V210 C230 230 290 230 290 210 V130" fill="white"/>'
        s+=ellipse(260,130,30,10)+line(260,130,260,40)+line(260,40,393,40)
        s+=ellipse(420,40,27,27)+line(447,40,520,40)+line(520,40,520,215)+line(520,215,440,215)
        s+=line(260,85,330,85)+f'<rect x="330" y="76" width="65" height="18" fill="white"/>'+line(395,85,520,85)
        s+=line(403,40,436,40,True)+line(120,345,120,278,True)+line(400,345,400,278,True)
        for x,y,t in [(218,122,'O'),(213,390,'O′'),(267,117,'X'),(449,242,'Y'),(411,4,'S'),(410,64,'I'),(348,116,'R₀'),(131,317,'B'),(411,317,'B')]:s+=text(x,y,t,22)
    else:
        s+=ellipse(170,215,40,130)+ellipse(420,215,40,130)
        s+=line(70,215,550,215,True)+line(295,215,295,40,True)+line(295,215,370,135,True)
        s+=line(170,215,170,100,True)+line(420,215,420,100,True)
        s+=line(170,248,295,248)+line(295,248,420,248)
        s+=line(170,240,170,256)+line(295,240,295,256)+line(420,240,420,256)
        for x,y,t in [(148,237,'O₁'),(424,237,'O₂'),(280,207,'O'),(555,222,'z'),(302,37,'y'),(376,133,'x'),(145,158,'R'),(430,158,'R'),(205,281,'D'),(344,281,'D'),(123,190,'Q'),(448,190,'Q')]:s+=text(x,y,t,22)
    bounds={0:'80 50 450 280',1:'45 65 520 325',2:'70 55 395 330',3:'20 15 550 370',4:'65 0 470 400',5:'65 25 510 330'}
    return s.replace('viewBox="0 0 600 400"',f'viewBox="{bounds[n]}"')+'</g></svg>'

def replace(path,lang):
    doc=fitz.open(path);source=fitz.open(ROOT/'tmp/source-audit/CPhO_2005_T_EN.pdf')
    for n,pi in enumerate(range(1,7)):
        rect=source[pi].get_image_rects(source[pi].get_images(full=True)[0][0])[0]
        svg=explicit_strokes(figure(n,lang));FIG.mkdir(parents=True,exist_ok=True);(FIG/f'figure-{n+1}-{lang}.svg').write_text(svg,encoding='utf8')
        image=fitz.open(stream=svg.encode(),filetype='svg');vector=fitz.open(stream=image.convert_to_pdf(),filetype='pdf')
        doc[pi].draw_rect(rect,color=None,fill=(1,1,1));doc[pi].show_pdf_page(rect,vector,0)
    out=path.with_suffix('.redrawn.pdf');doc.save(out,garbage=4,deflate=True);doc.close();out.replace(path)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('lang',choices=['en','ko']);a=p.parse_args();replace(a.path,a.lang)
