from pathlib import Path
import sys,json,hashlib,pikepdf
import pymupdf as fitz
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools'),str(B.parent/'izho-natural-spacing'),str(B)]
from izho_natural_spacing_rebuild import prepare,split_scopes_around_math
from pdf_memory_gate import page_worker
from coalesce_initial_scopes import coalesce
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=B/'2017/native-baseline';output=f/'IZhO_2017_T_KO_native-baseline.pdf'
with pikepdf.Pdf.new()as joined:
 for n in range(1,8):
  with pikepdf.open(f/f'page{n:02}.pdf')as doc:joined.pages.append(doc.pages[0])
 joined.save(output,compress_streams=False)
(f/'edition-input.json').write_text(json.dumps(dict(year=2017,kind='T',pdf=str(output),sha256=sha(output)),indent=2),encoding='utf8')
for n,pp in enumerate(prepare(2017,'T'),1):
 d=json.loads(pp.read_text('utf8'));d['reviewed_initial_prose_reading_order']=True;d['baseline_tolerance_pt']=.75
 labels={(13,1):'우주선',(16,0):'행성',(17,0):'항로',(18,0):'중심'}if n==3 else{}
 runs=json.loads((B/f'2017/page{n:02}.runs.json').read_text('utf8'));rects=[];native_label_holes=[]
 for scope in d['source_line_scopes']:
  old=list(scope['rect']);r=list(old);bi,li=scope['source_at'];y=scope['baseline']
  if y>=60:r[0]=max(84.734,r[0]);r[2]=min(559.6,r[2])
  if n==3 and((bi==5 and 2<=li<=5)or(bi==6 and li<=1)):r[2]=min(r[2],444.1)
  if n==6 and bi==1 and(li<=2 or 4<=li<=6):r[2]=min(r[2],425.2)
  if n==6 and bi==4:r[0],r[2]=([84.734,294]if li==0 else[319,559.6])
  if(bi,li)in labels:
   source=runs[f'{bi},{li},0'];box=source['bbox'];center=(box[0]+box[2])/2;half=max((box[2]-box[0])/2+1,len(labels[(bi,li)])*source['size']/2+2)
   r[0]=center-half;r[2]=center+half;native_label_holes.append(list(r))
   d['centered_lines'].append(dict(baseline=y,center=center,rect=list(r)))
  scope['rect']=r
  for a in d['centered_lines']+d['right_aligned_lines']:
   if a.get('rect')==old:a['rect']=list(r)
  rects.append(r)
 d['allowed_line_rects']=rects;coalesce(d)
 displays=[]
 if n==3:displays=[[310,449,359,466],[225,544,262,566]]
 if n==5:displays=[[256,143,558,162],[254,289,558,310],[255,481,558,501]]
 d['frozen_display_math_rects']=displays;d['excluded_figure_rects']+=displays
 if n==3:
  figure=[181.5,218.3,456.6,397.6];d['excluded_figure_rects'].append(figure)
  # Keep every native figure variable/line/image fixed, allowing only the four
  # explicitly selected source language labels through their exact row slots.
  pieces=[figure]
  for hole in native_label_holes:
   new=[]
   for box in pieces:
    a=fitz.Rect(box);inter=a&fitz.Rect(hole)
    if inter.is_empty:new.append(box);continue
    for part in [[a.x0,a.y0,a.x1,inter.y0],[a.x0,inter.y1,a.x1,a.y1],[a.x0,inter.y0,inter.x0,inter.y1],[inter.x1,inter.y0,a.x1,inter.y1]]:
     if part[2]>part[0]and part[3]>part[1]:new.append(part)
   pieces=new
  d['reviewed_layout_figure_rects']=[r for r in d['excluded_figure_rects']if r!=figure]+pieces
  d['reviewed_native_figure_language_labels']=[dict(at=[*at,0],text=text,reviewed=True,source_sha256=d['original_english_source_sha256'])for at,text in labels.items()]
 with fitz.open(d['original_english_source'])as source:
  whites=[list(p['rect'])for p in source[n-1].get_drawings()if p.get('fill')==(1,1,1)and p.get('color')is None]
  if whites and n!=3:d['native_move_options']=dict(reviewed_white_panel_rects=whites)
  folder=B/'2017/source-page-review';folder.mkdir(exist_ok=True)
  with page_worker():source[n-1].get_pixmap(matrix=fitz.Matrix(1.3,1.3),alpha=False).save(folder/f'page{n:02}.png')
 pp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');print('PREPARED_INITIAL',2017,n,flush=True)
