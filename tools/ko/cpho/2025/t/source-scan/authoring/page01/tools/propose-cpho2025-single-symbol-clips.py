from pathlib import Path
import json,math
import numpy as np
from PIL import Image
from scipy.ndimage import label,find_objects
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');p=B/'authoring/page01-draft-layout.json';q=json.loads(p.read_text('utf8'))
a=np.array(Image.open(B/'source-original-p1.png').convert('L'));sx=2420/595;sy=3420/840.8678;oy=.5660843
names={'O','A','B','B2','p','p2mag','y','x','x2','m','theta','t','zero','k','omega','omega2','rho','tau','one','six'}
out=[]
for row in q['rows']:
    for atom in row['atoms']:
        # x2 sometimes means the complete x=x_2 identity, not a single x.
        if atom['id']not in names or atom['id']in{'x2','zero'}and atom['rect'][2]-atom['rect'][0]>13:continue
        if atom['id']=='B2'and atom['rect'][2]-atom['rect'][0]>10.5:continue
        x0,y0,x1,y1=atom['rect'];l=math.floor((x0-3)*sx);r=math.ceil((x1+3)*sx);t=math.floor((y0-oy-2)*sy);b=math.ceil((y1-oy+2)*sy)
        crop=a[t:b,l:r];labels,count=label(crop<160,np.ones((3,3)));components=[]
        for i,sl in enumerate(find_objects(labels),1):
            pixels=int((labels[sl]==i).sum())
            rect=[(l+sl[1].start)/sx,(t+sl[0].start)/sy+oy,(l+sl[1].stop)/sx,(t+sl[0].stop)/sy+oy]
            if pixels<15 or rect[0]<x0-2.2 or rect[2]>x1+2.2 or rect[1]<y0-2.2 or rect[3]>y1+2.2:continue
            if abs((rect[0]+rect[2]-x0-x1)/2)>3:continue
            components.append(dict(pixels=pixels,rect=rect))
        if not components:raise ValueError((row['id'],atom))
        chosen=min(components,key=lambda c:(abs((c['rect'][0]+c['rect'][2]-x0-x1)/2),-c['pixels']));x,y,u,v=chosen['rect']
        proposal=[math.floor((x-.6)*4)/4,math.floor((y-.6)*4)/4,math.ceil((u+.6)*4)/4,math.ceil((v+.6)*4)/4]
        out.append(dict(row=row['id'],atom=atom['id'],old_rect=atom['rect'],proposed_rect=proposal,actual_source_component_pixels=chosen['pixels'],components=components,
                        status='PROPOSED_SOURCE_CLIP_REQUIRES_CONTACT_SHEET_REVIEW',note='Connected source ink only locates a candidate; neither original image nor mathematical glyph is regenerated.'))
(B/'authoring/page01-single-symbol-clip-proposals.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n','utf8')
print('Proposed',len(out),'single-symbol clips for manual visual review')
