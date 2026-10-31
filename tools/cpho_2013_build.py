"""Rebuild CPhO 2013 Korean questions and bilingual vector figures."""
from pathlib import Path
import json
import re
import shutil
import urllib.request
import pymupdf as fitz
import pdf_layout_translate as layout
import cpho_2013_figures as figures
from cpho_2025_build import whole_paragraph

ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'tmp/source-audit/CPhO_2013_T_EN.pdf'
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(urllib.request.urlopen('https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-cpho/'+source.name,timeout=60).read())
    work=ROOT/'tmp/cpho-build/2013';layout.extract(source,work)
    p=work/'translation.json';data=json.loads(p.read_text(encoding='utf8'))
    ko=dict(l.split('|',1) for l in (ROOT/'tools/ko/cpho/2013/problem/korean.txt').read_text(encoding='utf8').splitlines() if '|' in l)
    for e in data['entries']:
        e['ko']='CPhO 제30회 (2013) - 결선 - 이론시험 문제                              한국어판' if e['id'].endswith('-0') else ko.get(e['id'],'')
    original=fitz.open(source)
    def crop(page,name,bounds):
        r=fitz.Rect(bounds);original[page].get_pixmap(matrix=fitz.Matrix(4,4),clip=r).save(work/name)
        return {'file':name,'width':r.width,'height':r.height}
    by={e['id']:e for e in data['entries']}
    area=crop(0,'area.png',[68,341.5,105,369])
    intro={'id':'1-intro','page':0,'rect':[68,268,528,369],'size':10.9,
        'source':'[[0]] [[1]] [[2]] [[3]]','math':by['1-8']['math']+[area],
        'ko':'질량 [[0]]인 작은 공을 수평 지면으로부터 높이 [[2]]인 곳에서 수평 속력 [[1]]로 던졌다. 공기저항은 무시한다. 공이 지면에서 튀어 오를 때마다 수평 속도성분은 변하지 않고, 연직 속도성분의 크기는 매번 같은 비율로 감소한다. 첫 번째 튀어 오름 이후 공의 궤적과 그 궤적을 지면에 사영한 선 사이의 총넓이는 [[3]]이다. 모든 충돌에서 지면이 공에 가한 총충격량을 구하여라.'}
    hint={'id':'1-hint','page':0,'rect':[68,371,528,418],'size':10.9,
        'source':'[[0]]','math':[crop(0,'two-thirds.png',[506.4,382.3,514.6,409.1])],
        'ko':'힌트: 지면에서 출발하여 다시 지면에 도달하는 각각의 포물선 운동에서 궤적과 지면의 사영 사이 넓이는 최고 높이와 수평 도달거리 곱의 [[0]]이다.'}
    beta={'id':'4-beta','page':3,'rect':[68,697.5,528,726],'size':10.9,
        'source':'[[0]] [[1]]','math':[crop(3,'beta.png',[99,697.5,128.5,725]),crop(3,'light-speed.png',[153.3,705.2,159,717])],
        'ko':'여기서 [[0]]이고 [[1]]는 진공에서 빛의 속력이다.'}
    removed={'1-8','1-9','1-10','1-11','1-12','4-10','4-11'}
    data['entries']=[e for e in data['entries'] if e['id'] not in removed]+[intro,hint,beta]
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    target=ROOT/'pdfx/cpho';target.mkdir(parents=True,exist_ok=True)
    korean=target/'CPhO_2013_T_KO.pdf';english=target/'CPhO_2013_T_BAUPC_EN.pdf'
    layout.build(work,korean);shutil.copyfile(source,english)
    figures.replace(korean,'ko');figures.replace(english,'en')

def solutions():
    source=ROOT/'tmp/source-audit/CPhO_2013_TS.pdf'
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(urllib.request.urlopen('https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-cpho/'+source.name,timeout=60).read())
    work=ROOT/'tmp/cpho-build/2013-solutions';layout.extract(source,work)
    p=work/'translation.json';data=json.loads(p.read_text(encoding='utf8'))
    ko=dict(l.split('|',1) for l in (ROOT/'tools/ko/cpho/2013/solution/korean.txt').read_text(encoding='utf8').splitlines() if '|' in l)
    original=fitz.open(source);entries=[];preserved=[]
    math_words={'d','sin','cos','tan','arccos','arcsin','exp','log','const','and','when','re','im'}
    for e in data['entries']:
        residual=re.sub(r'\[\[\d+\]\]',' ',e['source'])
        words=re.findall(r'[A-Za-z]+',residual.lower())
        if not words or all(w in math_words for w in words):
            preserved.append({'id':e['id'],'source':e['source']})
            # Keep the original vector formula. Translate only its short
            # joining words rather than rasterising a displayed equation.
            block=original[e['page']].get_text('dict')['blocks'][int(e['id'].split('-')[1])]
            for li,line in enumerate(block['lines']):
                for si,span in enumerate(line['spans']):
                    word=span['text'].strip().lower()
                    if word in {'and','when'}:
                        entries.append({'id':e['id']+f'-label{li}-{si}','page':e['page'],
                            'rect':span['bbox'],'size':span['size'],'source':word,'math':[],
                            'ko':'및' if word=='and' else '일 때','redact_fill':None})
            continue
        e['ko']=('CPhO 제30회 (2013) - 결선 - 이론시험 해설                              한국어판' if e['id'].endswith('-0') else
                 '풀이' if e['source']=='Solution' else ko.get(e['id'],''))
        if e['id'] in {'3-38','10-29','11-18'}:
            e['insert_rect']=[e['rect'][0],e['rect'][1],527,e['rect'][3]]
        e['redact_fill']=None
        entries.append(e)
    data['entries']=entries;data['preserved_formula_regions']=preserved
    data['outline_source']=True
    # Equation references are prose here: the source math-font runs include
    # neighboring letters and must not be reinserted as formula pictures.
    intro=next(e for e in data['entries'] if e['id']=='1-6')
    intro['english_source']=intro['source']
    intro['source']='Introduction and equation numbering note'
    intro['math']=[]
    intro['ko']='문제집 ‘제30회 결선 문제 및 정답’의 문제 뒤에 실린 공식 참고 해설을 번역하였다. 각 문항의 식 번호 (1), (2), …는 중국어 원문을 따른다. 다른 풀이에서 같은 번호가 반복되는 경우에는 (1′), (2′), …처럼 프라임을 붙여 한 문항 안에서 식 번호가 구별되게 하였다. 문항별 채점 기준도 빠짐없이 번역하였다. 원문의 명백한 오식은 원문대로 옮기고 옮긴이 주에서 올바른 형태를 제시한다. 문제의 문구와 기호는 별도 문제지와 같다.'
    # Two-letter joining words are below the generic extractor's prose cutoff.
    for pi,page in enumerate(original):
        for bi,block in enumerate(page.get_text('dict')['blocks']):
            if block['type']!=0:continue
            for li,line in enumerate(block['lines']):
                for si,span in enumerate(line['spans']):
                    if span['text'].strip()=='or':
                        if any(e['page']==pi and fitz.Rect(e['rect']).contains(fitz.Rect(span['bbox'])) for e in data['entries']):continue
                        r=list(span['bbox']);r[2]=max(r[2],r[0]+24)
                        data['entries'].append({'id':f'{pi+1}-{bi}-or{li}-{si}',
                            'page':pi,'rect':span['bbox'],'size':span['size'],
                            'insert_rect':r,'source':'or','math':[],'ko':'또는','redact_fill':None})
    whole_paragraph(data,original,work,2,6,7,'angular-velocity',[83,231.5,512,260.5],
        [{'rect':[114.6,231.5,150,258.8],'roman':'d'}],
        '여기서 [[0]]는 막대의 회전 각속도이다. 공 2의 속도는 다음과 같다.')
    whole_paragraph(data,original,work,13,1,3,'event-one',[83,75,512,184],
        [{'rect':[205.5,75.3,216.3,88.6],'roman':'S'},(159.8,89,193.5,105),
         (220.5,89,256,105),(320.2,116,372,130),(441.5,116,451.5,130),
         (475.5,116,488,130),{'rect':[397,129.5,410.2,143],'roman':'S'},
         (458,143.3,467.5,159.5),{'rect':[265.5,156.8,278.7,170.4],'roman':'S'}],
        '2. 기준계 [[0]]에서 사건 1, 즉 ‘장이 처음 박수를 침’의 시각과 위치는 [[1]], [[2]]이다. 두 학생은 각자 기준계의 원점에 있고, [[3]]에서 두 원점이 일치하며 [[4]], [[5]]축이 같은 방향으로 일치한다고 가정한다. 왕이 정지한 기준계 [[6]]에서는 장의 시계가 느리게 간다. 시간지연 관계를 이용하면 사건 1의 시각 [[7]]을 기준계 [[8]]에서 나타낸 값(왕의 시계가 가리키는 값)은 다음과 같다.')
    whole_paragraph(data,original,work,13,15,18,'event-two',[83,340.8,512,399.5],
        [{'rect':[292,340.8,305.5,354.5],'roman':'S'},(385.3,340.8,422.6,357),
         (83,354.3,115.5,370.5),{'rect':[82.8,368,92.5,381.5],'roman':'S'},
         (138.6,381.4,148,397.6),{'rect':[383,381.4,393.6,395],'roman':'S'}],
        '이 박수는 기준계 [[0]]에서 시각 [[1]], 위치 [[2]]인 원점에서 일어나며 이를 사건 2라 한다. 장이 정지한 기준계 [[3]]에서는 왕의 시계가 느리게 간다. 시간지연 관계를 이용하여 사건 2의 시각 [[4]]를 기준계 [[5]]에서 나타내면 다음과 같다.')
    whole_paragraph(data,original,work,13,24,26,'subsequent-events',[83,468,512,518],
        [(104.2,468.2,113.6,484.3),(330.6,483.8,338.4,495.5),
         (440.7,481.8,466,498),(101.8,497,141,509),{'rect':[334,495.3,344.8,509],'roman':'S'}],
        '[[0]]은 장의 시계가 가리키는 값이다. 이를 반복하면 장이 [[1]]번째 박수를 치는 시각 [[2]], 즉 [[3]]번째 사건의 기준계 [[4]]에서의 시각(장의 시계가 가리키는 값)은 다음과 같다.')
    data['entries']=[e for e in data['entries'] if not e['id'].startswith('14-24-label')]
    next(e for e in data['entries'] if e['id']=='14-subsequent-events')['redact_rect']=[83,468,512,522]
    whole_paragraph(data,original,work,12,23,28,'slit-distance',[83,295,512,349],
        [(436.8,295,508.5,323.3),(262.5,313.5,284.6,349)],
        '두 슬릿의 평면과 관측면 사이의 거리는 [[0]]이고, 두 슬릿 사이의 간격은 [[1]]이다. 따라서 간섭무늬 간격은')
    for key,label in [('13-2','위쪽 허상:'),('13-7','아래쪽 허상:')]:
        e=next(e for e in data['entries'] if e['id']==key)
        e['english_source']=e['source'];e['source']='Virtual-image label';e['ko']=label;e['math']=[]
        e['rect']=[e['rect'][0],e['rect'][1],278,e['rect'][3]]
    e=next(e for e in data['entries'] if e['id']=='13-34')
    e['english_source']=e['source'];e['source']='From this the wire diameter is';e['ko']='따라서 철사의 지름 d는';e['math']=[]
    whole_paragraph(data,original,work,14,23,24,'event-note',[95,313,450,329],[],
        'ᵃ 옮긴이 주: 원문 그대로이다. S″에서 사건 1의 위치는 x″₁ ≠ 0으로 써야 한다.')
    for e in data['entries']:e['redact_fill']=None
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    target=ROOT/'pdfx/cpho';target.mkdir(parents=True,exist_ok=True)
    korean=target/'CPhO_2013_TS_KO.pdf';english=target/'CPhO_2013_TS_BAUPC_EN.pdf'
    layout.build(work,korean);shutil.copyfile(source,english)
    figures.replace(korean,'ko');figures.replace(english,'en')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--solutions-only',action='store_true');p.add_argument('--problems-only',action='store_true');a=p.parse_args()
    if not a.solutions_only:main()
    if not a.problems_only:solutions()
