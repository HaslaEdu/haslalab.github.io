"""Rebuild the CPhO 2005 Korean questions and bilingual vector illustrations.

The available source is a seven-page English problem booklet; no official
solution is present in the source archive. The title-page translator credit
and original page geometry are retained.
"""
from pathlib import Path
import json, shutil, urllib.request
import pymupdf as fitz
import pdf_layout_translate as layout
from cpho_2025_build import join_existing, fit_math_leading
import cpho_2005_figures as figures
ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'tmp/source-audit/CPhO_2005_T_EN.pdf'
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(urllib.request.urlopen('https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-cpho/'+source.name,timeout=60).read())
    work=ROOT/'tmp/cpho-build/2005';layout.extract(source,work,roman_prose=True)
    p=work/'translation.json';data=json.loads(p.read_text(encoding='utf8'))
    merges=[(1,2,3,'part-a',[132,428.6,519.5,477]),
        (1,4,6,'part-b',[132,485.4,519.5,590]),
        (4,0,1,'parameters',[126,133.2,519.5,216]),
        (4,5,6,'part-a',[132,476.6,519.5,527]),
        (4,7,8,'part-b',[132,533.4,519.5,632.5]),
        (6,0,1,'part-a',[132,133.5,519.5,165]),
        (6,5,6,'graph',[132,509.5,519.5,558]),
        (6,7,8,'motion',[132,566.3,519.5,615])]
    for page,start,end,name,bounds in merges:join_existing(data,page,start,end,name,bounds)
    ko=dict(line.split('|',1) for line in (ROOT/'tools/ko/cpho/2005/problem/korean.txt').read_text(encoding='utf8').splitlines() if '|' in line)
    for e in data['entries']:
        if e['id']=='4-3':
            e['id']='4-parameters';e['preserved_math']=[0]
            e['rect']=[126,641.5,519.5,675.1]
            e['english_source']=e['source'];e['source']='Spring constants and friction coefficient'
            e['math']=[];e['preserved_math']=[]
        if e['id']=='5-parameters':
            e['english_source']=e['source'];e['source']='Buffer friction angle and initial and additional compressions';e['math']=[]
        e['ko']=ko[e['id']]
        if e['page']>0:e['size']=11.95;fit_math_leading(e)
        else:
            e['align']='center';e['insert_rect']=[68,e['rect'][1],544,e['rect'][3]+2]
        if e['id']=='1-2':e['insert_rect']=[150,402,460,424];e['size']=12
    data['outline_source']=True
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    out=ROOT/'pdfx/cpho';out.mkdir(parents=True,exist_ok=True)
    korean=out/'CPhO_2005_T_KO.pdf';english=out/'CPhO_2005_T_BAUPC_EN.pdf'
    layout.build(work,korean);shutil.copy2(source,english)
    figures.replace(korean,'ko');figures.replace(english,'en')

if __name__=='__main__':main()
