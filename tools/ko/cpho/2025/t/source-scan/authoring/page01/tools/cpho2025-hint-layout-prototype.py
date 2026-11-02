from pathlib import Path
import sys,json,hashlib,re,time
from io import BytesIO
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
sys.path[:0]=[str(B/'tools'),str(ROOT/'tools'),'D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
import pymupdf as fitz,pikepdf
import cpho2025_scan_fonts as fonts
from pdf_original_raster_math import replay
from pdf_memory_gate import page_worker
fonts.BASE=B;fonts.ROOT=ROOT
SOURCE=B/'CPhO_2025_T_original-explicit-page-clip.pdf';OUT=B/'hint-layout-prototypes';OUT.mkdir(exist_ok=True)
R={'42':[178.2,90.8,191.6,101.3],'year':[234.8,110.9,255.,119.1],'month':[271.1,110.9,280.4,119.1],'day':[295.95,111.4,306.9,119.4],'time':[322.75,111.4,368.65,119.4],'function':[176.7,146.75,214.75,157.75],'derivative':[235.1,138.4,427.0,161.3]}
SIZES={'title':13.78,'date':10.2,'hint':10.32,'fixed':7.16};BASELINES={'title':101.30988595289259,'date':119.01236529173555,'hint':155.1549272752066,'fixed':158.59707603553719}
TITLE_CENTER=301.;DATE_CENTER=301.5
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def text(value,role):return dict(kind='text',text=value,role=role)
def image(name,role):return dict(kind='image',name=name,role=role)
def build(lang):
 pools={'sans':'','serif':''};spec={}
 if lang=='ko':
  title=[text('제','title'),image('42','title'),text('회 전국 중학생 물리경시대회 결선 이론시험 문제','title')]
  date=[image('year','date'),text('년 ','date'),image('month','date'),text('월 ','date'),image('day','date'),text('일 ','date'),image('time','date')]
  hint=[text('힌트: 다변수 함수 ','hint'),image('function','hint'),text('에 대해, ','hint'),image('derivative','hint'),text('; 나머지도 마찬가지다.','hint')];fixed='고정'
 else:
  title=[image('42','title'),text('nd Chinese Physics Olympiad — Final Theory Problems','title')]
  date=[image('day','date'),text(' October ','date'),image('year','date'),text(', ','date'),image('time','date')]
  hint=[text('Hint: For multivariable ','hint'),image('function','hint'),text(': ','hint'),image('derivative','hint'),text('; similarly.','hint')];fixed='fixed'
 for unit in title+date+hint:
  if unit['kind']=='text':pools['sans'if unit['role']in['title','date']else'serif']+=unit['text']
 pools['serif']+=fixed
 paths={'sans':ROOT/'tools/ko/fonts/NotoSansCJKkr-Regular.otf'if lang=='ko'else B.parent/'official-hans-fonts/faces/simhei.ttf','serif':Path('C:/Windows/Fonts/batang.ttc')if lang=='ko'else Path('C:/Windows/Fonts/simsun.ttc')}
 for name,pool in pools.items():spec[name]=fonts.new_font(paths[name],pool)
 annotation_x=427.1219008264463;fixed_width=fonts.width(spec['serif'][1],fixed,SIZES['fixed']);derivative_reserve=max(R['derivative'][2]-R['derivative'][0],annotation_x-R['derivative'][0]+fixed_width+.6)
 def width(u):
  if u['kind']=='image':return derivative_reserve if u['name']=='derivative'else R[u['name']][2]-R[u['name']][0]
  face='sans'if u['role']in['title','date']else'serif';return fonts.width(spec[face][1],u['text'],SIZES[u['role']])
 placements=[];atoms=[];derivative_dx=None
 for units,left in[(title,TITLE_CENTER-sum(map(width,title))/2),(date,DATE_CENTER-sum(map(width,date))/2),(hint,84.5)]:
  x=left
  for u in units:
   w=width(u);role=u['role']
   if u['kind']=='image':
    rect=R[u['name']];dx=x-rect[0];atoms.append(dict(id=u['name'],image_path=[10],rect=rect,dx=dx,reviewed=True,reason='Original scan glyphs at their original image scale and y; no mathematical or numerical glyph is retyped.'))
    if u['name']=='derivative':derivative_dx=dx
   else:placements.append(dict(text=u['text'],point=[x,BASELINES[role]],size=SIZES[role],face='sans'if role in['title','date']else'serif',role=role))
   x+=w
  assert left>=35 and x<=560,(lang,left,x)
 with pikepdf.open(SOURCE)as source,pikepdf.Pdf.new()as d:
  d.pages.append(source.pages[0]);base=OUT/f'page01-{lang}-blanked.pdf';d.save(base,compress_streams=False)
 with fitz.open(base)as d:
  for rect in[[155,85,447,107],[230,106,375,124],[82,137,497,163]]:d[0].draw_rect(rect,color=None,fill=(1,1,1),overlay=True)
  erased=OUT/f'page01-{lang}-erased.pdf';d.save(erased,garbage=0,deflate=False)
 raw,journal=replay(SOURCE,1,erased,atoms)
 with fitz.open(stream=raw,filetype='pdf')as d:
  page=d[0];old=[427.0+derivative_dx,150.3,444.0+derivative_dx,161.0];page.draw_rect(old,color=None,fill=(1,1,1),overlay=True)
  for face,(buffer,metric,provenance)in spec.items():page.insert_font(fontname='Translation'+face,fontbuffer=buffer)
  placements.append(dict(text=fixed,point=[annotation_x+derivative_dx,BASELINES['fixed']],size=SIZES['fixed'],face='serif',role='fixed'))
  for p in placements:
   line_width=(.35 if p['face']=='sans'else .30)if lang=='ko'else .50
   fonts.write_words(page,*p['point'],p['text'],spec[p['face']][1],p['size'],'Translation'+p['face'],2,line_width)
   p['user_space_stroke_width_pt']=line_width
  target=OUT/f'page01-{lang}-header-hint-prototype.pdf';d.save(target,garbage=0,deflate=False)
 with fitz.open(target)as d:d[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(35,78,560,170),alpha=False,colorspace=fitz.csRGB).save(OUT/f'page01-{lang}-header-hint.png')
 q=dict(status='DRAFT_HEADER_HINT_ONLY_NOT_FOR_PUBLICATION',language=lang,source_original_sha256='b7c3ff8e024d4805306b7cd7e11bb22dd487ff1ee1aa6a504f096a1676296957',normalized_source_sha256=sha(SOURCE),output=str(target),sha256=sha(target),original_numeric_and_math_bitmap_replay=journal,placements=placements,source_inferred_point_sizes=SIZES,mathematics_recognized_or_retyped=False,note='Only title/date/hint are translated in this internal style proof; all remaining body text is deliberately unchanged and the document is not READY.')
 (target.with_suffix('.json')).write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(dict(language=lang,output=str(target),sha256=q['sha256'])),flush=True)
for lang in['ko','en']:
 with page_worker():build(lang)
 time.sleep(.6)
