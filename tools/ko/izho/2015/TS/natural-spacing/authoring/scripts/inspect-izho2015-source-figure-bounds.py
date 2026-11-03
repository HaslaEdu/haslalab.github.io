from pathlib import Path
import pymupdf as f,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions')
with f.open(B/'2015/source/IZhO_2015_TS.pdf')as doc:
 for n,page in enumerate(doc,1):
  print(n,[(v['number'],[round(x,3)for x in v['bbox']])for v in page.get_image_info()])
