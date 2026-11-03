from pathlib import Path
import pymupdf as f,numpy as np,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
plan=json.loads((B/'authoring/page04-layout-proposal.json').read_text('utf8'))
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf') as d:
 for row in plan['rows']:
  for a in row['atoms']:
   p=d[3].get_pixmap(matrix=f.Matrix(8,8),clip=f.Rect(a['rect']),colorspace=f.csGRAY,alpha=False)
   ar=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<150
   sides={name:int(v.sum()) for name,v in [('top',ar[:2,:]),('bottom',ar[-2:,:]),('left',ar[:,:2]),('right',ar[:,-2:])]}
   if any(sides.values()):print(a['id'],sides,flush=True)
