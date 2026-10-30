"""CPhO 2007 diagrams in the same thin monochrome style as BAUPC."""
from pathlib import Path
import json,math
import numpy as np
import pymupdf as fitz
from cpho_2023_figures import line,text,arrow_head,poly,circle,arc,svg
from svg_pdf import explicit_strokes
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'tools/ko/cpho/2007/figures'

def spring(x,y1,y2,width=22,turns=8):
    points=[(x,y1),(x,y1+10)]
    for j in range(turns*2+1):points.append((x+width*(1 if j%2==0 else -1),y1+10+(y2-y1-20)*j/(turns*2)))
    points.extend([(x,y2-10),(x,y2)])
    return poly(points)

def balls(solution=False):
    O=np.array([270.,275.]);A=np.array([70.,275.]);C=O+np.array([100.,-100*math.sqrt(3)])
    s=line(35,275,570,275,True)+line(270,315,270,10,True)
    s+=line(*A,*O)+line(*O,*C)+arc(*O,54,-math.pi/3,0)
    for P,name,dx,dy in [(A,'A',-18,-15),(O,'B',-45 if solution else -25,14 if solution else -14),(C,'C',13,-2)]:
        s+=circle(*P,9,'fill="white"')+text(P[0]+dx,P[1]+dy,name,27)
    s+=text(283,302,'O',26)+text(562,302,'x',26)+text(287,26,'y',26)
    s+=text(171,259,'ℓ',28)+text(331,193,'ℓ',28)+text(326,261,'α',27)
    if not solution:
        s+=circle(270,132,9,'fill="white"')+text(239,124,'D',27)
        s+=line(270,143,270,202,True,'stroke-width="2.7"')+text(223,185,'v₀',27)
    return svg(610,340,s)

def piston():
    s='<rect x="78" y="25" width="250" height="405"/><rect x="89" y="36" width="228" height="383"/>'
    for y in range(35,422,12):
        s+=line(78,y,89,y-10)+line(317,y,328,y-10)
    for x in range(90,327,12):s+=line(x,25,x-10,36)+line(x,419,x-10,430)
    s+='<rect x="90" y="319" width="226" height="14" fill="white"/>'
    s+=spring(202,37,158,27,8)+spring(202,158,319,32,5)
    s+=text(245,101,'k₁',28)+text(249,237,'k₂',28)+text(268,309,'A',28)
    s+=line(372,25,372,430,True,'marker-start="url(#arrow)"')+line(329,25,389,25)+line(329,430,389,430)
    s+=text(384,234,'H',28)
    s+=line(115,333,115,418,True,'marker-start="url(#arrow)"')+text(124,386,'h₁',27)
    s+='<path d="M167 442 V392 H238 V442"/>'
    for x in [177,192,207,222]:s+=circle(x,409,7)
    s+=text(190,385,'R',27)
    return svg(445,470,s)

def insulator_shape(cx,cy,r=45):
    s=arc(cx,cy,r*1.38,math.pi,2*math.pi)+arc(cx,cy,r*1.18,math.pi,2*math.pi)
    s+=circle(cx,cy,r,'fill="white"')
    s+=line(cx-r*1.56,cy,cx-r,cy)+line(cx+r,cy,cx+r*1.56,cy)
    s+='<path d="M'+str(cx-5)+' '+str(cy-r*1.38)+' v-13 h10 v13"/>'
    s+=line(cx,cy+r,cx,cy+r+18)
    return s

def insulator_chain(lang):
    s=''
    for cy in [85,210,335,460]:s+=insulator_shape(120,cy,43)
    s+=text(88,26,'A',26)+text(115,540,'B',26)
    s+=text(120,583,'그림 가' if lang=='ko' else 'Fig. a',23,False,'middle')
    return svg(250,610,s)

def insulator_section(lang):
    cx,cy,R=200,215,100;s=arc(cx,cy,166,math.pi,2*math.pi)
    s+=arc(cx,cy,144,math.pi,2*math.pi)
    s+=circle(cx,cy,R)
    s+=line(cx-182,cy,cx-R,cy)+line(cx+R,cy,cx+182,cy)
    s+=line(cx-182,cy-13,cx-166,cy-13)+line(cx+166,cy-13,cx+182,cy-13)
    for t in np.linspace(math.pi+.08,2*math.pi-.08,32):
        s+=line(cx+102*math.cos(t),cy+102*math.sin(t),cx+142*math.cos(t+.02),cy+142*math.sin(t+.02))
    s+=line(cx,cy,cx-98,cy-105,True)+line(cx,cy,cx+71,cy-71,True)
    s+=text(cx-78,cy-42,'R₂',26)+text(cx+40,cy-29,'R₁',26)+text(cx-7,cy+32,'O',26)
    s+='<rect x="189" y="34" width="22" height="15"/>'
    s+='<rect x="189" y="315" width="22" height="16"/>'
    for x1,y1,x2,y2,ko,en in [(311,98,380,66,'도체 껍질','Conducting shell'),(324,157,380,135,'절연층','Dielectric'),(248,277,380,285,'도체 구','Conducting sphere')]:
        s+=line(x1,y1,x2,y2)+text(x2+7,y2+5,ko if lang=='ko' else en,21,False)
    s+=text(295,380,'그림 나' if lang=='ko' else 'Fig. b',23,False,'middle')
    return svg(590,405,s)

def charged_tube(force=False):
    s=line(85,455,85,22,True)+line(65,423,359,423,True)
    s+='<rect x="78" y="62" width="14" height="361"/>'
    s+=circle(85,247,3.5,'fill="black"')+circle(310,423,3.5,'fill="black"')
    s+=text(44,252,'P',27)
    for x,y,v in [(101,31,'y'),(356,450,'x'),(59,452,'O'),(110,109,'G'),(306,408,'A'),(203,452,'d')]:s+=text(x,y,v,27)
    if force:
        s+=line(85,247,310,423)+text(225,335,'r',27)
        s+=line(85,247,85,174,True)+line(85,247,85,316,True)
        s+=text(101,202,'F',27)+text(117,211,'Ey',18)+text(108,300,'mg',27)
    return svg(390,485,s)

def reflector():
    cx,cy,R=360,155,130;s=circle(cx,cy,R)+line(25,cy,575,cy)
    # Only the right hemisphere is mirrored; hatching identifies that surface.
    for t in np.linspace(-math.pi/2,math.pi/2,41):
        s+=line(cx+R*math.cos(t),cy+R*math.sin(t),cx+(R+11)*math.cos(t+.018),cy+(R+11)*math.sin(t+.018))
    for x in [65,cx-R,cx,cx+R]:s+=circle(x,cy,3,'fill="black"')
    for x,y,v in [(54,138,'P'),(cx-R-20,139,'O₁'),(cx-7,183,'O'),(cx+R+8,151,'O₂'),(137,181,'s')]:s+=text(x,y,v,26)
    return svg(600,315,s)

def laser(lang):
    s=line(65,100,650,100,True)+circle(65,100,4,'fill="black"')
    s+=line(65,100,229,34,True,'stroke-width="2.8"')+arc(65,100,58,-.383,0)
    s+='<path d="M498 86 H362 V70 L292 100 L362 130 V114 H498 Z" fill="white"/>'
    s+=text(209,26,'u',28)+text(133,90,'θ',26)+text(614,82,'z',28)
    s+=text(43,54,'나트륨 원자' if lang=='ko' else 'Sodium atom',22,False)
    s+=text(396,160,'레이저 빔' if lang=='ko' else 'Laser beam',22,False,'middle')
    return svg(690,185,s)

def collision_velocities():
    value=balls(True).rsplit('</g></svg>',1)[0]
    O=np.array([270.,275.]);C=O+np.array([100.,-100*math.sqrt(3)])
    s=circle(270,250,9,'fill="white"')+text(240,247,'D',27)
    s+=line(270,239,270,181,True,'stroke-width="2.8"')+text(242,203,'v',27)
    s+=line(80,275,145,275,True,'stroke-width="2.8"')+text(110,304,'v₁',27)
    s+=line(*(C+np.array([-8,14])),*(C+np.array([-38,66])),True,'stroke-width="2.8"')
    s+=text(C[0]-68,C[1]+48,'v₃',27)
    s+=line(*O,298,373,True,'stroke-width="2.8"')+text(308,387,'v₂',27)
    s+=arc(*O,59,0,math.atan2(98,28))+text(315,334,'θ',27)
    value+=s+'</g></svg>'
    return value.replace('height="340"','height="430"').replace('viewBox="0 0 610 340"','viewBox="0 0 610 430"')

def solar_orbits(lang):
    # A schematic ellipse with the Sun at a focus, a = Earth's orbital radius.
    # The eccentricity is displayed schematically so perihelion remains visible.
    a,e=200.,.95;b=a*math.sqrt(1-e*e);S=np.array([420.,230.])
    u=np.array([.6,-.8]);v=np.array([.8,.6]);Q=S-e*a*u
    P=Q+a*u;B=Q-a*u;E=Q+b*v;A=S+np.array([-100.,-math.sqrt(30000)])
    t=np.linspace(0,2*math.pi,600)
    s=circle(*S,a)+poly([Q+a*math.cos(q)*u+b*math.sin(q)*v for q in t])
    s+=line(*Q,*P,False,'stroke-dasharray="6 5"')+line(*Q,*E,False,'stroke-dasharray="6 5"')
    s+=line(*S,*A)+line(*S,*E)
    for point in [Q,P,E]:s+=circle(*point,3,'fill="black"')
    for theta in np.linspace(0,2*math.pi,8,endpoint=False):
        s+=line(S[0]-7*math.cos(theta),S[1]-7*math.sin(theta),S[0]+7*math.cos(theta),S[1]+7*math.sin(theta))
    s+=line(*E,*(E+u*83),True,'stroke-width="2.5"')
    direction=np.array([-(S-E)[1],(S-E)[0]])/a
    s+=line(*E,*(E+direction*83),True,'stroke-width="2.5"')
    radial=math.atan2(*(S-E)[::-1]);tangent=math.atan2(u[1],u[0])
    s+=arc(*E,49,radial,tangent)
    for x,y,label in [(A[0]-4,A[1]-12,'A'),(B[0]-4,B[1]+31,'B'),(Q[0]-29,Q[1]-3,'Q'),(S[0]-21,S[1]+17,'S'),
                      (E[0]-17,E[1]+31,'E'),(361,133,'rₛₑ'),(353,306,'a'),(313,421,'b'),
                      (E[0]+57,E[1]-73,'v'),(E[0]+76,E[1]+45,'vₑ'),(E[0]+22,E[1]-53,'θ')]:s+=text(x,y,label,27)
    s+=line(*P,453,199)+text(456,198,'P',27)
    s+=text(340,606,'그림 1' if lang=='ko' else 'Fig. 1',26,False,'middle')
    return svg(680,635,s)

def velocity_triangle(lang):
    e=.95;axis=np.array([.6,-.8]);side=np.array([.8,.6])
    d=e*axis-math.sqrt(1-e*e)*side;earth=np.array([-d[1],d[0]])
    E=np.array([150.,400.]);v=axis*150;ve=earth*150;u=v-ve;S=E+d*270
    s=line(*E,*S,True)+line(*E,*(E+v),True,'stroke-width="2.6"')
    s+=line(*E,*(E+u),True,'stroke-width="2.6"')+line(*E,*(E+ve),True,'stroke-width="2.6"')
    s+=line(*(E+u),*(E+v),False,'stroke-dasharray="6 5"')+line(*(E+ve),*(E+v),False,'stroke-dasharray="6 5"')
    s+=poly([E+d*20,E+d*20+earth*20,E+earth*20])
    s+=arc(*E,62,math.atan2(d[1],d[0]),math.atan2(axis[1],axis[0]))
    for x,y,value in [(S[0]+13,S[1],'S'),(E[0]-21,E[1]+17,'E'),(E[0]+u[0]-26,E[1]+u[1]-12,'u'),
                      (E[0]+v[0]+12,E[1]+v[1],'v'),(E[0]+ve[0]+9,E[1]+ve[1]+14,'vₑ'),(E[0]+29,E[1]-65,'θ')]:s+=text(x,y,value,29)
    s+=circle(*S,5,'fill="black"')
    s+=text(200,503,'그림 2' if lang=='ko' else 'Fig. 2',27,False,'middle')
    return svg(400,530,s)

def capacitor(x,y,vertical=True,label='C₀',side=1,label_above=False,label_below=False):
    if vertical:
        s=line(x,y-16,x,y-5)+line(x,y+5,x,y+16)+line(x-17,y-5,x+17,y-5)+line(x-17,y+5,x+17,y+5)
        s+=text(x+23 if side>0 else x-40,y-19 if label_above else y+43 if label_below else y+9,label,22)
    else:
        s=line(x-16,y,x-5,y)+line(x+5,y,x+16,y)+line(x-5,y-17,x-5,y+17)+line(x+5,y-17,x+5,y+17)
        s+=text(x-12,y-25,label,22)
    return s

def circuit(potentials=False):
    s=line(45,30,640,30)+line(45,350,615,350)
    chain=295
    for i in range(4):
        top=30+i*80;bottom=top+80;mid=(top+bottom)/2
        s+=line(chain,top,chain,mid-16)+capacitor(chain,mid,label='C₀')+line(chain,mid+16,chain,bottom)
        s+=circle(chain,top,3,'fill="black"')
    s+=circle(chain,350,3,'fill="black"')+text(628,359,'U₀',24)
    # Each lower terminal has C1 to ground, including the lowest terminal.
    for x,node in [(55,350),(105,270),(155,190),(205,110)]:
        mid=190 if node==350 else 61
        s+=line(x,30,x,mid-16)+capacitor(x,mid,label='C₁',side=-1,label_below=node!=350)+line(x,mid+16,x,node)+line(x,node,chain,node)
        s+=circle(x,30,3,'fill="black"')
    # Each upper terminal has C2 to the high-voltage bottom rail.
    for x,node in [(405,270),(465,190),(525,110),(595,30)]:
        mid=190 if node==30 else 316
        s+=line(chain if node!=30 else x,node,x,node)+line(x,node,x,mid-16)
        s+=capacitor(x,mid,label='C₂',label_above=True)+line(x,mid+16,x,350)+circle(x,350,3,'fill="black"')
    s+=line(640,30,640,72)+line(627,72,653,72)+line(632,78,648,78)+line(637,84,643,84)
    if potentials:
        for y,value in [(110,'U₃'),(190,'U₂'),(270,'U₁')]:s+=text(246,y-10,value,23)
    return svg(700,390,s)

def figure(index,lang):
    builders={1:lambda:balls(),2:piston,3:lambda:insulator_chain(lang),
              4:lambda:insulator_section(lang),5:charged_tube,6:reflector,7:collision_velocities,
              8:lambda:solar_orbits(lang),9:lambda:velocity_triangle(lang),10:circuit,11:lambda:circuit(True),
              12:lambda:charged_tube(True),13:lambda:laser(lang)}
    if index not in builders:raise ValueError('Solution diagram not reviewed: '+str(index))
    return explicit_strokes(builders[index]())

def replace(path,lang):
    panels=json.loads((FOLDER/'placements.json').read_text(encoding='utf8'))['images']
    doc=fitz.open(path)
    panels=[p for p in panels if p['page']<=len(doc)]
    if len(doc)>=4:panels.append({'index':13,'page':4,'rect':[160,558,440,620]})
    drawings={p['index']:fitz.open(stream=figure(p['index'],lang).encode('utf8'),filetype='svg') for p in panels}
    for p in panels:
        page=doc[p['page']-1];r=fitz.Rect(p['rect'])
        if p['index']==1:r=fitz.Rect(325,188,507,311)
        if p['index']==2:r=fitz.Rect(345,65,526,268)
        if p['index']==3:r.y1=676
        if p['index']==4:r=fitz.Rect(280,480,575,675)
        if p['index']==5:r=fitz.Rect(348,280,490,469)
        if p['index']==6:r=fitz.Rect(277,100,510,220)
        if p['index']==7:r=fitz.Rect(300,154,514,319)
        if p['index']==8:r.y1=334
        if p['index']==9:r=fitz.Rect(228,380,350,570)
        if p['index']==10:r=fitz.Rect(135,65,458,215)
        if p['index']==11:r=fitz.Rect(130,316,455,468)
        if p['index']==12:r=fitz.Rect(348,264,500,469)
        if p['index']==13:
            page.add_redact_annot(r,fill=(1,1,1));page.apply_redactions(images=0,graphics=0)
        page.draw_rect(r,color=None,fill=(1,1,1))
        picture=drawings[p['index']];vector=fitz.open(stream=picture.convert_to_pdf(),filetype='pdf')
        page.show_pdf_page(r,vector,0,keep_proportion=True);vector.close()
    temp=Path(str(path)+'.figures.pdf');doc.save(temp,garbage=4,deflate=True);doc.close();temp.replace(path)
    for p in drawings.values():p.close()

def proof():
    FOLDER.mkdir(parents=True,exist_ok=True);out=ROOT/'tmp/cpho-build/2007-figures'
    out.mkdir(parents=True,exist_ok=True)
    for index in range(1,14):
        for lang in ['ko','en']:
            value=figure(index,lang);(FOLDER/f'figure-{index}-{lang}.svg').write_text(value,encoding='utf8')
            doc=fitz.open(stream=value.encode('utf8'),filetype='svg')
            doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(out/f'proof-{index}-{lang}.png')

if __name__=='__main__':proof()
