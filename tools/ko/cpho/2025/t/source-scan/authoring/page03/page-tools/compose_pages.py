"""2025 source-page compositor. Original bitmap math first, new prose last."""
from pathlib import Path
import sys,json,re,hashlib,math,argparse
BASE=Path(__file__).resolve().parents[1];B=BASE.parent
ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
sys.path[:0]=['D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools',str(ROOT/'tools')]
import pymupdf as fitz,pikepdf
import cpho_2013_ts_compose as shared
shared.BASE=BASE
from pdf_original_raster_math import replay
from pdf_memory_gate import page_worker
SOURCE=B/'CPhO_2025_T_original-explicit-page-clip.pdf';SOURCE_SHA='c9562e8f6053b454391083289b179f28ed29f7d9024723a34a2a8b0e663bd306'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def layout(row,lang,metric):
 amap={a['id']:a for a in row['atoms']};tokens=[];used=[]
 for part in re.split(r'(\[\[[^]]+\]\])',row[lang]):
  if not part:continue
  if part.startswith('[['):
   key=part[2:-2];a=amap[key];used.append(key);tokens.append(dict(kind='math',width=a['rect'][2]-a['rect'][0],atom=a))
  else:tokens.append(dict(kind='prose',text=part,width=shared.width(metric,part,row['size'])))
 if sorted(used)!=sorted(amap):raise ValueError(('Original symbol dropped or repeated',row['id'],used,list(amap)))
 total=sum(t['width']for t in tokens);x=row['left']
 if row.get('align')=='center':x=(row['left']+row['right']-total)/2
 left=x
 for token in tokens:token['x']=x;x+=token['width']
 if x>row['right']+.001:raise ValueError(('Fixed-size row overflow',row['id'],lang,x,row['right']))
 return tokens,left,x

def build(number,lang):
 if sha(SOURCE)!=SOURCE_SHA:raise ValueError('Source PDF changed')
 path=BASE/f'plans/page{number:02d}-draft-layout.json';plan=json.loads(path.read_text('utf8'))
 if not plan.get('manual_rois_reviewed'):raise ValueError('Full source-contact review required before replay')
 out=BASE/'proofs'/lang;out.mkdir(parents=True,exist_ok=True);stem=out/f'page{number:02d}'
 pool=''.join(re.sub(r'\[\[[^]]+\]\]','',r[lang])for r in plan['rows'])
 fp=Path('C:/Windows/Fonts/batang.ttc')if lang=='ko'else Path('C:/Windows/Fonts/simsun.ttc');raw,metric,fontqa=shared.new_font(fp,pool)
 atoms=[];placements=[];prose=[]
 for row in plan['rows']:
  tokens,left,right=layout(row,lang,metric)
  for token in tokens:
   if token['kind']=='math':
    a=token['atom']
    if a.get('reviewed')is not True:raise ValueError(('Unreviewed original math bitmap',row['id'],a['id']))
    atoms.append(dict(id=row['id']+'/'+a['id'],rect=a['rect'],image_path=a['image_path'],dx=token['x']-a['rect'][0],reviewed=True,reason=a['reason']))
   else:prose.append(dict(text=token['text'],point=[token['x'],row['baseline']],size=row['size'],row=row['id'],stroke=row['printed_stroke_by_language'][lang]['regular']))
  placements.append(dict(id=row['id'],text=row[lang],point_size=row['size'],baseline=row['baseline'],left=left,right=right,tokens=tokens))
 linked=[];by_id={a['id']:a for a in atoms}
 for dependent,anchor in plan.get('linked_original_math_dx',{}).items():
  if not plan.get('linked_original_math_dx_evidence')or dependent not in by_id or anchor not in by_id:raise ValueError('Unreviewed or unknown original multiline mathematical anchor')
  item=by_id[dependent];ref=by_id[anchor];item['dx']=ref['dx'];linked.append(dict(dependent=dependent,anchor=anchor,dx=item['dx'],original_relative_xy_unchanged=True,evidence=plan['linked_original_math_dx_evidence']))
 single=stem.with_suffix('.source.pdf')
 with pikepdf.open(SOURCE)as src,pikepdf.Pdf.new()as outdoc:outdoc.pages.append(src.pages[number-1]);outdoc.save(single,compress_streams=False)
 erased=stem.with_suffix('.erased.pdf');erase=[rect for row in plan['rows']for rect in row['erase_rects']]+[a['rect']for a in atoms]
 shared.add_erase_rects(single,erased,erase)
 encoded,journal=replay(SOURCE,number,erased,atoms)
 control=stem.with_suffix('.pre-prose.pdf');control.write_bytes(encoded)
 target=stem.with_suffix('.pdf');reference=stem.with_suffix('.prose-only.pdf')
 with fitz.open(stream=encoded,filetype='pdf')as doc:
  page=doc[0];page.insert_font(fontname='ScanBody',fontbuffer=raw)
  ref=fitz.open();rp=ref.new_page(width=page.rect.width,height=page.rect.height);rp.insert_font(fontname='ScanBody',fontbuffer=raw)
  for part in prose:
   for p in[page,rp]:shared.write_words(p,*part['point'],part['text'],metric,part['size'],'ScanBody',2,part['stroke'])
  doc.save(target,garbage=0,deflate=False);ref.save(reference,garbage=0,deflate=False);ref.close()
 with fitz.open(target)as d:d[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(stem.with_suffix('.png'))
 report=dict(status='PROOF_NOT_FOR_PUBLICATION',source=str(SOURCE),source_sha256=SOURCE_SHA,source_page=number,language=lang,proof=str(target),proof_sha256=sha(target),plan=str(path),plan_sha256=sha(path),font=fontqa,placements=placements,prose_placements=prose,math_replay=journal,linked_original_math_dx=linked,math_control=str(control),prose_reference=str(reference),no_math_resampling=True,source_math_y_unchanged=True,manual_final_visual_review_required=True,publication_ready=False)
 stem.with_suffix('.composition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print('PROOF',number,lang,sha(target),flush=True);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('page',type=int);p.add_argument('language',choices=['ko','en']);a=p.parse_args()
 with page_worker():build(a.page,a.language)
