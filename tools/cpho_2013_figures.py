"""Recreate the four 2013 figures as bilingual BAUPC-style vector line art."""
from pathlib import Path
import pymupdf as fitz
from svg_pdf import explicit_strokes
from cpho_2025_figures import HEAD, line, text, arrow_head
from cpho_2024_figures import mirror, splitter, circle, label

ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'tools/ko/cpho/2013/figures'

def figure(n,lang):
    s=HEAD
    if n==0:
        s+=line(180,320,510,320,True)+line(180,320,180,40,True)
        s+=line(184,92,184,317,False,'stroke-width="2.2"')
        for y in range(93,320,12):s+=line(169,y+9,180,y)
        for x in range(180,470,12):s+=line(x,331,x+11,320)
        s+='</g><circle cx="187" cy="110" r="5" fill="black"/><circle cx="187" cy="316" r="5" fill="black"/><g fill="none" stroke="black" stroke-width="1.6">'
        s+=text(203,116,'1',23,False)+text(203,308,'2',23,False)+text(520,327,'x',24)+text(171,32,'y',24)
    elif n==1:
        xs=[70,165,345,440,535]
        for x in xs:
            s+=circle(x,100,14)+circle(x,100,22)+line(x,114,x,220)
            s+=line(x,78,x,52)
        s+=line(70,52,580,52)+line(580,52,580,67)+line(568,67,592,67)+line(572,73,588,73)+line(577,79,583,79)
        for x0,x1 in [(70,165),(165,260),(345,440),(440,535)]:
            mid=(x0+x1)/2;s+=line(x0,220,mid-23,220)+f'<rect x="{mid-23}" y="210" width="46" height="20"/>'+line(mid+23,220,x1,220)+text(mid,204,'R',21,True,'middle')
        s+=line(260,220,345,220,False,'stroke-dasharray="5 4"')
        s+=line(70,220,70,245)+line(70,269,70,305)+line(70,269,80,247)
        s+=line(70,305,254,305)+f'<rect x="254" y="295" width="46" height="20"/>'+line(300,305,360,305)
        s+=line(360,297,360,313)+line(370,291,370,319)+line(370,305,535,305)+line(535,305,535,220)
        s+=line(70,305,70,329)+line(58,329,82,329)+line(62,335,78,335)+line(67,341,73,341)
        s+=text(278,285,'R₀',20,True,'middle')+text(365,281,'E',21,True,'middle')
        for x,t in [(70,'1'),(165,'2'),(440,'N'),(535,'N+1')]:s+=text(x+25,116,t,18,True)
    elif n==2:
        s+='<ellipse cx="300" cy="254" rx="102" ry="31"/><path d="M198 254 V350 M402 254 V350 M198 350 C198 392 402 392 402 350"/>'
        s+='<ellipse cx="300" cy="180" rx="55" ry="15"/><ellipse cx="300" cy="176" rx="55" ry="15"/>'
        for offset in [-80,-55,-30,0,30,55,80]:
            start=300+offset*.55;end=300+offset*1.8
            s+=f'<path d="M{start} 254 Q{start} 116 {end} 55"/>'+arrow_head(end,55,end-start,-61)
        s+=line(300,255,300,43,True)+line(300,255,458,255,True)+text(309,44,'z',25)+text(465,262,'r',25)
        s+=text(365,168,'Bz',25)+text(423,241,'Br',25)
    elif n==3:
        # (a) incident paths, wire, CCD and computer.
        s+='<rect x="34" y="48" width="17" height="35"/>'
        s+=line(42,83,42,105,True)+line(42,105,160,105,True)+line(160,105,160,190,True)
        s+=line(42,105,42,280,True)+line(42,280,160,280,True)+line(160,280,160,205,True)
        s+=splitter(42,105)+mirror(160,105,1)+mirror(42,280,1)+mirror(160,280,-1)+circle(160,198,10)
        s+=line(170,198,227,198,True)+line(238,198,263,198)
        s+='<rect x="227" y="187" width="11" height="22"/><rect x="263" y="179" width="27" height="37"/>'
        for x,y,k,e in [(99,61,'倍频 Nd:YVO₄','Nd:YVO₄'),(41,91,'빔분할기','BS'),(181,218,'철사','wire'),(232,240,'카메라','CCD'),(274,264,'컴퓨터','PC')]:
            s+=label(x,y,k if k!='倍频 Nd:YVO₄' else '주파수 배가 Nd:YVO₄',e,lang,13)
        s+=text(168,95,'M₁',17)+text(167,302,'M₂',17)+text(21,301,'M₃',17)+text(153,340,'(a)',20,False,'middle')
        # (b) cross section with y upward, z towards the screen, x into paper.
        s+=circle(370,200,28)+line(326,200,575,200,True)+line(370,290,370,52,True)+line(555,74,555,296)
        s+=line(370,172,370,92,True)+line(370,276,370,228,True)
        s+=line(370,172,555,133,True)+line(370,228,555,133,True)
        s+=line(370,172,401,142,False,'stroke-dasharray="4 4"')+line(370,228,400,258,False,'stroke-dasharray="4 4"')
        s+='<path d="M370 137 A35 35 0 0 1 394 147"/><path d="M370 263 A35 35 0 0 0 395 252"/>'
        s+=line(370,294,555,294,False,'marker-start="url(#arr)" marker-end="url(#arr)"')
        s+=text(362,224,'O',18)+text(359,45,'y',20)+text(580,206,'z',20)+text(559,129,'P',20)+text(460,319,'D',21,True,'middle')
        s+=text(380,137,'θ₁',19)+text(380,278,'θ₂',19)+label(555,62,'관측면','screen',lang,14)+text(460,340,'(b)',20,False,'middle')
    elif n==4:
        s+=line(180,45,180,320,False,'stroke-width="2.2"')+line(180,320,520,320,False,'stroke-width="2.2"')+line(180,100,400,320,False,'stroke-width="2.2"')
        for y in range(45,320,12):s+=line(168,y+10,180,y)
        for x in range(180,520,12):s+=line(x,332,x+12,320)
        s+='</g><circle cx="180" cy="100" r="6" fill="black"/><circle cx="400" cy="320" r="6" fill="black"/><g fill="none" stroke="black" stroke-width="1.6">'
        s+='<path d="M180 153 A53 53 0 0 0 217 137"/>'
        s+=text(197,94,'1',23,False)+text(408,311,'2',23,False)+text(195,158,'θ',23)
    elif n==5:
        s+=circle(260,240,155)+line(87,240,555,240,True)+line(260,398,260,20,True)
        s+=line(369.6,130.4,369.6,40)+line(383.8,146.7,383.8,40)
        s+=line(260,240,420,80)+line(260,240,451,96)
        s+=line(369.6,130.4,520,130.4,True)+line(383.8,146.7,527,187.8,True)
        s+=line(260,111.2,383.8,146.7,False,'stroke-dasharray="4 4"')
        s+=line(260,130.4,369.6,130.4,False,'stroke-dasharray="4 4"')+line(260,146.7,383.8,146.7,False,'stroke-dasharray="4 4"')
        s+='<path d="M260 193 A47 47 0 0 1 293 207"/><path d="M307 193 A67 67 0 0 1 314 200"/><path d="M435 147 A51 51 0 0 1 433 161"/>'
        for x,y,t in [(252,15,'y'),(560,247,'z'),(242,265,'O'),(241,113,'E'),(238,135,'Q'),(233,162,'Q₊'),(349,37,'A'),(391,38,'A₊'),(348,124,'P'),(386,169,'P₊'),(526,132,'B'),(530,196,'B₊'),(267,201,'π/4'),(303,184,'Δθ'),(444,163,'2Δθ')]:s+=text(x,y,t,18)
    boxes={0:'130 20 425 330',1:'40 35 560 320',2:'120 25 370 365',3:'20 35 580 315',4:'150 35 390 310',5:'80 10 495 390'}
    s=s.replace('viewBox="0 0 600 400"',f'viewBox="{boxes[n]}"')
    return s+'</g></svg>'

def replace(path,lang):
    solutions='_TS_' in path.name
    doc=fitz.open(path);source=fitz.open(ROOT/('tmp/source-audit/CPhO_2013_TS.pdf' if solutions else 'tmp/source-audit/CPhO_2013_T_EN.pdf'))
    for pi,n in ([(2,4),(10,5)] if solutions else [(0,0),(1,1),(2,2),(3,3)]):
        p=doc[pi];sp=source[pi];rect=sp.get_image_rects(sp.get_images(full=True)[0][0])[0]
        p.draw_rect(rect,color=None,fill=(1,1,1))
        svg=explicit_strokes(figure(n,lang));FIG.mkdir(parents=True,exist_ok=True);(FIG/f'figure-{n+1}-{lang}.svg').write_text(svg,encoding='utf8')
        image=fitz.open(stream=svg.encode(),filetype='svg');pdf=fitz.open(stream=image.convert_to_pdf(),filetype='pdf');p.show_pdf_page(rect,pdf,0)
    out=path.with_name(path.stem+'.redrawn.pdf');doc.save(out,garbage=4,deflate=True);doc.close();out.replace(path)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('path',type=Path);p.add_argument('lang',choices=['en','ko']);a=p.parse_args();replace(a.path,a.lang)
