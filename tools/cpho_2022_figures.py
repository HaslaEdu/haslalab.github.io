"""Six bilingual CPhO 2022 problem diagrams, redrawn as scientific vectors."""
from pathlib import Path
import math,json,re
import numpy as np
import pymupdf as fitz
from cpho_2023_figures import line,text,arrow_head,poly,circle,arc,svg
from svg_pdf import explicit_strokes
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'tools/ko/cpho/2022/figures'

def caption(x,y,number,lang,size=30):return text(x,y,('그림 ' if lang=='ko' else 'Fig. ')+number,size,False,'middle')

def parabolic_rod(lang):
    # l=1, a=2/3 gives the stated nonhorizontal equilibrium at theta=30 deg.
    a=2/3;theta=math.pi/6;xm=math.tan(theta)/(2*a);half=math.cos(theta)
    B=np.array([xm-half,a*(xm-half)**2]);A=np.array([xm+half,a*(xm+half)**2])
    X=lambda p:np.array([220+170*p[0],365-170*p[1]])
    s=line(40,365,555,365,True)+line(220,415,220,28,True)
    xs=np.linspace(-1.45,1.55,300);s+=poly([X([x,a*x*x]) for x in xs],'stroke-width="2.7"')
    s+=line(*X(B),*X(A),False,'stroke-width="5"')
    for point in [B,A]:s+=circle(*X(point),7,'fill="white"')
    s+=text(*(X(A)+[16,-9]),'A',34)+text(*(X(B)+[-26,20]),'B',34)
    s+=text(228,34,'y',33)+text(552,400,'x',33)+text(191,397,'O',32)
    s+=caption(300,470,'1a',lang)
    return svg(650,505,s,x=-50)

def impact_parameter(lang):
    s=circle(115,105,43)+circle(360,218,43)
    s+=text(107,115,'1',32,False)+text(351,228,'2',32,False)
    s+=line(161,105,327,105,True,'stroke-width="2.5"')
    s+=line(328,105,493,105,False,'stroke-dasharray="6 5"')
    s+=line(403,218,493,218,False,'stroke-dasharray="6 5"')
    s+=line(480,105,480,218,True,'marker-start="url(#arrow)"')+text(495,175,'b',34)
    s+=caption(300,310,'2a',lang)
    s+=text(300,348,'충돌 매개변수 b의 기하학적 정의' if lang=='ko' else 'Geometry of the impact parameter b',24,False,'middle')
    return svg(600,375,s)

def rolling_ring(lang):
    theta,phi=.36,.95;R=1.45
    u=np.array([math.cos(phi),math.sin(phi),0]);normal=np.array([-math.sin(phi),math.cos(phi),0])
    z=np.array([0.,0.,1.]);w=math.sin(theta)*normal+math.cos(theta)*z
    C=np.array([1.5,1.6,0]);G=C+R*w
    # Keep the original axis directions; this view also shows the ring's
    # plane clearly instead of projecting its circle almost edge-on.
    def P(q):x,y,z=q;return np.array([350-105*(.5*x+.4*y),360+105*(-.4*x+.45*y-1.1*z)])
    s=line(*P([0,0,0]),*P([1,0,0]),True)+line(*P([0,0,0]),*P([0,3.2,0]),True)
    angles=np.linspace(0,2*math.pi,400)
    s+=poly([P(G+R*(math.cos(t)*u+math.sin(t)*w)) for t in angles],'stroke-width="2.8"')
    s+=line(*P(C),*P(C+u*2.25),False,'stroke-dasharray="6 5"')+line(*P(C),*P(C-u*.85),False,'stroke-dasharray="6 5"')
    s+=line(*P(C),*P(C+2.4*R*w),False,'stroke-dasharray="6 5"')+circle(*P(C),4,'fill="black"')
    s+=line(*P(C),*P(C+z*2.65),True,'stroke-dasharray="6 5"')
    s+=poly([P(C+.8*(math.cos(t)*z+math.sin(t)*normal)) for t in np.linspace(0,theta,60)])
    s+=poly([P(C-1.4*np.array([math.cos(t),math.sin(t),0])) for t in np.linspace(0,phi,60)])
    s+=line(*P(C),*P(C-np.array([2.,0,0])),False,'stroke-dasharray="5 5"')
    for point,offset,label in [(P([1,0,0]),[10,-20],'x'),(P([0,3.2,0]),[-14,26],'y'),
        (P([0,0,0]),[12,20],'O'),(P(C+.8*z),[10,6],'θ(t)'),
        (P(C-1.7*np.array([math.cos(phi/2),math.sin(phi/2),0])),[0,8],'φ(t)')]:
        s+=text(*(point+offset),label,29)
    s+=text(*(P(C+z*2.65)+[-65,-12]),'연직 방향' if lang=='ko' else 'Vertical',23,False)
    s+=caption(340,525,'3a',lang)
    return svg(680,560,s)

def fel(lang):
    s='';start,end=300,800;beam_y=210
    # Alternating pole faces in front/back rows form the undulator.
    for row,yy in enumerate([137,263]):
        for k in range(12):
            xx=start+k*(end-start)/12
            s+=f'<rect x="{xx}" y="{yy}" width="{(end-start)/12}" height="39" fill="white"/>'
            s+=text(xx+20,yy+28,'N' if (k+row)%2==0 else 'S',23,False,'middle')
    s+=line(92,beam_y,986,beam_y,True)
    ts=np.linspace(0,1,800)
    s+=poly([(start+(end-start)*t-12*math.sin(t*12*math.pi),beam_y+12*math.sin(t*12*math.pi)) for t in ts],'stroke-width="2.6"')
    s+='<path d="M180 210 Q145 210 131 182 L77 75"/>'+arrow_head(180,210,1,0)
    s+='<path d="M800 210 Q853 210 875 166 L923 73"/>'+arrow_head(923,73,.5,-1)
    s+='<path d="M48 75 L90 53 L124 117 L82 139 Z" fill="white"/>'
    s+='<path d="M891 53 L934 75 L900 139 L858 117 Z" fill="white"/>'
    for cx in [184,871]:
        s+=f'<ellipse cx="{cx}" cy="210" rx="7" ry="35"/>'
    s+=text(13,36,'전자 가속기' if lang=='ko' else 'Electron accelerator',25,False)
    s+=text(815,36,'전자 수집기' if lang=='ko' else 'Electron collector',25,False)
    for x,y,ko,en in [(220,112,'편향 자석','Bending magnet'),(712,110,'편향 자석','Bending magnet'),
                       (162,359,'공진기 거울','Cavity mirror'),(825,359,'공진기 거울','Cavity mirror'),
                       (546,347,'언듈레이터','Undulator'),(247,194,'전자','Electrons'),(947,194,'광선','Light')]:
        s+=text(x,y,ko if lang=='ko' else en,21 if ko in ['편향 자석','전자'] else 23,False,'middle')
    s+=line(184,246,184,326)+line(871,246,871,326)
    s+=line(255,415,351,415,True)+line(255,415,255,365,True)+line(255,415,219,452,True)
    s+=text(358,425,'z',27)+text(246,361,'x',27)+text(201,468,'y',27)
    s+=caption(555,479,'4a',lang,29)
    return svg(1080,510,s)

def lattice(lang):
    O=np.array([150.,370.]);a=np.array([70.,0]);b=np.array([35.,-60.62]);s=''
    for i in range(5):
        for j in range(5):
            p=O+i*a+j*b
            if i<4:s+=line(*p,*(p+a))
            if j<4:s+=line(*p,*(p+b))
            s+=circle(*p,4,'fill="white"')
    s+=line(100,370,616,370,True)+line(150,370,150,60,True)+line(150,370,65,422,True)
    for y in [145,193,241,289,337]:s+=line(18,y,90,y,True)
    s+=text(615,398,'z',32)+text(125,57,'x',32)+text(47,451,'y',32)+text(123,398,'O',29)
    start=O+2*a+2*b;angle=.89
    s+=line(*start,*(start+225*np.array([math.cos(angle),-math.sin(angle)])),True)
    s+=arc(*start,57,-angle,0)+text(*(start+[64,-19]),'θ',31)
    top=O+4*b;corner=O+3*b
    s+=text(*(top+[26,-20]),'d',29)+text(*(corner+[-30,-23]),'d',29)
    s+=arc(*corner,44,-math.pi/3,0)+text(*(corner+[41,-18]),'60°',25,False)
    s+=text(48,112,'레이저' if lang=='ko' else 'Laser',25,False,'middle')
    s+=text(468,52,'회절광' if lang=='ko' else 'Diffracted light',26,False,'middle')
    s+=caption(320,452,'4b',lang)
    return svg(660,485,s)

def birefringence(lang):
    O=np.array([330.,185.]);theta=.55;down=np.array([0.,1.]);optic=np.array([-math.sin(theta),math.cos(theta)]);xdir=np.array([math.cos(theta),math.sin(theta)])
    s='<path d="M70 65 V492 H635 V65"/>'+line(70,185,635,185)
    s+=line(*O,*(O+down*228),False,'stroke-dasharray="6 5"')
    s+=line(*O,*(O+optic*260),True,'stroke-dasharray="6 5"')+line(*O,*(O+xdir*235),True,'stroke-dasharray="6 5"')
    s+=line(O[0],185,O[0],55,True)
    s+=arc(*O,112,math.pi/2,math.pi/2+theta)
    s+=text(263,288,'θ',32)+text(555,337,'x',32)
    s+=text(147,441,'광축 y' if lang=='ko' else 'Optical axis y',26,False)
    s+=text(539,172,'공기' if lang=='ko' else 'Air',25,False)
    s+=text(539,223,'결정' if lang=='ko' else 'Crystal',25,False)
    s+=caption(350,541,'5a',lang)
    return svg(690,575,s)

def figure(index,lang):
    funcs={1:parabolic_rod,2:impact_parameter,3:rolling_ring,4:fel,5:lattice,6:birefringence}
    return explicit_strokes(funcs[index](lang))

def replace(path,lang):
    panels=json.loads((FOLDER.parent/'regions.json').read_text(encoding='utf8'))['exclude']
    drawings={i:fitz.open(stream=figure(i,lang).encode('utf8'),filetype='svg') for i in range(1,7)}
    doc=fitz.open(path)
    for index,panel in enumerate(panels,1):
        page=doc[panel['page']-1];r=fitz.Rect(panel['rect'])
        # Remove only the old native Chinese callouts/captions. Broad panel
        # redaction can hit oversized source equation bboxes next to a figure.
        for block in page.get_text('dict')['blocks']:
            if block['type']!=0:continue
            for row in block['lines']:
                for span in row['spans']:
                    box=fitz.Rect(span['bbox']);centre=(box.tl+box.br)/2
                    if re.search('[\u3400-\u9fff]',span['text']) and r.contains(centre):page.add_redact_annot(box,fill=None)
        page.apply_redactions(images=0,graphics=0)
        page.draw_rect(r,color=None,fill=(1,1,1))
        source=drawings[index];pdf=fitz.open(stream=source.convert_to_pdf(),filetype='pdf')
        page.show_pdf_page(r,pdf,0,keep_proportion=True);pdf.close()
    temp=Path(str(path)+'.figures.pdf');doc.save(temp,garbage=4,deflate=True);doc.close();temp.replace(path)
    for d in drawings.values():d.close()

def proof():
    FOLDER.mkdir(parents=True,exist_ok=True);out=ROOT/'tmp/cpho-build/2022/figures';out.mkdir(parents=True,exist_ok=True)
    for i in range(1,7):
        for lang in ['ko','en']:
            value=figure(i,lang);(FOLDER/f'figure-{i}-{lang}.svg').write_text(value,encoding='utf8')
            d=fitz.open(stream=value.encode('utf8'),filetype='svg');d[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(out/f'proof-{i}-{lang}.png')

if __name__=='__main__':proof()
