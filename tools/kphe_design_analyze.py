"""Measure all 24 official 2024--2026 papers in A4 points, by course/sitting."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT/'tmp/kphe_archive/originals'
OUTPUT = ROOT/'tools/kphe_design_profiles.json'

def measure(path):
    doc=fitz.open(path)
    body, equations, headings, origins, leading = (Counter() for _ in range(5))
    image_sizes=[]; pure_equations=[]
    for pn,page in enumerate(doc,1):
        scale=595.276/page.rect.width
        lines_by_column={0:[],1:[]}
        for block in page.get_text('dict')['blocks']:
            if block['type']==1:
                box=fitz.Rect(block['bbox'])*scale
                if box.y0>70 and box.y1<790:
                    image_sizes.append([round(box.width,2),round(box.height,2)])
                continue
            for line in block.get('lines',[]):
                text=''.join(s['text'] for s in line['spans'])
                box=fitz.Rect(line['bbox'])*scale
                has_math=False
                for span in line['spans']:
                    point=round(span['size']*scale,2)
                    font=span['font']
                    weight=len(span['text'].strip())
                    if box.y1<70:
                        headings[(font,point)]+=weight
                    elif 70<box.y0<780:
                        if 'EQ' in font:
                            equations[(font,point)]+=weight;has_math=True
                        elif re.search('[가-힣]',span['text']) and font in ('Gulim','Haansoft Batang'):
                            body[(font,point)]+=weight
                            origins[round(span['origin'][0]*scale,1)]+=weight
                            if span['size']*scale>9.7:
                                lines_by_column[int(box.x0>297.6)].append((round(span['origin'][0]*scale,1),span['origin'][1]*scale))
                if has_math and not re.search('[가-힣]',text) and box.width>35 and len(pure_equations)<30:
                    pure_equations.append({'page':pn,'bbox_pt':[round(v,2) for v in box],
                        'sizes_pt':sorted({round(s['size']*scale,2) for s in line['spans'] if 'EQ' in s['font']})})
        for lines in lines_by_column.values():
            seen=sorted(set(lines),key=lambda pair:pair[1])
            for (x1,y1),(x2,y2) in zip(seen,seen[1:]):
                if abs(x1-x2)<.3 and 10<y2-y1<25:
                    leading[round(y2-y1,2)]+=1
    def ranked(counter):
        return [{'font':font,'point':point,'characters':weight} for (font,point),weight in counter.most_common()]
    math_main=next((item for item in equations.most_common() if item[0][1]>=7),None)
    return {'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':len(doc),
        'body':ranked(body),'math':ranked(equations),'header':ranked(headings),
        'body_origins_pt':origins.most_common(10),'body_leading_pt':leading.most_common(8),
        'figure_sizes_pt':image_sizes,'display_equation_examples':pure_equations,
        'dominant_math_font':math_main[0][0] if math_main else None,
        'dominant_math_point':math_main[0][1] if math_main else None}

def main():
    paths=sorted(INPUT.glob('KPhE_202[456]_T[12][abcd]_KO.pdf'))
    if len(paths)!=24:raise ValueError(f'Expected 24 original papers, found {len(paths)}')
    profiles={path.name:measure(path) for path in paths}
    canonical={}
    for course in 'abcd':
        key=f'KPhE_2026_T2{course}_KO.pdf'
        profile=profiles[key]
        canonical[course]={'reference':key,'body_font':profile['body'][0]['font'],
            'body_point':profile['body'][0]['point'],
            'equation_font':profile['dominant_math_font'] or 'HyhwpEQ',
            'inline_equation_point':profile['dominant_math_point'] or 9.81,
            'display_equation_point':9.81,'body_leading_point':15.70,
            'column_rects_pt':[[46.4,290.9],[307.1,551.6]],'question_indent_point':12.3,
            'display_alignment':'center in the full column, independently of the question indent',
            'figure_label_point':9.0,'minimum_table_text_point':9.0}
    report={'checked':'2026-10-30','official_papers':24,'official_pages':sum(p['pages'] for p in profiles.values()),
        'coordinate_system':'A4 points, source dimensions normalized by page width',
        'decision':'Retain each official PDF unchanged. Use the latest sitting per course for 2023 stationery; distinguish inline and separately displayed equations. Reconstruct figures with real vector geometry and readable text, without scaling raster ink contours.',
        'canonical_2023':canonical,'profiles':profiles}
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    for course,profile in canonical.items():print(course,json.dumps(profile,ensure_ascii=False))
    print('Measured',len(profiles),'official papers /',report['official_pages'],'pages')

if __name__=='__main__':main()
