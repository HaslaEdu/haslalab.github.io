"""Explicit manual source-object windows, with location proposals only."""
from pathlib import Path
import json,math,sys
import numpy as np,cv2,pymupdf as f
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_native_inline_reposition import inspect_inline_groups
specs=[]
def add(id,rect,path,center=None):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=center))
for id,rect in {
 'eq1-7':[72,57,133,76], 'eq11-12':[156,57,218,76], 'eq3':[261,57,283,76],
 'F-old':[349,57,365,76], 'F-prime':[389,56,405,76],
 'fixed-k-alpha-mu':[76,165,140,185], 'fixed-x':[151,165,193,185],
 'eq10':[285,165,315,185], 'eq13':[325,165,355,185],
 'dx-coefficient':[139,184,164,204], 'F-linear':[299,184,314,204], 'Fp-linear':[323,183,341,204], 'dx-linear':[354,183,379,204],
 'F-sum':[146,203,161,224], 'Fp-sum':[178,202,195,224], 'F0':[302,203,322,224], 'F0p':[339,202,359,224],
 'dx-proportional':[76,223,100,243], 'Kdx':[181,222,213,243], 'Kpdx':[233,222,270,243]
}.items():add(id,rect,259)
for id,rect in {'dx-compression':[77,442,103,461], 'dxm-compression':[167,441,195,461], 'F-work':[264,442,280,461]}.items():add(id,rect,268)
for id,rect in {'dx-recovery':[450,64,476,85], 'dxm-recovery':[490,64,518,85], 'Fp-work':[639,64,656,85]}.items():add(id,rect,277)
for id,rect in {'eq20-21':[448,121,508,141], 'eq16-19':[472,171,545,192], 'part-one':[461,227,475,244], 'p-recoil':[645,263,662,283], 'nu0':[469,281,485,302]}.items():add(id,rect,286)
for id,rect in {'mass-m':[463,418,482,439], 'speed-v':[620,418,637,439]}.items():add(id,rect,295)
S=8;out=[];previews=[];cv2.setNumThreads(1)
corrections={
 'eq1-7':[74,57,133,76], 'eq11-12':[159.25,57,218,76], 'eq3':[262,57,283,76],
 'F-old':[349,57,361,76], 'fixed-x':[153,165,193,185],
 'eq10':[288,165,315,185], 'eq13':[328,165,355,185],
 'F-linear':[299,184,311,204], 'Fp-linear':[326,183,341,204],
 'F-sum':[146,203,158.5,224], 'F0':[302,203,320,224],
 'Kdx':[181,222,211,243], 'Kpdx':[233,222,268,243],
 'eq20-21':[451,121,508,141], 'eq16-19':[476.5,171,545,192],
 'p-recoil':[649,263,662,283], 'speed-v':[626,418,637,439]
}
for spec in specs:
 if spec['id'] in corrections:spec['search_rect']=corrections[spec['id']]
boxes={r['path'][0]:r['bbox']for r in inspect_inline_groups(B/'inputs/CPhO_2005_Chinese_original.pdf',8)['images']}
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as d:
 page=d[7]
 for spec in specs:
  p=page.get_pixmap(matrix=f.Matrix(S,S),clip=f.Rect(spec['search_rect']),colorspace=f.csGRAY,alpha=False)
  gray=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)
  n,labels,stats,centers=cv2.connectedComponentsWithStats((gray<150).astype(np.uint8))
  selected=[(i,x,y,w,h,area)for i,(x,y,w,h,area)in enumerate(stats[1:],1)if area>=30]
  if spec['center_hint']is not None:
   eligible=[r for r in selected if r[3]>=1.5*S and r[4]>=3*S]
   assert eligible,spec
   eligible.sort(key=lambda r:(abs((p.x+centers[r[0]][0])/S-spec['center_hint']),-r[5]))
   selected=[eligible[0]]
  assert selected,spec
  x0=min(r[1]for r in selected);y0=min(r[2]for r in selected)
  x1=max(r[1]+r[3]for r in selected);y1=max(r[2]+r[4]for r in selected)
  tight=[(p.x+x0)/S,(p.y+y0)/S,(p.x+x1)/S,(p.y+y1)/S]
  pad=spec.get('padding',[.75,.75,.75,.75])
  rect=[tight[0]-pad[0],tight[1]-pad[1],tight[2]+pad[2],tight[3]+pad[3]]
  box=boxes[spec['image_path'][0]]
  rect=[max(rect[0],box[0]),max(rect[1],box[1]),min(rect[2],box[2]),min(rect[3],box[3])]
  touched=bool(x0<2 or y0<2 or x1>p.width-2 or y1>p.height-2)
  r=dict(**spec,rect=rect,source_dark_component_bbox=tight,search_boundary_touched=touched,reviewed=False,may_publish=False)
  out.append(r)
  pic=page.get_pixmap(matrix=f.Matrix(5,5),clip=f.Rect(rect),alpha=False)
  im=Image.frombytes('RGB',[pic.width,pic.height],pic.samples)
  if im.width>290:im.thumbnail((290,125))
  previews.append((spec['id'],im,touched))
atlas=Image.new('RGB',(1800,math.ceil(len(previews)/6)*155),'#ddd');draw=ImageDraw.Draw(atlas)
for i,(id,im,touched)in enumerate(previews):
 x=i%6*300;y=i//6*155;draw.text((x+4,y+3),id+(' CHECK EDGE'if touched else''),fill='red'if touched else'black');atlas.paste(im,(x+4,y+23))
atlas.save(B/'source-renders/page08-native-math-proposals.png')
(B/'authoring/page08-native-math-proposals.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=8,reviewed=False,mathematical_transcription_forbidden=True,atoms=out),ensure_ascii=False,indent=2)+'\n','utf8')
print('UNREVIEWED_NATIVE_MATH',len(out),'SEARCH_EDGES',[r['id']for r in out if r['search_boundary_touched']])
