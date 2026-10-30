"""Check reconstructed diagrams and course-specific 2023 equation/layout rules."""
import hashlib
import json
from pathlib import Path
import re
import sys
import pymupdf as fitz
from kphe_template import set_typography, inline_equation_pdf, equation_pdf, COLUMNS
from kphe_typesetting_validate import fields

ROOT=Path(__file__).resolve().parents[1]

def main():
    errors=[];runs=0;unique=set();maximum=0
    for path in sorted((ROOT/'tools/kphe_solutions').glob('2023-*.json')):
        for part,rows in json.loads(path.read_text(encoding='utf8')).items():
            if not isinstance(rows,list):continue
            set_typography(ROOT/'tmp/kphe_archive/originals'/f'KPhE_2026_T2{part[-1]}_KO.pdf')
            for row in rows:
                for field,value in fields(row):
                    display=field.startswith('problem.statement') and bool(re.fullmatch(r'\s*\$[^$]+\$\s*',value))
                    limit=244.5 if display else 232.2-(5 if field.startswith('problem.givens') else 0)
                    if value.count('$')%2:errors.append([path.name,part,row['number'],field,'unbalanced math'])
                    outside=re.sub(r'\$[^$]+\$','',value)
                    if re.search(r'[_^α-ωΑ-Ω√∫Σ∑ħℏ²³₀-₉]|\bsqrt\s*\(',outside):
                        errors.append([path.name,part,row['number'],field,'unmarked mathematics'])
                    for match in re.finditer(r'\$([^$]+)\$',value):
                        runs+=1;unique.add(match[1])
                        try:
                            _,width,_,_=equation_pdf(match[1],9.81) if display else inline_equation_pdf(match[1],9.8)
                            maximum=max(maximum,width)
                            if width>limit:errors.append([path.name,part,row['number'],field,'overwide equation',width,limit,match[1]])
                        except Exception as error:errors.append([path.name,part,row['number'],field,str(error)])
    native_count=0;image_count=0;statuses=[]
    if '--math-only' not in sys.argv:
        from kphe_redraw import records,native_figure
        from kphe_figures import crop_key
        original=json.loads((ROOT/'tools/kphe_figures/index.json').read_text(encoding='utf8'))['figures']
        if set(records())!=set(original):errors.append(['native crop coverage',len(records()),len(original)])
        for key,old in original.items():
            try:
                path,item=native_figure(old['source'],old['page'],old['rect'])
                if crop_key(item['source'],item['page'],item['rect'])!=key:
                    errors.append([key,'diagram source identity differs'])
                doc=fitz.open(path);native_count+=1
                if len(doc)!=1:errors.append([key,'diagram must have exactly one page'])
                images=sum(len(page.get_images(full=True)) for page in doc);image_count+=images
                if images:errors.append([key,'raster image inside native diagram'])
                if abs(doc[0].rect.width-item['width_pt'])>.1 or abs(doc[0].rect.height-item['height_pt'])>.1:
                    errors.append([key,'native dimensions differ'])
                statuses.append(item['status'])
            except Exception as error:errors.append([key,str(error)])
        overlay=json.loads((ROOT/'tools/kphe_print.json').read_text(encoding='utf8'))['kphe']
        for year in ('2023-1','2023-2'):
            for part,files in overlay[year]['f'].items():
                for kind,name in files.items():
                    if kind not in ('paper','key','sol'):continue
                    for pn,page in enumerate(fitz.open(ROOT/name),1):
                        text=page.get_text()
                        if any(s in text for s in ('첨부 기출을 최신 형식','공식 배포 원본과 구분','자체 작성 풀이 해설')):
                            errors.append([name,pn,'removed footer still present'])
        doc=fitz.open(ROOT/'pdfx/kphe/KPhE_2023_T2d_KO.pdf')
        regions=overlay['2023-2']['questionRegions']['T2d']
        for number in (1,2,3):
            region=regions[number-1];region=region[0] if isinstance(region,list) else region
            page=doc[region['page']-1]
            r=fitz.Rect(region['rect']);clip=fitz.Rect(r.x0*page.rect.width,r.y0*page.rect.height,r.x1*page.rect.width,r.y1*page.rect.height)
            spans=[span for block in page.get_text('dict',clip=clip)['blocks'] for line in block.get('lines',[]) for span in line['spans']]
            if not any('KPhE' in span['font'] and 'V' in span['text'] and span['size']>=9.8 for span in spans):
                errors.append(['T2d',number,'potential display equation is not full size'])
    report={'math_runs':runs,'unique_math':len(unique),'maximum_equation_width':maximum,
        'native_figures':native_count,'raster_images_in_native_figures':image_count,'errors':errors}
    suffix='math' if '--math-only' in sys.argv else 'publication'
    (ROOT/f'tools/kphe_2023_{suffix}_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=1))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
