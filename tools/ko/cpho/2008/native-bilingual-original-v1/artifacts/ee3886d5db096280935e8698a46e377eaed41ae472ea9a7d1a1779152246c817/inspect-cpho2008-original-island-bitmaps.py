"""Read original image pixels for two source-only Chinese word measurements."""
from pathlib import Path
import sys,json,hashlib
import pymupdf as f
from PIL import Image
B=Path(__file__).resolve().parents[1];S=B/'source/CPhO_2008_original_combined_ZH.pdf';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_original_image_ink import resolved_images
sha=lambda data:hashlib.sha256(data).hexdigest()
with page_worker():
 with f.open(S)as doc:
  results=[]
  for i,info in enumerate(resolved_images(doc,doc[3])[:2]):
   xref=info['xref'];extracted=doc.extract_image(xref);raw=extracted['image'];out=B/f'inspection/page04-original-circuit{i+1:02}.{extracted["ext"]}';out.write_bytes(raw)
   pix=f.Pixmap(doc,xref)
   if pix.colorspace.n!=3:pix=f.Pixmap(f.csRGB,pix)
   png=B/f'inspection/page04-original-circuit{i+1:02}-canonicalRGB.png';pix.save(png)
   rect=[270,60,450,135]if i==0 else[220,210,402,270]
   im=Image.open(png);crop=im.crop(rect);preview=B/f'inspection/page04-original-island{i+1:02}-word-ROI.png';crop.save(preview)
   a=crop.convert('L');columns=[sum(a.getpixel((x,y))<180 for y in range(a.height))for x in range(a.width)]
   safe_info={k:v.hex()if isinstance(v,bytes)else v for k,v in info.items()}
   results.append(dict(source_sha256=sha(S.read_bytes()),source_page=4,image_index=i,image_info=safe_info,extracted_image_sha256=sha(raw),actual_RGB_png_sha256=sha(png.read_bytes()),rough_source_only_roi_pixels=rect,black_ink_column_counts=columns))
  p=B/'inspection/page04-original-island-bitmaps-source-info.json';p.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n','utf8');print('C08_SOURCE_ONLY_ISLAND_BITMAPS',[(r['image_index'],r['image_info']['width'],r['image_info']['height'],r['rough_source_only_roi_pixels'])for r in results],flush=True)
