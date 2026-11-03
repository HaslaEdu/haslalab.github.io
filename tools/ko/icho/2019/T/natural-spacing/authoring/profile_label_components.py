from pathlib import Path
import json
import pymupdf as f,numpy as np
from fontTools.ttLib import TTFont
import icho2019_write_guard as g
doc=f.open(g.SOURCE)
for n,r in[(45,[268,156,302,167]),(58,[122,155,165,166]),(58,[270,465,288,477]),(58,[405,465,424,476]),(60,[255,415,287,428])]:
    pix=doc[n-1].get_pixmap(matrix=f.Matrix(16,16),clip=f.Rect(r),colorspace=f.csGRAY,alpha=False);arr=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);active=(arr<180).any(axis=0);runs=[];s=None
    for i,v in enumerate(list(active)+[False]):
        if v and s is None:s=i
        elif not v and s is not None:runs.append([r[0]+s/16,r[0]+i/16]);s=None
    print(json.dumps(dict(page=n,clip=r,x_ink_runs=runs)),flush=True)
for name in['arial.ttf','arialbd.ttf']:
    font=TTFont('C:/Windows/Fonts/'+name);units=font['head'].unitsPerEm;cm=font.getBestCmap();glyphs=font['glyf'];advance=font['hmtx'].metrics
    for word in['catalyst','Lysine','structure','perspective formula','reagent','LevoBupivacaine',"Mosher's acid"]:
        x=0;rect=None
        for c in word:
            gn=cm[ord(c)];gg=glyphs[gn]
            if gg.numberOfContours:
                b=[x+gg.xMin,gg.yMin,x+gg.xMax,gg.yMax];rect=b if rect is None else[min(rect[0],b[0]),min(rect[1],b[1]),max(rect[2],b[2]),max(rect[3],b[3])]
            x+=advance[gn][0]
        if word=='catalyst':
            sx=31.478230696/(rect[2]-rect[0])*units;sy=8.488812798/(rect[3]-rect[1])*units
            print(json.dumps(dict(font=name,word=word,units=units,bbox_em=[v/units for v in rect],size_by_width=sx,size_by_ink_height=sy)),flush=True)
