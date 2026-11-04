from pathlib import Path
import sys,json,math
import numpy as np
import pymupdf as f
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from cpho2008_bitmap_language_qa import rgb
with page_worker():
    report=json.loads((B/'proofs/ko/page04.bitmap-language-native-source-audit.json').read_text('utf8'))
    q=json.loads((B/'authoring/page04-original-island-language-policy.json').read_text('utf8'))
    original=rgb(report['actual_original_graphics_control_path']);after=rgb(report['actual_final_graphics_control_path'])
    results=[]
    for row in q['labels']:
        rect=row['erase_rect_pt'];x0,y0,x1,y1=math.floor(rect[0]*4),math.floor(rect[1]*4),math.ceil(rect[2]*4),math.ceil(rect[3]*4)
        mask=np.any(original[y0:y1,x0:x1]!=255,2)&np.any(after[y0:y1,x0:x1]!=255,2)
        yy,xx=np.where(mask)
        data=dict(rect=rect,remaining=int(mask.sum()),bounds=[int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0),int(yy.max()+y0)]if len(xx)else None,
            remaining_gray_values=np.unique(after[y0:y1,x0:x1][mask],axis=0).tolist(),
            examples=[dict(x=int(x+x0),y=int(y+y0),source=original[y+y0,x+x0].tolist(),after=after[y+y0,x+x0].tolist())for y,x in zip(yy[:30],xx[:30])])
        results.append(data)
    out=B/'inspection/page04-old-bitmap-language-clearance-diagnostic.json';out.write_text(json.dumps(results,indent=2)+'\n','utf8')
    print(json.dumps(results,ensure_ascii=False))
