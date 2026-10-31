"""Bilingual scientific line diagrams for CPhO 2023.

Optical ray paths are computed from Snell's law on a spherical drop. The
effective-potential plots use the source's analytic decomposition, rather than
an artist's approximation. Remaining source data plots retain measured point
coordinates when redrawn. All twenty figure replacements are reviewed in both
languages, including the three native captions and the vector pendulum.
"""
from pathlib import Path
import html,json,math,re
import numpy as np
import pymupdf as fitz
from cpho_2025_figures import line,text as roman_text,arrow_head
from svg_pdf import explicit_strokes
ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'tools/ko/cpho/2023/figures'
COLORS=['#bb1919','#dd6c17','#b7a91c','#31864b','#3276a4','#595b9b','#835b96']

def text(x,y,value,size=25,italic=True,anchor='start'):
    if not re.search('[가-힣]',value):return roman_text(x,y,value,size,italic,anchor)
    # Use actual bundled font outlines, avoiding SVG fallback-font advances.
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    path=TextPath((0,0),value,size=size,prop=FontProperties(fname=str(ROOT/'tools/ko/fonts/NotoSansKR-Regular.ttf')))
    bounds=path.get_extents()
    if anchor=='middle':x-=(bounds.x0+bounds.x1)/2
    elif anchor=='end':x-=bounds.x1
    parts=[]
    for vertices,code in path.iter_segments(curves=True):
        if code==79:parts.append('Z');continue
        command={1:'M',2:'L',3:'Q',4:'C'}[code]
        coords=[f'{x+vertices[j]:.3f} {y-vertices[j+1]:.3f}' for j in range(0,len(vertices),2)]
        parts.append(command+' '.join(coords))
    return '</g><path d="'+' '.join(parts)+'" fill="black" stroke="none"/><g fill="none" stroke="#111" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'

def svg(width,height,body,x=0,y=0):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{x} {y} {width} {height}"><g fill="none" stroke="#111" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+body+'</g></svg>'

def poly(points,attrs=''):
    return '<polyline points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in points)+f'" {attrs}/>'

def circle(x,y,r,attrs=''):
    return f'<circle cx="{x}" cy="{y}" r="{r}" {attrs}/>'

def arc(cx,cy,r,a,b,attrs=''):
    points=[(cx+r*math.cos(t),cy+r*math.sin(t)) for t in np.linspace(a,b,120)]
    return poly(points,attrs)

def raytrace(impact,n=4/3,reflections=2):
    r=np.array([-math.sqrt(1-impact**2),impact]);k=np.array([1.,0.])
    def refract(k,normal,eta):
        ci=-np.dot(k,normal);return eta*k+(eta*ci-math.sqrt(max(0,1-eta*eta*(1-ci*ci))))*normal
    internal=refract(k,r,1/n);points=[r.copy()];out=[]
    for j in range(reflections+1):
        r=r-2*np.dot(r,internal)*internal;points.append(r.copy())
        out.append(refract(internal,-r,n))
        internal=internal-2*np.dot(internal,r)*r
    return points,out

def finish_ray(p,k,bounds):
    x0,y0,x1,y1=bounds;ts=[]
    for dim,low,high in [(0,x0,x1),(1,y0,y1)]:
        if abs(k[dim])>1e-8:
            ts.extend(t for t in [(low-p[dim])/k[dim],(high-p[dim])/k[dim]] if t>1e-5)
    return p+min(ts)*k

def rainbow(lang,extra=False):
    if not extra:
        s=line(25,250,575,250)
        for i,color in enumerate(COLORS):
            s+=arc(300,250,183-i*2.7,math.pi,2*math.pi,f'stroke="{color}" stroke-width="2.4"')
            s+=arc(300,250,213+i*2.7,math.pi,2*math.pi,f'stroke="{color}" stroke-width="1.6"')
        s+=circle(300,230,4,'fill="white"')+line(300,234,300,246)+line(300,239,294,243)+line(300,239,306,243)
        s+=line(300,246,295,250)+line(300,246,305,250)
        return svg(600,270,s)
    s=''
    for i,color in enumerate(COLORS):s+=arc(-180,460,510-i*4,-1.12,-.07,f'stroke="{color}" stroke-width="3.1"')
    for radius in [471,460,450]:s+=arc(-180,460,radius,-1.12,-.07,'stroke="#6b7b7c" stroke-width="1.2"')
    s+=text(25,205,'과잉무지개' if lang=='ko' else 'Supernumerary',18)
    s+=line(100,219,192,230,True)
    return svg(400,470,s)

def drop_paths(lang,family=False):
    if family:
        cx,cy,R=200,235,170;s=circle(cx,cy,R)
        for impact in np.linspace(.08,.98,13):
            points,out=raytrace(float(impact),reflections=1)
            convert=lambda r:np.array([cx+R*r[0],cy-R*r[1]])
            p=[convert(r) for r in points]
            s+=line(12,p[0][1],p[0][0],p[0][1])
            s+=poly(p)
            end=finish_ray(p[-1],np.array([out[-1][0],-out[-1][1]]),[12,10,388,505])
            s+=line(*p[-1],*end,True)
        return svg(400,520,s)
    cx,cy,R=305,195,140;s=circle(cx,cy,R,'fill="#fbfbfb"')
    points,out=raytrace(.70,reflections=2)
    convert=lambda r:np.array([cx+R*r[0],cy-R*r[1]])
    p=[convert(r) for r in points]
    s+=line(35,p[0][1],*p[0],True,'stroke-width="3"')
    for j in range(2):s+=line(*p[j],*p[j+1],True,'stroke-width="3"')
    s+=line(*p[2],*p[3],True)
    for j in range(3):
        direction=np.array([out[j][0],-out[j][1]])
        end=finish_ray(p[j+1],direction,[30,12,565,377])
        s+=line(*p[j+1],*end,True)
        lx,ly=[(470,245),(170,385),(45,43)][j]
        s+=text(lx,ly,f'{j}차 광' if lang=='ko' else f'Order {j}',19)
    s+=line(p[0][0]-38,p[0][1]-38,cx,cy,False,'stroke-dasharray="5 5"')
    s+=text(p[0][0]-12,p[0][1]-19,'i',23)
    s+=arc(p[0][0],p[0][1],28,math.pi,2*math.pi+math.atan2(p[0][1]-cy,p[0][0]-cx))
    s+=text(40,p[0][1]-18,'입사광' if lang=='ko' else 'Incident',20)
    s+=line(*p[2],p[2][0]+95,p[2][1],True,'stroke-dasharray="5 5"')
    outgoing=np.array([out[1][0],-out[1][1]]);angle=math.atan2(outgoing[1],outgoing[0])
    s+=arc(p[2][0],p[2][1],43,0,angle)
    s+=text(338,375,'편향각' if lang=='ko' else 'Deviation',19)
    return svg(600,410,s)

def potential(strong):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import io
    plt.rcParams.update({'font.family':'STIXGeneral','mathtext.fontset':'stix','svg.fonttype':'path'})
    fig,ax=plt.subplots(figsize=(4.5,3.6));phi=np.linspace(-3.5,3.5,801)
    gravity=1-np.cos(phi);shaking=(.65 if strong else .20)*(1-np.cos(2*phi))
    ax.plot(phi,gravity+shaking,c='black',lw=1.7)
    ax.plot(phi,gravity,c='#555',lw=1.0,ls='--')
    ax.plot(phi,shaking,c='#777',lw=1.0,ls=':')
    for x in [-math.pi,math.pi]:ax.plot([x,x],[0,2],c='black',lw=1,ls='--')
    ax.set_xlim(-3.65,3.85);ax.set_ylim(-.08,2.8 if strong else 2.3)
    ax.spines[['right','top']].set_visible(False);ax.spines[['left','bottom']].set_position('zero')
    ax.set_xticks([-math.pi,0,math.pi],labels=[r'$-\pi$','0',r'$\pi$'],fontsize=14)
    ax.set_yticks([.5,1,1.5,2]+([2.5] if strong else []));ax.tick_params(width=.7,length=3,labelsize=10)
    ax.plot([ax.get_xlim()[1]],[0],'>k',ms=5,clip_on=False)
    ax.plot([0],[ax.get_ylim()[1]],'^k',ms=5,clip_on=False)
    ax.text(.25,ax.get_ylim()[1]-.12,r'$V_{\mathrm{eff}}(\varphi)$',fontsize=17)
    ax.text(3.5,.08,r'$\varphi$',fontsize=17)
    fig.tight_layout(pad=.6);buffer=io.StringIO();fig.savefig(buffer,format='svg');plt.close(fig)
    return buffer.getvalue()

def cross_section_plot(lang):
    """Trace the supplied measured plot ink; do not invent numerical data."""
    import cv2,io
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.path import Path as PlotPath
    from matplotlib.patches import PathPatch
    placement=next(item for item in json.loads((FIG/'placements.json').read_text(encoding='utf8'))['images'] if item['audit_index']==9)
    source=fitz.open(ROOT/'tmp/source-audit/CPhO_2023_T_ZH.pdf')
    pix=source[placement['page']-1].get_pixmap(matrix=fitz.Matrix(3,3),clip=fitz.Rect(placement['rect']),alpha=False)
    image=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
    grey=cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)
    sx,sy=pix.width/251,pix.height/341
    left,top,right,bottom=[int(v) for v in [64*sx,22*sy,227*sx,290*sy]]
    ink=(grey[top:bottom,left:right]<205).astype(np.uint8)*255
    # Remove the old theta annotation, which is redrawn as mathematical text.
    ink[max(0,int(212*sy)-top):int(242*sy)-top,max(0,int(84*sx)-left):int(178*sx)-left]=0
    contours,hierarchy=cv2.findContours(ink,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    vertices=[];codes=[]
    for contour in contours:
        if abs(cv2.contourArea(contour))<.35:continue
        points=cv2.approxPolyDP(contour,.16,True).reshape(-1,2).astype(float)
        if len(points)<3:continue
        points[:,0]=(points[:,0]+left)/sx;points[:,1]=(points[:,1]+top)/sy
        energy=10+(points[:,0]-61)*35/168
        cross_section=10**(3-(points[:,1]-17)/69.5)
        xy=list(zip(energy,cross_section));vertices.extend(xy+[xy[0]])
        codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(xy)-1)+[PlotPath.CLOSEPOLY])
    plt.rcParams.update({'font.family':'STIXGeneral','mathtext.fontset':'stix','svg.fonttype':'path'})
    fig,ax=plt.subplots(figsize=(3.8,5.3));ax.set_yscale('log');ax.set_xlim(10,45);ax.set_ylim(.1,1000)
    ax.add_patch(PathPatch(PlotPath(vertices,codes),facecolor='black',edgecolor='none'))
    ax.set_xticks(range(10,46,5));ax.set_yticks([1,10,100,1000],labels=['1','10','100','1000'])
    ax.minorticks_off();ax.tick_params(direction='in',labelsize=11)
    xlabel='α 입자 운동에너지 / MeV' if lang=='ko' else r'$\alpha$-particle kinetic energy / MeV'
    ylabel='미분 단면적 (상대값)' if lang=='ko' else 'Differential cross section (relative)'
    # Matplotlib uses the same bundled Hangul font as the translated text.
    from matplotlib.font_manager import FontProperties
    hangul=FontProperties(fname=str(ROOT/'tools/ko/fonts/NotoSansKR-Regular.ttf'),size=11)
    ax.set_xlabel(xlabel,fontproperties=hangul if lang=='ko' else None)
    ax.set_ylabel(ylabel,fontproperties=hangul if lang=='ko' else None)
    ax.text(16,.7,r'$\theta=60^\circ$',fontsize=17)
    for spine in ax.spines.values():spine.set_linewidth(.9)
    fig.tight_layout(pad=.6);buffer=io.StringIO();fig.savefig(buffer,format='svg');plt.close(fig)
    return buffer.getvalue()

def colour_order(lang):
    centres=[(155,35),(240,60),(325,100),(395,145),(430,173),(500,255),(540,335),(565,417)]
    impacts=[-.60,-.75,-.89,-.95,.86,.65,.40,.15];s=''
    for j,((cx,cy),impact) in enumerate(zip(centres,impacts)):
        k=2 if j<4 else 1;n=(1.344-(j*.005) if j<4 else 1.329+(j-4)*.005)
        points,out=raytrace(impact,n,k)
        p=[np.array([cx+17*r[0],cy-17*r[1]]) for r in points]
        s+=circle(cx,cy,17)+line(cx-64,p[0][1],*p[0])+poly(p)
        direction=np.array([out[k][0],-out[k][1]]);end=p[-1]+direction*62
        s+=line(*p[-1],*end,True)
    for x,y,ko,en in [(120,100,'보라','Violet'),(315,213,'빨강','Red'),(365,258,'빨강','Red'),(476,461,'보라','Violet')]:
        s+=text(x,y,ko if lang=='ko' else en,20,False)
    s+=text(220,180,'k = 2',22)+text(206,205,'부무지개' if lang=='ko' else 'Secondary',19,False)
    s+=text(420,370,'k = 1',22)+text(405,395,'주무지개' if lang=='ko' else 'Primary',19,False)
    s+=line(20,517,190,517)+circle(90,471,7,'fill="black"')+line(90,478,90,500,False,'stroke-width="8"')
    s+=line(90,500,78,516,False,'stroke-width="6"')+line(90,500,103,516,False,'stroke-width="6"')
    s+=line(90,484,77,494,False,'stroke-width="5"')+line(90,484,104,495,False,'stroke-width="5"')
    return svg(600,540,s)

def rutherford_apparatus(lang):
    cx,cy=325,225;s=circle(cx,cy,173)
    s+='<rect x="50" y="196" width="85" height="58" fill="white"/>'+circle(85,225,18)
    s+=line(105,225,325,225,True,'stroke-width="2.7"')
    s+=line(325,140,325,310,False,'stroke-width="2.5"')
    for angle in [0,-math.pi/4,-3*math.pi/4]:
        u=np.array([math.cos(angle),math.sin(angle)]);v=np.array([-u[1],u[0]])
        origin=np.array([cx,cy])
        for start,end,width,fill in [(121,127,44,'black'),(143,218,28,'white'),(218,247,15,'black')]:
            corners=[origin+u*start+v*width/2,origin+u*end+v*width/2,origin+u*end-v*width/2,origin+u*start-v*width/2]
            s+='<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in corners)+f'" fill="{fill}"/>'
        for t in [156,170,184,198]:s+=line(*(origin+u*t-v*12),*(origin+u*(t+8)+v*12))
    s+=line(cx,cy,cx+85,cy-85,True,'stroke-width="2.3"')
    s+=line(cx,cy,cx+108,cy,False,'stroke-dasharray="5 5"')+arc(cx,cy,55,-math.pi/4,0)
    s+=text(cx+57,cy-17,'θ',25)+text(195,248,'α',25)
    for x,y,ko,en in [(35,290,'방사선원','Source'),(272,350,'금박','Gold foil'),(483,375,'현미경','Microscope')]:
        s+=text(x,y,ko if lang=='ko' else en,26 if ko!='현미경' else 24,False)
    if lang=='ko':s+=text(500,309,'형광막',26,False)
    else:s+=text(500,303,'Fluorescent',22,False)+text(500,329,'screen',22,False)
    return svg(620,420,s)

def scattering_geometry(mode):
    # Repulsive Coulomb hyperbola with incoming impact parameter b.
    a,b=1.,2.5;e=math.sqrt(1+(b/a)**2);limit=math.acos(1/e)
    theta=math.pi-2*limit;axis=(math.pi+theta)/2;p=b*b/a
    psi=np.linspace(limit-.015,-limit+.015,1600);radius=p/(e*np.cos(psi)-1)
    phi=axis+psi;x=radius*np.cos(phi);y=radius*np.sin(phi)-b
    visible=(x>-8.5)&(x<8.5)&(y<6.6)
    points=np.stack([x[visible],y[visible]],axis=1)
    X=lambda q:np.array([300+30*q[0],235-30*q[1]])
    curve=[X(q) for q in points];s=poly(curve,'stroke-width="3"')
    s+=arrow_head(*curve[-1],*(curve[-1]-curve[-4]))
    A=X([0,-b]);C=X([-a,0])
    s+=line(35,235,565,235,False,'stroke-dasharray="6 5"')
    s+=line(*X([-5,math.tan(theta)*(-5+a)]),*X([8,math.tan(theta)*(8+a)]),False,'stroke-dasharray="6 5"')
    s+=line(A[0]-35,A[1],570,A[1],False,'stroke-dasharray="6 5"')
    s+=line(560,235,560,A[1],True,'marker-start="url(#arrow)"')
    s+=text(567,(235+A[1])/2+7,'b',25)+circle(*A,3,'fill="black"')+text(A[0]-8,A[1]+30,'A',24)
    s+=arc(C[0],C[1],52,-theta,0)+text(C[0]+57,C[1]-15,'θ',24)
    if mode!=1:s+=text(49,218,'α',25)
    if mode==1:
        j=int(np.argmin(abs(phi-axis)));P=X([x[j],y[j]])
        s+=line(*A,*P,True)+text((A[0]+P[0])/2+13,(A[1]+P[1])/2,'r',24)
        force=(P-A);force=force/np.linalg.norm(force)*62
        s+=line(*P,*(P+force),True,'stroke-width="3"')+text(P[0]-43,P[1]-65,'F',25)
        tangent=np.array([math.sin(axis),math.cos(axis)])*72
        s+=line(*P,*(P+tangent),True)+text(P[0]+75,P[1]-45,'v',24)
        s+=text(49,217,'v₀',24)
        angle=math.atan2(P[1]-A[1],P[0]-A[0]);s+=arc(*A,43,math.pi,angle+2*math.pi)
        s+=text(A[0]-54,A[1]-18,'φ',24)
    else:
        # At closest approach the force-centre radius is normal to velocity.
        P=X([p/(e-1)*math.cos(axis),p/(e-1)*math.sin(axis)-b])
        s+=line(*A,*P)
        if mode==2:
            s+=text(40,267,'(m, z, E)',22)
            s+=line(90,110,145,110,True)+line(90,110,90,55,True)
            s+=text(146,114,'x',23)+text(88,45,'y',23)+circle(180,65,7)+circle(180,65,1.8,'fill="black"')+text(176,44,'ẑ',24)
    return svg(600,380,s)

def magnetic_target(lang):
    s=circle(400,190,200,'stroke-dasharray="6 5"')
    s+='<path d="M28 240 V210 H75 V240 M28 260 V290 H75 V260 M725 240 V210 H772 V290 H725 V260"/>'
    s+=line(53,250,210,250,True)+line(590,250,747,250,True)
    t=np.linspace(0,math.pi/2,160)
    s+=poly([(210+190*math.sin(q),60+190*math.cos(q)) for q in t])
    s+=poly([(590-190*math.cos(q),60+190*math.sin(q)) for q in t])
    s+=line(362,60,438,60,False,'stroke-width="5"')+circle(400,272,13)
    s+=line(392,264,408,280)+line(392,280,408,264)+text(389,313,'B',27)
    for x,y,ko,en in [(400,38,'표적','Target'),(70,328,'α 입자원','α source'),(730,328,'α 입자 검출기','α detector'),(400,430,'자기장 편향 영역','Magnetic deflection region')]:
        s+=text(x,y,ko if lang=='ko' else en,21,False,'middle')
    return svg(800,470,s,y=-20)

def pendulum(lang):
    s=line(80,75,80,300,False,'stroke-dasharray="6 5"')+line(80,75,218,263,False,'stroke-width="4"')
    s+=circle(80,75,6,'fill="black"')+line(80,75,80,15,True)
    s+=arc(80,75,61,math.pi/2,math.atan2(188,138))
    s+=text(95,68,'O',29)+text(95,25,'z(t)',29)+text(96,149,'θ',29)
    s+=text(130,363,'그림 2a' if lang=='ko' else 'Fig. 2a',26,False,'middle')
    return svg(260,400,s)

def ellipse(cx,cy,rx,ry,attrs=''):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" {attrs}/>'

def coil(cx,top,bottom,radius=15,pitch=24):
    turns=(bottom-top)/pitch
    t=np.linspace(0,2*math.pi*turns,max(40,int(turns*45)))
    return poly([(cx+radius*math.sin(q),top+pitch*q/(2*math.pi)+radius*.22*math.cos(q)) for q in t])

def scattering_annuli():
    s=line(25,165,650,165,True)
    # An incident impact-parameter annulus maps onto a solid-angle annulus.
    for rx,ry in [(23,47),(30,60)]:s+=ellipse(155,165,rx,ry)
    for rx,ry in [(65,151),(75,165)]:s+=ellipse(545,165,rx,ry)
    for t in np.linspace(0,2*math.pi,33):
        s+=line(155+23*math.cos(t),165+47*math.sin(t),155+30*math.cos(t),165+60*math.sin(t))
        s+=line(545+65*math.cos(t),165+151*math.sin(t),545+75*math.cos(t),165+165*math.sin(t))
    # The two rays delimit b..b+db and theta..theta+dtheta.
    for start,end in [((35,118),(532,18)),((35,105),(542,1))]:
        a=np.array(start);b=np.array(end)
        control1=np.array([270.,start[1]+8]);control2=np.array([430.,end[1]+20])
        ts=np.linspace(0,1,160)
        pts=[(1-t)**3*a+3*(1-t)**2*t*control1+3*(1-t)*t*t*control2+t**3*b for t in ts]
        s+=poly(pts,'stroke-width="2.5"')
    s+=circle(280,165,5,'fill="black"')+text(267,197,'Ze',24)
    for xx,yy in [(545,14),(545,0)]:s+=line(280,165,xx,yy,False,'stroke-dasharray="6 5"')
    s+=arc(280,165,66,-.56,0)+arc(280,165,88,-.62,0)
    s+=text(345,148,'θ',25)+text(375,126,'θ + dθ',24)
    s+=line(65,165,65,118,True,'marker-start="url(#arrow)"')+text(72,151,'b',23)
    s+=line(65,104,65,88,True)+text(72,97,'db',23)
    s+=text(79,219,'dσ',25)
    return svg(680,375,s,y=-20)

def dirac_comparison(lang):
    s=''
    for cx,solenoid in [(115,False),(395,True)]:
        cy=108
        for angle in np.linspace(0,2*math.pi,8,endpoint=False):
            dx,dy=math.cos(angle),math.sin(angle)
            s+=line(cx,cy,cx+90*dx,cy+90*dy)
            s+=arrow_head(cx+65*dx,cy+65*dy,dx,dy)
        s+=text(cx+23,27,'B',28)+text(cx-53,92,'g',27)
        t=np.linspace(0,1,500)
        backbone=[(cx+27*math.sin(2*math.pi*u),cy+u*345) for u in t]
        s+=poly(backbone,'stroke-dasharray="6 5"' if not solenoid else '')
        if solenoid:
            loops=[(x+10*math.sin(u*2*math.pi*18),y+4*math.cos(u*2*math.pi*18)) for u,(x,y) in zip(t,backbone)]
            s+=poly(loops)
        else:
            for k in range(12):
                q=40+k*36
                if q>=len(backbone):continue
                x,y=backbone[q];dx,dy=np.array(backbone[max(0,q-5)])-backbone[q]
                s+=arrow_head(x,y,dx,dy,size=7,width=5)
        s+=line(cx+26,245,cx+26,208,True,'stroke-width="3.5"')
        s+=text(cx+43,235,'dm' if solenoid else 'g dℓ',25)
    s+=text(255,497,'그림 7a' if lang=='ko' else 'Fig. 7a',24,False,'middle')
    return svg(520,520,s)

def monopole_coordinates(lang,solution=False):
    O=np.array([135.,203.]);P=np.array([230.,78.]);R=np.array([135.,355.]);foot=np.array([230.,265.])
    s=line(135,475,135,15,True)+line(*O,308,203,True)+line(*O,27,296,True)
    s+=coil(135,214,470,16,24)
    s+=ellipse(135,78,96,21,'stroke-dasharray="6 5"')
    s+=arrow_head(43,72,-.3,.7,size=7,width=6)
    s+=line(*O,*P,True,'stroke-width="2.8"')
    s+=line(*P,*foot,False,'stroke-dasharray="5 5"')+line(*O,*foot,False,'stroke-dasharray="5 5"')
    s+=arc(*O,65,-math.pi/2,math.atan2(P[1]-O[1],P[0]-O[0]))
    s+=arc(*O,57,.58,2.43)+arrow_head(92,241,-.7,-.5,size=7,width=6)
    s+=circle(*O,8,'fill="black"')
    for x,y,value in [(152,24,'z'),(300,232,'y'),(22,321,'x'),(108,186,'g'),(157,122,'θ'),(99,272,'φ'),(38,121,'L'),(187,148,'r')]:s+=text(x,y,value,29)
    if solution:
        s+=line(*O,*R,True,'stroke-width="3.5"')+text(86,337,'r′',29)
        s+=line(*R,*P,True,'stroke-width="2.7"')+text(198,307,'r − r′',26)
    else:s+=text(167,520,'그림 7b' if lang=='ko' else 'Fig. 7b',27,False,'middle')
    return svg(335,540 if not solution else 495,s)

def triangular_loop(lang):
    cx=190;s=line(cx,412,cx,14,True)+coil(cx,107,184,15,23)+coil(cx,226,403,15,23)
    vertices=[(20,181),(261,151),(311,308),(20,181)]
    s+=poly(vertices,'stroke-width="2.7"')+circle(cx,115,8,'fill="black"')
    for x,y,value in [(204,34,'z'),(210,107,'g'),(128,163,'a'),(287,234,'a'),(133,270,'a')]:s+=text(x,y,value,31)
    s+=text(177,460,'그림 7c' if lang=='ko' else 'Fig. 7c',27,False,'middle')
    return svg(355,485,s)

def interferometer(lang):
    s=line(34,162,650,162,False,'stroke-dasharray="10 4 2 4"')
    # Source aperture, double slit and the distant observation screen.
    for xx,segments in [(44,[(70,151),(173,254)]),(135,[(26,104),(126,199),(221,290)])]:
        for y1,y2 in segments:s+=f'<rect x="{xx}" y="{y1}" width="7" height="{y2-y1}" fill="white"/>'
    s+='<rect x="614" y="16" width="7" height="275" fill="white"/>'
    s+=line(52,162,135,115)+line(52,162,135,210)
    s+=line(142,115,614,56,False,'stroke-width="2.8"')+line(142,210,614,56,False,'stroke-width="2.8"')
    s+=circle(183,162,16,'fill="white"')+circle(183,162,2.5,'fill="black"')
    s+=line(110,162,614,56,False,'stroke-dasharray="5 5"')
    s+=arc(183,162,62,-.207,0)
    s+=line(96,115,96,210,True,'marker-start="url(#arrow)"')
    s+=line(143,278,613,278,True,'marker-start="url(#arrow)"')
    s+=line(645,162,645,56,True,'marker-start="url(#arrow)"')
    for x,y,value in [(78,97,'d'),(101,186,'O′'),(249,146,'θ'),(341,79,'r₁'),(428,143,'r₂'),(375,307,'D'),(653,111,'x'),(627,187,'O')]:s+=text(x,y,value,28)
    s+=text(25,130,'전자' if lang=='ko' else 'Electron',19,False,'end')
    s+=text(25,155,'원' if lang=='ko' else 'source',19,False,'end')
    s+=text(204,228,'무한히 긴 솔레노이드' if lang=='ko' else 'Infinitely long solenoid',21,False)
    return svg(740,330,s,x=-50)

def _figure(index,lang):
    if index==1:return rainbow(lang)
    if index==2:return drop_paths(lang,True)
    if index==3:return drop_paths(lang)
    if index==4:return rainbow(lang,True)
    if index==5:return colour_order(lang)
    if index in [6,7]:return potential(index==6)
    if index==8:return rutherford_apparatus(lang)
    if index==9:return cross_section_plot(lang)
    if index in [10,11,12]:return scattering_geometry({10:0,11:1,12:2}[index])
    if index==13:return scattering_annuli()
    if index==14:return magnetic_target(lang)
    if index==15:return dirac_comparison(lang)
    if index==16:return monopole_coordinates(lang)
    if index==17:return triangular_loop(lang)
    if index==18:return interferometer(lang)
    if index==19:return monopole_coordinates(lang,True)
    if index==20:return pendulum(lang)
    raise ValueError(f'Figure {index} has not been reviewed yet')

def figure(index,lang):return explicit_strokes(_figure(index,lang))

def replace(path,lang):
    """Insert all reviewed figures at their original positions, before save."""
    placements=json.loads((FIG/'placements.json').read_text(encoding='utf8'))['images']
    panels=[]
    for item in placements:
        index=item['audit_index'];rect=list(item['rect'])
        # These three source captions intersect the bitmap and are owned here.
        if index in [15,16,17]:rect[3]={15:244.,16:553.,17:716.}[index]
        panels.append((item['page']-1,index,fitz.Rect(rect)))
    panels.append((4,20,fitz.Rect(428,72,508,193)))
    # Build every vector first so an error cannot leave a partially edited PDF.
    drawings={index:fitz.open(stream=figure(index,lang).encode('utf8'),filetype='svg') for _,index,_ in panels}
    doc=fitz.open(path)
    for pi,index,rect in panels:
        page=doc[pi]
        # Restrict text removal to native labels. Some source math fonts have
        # oversized boxes reaching into neighbouring raster figure rectangles.
        native={15:(407.4,230.28,445.56,243.84),
                16:(438.96,539.16,477.12,552.72),
                17:(464.16,702.12,502.32,715.80),20:tuple(rect)}
        if index in native:
            page.add_redact_annot(fitz.Rect(native[index]),fill=(1,1,1))
            page.apply_redactions(images=0,graphics=0)
        page.draw_rect(rect,color=None,fill=(1,1,1),overlay=True)
        picture=drawings[index];vector=fitz.open(stream=picture.convert_to_pdf(),filetype='pdf')
        page.show_pdf_page(rect,vector,0,keep_proportion=True)
        vector.close()
    temporary=Path(str(path)+'.figures.pdf');doc.save(temporary,garbage=4,deflate=True);doc.close()
    for picture in drawings.values():picture.close()
    temporary.replace(path)
    return {'figures':len(panels),'language':lang,'source':'CPhO_2023_T_ZH.pdf','source_pages':36}

def proof():
    FIG.mkdir(parents=True,exist_ok=True)
    for n in range(1,21):
        for lang in ['ko','en']:
            value=figure(n,lang);(FIG/f'figure-{n}-{lang}.svg').write_text(value,encoding='utf8')
            picture=fitz.open(stream=value.encode('utf8'),filetype='svg')
            picture[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(ROOT/f'tmp/cpho-build/2023-figures/proof-{n}-{lang}.png')

if __name__=='__main__':proof()
