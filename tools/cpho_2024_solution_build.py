"""CPhO 2024 complete Korean solutions, original equations and page geometry.

The original English solution booklet has several overlapping PDF text objects.
Coalesce them before typesetting and de-duplicate overlapping mathematical crops.
All 533 extracted source regions have reviewed Korean translations.
"""
from pathlib import Path
from collections import Counter
import json
import re
import shutil
import urllib.request
import pymupdf as fitz
from PIL import Image,ImageChops
import pdf_layout_translate as layout
import cpho_2024_solution_figures as figures
from cpho_2025_build import clean_math_image, fit_math_leading

ROOT=Path(__file__).resolve().parents[1]
FUNCTIONS={'cos','sin','tan','exp','lim','d','amu','mev','kev','ghz'}

def pure_mathematics(text):
    words=re.findall('[A-Za-z]+',re.sub(r'\[\[\d+\]\]',' ',text))
    return all(w.lower() in FUNCTIONS for w in words)

def combine(entries):
    maths=[];src=[];ko=[]
    for e in entries:
        offset=len(maths)
        convert=lambda m:f'[[{int(m[1])+offset}]]'
        src.append(re.sub(r'\[\[(\d+)\]\]',convert,e['source']))
        ko.append(re.sub(r'\[\[(\d+)\]\]',convert,e['ko']))
        maths.extend(e['math'])
    bounds=[min(e['rect'][0] for e in entries),min(e['rect'][1] for e in entries),
            max(e['rect'][2] for e in entries),max(e['rect'][3] for e in entries)]
    e=entries[0]
    return {'id':e['id']+'-merged','page':e['page'],'rect':bounds,
        'size':max(x['size'] for x in entries),'source':' '.join(src),'ko':' '.join(ko),
        'math':maths,'original_entry_ids':[x['id'] for x in entries]}

def coalesce(data):
    entries=data['entries'];parent=list(range(len(entries)))
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    for i,a in enumerate(entries):
        for j,b in enumerate(entries[i+1:],i+1):
            if a['page']!=b['page']:continue
            r=fitz.Rect(a['rect'])&fitz.Rect(b['rect'])
            if not r.is_empty and r.width>2 and r.height>1:parent[root(j)]=root(i)
    groups={}
    for i in range(len(entries)):groups.setdefault(root(i),[]).append(entries[i])
    out=[]
    for group in groups.values():
        group.sort(key=lambda e:int(e['id'].split('-')[1]))
        out.append(combine(group) if len(group)>1 else group[0])
    data['entries']=out

def repair_math(e,source,work):
    # Only merge adjacent tokens: intervening prose can change Korean word order.
    n=len(e['math']);parent=list(range(n))
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    for i,a in enumerate(e['math']):
        for j,b in enumerate(e['math'][i+1:],i+1):
            if not a.get('source_rect') or not b.get('source_rect'):continue
            r=fitz.Rect(a['source_rect'])&fitz.Rect(b['source_rect'])
            if not r.is_empty and r.width>.4 and r.height>.4:parent[root(j)]=root(i)
    groups={}
    for i in range(n):groups.setdefault(root(i),[]).append(i)
    for members in groups.values():
        if len(members)<2:continue
        pattern=r'\s*'.join(re.escape(f'[[{i}]]') for i in members)
        if not re.search(pattern,e['source']) or not re.search(pattern,e['ko']):continue
        bounds=fitz.Rect(e['math'][members[0]]['source_rect'])
        for i in members[1:]:bounds|=fitz.Rect(e['math'][i]['source_rect'])
        index=len(e['math']);filename=e['id']+f'-joined{index}.png'
        e['math'].append({'file':filename,'width':bounds.width,'height':bounds.height,'source_rect':list(bounds)})
        for key in ('source','ko'):e[key]=re.sub(pattern,f'[[{index}]]',e[key])
    used={int(i) for i in re.findall(r'\[\[(\d+)\]\]',e['source'])}
    for i in used:
        m=e['math'][i]
        if m.get('source_rect'):
            clean_math_image(source,e['page'],fitz.Rect(m['source_rect']),work/m['file'],roman='¯')
    fit_math_leading(e,cap=24)


def paragraph(data,source,work,page,start,end,name,bounds,crops,korean,size=10.9):
    """Replace fragmented text objects by one complete Korean paragraph."""
    previous=[];remaining=[]
    for e in data['entries']:
        ids=e.get('original_entry_ids',[e['id']])
        included=e['page']==page and any(start<=int(k.split('-')[1])<=end for k in ids)
        (previous if included else remaining).append(e)
    maths=[]
    for i,item in enumerate(crops):
        item=item if isinstance(item,dict) else {'rect':item}
        rect=fitz.Rect(item['rect']);filename=f'{page+1}-{name}-{i}.png'
        clean_math_image(source,page,rect,work/filename,pieces=item.get('pieces'),roman=item.get('roman','¯'))
        # TeX glyph boxes include substantial invisible ascender space.
        # Trim that space before centering a fraction/vector in Korean prose.
        image=Image.open(work/filename).convert('RGBA')
        mask=image.convert('RGB').convert('L').point(lambda v:255 if v<170 else 0)
        mask=ImageChops.multiply(mask,image.getchannel('A'));ink=mask.getbbox()
        if ink:
            box=(max(0,ink[0]-2),max(0,ink[1]-2),min(image.width,ink[2]+2),min(image.height,ink[3]+2))
            image=image.crop(box);image.save(work/filename)
        maths.append({'file':filename,'width':image.width/4,'height':image.height/4})
    entry=fit_math_leading({'id':f'{page+1}-{name}','page':page,'rect':bounds,'size':size,
       'source':' '.join(re.findall(r'\[\[\d+\]\]',korean)), 'ko':korean,'math':maths,
       'original_entry_ids':[i for e in previous for i in e.get('original_entry_ids',[e['id']])],
       'english_source':' '.join(e['source'] for e in previous)})
    remaining.append(entry);data['entries']=remaining


def repair_paragraphs(data,source,work):
    paragraph(data,source,work,0,10,11,'nuclear-decay',[83.62,493,512,524],
       [{'rect':[453.7,493.8,468.6,509.8],'roman':'P'},
        {'rect':[167.6,507.3,194.1,523.3],'roman':'D'},[294.8,493.7,308.8,507.2]],
       '(1) 문제에 따르면 어미 원자핵 [[0]]가 딸 원자핵 [[1]]로 바뀌는 [[2]] 붕괴는 다음과 같이 쓴다.')
    paragraph(data,source,work,2,52,56,'recoil-energy',[83.62,605,512,659],
       [{'rect':[357.7,604.9,383.8,620.6],'roman':'Po'},
        [304.6,617.9,325.0,647.4],[118.2,645.0,132,657.5]],
       '이 식의 물리적 의미는 명확하다. [[0]] 원자핵은 전자보다 훨씬 무거우므로 핵의 반동 운동 에너지 [[1]]는 전자의 운동 에너지에 비해 무시할 수 있다. 전자 운동 에너지는 [[2]]이다. 수치를 대입하면')
    paragraph(data,source,work,2,21,22,'daughter-nucleus',[83.62,378,512,396],
       [[309.9,378.2,324.0,391.7],{'rect':[202.1,378.2,229,394],'roman':'Po'}],
       '이 핵의 [[0]] 붕괴로 생긴 [[1]] 원자핵의 질량은')
    paragraph(data,source,work,4,1,1,'spin-equation',[242.5,76,512,104],
       [{'rect':[242.1,76,256,102.7],'roman':'¯'}],
       '[[0]] (이 가능성은 아직 배제되지 않는다)                         (30)')
    paragraph(data,source,work,4,2,7,'spin-summary',[83.62,106,512,179],
       [[83.3,122,97.3,135.5],{'rect':[403.6,116.3,417.5,143],'roman':'¯'},
        {'rect':[448.4,116.3,463,143],'roman':'¯'},
        {'rect':[190.8,151,233.9,178],'roman':'¯'},[461.9,158,472,171.1]],
       '종합하면, 양성자와 전자 외에 입자 하나가 더 생성되는 [[0]] 붕괴에서는 그 입자가 전기적으로 중성이며 스핀은 [[1]]이어야 한다. 스핀 [[2]]인 가능성은 아직 배제되지 않는다. 즉 전기적으로 중성인 페르미온이 존재해야 한다. [이것이 보통 중성미자라 부르는 입자이며, [[3]]이면 더 정확히는 전자 반중성미자 [[4]]이다.]')
    paragraph(data,source,work,11,44,54,'horizontal-polarizer',[83.62,431,512,535],
       [[143.3,455.5,157.9,471.3], [453.9,462.6,476.3,498.1], [436.1,490.7,458.5,526.5]],
       '(5) 수평 방향으로 투과하는 선형 편광판에는 (4)처럼 기저벡터에 작용시키는 방법을 쓴다. [[0]]를 P 편광(기저벡터 1, 수평 편광)에 작용시키면, 즉 P 편광이 수평 편광판을 지나면 여전히 P 편광 [[1]]을 얻는다. S 편광(기저벡터 2, 수직 편광)에 작용시키면 결과는 0, 즉 [[2]]이다. 따라서')
    entry=data['entries'].pop();maths=entry['math']
    method={**entry,'id':'12-horizontal-method','rect':[83.62,431,512,477],
       'source':'[[0]]','math':[maths[0]],
       'ko':'(5) 수평 투과 선형 편광판도 (4)처럼 기저벡터에 작용시킨다. [[0]]를 P 편광(기저벡터 1, 수평 편광)에 작용시키면, 수평 편광판을 지나도 P 편광이다.'}
    results={**entry,'id':'12-horizontal-results','rect':[83.62,478,512,535],
       'insert_rect':[83.62,478,512,530], 'source':'[[0]] [[1]]','math':maths[1:],
       'ko':'P 편광은 [[0]]으로 유지되고, S 편광(기저벡터 2, 수직 편광)은 0, 즉 [[1]]이 된다. 따라서'}
    data['entries'].extend([fit_math_leading(method),fit_math_leading(results)])
    paragraph(data,source,work,11,64,68,'diagonal-polarizer',[83.62,629,512,684],
       [[281,629,307.5,643], [472.7,635.6,488.1,671.5]],
       '[[0]] 방향으로 투과하는 선형 편광판에 진폭 1의 P 편광(수평 편광)이 입사하면, 진폭 [[1]]의 +45° 선형 편광이 된다. 정규화된 +45° 선형 편광 기저벡터를 P–S 기저에서 행렬로 나타내면')
    data['entries'][-1]['erase_rects']=[[83.3,682.2,91.6,694]]
    paragraph(data,source,work,8,7,8,'phase-increments',[83.62,459,512,527],
       [[393.1,459.5,402.6,472.3],[430.6,459.5,439.4,472.3],
        [468.0,473.0,480.8,485.7],[395.0,483.8,408.2,500.7],
        [415.1,483.8,428.3,500.7]],
       '(진폭은 같으므로 위상만 나타냈다.) [[0]], [[1]]는 각각 빔분할기의 반사·투과로 생기는 위상 증가량이고, [[2]]는 전반사 거울에서 반사될 때의 위상 증가량이다. [[3]], [[4]]는 각각 위쪽·아래쪽 경로를 거쳐 두 번째 빔분할기에서 위로 나아가 검출기 B로 들어가는 전기장이라 하자. 마찬가지로')
    paragraph(data,source,work,8,16,17,'constructive-fields',[83.62,647,512,677],
       [[172.8,647.1,186,664],[211.8,647.1,225,664],
        [459.4,647.1,472.6,664],[498.4,647.1,511.7,664]],
       '동시에 [[0]], [[1]]는 보강 간섭하므로, [[2]]와 [[3]]의 위상차는 0이어야 한다. (6)')
    paragraph(data,source,work,15,3,7,'phase-recovery',[83.62,271,512,380],
       [[235.4,271.3,260.3,283.1],[342.5,271.3,367.4,283.1],
        [133.5,310.0,150.4,326.5],[158.8,310.0,184.2,326.5],
        [145.9,352.5,164.3,364.4],[245.0,350.7,265,367.1],
        [285.4,350.7,305.5,367.1],[136.9,366.1,148.6,378.8]],
       '(7) 검출기 A는 cos[[0]], B는 sin[[1]]를 주므로 위상차를 유일하게 정할 수 있다. (*) 실제 실험에서는 a) [[2]], [[3]]를 기록하여 그림 S3c를 그리거나, 이들을 오실로스코프의 X, Y 입력에 연결하여 리사주 도형을 얻는다. (**) 또는 b) [[5]]와 [[6]]의 비로 tan[[4]]를 구한 뒤, [[7]]의 부호로 각도의 부호를 정한다. (***)')
    paragraph(data,source,work,15,10,14,'prefactor-note',[83.62,558.3,512,614],
       [[381.2,558.5,394.3,588], [84.4,579.5,98.0,609], [151.1,579.5,164.2,609]],
       'b 번역주: 원문에서 이 식과 (41), (42)의 앞 계수는 [[0]]이다. (34), (40)은 [[1]]을 준다. 일관된 계수는 [[2]]이다.',size=9)
    paragraph(data,source,work,17,7,9,'rod-principal-axes',[83.62,314,512,402],
       [[333.0,326.5,336.2,335.4],
        {'rect':[245.2,355.2,344.4,368.9],'roman':'cosin'},
        [350.4,355.2,381.8,368.9],
        {'rect':[388.4,355.2,487.6,368.9],'roman':'sincos'},
        {'rect':[336.0,365.5,455,392.3], 'pieces':[
         [336.0,372.8,455,392.3],[421.4,365.5,427.7,377.4]]},
        [462.0,372.9,509,386]],
       '풀이 1a: 총각운동량을 질량 중심의 원점 D[[0]]에 대한 각운동량과 강체의 질량 중심에 대한 각운동량으로 나눈다. 막대의 관성 주축은 [[1]], [[2]], [[3]]이다. 각 주축에 대한 관성 모멘트는 [[4]], [[5]]이다. 막대의 질량 중심에 대한 각운동량은')
    paragraph(data,source,work,17,3,5,'rotating-derivatives',[83.62,231.4,512,295],
       [[263.3,245.2,269.3,257],[115.1,245.2,122.3,257],
        [506.8,231.6,512.1,243.4],[402.7,231.6,410.3,243.4],
        {'rect':[208.8,267.1,257.4,294.1],'roman':'d'},
        {'rect':[285.0,267.1,325.8,294.1],'roman':'d'},
        {'rect':[352.8,267.1,387.7,294.1],'roman':'d'}],
       '첫 식은 함께 움직이는 기준계 [[0]]의 [[1]]축 단위벡터 [[2]]를 기준계 [[3]]의 성분으로 나타낸 것이다. 다른 두 식도 같은 뜻이다. 또한 [[4]], [[5]], [[6]]이다.')


def translate_short_conjunctions(data,source):
    for pi,page in enumerate(source):
        for block in page.get_text('dict')['blocks']:
            if block['type']!=0:continue
            for ln in block['lines']:
                for sp in ln['spans']:
                    if sp['text'].strip()!='or':continue
                    r=fitz.Rect(sp['bbox'])
                    if any(e['page']==pi and fitz.Rect(e['rect']).contains(r) for e in data['entries']):continue
                    rect=list(r);insert=[r.x0,r.y0,r.x0+24,r.y1+1];ko='또는';size=9.5
                    if pi==12:
                        # This conjunction is inside a matrix cell as '(or*)'.
                        rect=[349.6,510.0,374,524.1];insert=[349.6,511.8,380.6,525];ko='(또는*)';size=9
                    data['entries'].append({'id':f'{pi+1}-or-label','page':pi,'rect':rect,
                       'insert_rect':insert,'size':size,'source':'or','ko':ko,'math':[],'line_height':1.1})

def main():
    sourcepath=ROOT/'tmp/source-audit/CPhO_2024_TS.pdf'
    if not sourcepath.exists():
        sourcepath.parent.mkdir(parents=True,exist_ok=True)
        sourcepath.write_bytes(urllib.request.urlopen('https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-cpho/CPhO_2024_TS.pdf',timeout=60).read())
    source=fitz.open(sourcepath);work=ROOT/'tmp/cpho-build/2024-solution'
    layout.extract(sourcepath,work)
    path=work/'translation.json';data=json.loads(path.read_text(encoding='utf8'))
    ko=dict(line.split('|',1) for line in (ROOT/'tools/ko/cpho/2024/solution/korean.txt').read_text(encoding='utf8').splitlines() if '|' in line)
    missing=[e['id'] for e in data['entries'] if not ko.get(e['id'],'').strip()]
    if missing:raise ValueError('Missing source translations: '+str(missing))
    for e in data['entries']:
        e['ko']=ko[e['id']]
        expected=Counter(re.findall(r'\[\[(\d+)\]\]',e['source']))
        actual=Counter(re.findall(r'\[\[(\d+)\]\]',e['ko']))
        if expected!=actual:raise ValueError(f'Math tokens {e["id"]}: {expected} != {actual}')
    preserved=[e['id'] for e in data['entries'] if pure_mathematics(e['source'])]
    data['entries']=[e for e in data['entries'] if e['id'] not in preserved]
    data['preserved_original_formula_entries']=preserved
    coalesce(data)
    for e in data['entries']:
        repair_math(e,source,work)
        if e['rect'][2]-e['rect'][0]<180:
            e['insert_rect']=[e['rect'][0],e['rect'][1],min(527,e['rect'][0]+250),e['rect'][3]+1]
    repair_paragraphs(data,source,work)
    translate_short_conjunctions(data,source)
    data['outline_source']=True
    for e in data['entries']:
        e['redact_fill']=None
        r=fitz.Rect(e['rect']);e['redact_rect']=[r.x0-.7,r.y0-.7,r.x1+.7,r.y1+.9]
        if e['id']=='12-horizontal-polarizer':e['insert_rect']=[83.62,431,512,525]
        if e['id']=='1-7':e['ko']=e['ko'].replace('해설의 그림은 원문에서 발췌했다.','해설의 그림은 원문의 내용에 맞춰 선 도식으로 다시 그렸다.')
        if e['id']=='16-2':e['ko']='그림 S3c. 간섭항은 [[0]]로 표기한다.'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    target=ROOT/'pdfx/cpho';target.mkdir(parents=True,exist_ok=True)
    korean=target/'CPhO_2024_TS_KO.pdf'
    layout.build(work,korean)
    english=target/'CPhO_2024_TS_BAUPC_EN.pdf';shutil.copyfile(sourcepath,english)
    figures.replace(korean,'ko');figures.replace(english,'en')
    print('Preserved original formula entries:',len(preserved))

if __name__=='__main__':main()
