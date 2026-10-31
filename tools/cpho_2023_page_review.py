"""Preflight a complete translated source page, then build both fixed-size proofs."""
import argparse,json
from pathlib import Path
from pymupdf import Font
import cpho_2023_original_style as m

def review(number,build=True):
    data=json.loads((m.OUT/'slots.json').read_text(encoding='utf8'));page=next(p for p in data['pages']if p['number']==number)
    t={k:dict(ko=ko,en=en)for k,ko,en in(row.split('\t')for row in(m.ROOT/'tools/ko/cpho/2023/original-style.tsv').read_text(encoding='utf8').splitlines()if row.strip())}
    fonts={};errors=[]
    for s in page['slots']:
        for lang in ['ko','en']:
            if s['id']not in t:errors.append(dict(id=s['id'],source=s['source'],reason='Missing'));continue
            text=t[s['id']][lang]
            if '[REVIEW]'in text:errors.append(dict(id=s['id'],reason='Unreviewed'));continue
            if text==s['source']:continue
            width=0
            for path,run in m.text_runs(s,text,lang):
                if path not in fonts:fonts[path]=Font(fontfile=str(path))
                width+=m.run_advance(s,fonts[path],run)
            if width>s['right']-s['origin'][0]+.02:errors.append(dict(id=s['id'],lang=lang,excess=round(width-s['right']+s['origin'][0],2),text=text))
    print(json.dumps(errors,ensure_ascii=False,indent=2),flush=True)
    if errors:raise SystemExit(1)
    if build:
        data['pages']=[page]
        for lang in ['ko','en']:m.build(data,t,lang)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('page',type=int);p.add_argument('--preflight',action='store_true');a=p.parse_args();review(a.page,not a.preflight)
