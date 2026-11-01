from pathlib import Path
import sys,numpy as np,cv2
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural');sys.path.insert(0,str(B/'engine'))
from cpho2024_figure_label_plan import LABELS
names={'quad-vertical-polarizer','quad-polarizer-h','quad-path1','quad-splitter2','quad-detector-a'}
a=np.asarray(Image.open(B/'inspection/image-p3-1.png').convert('L'));_,cc,stats,_=cv2.connectedComponentsWithStats((a<160).astype('uint8'),8)
for label in LABELS:
 if label['id']not in names:continue
 x0,y0,x1,y1=label['source_word_roi_px'];ids=set(int(v)for v in np.unique(cc[y0:y1,x0:x1]))-{0};print(label['id'])
 for i in sorted(ids):
  x,y,w,h,n=map(int,stats[i]);print(i,[x,y,x+w,y+h],n)
