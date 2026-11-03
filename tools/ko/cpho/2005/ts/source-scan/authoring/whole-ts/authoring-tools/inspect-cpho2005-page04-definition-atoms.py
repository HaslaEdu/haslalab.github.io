from pathlib import Path
import sys,json,hashlib,re
import pymupdf as fitz
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_memory_gate import page_worker
from cpho_2005_ts_compose import new_font,font_path,width
rects=dict(item1=[89.8,100.5,99.7,112.0],d=[118.2,100.0,126.5,112.6],v1=[222.2,102.0,234.5,115.0],v2=[251.2,102.0,263.8,115.0],light1=[317.4,98.0,332.4,112.8],light2=[349.3,98.0,365.0,112.8],r1=[159.3,119.0,170.1,132.06],r2=[186.8,119.0,198.4,132.06],t1=[330.3,118.8,340.7,132.06],t2=[355.3,118.8,366.5,132.06])
proposal=dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',source_page=4,reviewed=False,atoms=[dict(id=k,rect=v,image_path=[343])for k,v in rects.items()])
out=B/'authoring/page04-definition-atom-proposals.json';out.write_text(json.dumps(proposal,indent=2)+'\n','utf8')
canvas=Image.new('RGB',(1000,300),'#ddd');draw=ImageDraw.Draw(canvas)
with page_worker(),fitz.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as doc:
 for i,(name,rect)in enumerate(rects.items()):
  pix=doc[3].get_pixmap(matrix=fitz.Matrix(6,6),clip=fitz.Rect(rect),alpha=False)
  im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);x=(i%5)*200;y=(i//5)*150;canvas.paste(im,(x+10,y+28));draw.text((x+10,y+6),name+' '+str(rect),fill='black')
canvas.save(B/'source-renders/page04-definition-math-proposals.png')
texts=dict(ko=['[[item1]] 판의 두께를 [[d]], [[light1]], [[light2]]의 판 내 속력을 [[v1]], [[v2]],','굴절각을 [[r1]], [[r2]], 판 통과 시간을 [[t1]], [[t2]]라 하면','다음이 성립한다.'],en=['[[item1]] [[d]]: slab thickness; [[v1]], [[v2]]: speeds of [[light1]], [[light2]];','[[r1]], [[r2]]: refraction angles; [[t1]], [[t2]]: transit times','through the slab. Then'])
for language,lines in texts.items():
 raw,metric,qa=new_font(font_path(language),' '.join(re.sub(r'\[\[[^\]]+\]\]','',t)for t in lines))
 for index,text in enumerate(lines):
  size=12.3 if index<2 else 12.425;w=width(metric,re.sub(r'\[\[[^\]]+\]\]','',text),size)+sum(rects[m][2]-rects[m][0]for m in re.findall(r'\[\[([^\]]+)\]\]',text));print(language,index+1,round(w,3),'available',319.5 if index==0 else 338.5 if index==1 else 178,text)
print('PROPOSALS_REQUIRE_VISUAL_REVIEW',out,flush=True)
