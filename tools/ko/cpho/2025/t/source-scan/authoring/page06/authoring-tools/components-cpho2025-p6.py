from pathlib import Path
import json,sys,math
import numpy as np
from scipy.ndimage import label,find_objects
from PIL import Image,ImageDraw,ImageFont
P=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/p6-authoring');q=json.loads((P/'plans/page06-draft-layout.json').read_text('utf8'))
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
full=Image.open(P/'source-p6-4x.png').convert('RGB')
selected=['debye-value/lambda','quasineutral-scale/lambda1','quasineutral-scale/lambda2','ion-flow-equilibrium/vi','gradient-frequency/gradient','gradient-frequency/omega0','gradient-frequency/wpe','gradient-frequency/wpe-definition','gradient-frequency/wce-definition','gradient-frequency/w0','gradient-frequency/ratio','density-estimate/freq','density-estimate/B','density-estimate/ratio','small-perturbation/exp','small-perturbation/omega','dispersion-variables/omega','dispersion-variables/lambda','dispersion-variables/kb','ion-sound-scale/omega','ion-sound-scale/ion-scale','ion-sound-scale/Te','ion-sound-scale/Ti','ion-sound-scale/dispersion','electron-scale/omega','electron-scale/electron-scale','electron-scale/Te','electron-scale/Ti','group-velocity/vg','group-velocity/wpe','boltzmann-electrons/poisson','quasineutral-dispersion/dispersion','classical-ion-sound/relation']
all=[]
selected+=['ion-flow-equilibrium/B','equilibrium-electric-field/E','equilibrium-electric-field/L','equilibrium-electric-field/x','gradient-frequency/wce','small-perturbation/k','dispersion-variables/k','dispersion-variables/gamma','dispersion-variables/m','dispersion-variables/T','density-estimate/n0','quasineutral-dispersion/neutral']
for row in q['rows']:
 for atom in row['atoms']:
  key=row['id']+'/'+atom['id']
  if key not in selected:continue
  r=atom['rect'];im=full;ox=oy=0
  box=[math.floor((r[0]-3)*4),math.floor((r[1]-1)*4),math.ceil((r[2]+3)*4),math.ceil((r[3]+1)*4)];crop=im.crop(box);a=np.array(crop.convert('L'));labs,_=label(a<160,np.ones((3,3)));cc=[]
  for i,sl in enumerate(find_objects(labs),1):
   count=int((labs[sl]==i).sum())
   if count<3:continue
   rr=[ox+(box[0]+sl[1].start)/4,oy+(box[1]+sl[0].start)/4,ox+(box[0]+sl[1].stop)/4,oy+(box[1]+sl[0].stop)/4]
   cc.append(dict(id=i,pixels=count,rect=rr))
  zoom=2;tile=Image.new('RGB',(680,230),'#ededed');draw=ImageDraw.Draw(tile);draw.text((4,2),key,font=font,fill='black');draw.text((4,20),str(r),font=font,fill='black');tile.paste(crop,(4,58))
  for c in cc:
   x0,y0,x1,y1=c['rect'];xx=(x0-ox)*4-box[0]+4;yy=(y0-oy)*4-box[1]+58
   draw.rectangle((xx,yy,xx+(x1-x0)*4,yy+(y1-y0)*4),outline='red',width=1);draw.text((xx,yy-15),str(c['id']),font=font,fill='blue')
  all.append(dict(key=key,rect=r,components=cc));tile.save(P/f'cc-{selected.index(key)+1:02d}.png')
(P/'component-bounds.json').write_text(json.dumps(all,indent=2),'utf8')
for j in range(math.ceil(len(selected)/6)):
 sheet=Image.new('RGB',(1360,690),'#dddddd')
 for k,key in enumerate(selected[j*6:j*6+6]):sheet.paste(Image.open(P/f'cc-{selected.index(key)+1:02d}.png'),((k%2)*680,(k//2)*230))
 sheet.save(P/f'cc-sheet-{j+1}.png')
print('components',len(all))
