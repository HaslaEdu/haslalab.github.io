"""Manually specified source math search windows; unreviewed native ROI proposals."""
from pathlib import Path
import json,math
import numpy as np,cv2,pymupdf as f
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
specs=[]
def add(name,rect,path,center=None):specs.append(dict(id=name,search_rect=rect,image_path=[path],selection='nearest Latin glyph component'if center is not None else'all complete components within manually specified source object window',center_hint=center))
for name,rect in dict(threshold=[63,56.93,144.5,93.5],**{'i-prime':[252,61,264,80]},equality=[292,56.93,390.5,93.5],eq7=[224,92,244.5,112],light1=[322,91,338,110.5],light2=[340,91,355.5,110.5],Ox=[66,168,85,186]).items():add(name,rect,315)
for name,rect,center in [('O',[115,168,126.5,186],121.8),('A-initial',[180,168,193.5,186],186.8),('B-attached',[65,205,79,224],72.3),('B-release',[117,205,132,224],124.9),('A-system',[182,224,196,243],189),('B-system',[209,224,223.5,243],216.7)]:add(name,rect,315,center)
for name,rect,center in [('A-axis',[289,247,301.5,265],296.4),('B-axis',[305,247,317,265],309.8),('B-weight',[157,265,172,285],164.4),('A-accelerating',[87,304,100.5,323],94.5),('B-accelerating',[104,304,116.5,323],109.7),('A-coordinate',[214,304,228,323],220.5),('x-coordinate',[281,304,295,323],287.8),('a',[61,322,75,342],68.3),('A-balance',[170,361,184.5,380],177.7),('B-balance',[197,361,211,380],203.7),('A-equilibrium',[148,381,162,401],155.1),('A-overshoot',[264,430,278,450],270.8)]:add(name,rect,324,center)
for name,rect in dict(**{'mg-weight':[210,265,231,286],'mg-drive':[259,284,281.5,305],'muMg-friction':[370,284,397,305],'a-zero':[76,361,114,380],'x1-equilibrium':[199,381,212,401],'eq1':[244,381,266,401],'mg-constant':[377.5,447,398,469],'muMg-constant':[61,466,89,487],'x-equal':[381,466,403,487],'x1-equal':[62.5,487,77.5,507.74]}).items():add(name,rect,324)
for name,rect in dict(**{'x1-amplitude':[477,97,493,115],'2x1-distance':[437,164,458.5,185],'2x1-extension':[565,164,588.5,185],'AB-force':[647,164,667,185],'mg-force':[731.5,164,755.5,185],'2kx1-mg':[463,185,524.5,207],'eq6':[604,285,624,305]}).items():add(name,rect,333)
for name,rect,center in [('A-start',[476,146,490,166],483.2),('A-distance',[684,146,698,166],690.3),('A-left',[546,229,559.5,247],552.5),('A-left-coordinate',[471,247,485.5,268],478.1),('x-left',[536,247,551,268],543),('a-left',[658,247,672,268],665.2),('A-second-equilibrium',[713,285,727,305],720)]:add(name,rect,333,center)
for name,rect in dict(**{'xeqx2-first':[460,331,501,356],'xeqx2-second':[474,370,519,395],'2x1-amplitude':[749,370,771,395],'minus-x2-amplitude':[436,393,466,416],'AB-rest':[452,439,474,463],'x-prime':[437,479,454,499]}).items():add(name,rect,342)
for name,rect,center in [('A-left-SHM',[435,331,449,356],442),('T',[696,370,709,395],702.2),('A-rest',[562,439,576.5,463],569.2)]:add(name,rect,342,center)
S=8;proposals=[];previews=[];cv2.setNumThreads(1)
corrections={'equality':[292,56.93,388,93.5],'light1':[322,91,336.5,110.5],'O':[114,167,128.5,187],'a-zero':[77,361,112.3,380],'x1-equilibrium':[205.5,381,220,401],'mg-constant':[380.5,447,399,469],'2x1-extension':[565,164,586.7,185],'mg-force':[731.5,164,753,185],'2kx1-mg':[466,185,525,207],'xeqx2-first':[461,333,499.7,356],'xeqx2-second':[478,377.5,518.7,394],'minus-x2-amplitude':[436,393,464.5,416]}
for spec in specs:
 if spec['id']in corrections:spec['search_rect']=corrections[spec['id']]
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as d:
 page=d[4]
 for spec in specs:
  p=page.get_pixmap(matrix=f.Matrix(S,S),clip=f.Rect(spec['search_rect']),colorspace=f.csGRAY,alpha=False);gray=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width);n,labels,stats,centers=cv2.connectedComponentsWithStats((gray<150).astype(np.uint8));selected=[]
  for index,(x,y,w,h,area)in enumerate(stats[1:],1):
   if area>=30:selected.append((index,x,y,w,h,area))
  if spec['center_hint']is not None:
   eligible=[r for r in selected if r[3]>=1.5*S and r[4]>=3*S]
   assert eligible,spec
   eligible.sort(key=lambda r:(abs((p.x+centers[r[0]][0])/S-spec['center_hint']),-r[5]));selected=[eligible[0]]
  assert selected,spec
  x0=min(r[1]for r in selected);y0=min(r[2]for r in selected);x1=max(r[1]+r[3]for r in selected);y1=max(r[2]+r[4]for r in selected)
  nativebox=[(p.x+x0)/S,(p.y+y0)/S,(p.x+x1)/S,(p.y+y1)/S];rect=[nativebox[0]-.75,nativebox[1]-.75,nativebox[2]+.75,nativebox[3]+.75]
  imagebox={315:[56.7,56.92000732421877,410.7,243.67000732421877],324:[56.7,245.24700732421877,410.7,507.74700732421877],333:[431.6,58.87000732421876,784.85,304.12000732421876],342:[431.6,310.0470073242187,784.85,536.5470073242187]}[spec['image_path'][0]]
  rect=[max(rect[0],imagebox[0]),max(rect[1],imagebox[1]),min(rect[2],imagebox[2]),min(rect[3],imagebox[3])]
  record=dict(**spec,rect=rect,source_dark_component_bbox=nativebox,search_boundary_touched=bool(x0<2 or y0<2 or x1>p.width-2 or y1>p.height-2),reviewed=False,may_publish=False,reason='Unreviewed location proposal only. Human must verify complete original mathematical object, all superscripts/subscripts, no Chinese remnants, no clipped glyph edges before native replay.')
  proposals.append(record)
  pix=page.get_pixmap(matrix=f.Matrix(5,5),clip=f.Rect(rect),alpha=False);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
  if im.width>290:im.thumbnail((290,125))
  previews.append((spec['id'],im,record['search_boundary_touched']))
width=1800;height=math.ceil(len(previews)/6)*155;image=Image.new('RGB',(width,height),'#ddd');draw=ImageDraw.Draw(image)
for i,(name,im,touched)in enumerate(previews):
 x=i%6*300;y=i//6*155;draw.text((x+4,y+3),name+(' CHECK SEARCH EDGE'if touched else''),fill='red'if touched else'black');image.paste(im,(x+4,y+23))
image.save(B/'source-renders/page05-native-math-proposals.png')
(B/'authoring/page05-native-math-proposals.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=5,reviewed=False,mathematical_transcription_forbidden=True,atoms=proposals),ensure_ascii=False,indent=2)+'\n','utf8')
print('UNREVIEWED_MATH_ATOM_PROPOSALS',len(proposals),[r['id']for r in proposals if r['search_boundary_touched']],flush=True)
