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
for id,rect,c in [('A-final',[106,100,120,120],113),('B-final',[121,100,136,120],128),('B-state',[275,100,291,120],283),('P-plate',[185,302,200,322],193),('F-external',[247,302,263,322],255),('C-right',[326,302,342,322],335),('D-right',[342,302,358,322],350),('A-spring',[132,322,147,342],140),('B-spring',[155,322,171,342],163),('C-figure',[264,322,280,342],273),('A-contact',[259,339,274,360],267),('P-contact',[276,339,291,360],284),('Q-contact',[290,339,305,360],297),('N-contact',[302,339,318,360],310),('C-contact',[328,339,344,360],336),('N-friction',[187,358,202,377.25],195),('P-friction',[202,358,218,377.25],210),('Q-friction',[226,358,242,377.25],234),('C-friction',[276,358,292,377.25],284)]:add(id,rect,287,c)
for id,rect in {'eq7-12':[80,171,144,190],'eq6':[81,233,100,252],'eq13':[106,233,131,252],'eq1':[170,233,190,252],'fig1a':[363,322,391,342],'FA':[116,339,136,360],'FP':[138,339,158,360],'FQ':[160,339,180,360],'FN':[191,339,211,360],'fN':[88,358,106,377.25],'fP':[105,358,123,377.25],'fQ':[122,358,141,377.25]}.items():add(id,rect,287)
for id,rect in {'dx1':[179,388,205,409],'dx2':[215,388,242,409]}.items():add(id,rect,296)
for id,rect,c in [('A-extra',[365,388,381,409],373),('B-extra',[390,388,407,409],399)]:add(id,rect,296,c)
add('figure-one',[615,219,626,238],305)
for id,rect,c in [('P-mass',[527,237,542,256],535),('Q-mass',[541,237,556,256],549),('C-mass',[555,237,570,256],563),('D-mass',[570,237,585,256],577),('A-mass',[585,237,600,256],593),('B-mass',[600,237,615,256],608),('C-zero',[635,257,651,276],643)]:add(id,rect,305,c)
add('seven',[661,257,676,276],305)
add('fig1b',[569,458,598,478],323)
S=8;out=[];previews=[];cv2.setNumThreads(1)
corrections={'Q-contact':[290,339,306,362],'eq6':[82.5,233,100,252],'FA':[116,339,133,360],'FP':[138,339,153,360],'FQ':[160,339,175.5,360],'FN':[191,339,208,360],'fN':[88,358,102.5,377.25],'fP':[105,358,120.5,377.25],'fQ':[122,358,136,377.25],'dx1':[179,388,202,409],'seven':[661,257,671,276],'fig1b':[569,458,595,478]}
corrections.update({'Q-contact':[288.5,339,306,359],'fP':[102.5,358,119,377.25],'fQ':[118.875,358,136,377.25],'fig1b':[569,458,597,478]})
for spec in specs:
 if spec['id']in corrections:spec['search_rect']=corrections[spec['id']]
 if spec['id']in ['fP','fQ']:spec['original_list_separator_retained']=True
 if spec['id']=='fig1b':spec['padding']=[.75,.75,.375,.75]
boxes={r['path'][0]:r['bbox']for r in inspect_inline_groups(B/'inputs/CPhO_2005_Chinese_original.pdf',7)['images']}
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as d:
 page=d[6]
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
atlas.save(B/'source-renders/page07-native-math-proposals.png')
(B/'authoring/page07-native-math-proposals.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=7,reviewed=False,mathematical_transcription_forbidden=True,atoms=out),ensure_ascii=False,indent=2)+'\n','utf8')
print('UNREVIEWED_NATIVE_MATH',len(out),'SEARCH_EDGES',[r['id']for r in out if r['search_boundary_touched']])
