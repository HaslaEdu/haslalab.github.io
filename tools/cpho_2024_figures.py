"""CPhO 2024: bilingual monochrome vector figures in the BAUPC line style."""
from pathlib import Path
import math
import pymupdf as fitz
from cpho_2025_figures import HEAD, line, text

ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'tools/ko/cpho/2024/figures'

def circle(x,y,r=7):return f'<circle cx="{x}" cy="{y}" r="{r}"/>'
def mirror(x,y,slope=1):
    return line(x-16,y-16*slope,x+16,y+16*slope,False,'stroke-width="3"')
def splitter(x,y):
    return f'<rect x="{x-12}" y="{y-12}" width="24" height="24"/>'+line(x-11,y-11,x+11,y+11)
def label(x,y,ko,en,lang,size=18,anchor='middle'):
    return text(x,y,ko if lang=='ko' else en,size,False,anchor)

def figure(n,lang):
    s=HEAD
    cap=lambda k:('그림 ' if lang=='ko' else 'Fig. ')+k
    if n==0:
        s+=line(100,310,540,310,True)+line(100,310,100,38,True)
        points=[(0,.76),(.03,.87),(.07,.95),(.12,.98),(.17,.97),(.22,.92),(.3,.80),(.4,.63),(.5,.47),(.6,.32),(.7,.20),(.8,.115),(.9,.055),(1,.018),(1.1,.002),(1.2,0)]
        coords=[(100+x/1.2*420,310-y*242) for x,y in points]
        s+='<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in coords)+'"/>'
        for i,(x,y) in enumerate(coords[1:-1]):
            if i%2==0:s+=f'</g><circle cx="{x}" cy="{y}" r="2.6" fill="black"/><g fill="none" stroke="black" stroke-width="1.6">'
        for i in range(7):
            x=100+i*70;s+=line(x,310,x,303)+text(x,333,f'{i*.2:.1f}' if i else '0',20,False,'middle')
        s+=label(315,361,'전자 운동에너지 / MeV','electron kinetic energy / MeV',lang,20)
        s+='</g><text x="45" y="175" transform="rotate(-90 45 175)" text-anchor="middle" font-family="serif" font-size="20">'+('전자 수' if lang=='ko' else 'electron count')+'</text><g fill="none" stroke="black" stroke-width="1.6">'
        s+=text(390,170,'²¹⁰₈₃Bi',25)+text(300,394,cap('1a'),20,False,'middle')
    elif n==1:
        # MZ paths meet at the two splitters; the unused output remains open.
        s+=line(70,85,180,200,True)+line(180,200,300,90,True)+line(300,90,440,200,True)
        s+=line(180,200,300,310,True)+line(300,310,440,200,True)+line(440,200,532,294,True)
        s+=line(155,200,205,200,False,'stroke-width="4"')+line(415,200,465,200,False,'stroke-width="4"')
        s+=line(276,87,324,87,False,'stroke-width="3"')+line(276,313,324,313,False,'stroke-width="3"')
        s+='<path d="M529 283 l18 18 -18 18 -18 -18 Z"/>'
        s+=label(85,66,'입사광','incident light',lang)+label(300,60,'M₁ 전반사 거울','M₁ mirror',lang)
        s+=label(300,346,'M₂ 전반사 거울','M₂ mirror',lang)+label(117,221,'빔분할기','splitter',lang)
        s+=label(505,191,'빔분할기','splitter',lang)+label(532,344,'검출기','detector',lang)
        s+=text(300,389,cap('3a'),20,False,'middle')
    elif n==2:
        s+=line(90,220,210,220,True)+line(90,220,90,100,True)+circle(90,220,11)+circle(90,220,2)
        s+=text(218,228,'P')+text(70,97,'S')+text(65,252,'k')+text(145,309,'(a)',23,False,'middle')
        s+='<rect x="315" y="193" width="210" height="19"/>'
        s+=line(320,90,419,190,True)+line(419,190,517,90,True)+line(419,212,517,310,True)
        for x,y in [(352,122),(484,122),(484,278)]:s+=circle(x,y,10)+line(x-6,y-6,x+6,y+6)+line(x-6,y+6,x+6,y-6)
        s+=line(352,122,392,80,True)+line(484,122,446,80,True)+line(484,278,524,238,True)
        for x,y,t in [(310,104,'Sᵢ'),(393,78,'Pᵢ'),(402,167,'kᵢ'),(444,76,'Pᵣ'),(521,99,'kᵣ'),(500,145,'Sᵣ'),(523,231,'Pₜ'),(516,333,'kₜ'),(459,307,'Sₜ')]:s+=text(x,y,t,22)
        s+=label(420,244,'빔분할기','splitter',lang)+text(420,362,'(b)',23,False,'middle')
        s+=text(300,396,cap('3b'),20,False,'middle')
    elif n==3:
        s+=line(32,160,130,160,True)+line(130,160,130,263,True)+mirror(130,160)
        s+=text(52,149,'kᵢ',23)+text(142,245,'kᵣ',23)+label(115,113,'전반사 거울','mirror',lang,17)
        s+=line(285,205,365,205,True)+line(285,205,285,92,True)+circle(285,205,7)
        s+=line(285,205,346,144,False,'stroke-dasharray="5 4"')+line(285,205,346,266,False,'stroke-dasharray="5 4"')
        s+=text(368,211,'P',22)+text(275,82,'S',22)+text(262,230,'k',22)
        s+=label(348,129,'느린축','slow',lang,16)+label(349,292,'빠른축','fast',lang,16)
        s+=line(465,205,567,205,True)+line(465,205,465,92,True)+circle(465,205,7)
        s+=line(425,245,535,135,False,'stroke-dasharray="5 4"')
        s+=text(561,232,'P(H)',20)+text(455,78,'S(V)',20)+text(440,231,'k',20)+label(540,119,'+45°','+45°',lang,18)
        s+=label(125,337,'(a) 전반사 거울','(a) mirror',lang,17)+label(300,337,'(b) 사분파장판','(b) quarter-wave',lang,17)+label(488,337,'(c) 선형 편광판','(c) polarizer',lang,17)
        s+=text(300,390,cap('3c'),20,False,'middle')
    elif n==4:
        # Keep both path lengths and the order/orientation of every optical
        # element. P₁ leaves splitter1 downwards; P₂ follows mirrors2,3,4.
        s+=line(80,310,80,70,True)+line(80,70,490,70,True)+line(490,70,490,125,True)+line(490,125,280,125,True)+line(280,125,280,245,True)
        s+=line(180,70,180,245,True)+line(180,245,280,245,True)+line(280,245,280,340,True)+line(280,245,490,245,True)
        for x,y,sl in [(80,70,-1),(490,70,1),(490,125,-1),(280,125,-1),(180,245,1)]:s+=mirror(x,y,sl)
        s+=splitter(180,70)+splitter(280,245)
        s+='<ellipse cx="80" cy="190" rx="23" ry="7"/><ellipse cx="280" cy="190" rx="23" ry="7"/><ellipse cx="280" cy="310" rx="23" ry="7"/><ellipse cx="429" cy="245" rx="7" ry="23"/>'
        s+='<rect x="228" y="226" width="9" height="38"/><rect x="69" y="310" width="22" height="53"/><rect x="267" y="340" width="26" height="15"/><rect x="490" y="232" width="15" height="26"/>'
        for x,y,k,e in [(82,36,'全反镜1','M1'),(182,37,'分束器1','BS1'),(487,36,'全反镜2','M2'),(493,160,'全反镜3','M3'),(306,116,'全反镜4','M4'),(160,281,'全反镜5','M5')]:
            number=k[-1];ko=('빔분할기 ' if '分' in k else '거울 ')+number;s+=label(x,y,ko,e,lang,16)
        for x,y,k,e in [(77,211,'편광판(V)','polarizer(V)'),(365,182,'편광판(45°)','polarizer(45°)'),(359,218,'편광판(H)','polarizer(H)'),(375,329,'편광판(V)','polarizer(V)'),(238,284,'λ/4','λ/4'),(78,384,'레이저','laser'),(381,363,'검출기 A','detector A'),(504,291,'검출기 B','detector B'),(211,180,'광경로 1','path1'),(359,60,'광경로 2','path2')]:s+=label(x,y,k,e,lang,16)
        s+=text(300,399,cap('3d'),18,False,'middle')
    elif n==5:
        s+='<ellipse cx="170" cy="250" rx="68" ry="90" transform="rotate(22 170 250)"/><ellipse cx="420" cy="290" rx="68" ry="90" transform="rotate(22 420 290)"/>'
        s+=line(165,254,420,293)+line(292,273,231,55)+line(299,271,240,53)+line(231,55,240,53)
        s+=line(255,48,314,267,False,'marker-start="url(#arr)" marker-end="url(#arr)"')
        s+=line(420,293,456,225,False,'stroke-dasharray="5 4"')
        s+=text(319,166,'L, M',24)+text(282,297,'C',24)+text(453,276,'r',24)+text(424,198,'m',24)
        s+=text(300,396,cap('4a'),20,False,'middle')
    elif n==6:
        s+=line(150,322,450,322,False,'stroke-width="6"')+line(177,320,177,175,False,'stroke-width="3"')+line(423,320,423,175,False,'stroke-width="3"')+line(177,270,423,270)
        s+=line(300,270,300,45,False,'stroke-dasharray="7 5"')+line(300,270,370,35,False,'stroke-width="3"')
        s+='<path d="M300 93 A177 177 0 0 1 351 100" marker-end="url(#arr)"/>'
        s+=line(178,305,422,305,False,'marker-start="url(#arr)" marker-end="url(#arr)"')
        s+=text(297,292,'C',24)+text(295,300,'d',23)+text(322,79,'φ',25)+text(300,388,cap('4b'),20,False,'middle')
    elif n==7:
        s+='<circle cx="300" cy="233" r="104"/>'
        s+=line(300,128,300,35,False,'stroke-dasharray="4 4"')+line(270,134,236,37,False,'stroke-width="3"')
        s+='<path d="M300 72 A62 62 0 0 0 254 83" marker-end="url(#arr)"/>'
        s+=circle(300,233,12)+circle(300,233,2)
        s+=line(185,341,415,341,False,'stroke-width="4"')
        s+=text(267,65,'θ',25)+label(300,280,'토크','torque',lang,21)+text(300,392,cap('4c'),20,False,'middle')
    elif n==8:
        xs=[65,300,555]
        for x in xs:s+=line(x,65,x,310,False,'stroke-width="1.2"')
        s+=line(65,90,555,90,False,'marker-start="url(#arr)" marker-end="url(#arr)"')+line(65,135,300,135,False,'marker-start="url(#arr)" marker-end="url(#arr)"')
        for x0,x1,waves in [(65,300,3),(65,300,7),(65,300,11),(300,555,7)]:
            pts=[]
            for k in range(251):
                x=x0+(x1-x0)*k/250;y=225+43*math.sin(waves*math.pi*k/250);pts.append(f'{x:.2f},{y:.2f}')
            s+='<polyline stroke-width=".8" points="'+' '.join(pts)+'"/>'
        for x,t in zip(xs,['A','B','C']):s+=text(x,339,t,24,False,'middle')
        s+=text(310,77,'L',25)+text(175,123,'a',25)+text(300,389,cap('6a'),20,False,'middle')
    return s+'</g></svg>'

PANELS=[(0,0),(2,1),(3,2),(4,3),(4,4),(5,5),(6,6),(6,7),(8,8)]

def replace(path,lang):
    source=fitz.open(ROOT/'tmp/source-audit/CPhO_2024_T_EN.pdf');doc=fitz.open(path);counts={}
    for pi,n in PANELS:
        ii=counts.get(pi,0);counts[pi]=ii+1;p=doc[pi];sp=source[pi]
        rect=sp.get_image_rects(sp.get_images(full=True)[ii][0])[0]
        p.draw_rect(rect,color=None,fill=(1,1,1))
        svg=figure(n,lang)
        if n in (5,6,7):
            boxes={5:'90 25 420 375',6:'140 25 320 375',7:'180 25 240 375'}
            svg=svg.replace('viewBox="0 0 600 400"',f'viewBox="{boxes[n]}"')
        FIG.mkdir(parents=True,exist_ok=True);(FIG/f'figure-{n+1}-{lang}.svg').write_text(svg,encoding='utf8')
        image=fitz.open(stream=svg.encode(),filetype='svg');vector=fitz.open(stream=image.convert_to_pdf(),filetype='pdf')
        p.show_pdf_page(rect,vector,0,keep_proportion=True)
    out=path.with_name(path.stem+'.redrawn.pdf');doc.save(out,garbage=4,deflate=True);doc.close();out.replace(path);print(path)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('lang',choices=['en','ko']);a=p.parse_args();replace(a.path,a.lang)
