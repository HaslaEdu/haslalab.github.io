from pathlib import Path
import sys,json,numpy as np,cv2
from PIL import Image
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural');sys.path.insert(0,str(B/'engine'))
from cpho2024_figure_label_plan import LABELS
cache={};rows=[]
for label in LABELS:
 key=(label['page'],label['image_index'])
 if key not in cache:
  a=np.asarray(Image.open(B/f'inspection/image-p{key[0]}-{key[1]}.png').convert('L'));_,cc,stats,_=cv2.connectedComponentsWithStats((a<160).astype('uint8'),8);cache[key]=(cc,stats)
 cc,stats=cache[key];x0,y0,x1,y1=label['source_word_roi_px'];regions=label.get('source_word_regions_px',[[x0,y0,x1,y1]]);selected=np.zeros(cc.shape,bool)
 for a,b,c,d in regions:selected[b:d,a:c]=True
 ids=set(int(v)for v in np.unique(cc[selected]))-{0};clipped=[];partitions=[]
 for i in sorted(ids):
  x,y,w,h,n=map(int,stats[i]);
  if n>=2 and np.any((cc==i)&~selected):
   item=dict(component=i,bbox=[x,y,x+w,y+h],pixels=n,word_pixels=int(((cc==i)&selected).sum()),remaining_source_component_pixels=int(((cc==i)&~selected).sum()))
   review=label.get('reviewed_shared_source_bitmap_component_partition',{})
   if review.get('reviewed')and i in review.get('native_component_ids',[]):partitions.append(dict(item,review=review))
   else:clipped.append(item)
 row=dict(id=label['id'],source=label['source_text'],roi=[x0,y0,x1,y1],source_word_erasure_regions_px=regions,intersecting_components=len(ids),reviewed_source_word_component_partitions=partitions,clipped_or_nonlanguage_components=clipped,passed=not clipped);rows.append(row)
 if clipped:print(label['id'],clipped)
out=B/'inspection/figure-language-roi-review/source-component-review.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(dict(labels=rows,threshold=160,source_only=True,passed=all(r['passed']for r in rows)),ensure_ascii=False,indent=2)+'\n','utf8');print('Complete isolated source words:',sum(r['passed']for r in rows),'/',len(rows))
