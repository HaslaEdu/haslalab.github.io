"""Fit smooth code-native paths to the established KMChC programme emblem.

The PNG source stays unchanged. This is a derived display asset, not an official
vector master. Colour silhouettes are measured from the official account crop;
the centred benzene hexagon and circle are regular geometric primitives.
"""
from pathlib import Path
import argparse
import json
import hashlib
import numpy as np
from PIL import Image

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path,help='Unchanged official-account 104x128 PNG crop')
parser.add_argument('output_directory',type=Path,help='Directory for light/dark display SVGs and provenance')
args=parser.parse_args()
OUT=args.output_directory
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=args.source
source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
if source_sha!='71301ac77d019946c13437087824e2708cd3af4b1b57252e2788cda9db06e858':
    raise ValueError('Review the fixed benzene geometry and tip measurement after changing the source crop')
a = np.asarray(Image.open(SOURCE).convert('RGB')).astype(np.int16)
if a.shape[:2]!=(128,104):
    raise ValueError('The measured programme emblem crop must be reviewed after a source change')

def boundary(mask):
    edges = {}
    h,w=mask.shape
    def add(p,q): edges.setdefault(p,[]).append(q)
    for y,x in zip(*np.nonzero(mask)):
        if y==0 or not mask[y-1,x]: add((x,y),(x+1,y))
        if x==w-1 or not mask[y,x+1]: add((x+1,y),(x+1,y+1))
        if y==h-1 or not mask[y+1,x]: add((x+1,y+1),(x,y+1))
        if x==0 or not mask[y,x-1]: add((x,y+1),(x,y))
    loops=[]
    while edges:
        p=next(iter(edges)); start=p; line=[]
        while True:
            line.append(p)
            q=edges[p].pop()
            if not edges[p]: del edges[p]
            p=q
            if p==start: break
            if p not in edges: break
        loops.append(np.asarray(line,float))
    return max(loops,key=len)

def basis(u,knots,n,degree):
    # Work just inside the last knot; the limit has the correct endpoint value.
    u=np.minimum(np.asarray(u),1-1e-10)
    N=np.stack([(u>=knots[i])&(u<knots[i+1]) for i in range(len(knots)-1)],axis=1).astype(float)
    for p in range(1,degree+1):
        M=np.zeros((len(u),len(knots)-p-1))
        for i in range(M.shape[1]):
            l=knots[i+p]-knots[i]; r=knots[i+p+1]-knots[i+1]
            if l: M[:,i]+=(u-knots[i])/l*N[:,i]
            if r: M[:,i]+=(knots[i+p+1]-u)/r*N[:,i+1]
        N=M
    return N[:,:n]

def path_for(mask,tip,n=15,tip_override=None):
    line=boundary(mask)
    # Start/end at the pointed blade tip, allowing distinct endpoint tangents.
    i=int(np.argmin(np.sum((line-np.asarray(tip))**2,axis=1)))
    line=np.concatenate((line[i:],line[:i],line[i:i+1]))
    if tip_override is not None:
        # The very thin red tip is broken into JPEG speckles in the source;
        # join its visible extremity to the clean continuous body silhouette.
        point=np.asarray(tip_override,float)[None,:]
        line=np.concatenate((point,line[:-1],point))
    length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(line,axis=0),axis=1))]
    u=length/length[-1]
    knots=np.r_[np.zeros(4),np.linspace(0,1,n-2)[1:-1],np.ones(4)]
    B=basis(u,knots,n,3)
    p=np.zeros((n,2)); p[0]=p[-1]=line[0]
    p[1:-1]=np.linalg.lstsq(B[:,1:-1],line-B[:,[0]]*p[0]-B[:,[-1]]*p[-1],rcond=None)[0]
    def pos(x): return basis([x],knots,n,3)[0]@p
    def deriv(x):
        N=basis([x],knots,n+1,2)[0]; D=np.zeros(n)
        for j in range(n):
            l=knots[j+3]-knots[j]; r=knots[j+4]-knots[j+1]
            if l: D[j]+=3*N[j]/l
            if r: D[j]-=3*N[j+1]/r
        return D@p
    f=lambda q:f'{q[0]:.3f},{q[1]:.3f}'
    result='M'+f(p[0])
    for x0,x1 in zip(np.unique(knots)[:-1],np.unique(knots)[1:]):
        q0,q3=pos(x0),pos(x1); d=x1-x0
        result+=' C'+f(q0+deriv(x0)*d/3)+' '+f(q3-deriv(x1)*d/3)+' '+f(q3)
    fitted=B@p
    return result+' Z',{'rmsBoundaryError':float(np.sqrt(np.mean(np.sum((fitted-line)**2,axis=1)))), 'maxBoundaryError':float(np.sqrt(np.max(np.sum((fitted-line)**2,axis=1)))), 'controlPoints':n}

blue=(a[:,:,2]>a[:,:,0]+60)&(a[:,:,0]<110)&(a[:,:,1]<150)
red=(a[:,:,0]>150)&(a[:,:,0]>a[:,:,1]+90)&(a[:,:,0]>a[:,:,2]+65)
bp,be=path_for(blue,(24,96),18)
rp,re=path_for(red,(80,31),18,tip_override=(81.5,31.5))
report={'source':SOURCE.as_posix(),'sourceSha256':source_sha,'sourceDimensions':[104,128], 'classification':'derived-display-vector','blue':be,'red':re,
        'sourcePage':'https://olympiad.kchem.org/',
        'officialSourceAsset':'https://yt3.googleusercontent.com/ytc/AIdro_myRCrkt6XHYP2vgNYNsq8SQa1PSuwD7haIaGxLowpwkg=s900-c-k-c0x00ffffff-no-rj',
        'officialHeaderReference':'https://d2j16w31g89z0j.cloudfront.net/site/chemolympiad/header/olympiad_logo.png',
        'lightColourRGB':{'blue':[12,76,162],'red':[237,27,36]},'darkColourAdjustment':{'gamma':0.72,'whiteBackground':False},
        'notes':'Smooth cubic B-spline silhouettes fitted to the existing official-account source crop, with the established regular benzene hexagon/circle geometry. The thin red tip has compression-broken pixels and is joined to its visible extremity at (81.5,31.5). No new logo, text, or white background is introduced.'}
for mode,ink in [('light','#282c2d'),('dark','#ded5ee')]:
    colours=[]
    for color in ([12,76,162],[237,27,36]):
        rgb=np.asarray(color,float)
        if mode=='dark': rgb=255*(rgb/255)**0.72
        colours.append('#'+''.join(f'{int(round(channel)):02x}' for channel in rgb))
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="104" height="128" viewBox="0 0 104 128" role="img">
<title>KMChC programme emblem — derived display vector ({mode})</title>
<desc>Display reconstruction of the existing chemistry-olympiad emblem. The original official raster is retained separately.</desc>
<path fill="{colours[0]}" d="{bp}"/>
<path fill="{colours[1]}" d="{rp}"/>
<path fill="none" stroke="{ink}" stroke-width="4.4" stroke-linejoin="miter" d="M53.1 39.5 73.1 51.1 73.1 74.3 53.1 85.9 33.1 74.3 33.1 51.1Z"/>
<circle cx="53.1" cy="62.7" r="10.5" fill="none" stroke="{ink}" stroke-width="2.0"/>
</svg>
'''
    (OUT/('kmchc.svg' if mode=='light' else 'kmchc-dark.svg')).write_text(svg,encoding='utf8',newline='\n')
(OUT/'kmchc-provenance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps(report,indent=2))
