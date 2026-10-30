"""Prepare a Word/MathType translation manifest: retain tables and native equation rows."""
import argparse,json,re
from pathlib import Path
import pymupdf as f
from izho_extract_word import candidate,mathword,configure_math_fonts
from izho_translate import ROOT,resolve_source

def prose_span(s):
 words=re.findall(r'[A-Za-z]{2,}',s['text'])
 return bool(words) and any(not mathword(w) and w.lower() not in {'dx','dy','dz','dt','dr','du','da','dq','dv'} for w in words)
def label_translation(t):
 t=t.strip();basic={'Content':'내용','Points':'배점','Total':'합계','Graph:':'그래프:','at':'때','where':'여기서','for':'단,','and':','}
 if t in basic:return basic[t]
 m=re.fullmatch(r'Formula\s*(\(\s*\d+\s*\))\s*:?',t)
 if m:return '식 '+m[1]+':'
 m=re.fullmatch(r'Numerical value(?:s)? in (?:formula|equation)\s*(\(\s*\d+\s*\))\s*:?',t)
 if m:return '식 '+m[1]+'의 수치:'
 return ''

def prepare(path):
 data=json.loads(path.read_text('utf8'))
 if data.get('prepared_word'):raise ValueError('Already prepared; keep the reviewed manifest.')
 f.TOOLS.set_small_glyph_heights(bool(data.get('small_glyph_heights')))
 src=f.open(resolve_source(data))
 if data.get('source_pages') is not None:src.select(data['source_pages'])
 configure_math_fonts(src)
 blocks=[p.get_text('dict')['blocks'] for p in src]
 tables=[[f.Rect(t.bbox) for t in p.find_tables().tables] for p in src]
 data['tables']=[{'page':pi,'rect':list(r)} for pi,rs in enumerate(tables) for r in rs]
 data['preserve_rects']=[{'page':pi,'rect':b['bbox']} for pi,bs in enumerate(blocks) for b in bs if b['type']==1 and not f.Rect(b['bbox']).is_empty]
 labels=[]
 year=int(re.search(r'20\d{2}',data['provenance']['source_name']).group())
 kind=' 해설' if '_TS' in data['provenance']['source_name'] else ''
 for e in data['entries']:
  if 'International Zhautykov' in e['source']:
   e['ko']=f'제{year-2004}회 국제 자우티코프 올림피아드 / 이론시험{kind}';e['preserved_math']=list(range(len(e['math'])));e['redact_rect']=e['rect'][:];e['rect']=[36,35.8,450,49.2];e['size']=10
   labels.append({'id':f"{e['page']+1}-page",'page':e['page'],'rect':[518,35.8,562.4,49.2],'size':10,'source':'Page number','math':[],'ko':f"{e['page']+1}/{len(src)}쪽"});continue
  bi=int(e['id'].split('-')[1]);block=blocks[e['page']][bi]
  ps=[s for l in block['lines'] for s in l['spans'] if prose_span(s)]
  in_table=any(any(r.contains(f.Point((s['bbox'][0]+s['bbox'][2])/2,(s['bbox'][1]+s['bbox'][3])/2)) for r in tables[e['page']]) for s in ps)
  if in_table:
   e['passthrough']=True;e['ko']=e['source']
   for li,line in enumerate(block['lines']):
    for si,s in enumerate(line['spans']):
     if not prose_span(s):continue
     labels.append({'id':f"label-{e['page']}-{bi}-{li}-{si}",'page':e['page'],'rect':s['bbox'],'size':min(11,s['size']),'source':s['text'],'math':[],'ko':label_translation(s['text'])})
   continue
  if not ps:
   e['passthrough']=True;e['ko']=e['source'];continue
  top=min(s['bbox'][1] for s in ps);bottom=max(s['bbox'][3] for s in ps)
  keep=[]
  for mi,m in enumerate(e['math']):
   cy=(m['rect'][1]+m['rect'][3])/2
   numbered=bool(re.search(r'\(\s*\d+\s*\)',m['text']))
   prefix=cy<top-2 or (numbered and cy<top+6)
   suffix=cy>bottom+2
   if prefix or suffix:
    keep.append(mi)
    nearby=[]
    for b in blocks[e['page']]:
     if b['type']!=0:continue
     for line in b['lines']:
      for s in line['spans']:
       if candidate(s) and abs((s['bbox'][1]+s['bbox'][3])/2-cy)<17:nearby.append(f.Rect(s['bbox']))
    ys=[f.Rect(m['rect'])]+nearby
    data['preserve_rects'].append({'page':e['page'],'rect':[36,min(r.y0 for r in ys)-2,563,max(r.y1 for r in ys)+1]})
  if keep:
   e['preserved_math']=keep;e['redact_rect']=e['rect'][:];e['rect'][1]=top;e['rect'][3]=max(bottom,top+12)
  text=e['source']
  for mi in keep:text=text.replace(f'[[{mi}]]','')
  e['translate']=re.sub(r'^[\s.,;:]+','',text).strip()
 data['entries']+=labels;data['prepared_word']=True;data['mask_prose_instead_of_redact']=True;data['transparent_math_restore']=True;data['mask_original_prose_in_math']=True;data['merge_math_rects']=True;data['math_line_height']=True;data['header_rule']=True
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8')
 print('Native table regions:',sum(e.get('passthrough',False) for e in data['entries']),'label regions:',len(labels),'pending:',sum(not e.get('passthrough') and not e['ko'] for e in data['entries']))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);a=p.parse_args();prepare(a.manifest)
