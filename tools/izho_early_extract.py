"""Extract 2010--2017 IZhO prose without dropping Roman math subscripts.

The early Word PDFs often put a subscript on a separate extracted line.  A
font-only, line-by-line extraction loses those glyphs.  This extractor clusters
nearby math spans in two dimensions; complete display equations stay original.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, json, re
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
WORD = re.compile(r"[A-Za-zА-Яа-яЁё]{3,}")
MATH_WORDS = set("sin cos tan cot exp ln log max min lim sup inf const emf eff mev kev gev tev ghz ev kg mm cm nm km mol amu out int dt dx dy dz dr eb ir li jr ejr mmr nmmr vmag vmagnet".split())

def is_seed(s):
    font=s['font'].replace(' ','')
    # CMR is also used for ordinary TeX prose.  Its font name alone is not a
    # license to turn an English paragraph into a supposedly mathematical crop.
    return (font.startswith(('CM','LM','CambriaMath')) and math_candidate(s)) or font.startswith(('Symbol','MT-Extra','MTExtra')) or ('Italic' in font and not re.search(r'[A-Za-zА-Яа-яЁё]{2,}',s['text']))

def math_candidate(s):
    t=s['text'].strip()
    if not t:return False
    words=re.findall(r'[A-Za-zА-Яа-яЁё]+',t)
    return not words or all((len(w)==1 and not re.search(r'[А-Яа-яЁё]',w)) or w.lower() in MATH_WORDS or (len(w)<=5 and w.isupper() and not re.search(r'[А-Яа-яЁё]',w)) for w in words)

def extract(year,kind,source_name=None,pages=None):
    name=source_name or f'IZhO_{year}_'+('T_RU.pdf' if year==2012 and kind=='T' else 'T_EN.pdf' if kind=='T' else 'TS.pdf')
    source=ROOT/'tmp/source-audit'/name
    folder=ROOT/f'tools/ko/izho/{year}/{kind}';folder.mkdir(parents=True,exist_ok=True)
    old=json.loads((folder/'translation.json').read_text(encoding='utf8')) if (folder/'translation.json').exists() else {}
    previous={e['id']:e for e in old.get('entries',[])}
    doc=fitz.open(source);entries=[];skipped=[];diff=[]
    if pages is not None:doc.select(pages)
    fitz.TOOLS.set_small_glyph_heights(False)
    small=any(s['bbox'][3]-s['bbox'][1]>s['size']*2.5 for page in doc for b in page.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans'])
    fitz.TOOLS.set_small_glyph_heights(small)
    for pi,page in enumerate(doc):
      for bi,block in enumerate(page.get_text('dict')['blocks']):
        if block['type']!=0:continue
        key=f'{pi+1}-{bi}'
        spans=[dict(s) for line in block['lines'] for s in line['spans']]
        text=' '.join(s['text'] for s in spans)
        if not WORD.search(text):continue
        rects=[]
        for s in spans:
          r=fitz.Rect(s['bbox'])
          if r.height>s['size']*2.5:r.y0=s['origin'][1]-s['size']*1.05;r.y1=s['origin'][1]+s['size']*.30
          rects.append(r)
        selected={i for i,s in enumerate(spans) if is_seed(s) and s['text'].strip()}
        def close(i,j,limit=4.2):
          a,b=rects[i],rects[j]
          x=max(a.x0-b.x1,b.x0-a.x1,0); y=max(a.y0-b.y1,b.y0-a.y1,0)
          delta=abs(spans[i]['origin'][1]-spans[j]['origin'][1]);small=min(spans[i]['size'],spans[j]['size']);large=max(spans[i]['size'],spans[j]['size'])
          same_row=delta<=large*.36 or (small<large*.85 and delta<large*.94)
          return x<=limit and y<=.5 and same_row
        # Add Roman indices/functions touching a math glyph, including spans
        # emitted on a separate line by Word's equation engine.
        changed=True
        while changed:
          changed=False
          for i,s in enumerate(spans):
            if i not in selected and math_candidate(s) and any(close(i,j) for j in selected):
              selected.add(i);changed=True
        remaining=' '.join(s['text'] for i,s in enumerate(spans) if i not in selected)
        prose=[w for w in WORD.findall(remaining) if w.lower() not in MATH_WORDS]
        if not prose:
          skipped.append({'id':key,'rect':block['bbox'],'text':text});continue
        # Components preserve genuine inline separators but include fractions,
        # accents, and subscripts belonging to the same mathematical object.
        groups=[]
        for i in sorted(selected):
          touching=[g for g in groups if any(close(i,j) for j in g)]
          g={i}
          for t in touching:g|=t;groups.remove(t)
          groups.append(g)
        groups.sort(key=min);which={i:gi for gi,g in enumerate(groups) for i in g}
        maths=[]
        for gi,g in enumerate(groups):
          r=fitz.Rect(rects[min(g)])
          for i in g:r|=rects[i]
          r+=(-.25,-.25,.25,.25)
          fname=f'{key}-m{gi}.png'
          page.get_pixmap(matrix=fitz.Matrix(4,4),clip=r,alpha=False).save(folder/fname)
          maths.append({'file':fname,'rect':list(r),'width':r.width,'height':r.height,'text':' '.join(spans[i]['text'] for i in sorted(g))})
        chunks=[];seen=set()
        for i,s in enumerate(spans):
          if i in which:
            gi=which[i]
            if gi not in seen:chunks.append(f'[[{gi}]]');seen.add(gi)
          else:chunks.append(s['text'])
          chunks.append(' ')
        t=re.sub(r'\s+',' ',''.join(chunks)).strip()
        e={'id':key,'page':pi,'rect':block['bbox'],'size':max(s['size'] for s in spans),'source':t,'math':maths,'ko':''}
        if key in previous and previous[key]['source']==t:e['ko']=previous[key].get('ko','')
        if key in previous and previous[key]['source']!=t:diff.append({'id':key,'old':previous[key]['source'],'new':t})
        entries.append(e)
    data={'source':f'tmp/source-audit/{name}','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'provenance':{'source_name':name,'source_language':'Russian' if '_RU' in name else 'English','translation_language':'Korean'},'entries':entries,'extraction':'izho_early_extract.py / 2-D math clusters','untouched_display_blocks':skipped}
    if pages is not None:data['source_pages']=pages
    if small:data['small_glyph_heights']=True
    # The source originals and all skipped display formulas remain untouched.
    (folder/'translation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    (ROOT/f'tmp/izho-early/{year}-{kind}-extract-diff.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2),encoding='utf8')
    print(year,kind,len(entries),'prose;',len(skipped),'display blocks preserved')

if __name__=='__main__':
 import sys
 for year in map(int,sys.argv[1:] or range(2010,2018)):
  for kind in ['T','TS']:extract(year,kind)
