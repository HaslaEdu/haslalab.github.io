from pathlib import Path
import json
import pymupdf as f,numpy as np,cv2
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
atoms=json.loads((B/'authoring/page07-native-math-proposals.json').read_text('utf8'))['atoms']
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as d:
 for a in atoms:
  if a['id']not in ['Q-contact','fP','fQ','fig1b','FQ']:continue
  r=f.Rect(a['search_rect']);r.x0-=3;r.y0-=2;r.x1+=3;r.y1+=2
  p=d[6].get_pixmap(matrix=f.Matrix(8,8),clip=r,colorspace=f.csGRAY,alpha=False)
  ar=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)
  n,labels,stats,centers=cv2.connectedComponentsWithStats((ar<150).astype(np.uint8))
  components=[dict(bbox=[(p.x+x)/8,(p.y+y)/8,(p.x+x+w)/8,(p.y+y+h)/8],area=int(area))for x,y,w,h,area in stats[1:]if area>=30]
  print(a['id'],'search',a['search_rect'],'tight',a['source_dark_component_bbox'],'components',components,flush=True)
