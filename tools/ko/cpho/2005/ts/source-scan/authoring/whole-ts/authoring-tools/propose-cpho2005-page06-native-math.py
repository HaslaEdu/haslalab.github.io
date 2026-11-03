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
for id,rect in {'x-rest':[154,99,195,117]}.items():add(id,rect,273)
for id,rect,c in [('A-rest',[91,99,105,117],98),('B-release',[127,118,141,136],134),('A-distance',[361,118,376,136],369)]:add(id,rect,273,c)
add('B-cooling',[347,313,363,333],282,355)
for id,rect in {'alpha':[368,347,381,364],'one':[77,364,88,382],'QA':[335,421,355,440],'QB':[369,421,389,440],'WA':[217,439,239,458],'WB':[252,439,275,458]}.items():add(id,rect,291)
for id,rect,c in [('A-gas',[114,383,128,401],121),('B-gas',[128,383,142,401],136),('A-heat',[192,421,206,440],199),('B-heat',[208,421,222,440],215),('B-piston',[127,478,142,496],135),('x-descent',[371,497,385,516],378),('B-pressure',[61,514,76,533],69)]:add(id,rect,291,c)
for id,rect in {'VB':[591,84,611,103],'alphaVB':[673,84,698,103],'p0S':[492,151,517,171],'mg':[554,151,576,171],'kx':[684,151,703,171],'eq3':[451,269,470,286],'eq4':[477,269,496,286],'eq5':[502,269,521,286]}.items():add(id,rect,300)
for id,rect,c in [('B-volume',[451,84,467,103],459),('B-initial',[571,218,586,236],579),('A-pressure',[489,333,505,352],497)]:add(id,rect,300,c)
for id,rect in {'pA':[438,380,459,403],'VA1':[654,380,678,403],'VA2':[682,380,700,403],'T2':[531,478,548,498]}.items():add(id,rect,309)
for id,rect,c in [('A-volumes',[748,380,765,403],756),('A-work',[619,401,636,421],627),('A-continuation',[490,514,506,534],499),('B-continuation',[507,514,522,534],514)]:add(id,rect,309,c)
S=8;out=[];previews=[];cv2.setNumThreads(1)
for spec in specs:
 if spec['id']=='alpha':spec['search_rect']=[367,347,378.25,364]
 if spec['id']=='pA':spec['search_rect']=[438,380,456.75,403]
 if spec['id']=='VA1':spec['search_rect']=[654,380,676,403]
 if spec['id']=='T2':spec['search_rect']=[531,478,546.25,498]
boxes={r['path'][0]:r['bbox']for r in inspect_inline_groups(B/'inputs/CPhO_2005_Chinese_original.pdf',6)['images']}
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as d:
 page=d[5]
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
  rect=[tight[0]-.75,tight[1]-.75,tight[2]+.75,tight[3]+.75]
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
atlas.save(B/'source-renders/page06-native-math-proposals.png')
(B/'authoring/page06-native-math-proposals.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=6,reviewed=False,mathematical_transcription_forbidden=True,atoms=out),ensure_ascii=False,indent=2)+'\n','utf8')
print('UNREVIEWED_NATIVE_MATH',len(out),'SEARCH_EDGES',[r['id']for r in out if r['search_boundary_touched']])
