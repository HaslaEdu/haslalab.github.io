"""Bilingual CPhO 2006 in the source page geometry, with vector line diagrams.

This short Word-derived source uses damaged font names and separate fraction
objects. Reviewed paragraph boundaries and shared HTML formula constants avoid
using its unreliable extracted formula order. The two displayed equations stay
at their original coordinates. No solution is present in the source archive.
"""
from pathlib import Path
from collections import Counter
import hashlib,html,json,re,urllib.request
import pymupdf as fitz
import pdf_layout_translate as layout
import cpho_2006_figures as figures
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'tools/ko/cpho/2006'
SOURCE_SHA256='4ca77258299918a44f26320027466b81cc70c97e7e467ee190282be0f4516042'
FORMULAS={
 'earthR':'<i>R</i><sub>0</sub> = 6.37 × 10<sup>6</sup> m',
 'surfaceG':'<i>g</i> = 9.80 m·s<sup>−2</sup>',
 'sheetL':'<i>l</i> = √3<i>R</i>',
 'adiabatic':'<i>pV</i><sup>γ</sup> = <i>C</i>',
 'gamma':'γ = 1.40',
 'molar':'μ = 0.029 kg·mol<sup>−1</sup>',
 'gasR':'<i>R</i> = 8.31 J·(K·mol)<sup>−1</sup>',
 'atmosG':'<i>g</i> = 9.8 m·s<sup>−2</sup>†',
 'temp0':'<i>T</i><sub>e0</sub> = 300 K',
 'gateDelta':'δ = <i>T</i>/10',
 'alpha45':'α = π/4',
 'protonMass':'<i>m</i><sub>0</sub> = 1.67 × 10<sup>−27</sup> kg'
}
# page, inclusive original text-block range, translation key, insertion box
REGIONS=[
 (0,5,5,'title',[90,79,520,117]),
 (0,6,14,'q1',[90,126,520,296]),
 (0,16,18,'q2_intro',[90,324,521,383]),
 (0,19,27,'q2_wrap',[90,390,375,579]),
 (0,28,31,'q2_b',[90,588,521,667]),
 (0,32,34,'q3_intro',[90,676,521,734]),
 (1,41,57,'q3_body',[90,82,521,360]),
 (1,59,71,'q4_intro',[90,390,521,558]),
 (1,72,77,'q4_wrap',[90,566,252,689]),
 (1,80,81,'q4_distances',[90,720,252,755]),
 (2,4,7,'q4_continue',[90,82,521,139]),
 (2,8,13,'q4_a',[90,148,521,271]),
 (2,14,20,'q4_b',[90,276,521,425]),
 (2,22,26,'q5_intro',[90,456,521,557]),
 (2,27,28,'q5_a',[90,566,521,602]),
 (2,29,31,'q5_b',[90,610,521,667]),
 (3,5,11,'q6',[90,82,521,206])
]

def content(text):
    result=html.escape(text).replace('\n','<br>')
    for key in re.findall(r'\[\[([A-Za-z0-9]+)\]\]',text):
        if key not in FORMULAS:raise ValueError('Unknown formula '+key)
        result=result.replace('[['+key+']]',FORMULAS[key])
    return result

def main():
    source=ROOT/'tmp/source-audit/CPhO_2006_T_ZH.pdf'
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(urllib.request.urlopen('https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-cpho/'+source.name,timeout=60).read())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=SOURCE_SHA256:raise ValueError('CPhO 2006 source differs from the reviewed original')
    (ROOT/'tmp/cpho-build/2006').mkdir(parents=True,exist_ok=True)
    original=fitz.open(source);texts=json.loads((FOLDER/'bilingual.json').read_text(encoding='utf8'))
    for key,item in texts.items():
        if Counter(re.findall(r'\[\[[^]]+\]\]',item['ko']))!=Counter(re.findall(r'\[\[[^]]+\]\]',item['en'])):
            raise ValueError('Bilingual formula mismatch: '+key)
    provenance=[];archive=fitz.Archive(str(layout.FONT.parent))
    times=Path('C:/Windows/Fonts/times.ttf')
    if times.exists():archive.add(str(times.parent))
    roman='@font-face{font-family:SourceRoman;src:url(times.ttf);}' if times.exists() else ''
    family='SourceRoman,Korean' if times.exists() else 'serif,Korean'
    css='@font-face{font-family:Korean;src:url(NotoSansKR-Regular.ttf);}' + roman + \
        '*{font-family:'+family+';color:#000;}body,p{margin:0;padding:0;}'
    targets=ROOT/'pdfx/cpho';targets.mkdir(parents=True,exist_ok=True)
    for lang in ['ko','en']:
        doc=layout.outlined_copy(original);report=[]
        entries=[]
        for pi,start,end,key,bounds in REGIONS:
            blocks=original[pi].get_text('dict')['blocks']
            erase=[b['bbox'] for b in blocks[start:end+1] if b['type']==0]
            entries.append((pi,key,bounds,erase))
            if lang=='ko':provenance.append({'key':key,'page':pi+1,'original_blocks':[start,end],
                'source_text':' '.join(s['text'] for b in blocks[start:end+1] if b['type']==0 for line in b['lines'] for s in line['spans'])})
        for pi in range(len(doc)):
            for block in [0,2]:
                r=original[pi].get_text('dict')['blocks'][block]['bbox']
                entries.append((pi,'header',[90,r[1]-1,521,r[3]+1],[r]))
        entries.append((3,'note',[90,475,521,525],[]))
        for pi,key,bounds,erase in entries:
            page=doc[pi]
            if erase:page.draw_rect(fitz.Rect(bounds),color=None,fill=(1,1,1))
            header=key=='header';title=key=='title';note=key=='note'
            size=10 if header else 14 if title else 9 if note else 12
            lineheight=1.2 if header or title else 1.25 if lang=='en' else 1.5
            align='center' if header or title else 'left';color='#ff0000' if header else '#000000'
            text=content(texts[key][lang])
            spare,scale=page.insert_htmlbox(fitz.Rect(bounds),f'<p style="font-size:{size}pt;line-height:{lineheight};text-align:{align};color:{color}">{text}</p>',
                css=css,archive=archive,scale_low=.70)
            if spare<0:raise ValueError(f'Text does not fit: {key}/{lang}')
            report.append({'page':pi+1,'key':key,'scale':scale,'font_points':size*scale})
        # Add diagrams after HTML forms, then restore the source footer that
        # the fragmented picture canvas originally covered on page 2.
        figures.stamp(doc,original,lang)
        footer=next(item for item in entries if item[0]==1 and item[1]=='header' and item[2][1]>700)
        r=fitz.Rect(footer[2]);doc[1].draw_rect(r,color=None,fill=(1,1,1))
        spare,scale=doc[1].insert_htmlbox(r,f'<p style="font-size:10pt;line-height:1.2;text-align:center;color:#ff0000">{content(texts["header"][lang])}</p>',css=css,archive=archive,scale_low=.7)
        if spare<0:raise ValueError('Page 2 footer does not fit')
        name='CPhO_2006_T_KO.pdf' if lang=='ko' else 'CPhO_2006_T_BAUPC_EN.pdf'
        target=targets/name;doc.save(target,garbage=4,deflate=True);doc.close()
        (ROOT/f'tmp/cpho-build/2006/{lang}-qa.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        print(name,'minimum body font',round(min(r['font_points'] for r in report if r['key'] not in {'header','title','note'}),2))
    (ROOT/'tmp/cpho-build/2006/provenance.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'regions':provenance},ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':main()
