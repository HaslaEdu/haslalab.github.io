from pathlib import Path
import json,math,hashlib
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
B=Path(__file__).resolve().parent;R=B/'graphic-language-audit-01-56-20261103';data=json.loads((R/'graphic-language-audit-report.json').read_text('utf8'));fonts={n:TTFont('C:/Windows/Fonts/'+n)for n in['arial.ttf','times.ttf']};rows=[]
for v in data['ordinary_uncovered_vector_labels']:
 if len(v['source_paths'])!=1 or v['source_text']in['Yello- / wish']:continue
 word=v['source_text'];r=v['label_ink_bbox_page_pt'];candidates=[]
 for name,font in fonts.items():
  gs=font.getGlyphSet();cm=font.getBestCmap();unit=font['head'].unitsPerEm;x=0;rects=[]
  for ch in word:
   gn=cm[ord(ch)];pen=BoundsPen(gs);gs[gn].draw(pen)
   if pen.bounds:
    b=pen.bounds;rects.append([x+b[0],b[1],x+b[2],b[3]])
   x+=font['hmtx'].metrics[gn][0]
  b=[min(v[0]for v in rects),min(v[1]for v in rects),max(v[2]for v in rects),max(v[3]for v in rects)];sx=(r[2]-r[0])/(b[2]-b[0])*unit;sy=(r[3]-r[1])/(b[3]-b[1])*unit
  candidates.append(dict(reference_font=name,reference_font_sha256=hashlib.sha256(Path('C:/Windows/Fonts/'+name).read_bytes()).hexdigest(),outline_em_size_x=sx,outline_em_size_y=sy,abs_log_anisotropy=abs(math.log(sx/sy))))
 rows.append(dict(page=v['page'],source_word=word,source_ink_bbox=r,candidates=candidates));print(json.dumps(rows[-1]),flush=True)
(B/'graphic-source-font-role-inference.json').write_text(json.dumps(dict(rows=rows,basis='Compare original outlined word aspect ratios to local Arial and Times New Roman true outline bounds as supporting style-role inference only. Source Form has no font or point-size metadata; no exact source family/point-size assertion.'),ensure_ascii=False,indent=2)+'\n','utf8')
