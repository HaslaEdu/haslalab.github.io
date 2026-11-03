from pathlib import Path
import pymupdf as f,numpy as np,cv2,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
fields=dict(cond_eq_edge=[669,64,691,101],rel_five=[437,159,507,174.97],one=[512,362,535,382])
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf') as d:
 for name,rect in fields.items():
  p=d[3].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False)
  a=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)
  n,_,stats,_=cv2.connectedComponentsWithStats((a<150).astype(np.uint8))
  boxes=[]
  for x,y,w,h,area in stats[1:]:
   if area>10:boxes.append(dict(rect=[(p.x+x)/8,(p.y+y)/8,(p.x+x+w)/8,(p.y+y+h)/8],area=int(area)))
  print(name,json.dumps(sorted(boxes,key=lambda b:b['rect'][0])),flush=True)
