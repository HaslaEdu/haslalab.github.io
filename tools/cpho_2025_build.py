"""Build the reviewed CPhO 2025 Korean paper and bilingual vector diagrams.

python tools/cpho_2025_build.py

The source English translation remains attributed in tools/theory/cpho.json.
Its original PDF is fetched from this repository's existing archived release.
The published 2025 source contains no official solutions.
"""
from pathlib import Path
import json
import re
import shutil
import urllib.request
import pymupdf as fitz
import pdf_layout_translate as layout
import cpho_2025_figures as figures

ROOT = Path(__file__).resolve().parents[1]

def fit_math_leading(entry,cap=24):
    for image in entry['math']:
        if image['height']>cap:
            factor=cap/image['height'];image['height']*=factor;image['width']*=factor
    entry['line_height']=max(1.35,(max((m['height'] for m in entry['math']),default=0)+2)/entry['size'])
    return entry

def clean_math_image(source,page,rect,target,pieces=None,roman=''):
    """Render original mathematical glyph paths without neighbouring prose.

    Nominal TeX glyph boxes sometimes overlap the preceding/following line.
    Filtering glyph origins avoids including fragments of that prose in crops.
    """
    allowed=[];areas=[fitz.Rect(p) for p in (pieces or [list(rect)])]
    for b in source[page].get_text('rawdict')['blocks']:
        if b['type']!=0:continue
        for ln in b['lines']:
            for sp in ln['spans']:
                mathematical=sp['font'].startswith(('CM','LMMath')) or sp['size'] < 9
                for ch in sp['chars']:
                    point=fitz.Point(ch['origin'])
                    if (mathematical or ch['c'] in roman) and any(a.contains(point) for a in areas):
                        allowed.append((point.x,point.y))
    svg=source[page].get_svg_image(text_as_path=True)
    def keep(m):
        trans=re.search(r'transform="matrix\(([^)]+)\)"',m[0])
        if trans is None:return ''
        v=[float(x) for x in trans[1].split(',')]
        return m[0] if any(abs(v[-2]-x)<.02 and abs(v[-1]-y)<.02 for x,y in allowed) else ''
    svg=re.sub(r'<use\b[^>]*data-text=[^>]*?/?>',keep,svg)
    svg=re.sub(r'width="[^"]+"',f'width="{rect.width}"',svg,count=1)
    svg=re.sub(r'height="[^"]+"',f'height="{rect.height}"',svg,count=1)
    svg=re.sub(r'viewBox="[^"]+"',f'viewBox="{rect.x0} {rect.y0} {rect.width} {rect.height}"',svg,count=1)
    picture=fitz.open(stream=svg.encode(),filetype='svg')
    pdf=fitz.open(stream=picture.convert_to_pdf(),filetype='pdf')
    pdf[0].get_pixmap(matrix=fitz.Matrix(4,4)).save(target)
    return svg

def whole_paragraph(data, source, work, page, start, end, name, bounds, crops, korean, size=10.9):
    """Recompose overlapping source text objects using intact math fragments."""
    previous=[e for e in data['entries'] if e['page']==page and
              e['id'].split('-')[-1].isdigit() and start<=int(e['id'].split('-')[-1])<=end]
    ids={e['id'] for e in previous}
    data['entries']=[e for e in data['entries'] if e['id'] not in ids]
    maths=[]
    for i,item in enumerate(crops):
        rect=fitz.Rect(item['rect'] if isinstance(item,dict) else item)
        name_png=f'{page+1}-{name}-m{i}.png'
        clean_math_image(source,page,rect,work/name_png,
                         pieces=item.get('pieces') if isinstance(item,dict) else None,
                         roman=item.get('roman','') if isinstance(item,dict) else '')
        maths.append({'file':name_png,'width':rect.width,'height':rect.height})
    data['entries'].append(fit_math_leading({'id':f'{page+1}-{name}','page':page,'rect':bounds,'size':size,
        'source':' '.join(re.findall(r'\[\[\d+\]\]',korean)),
        'original_entry_ids':sorted(ids),'english_source':' '.join(e['source'] for e in previous),
        'math':maths,'ko':korean}))

def join_existing(data,page,start,end,name,bounds):
    previous=[e for e in data['entries'] if e['page']==page and
              e['id'].split('-')[-1].isdigit() and start<=int(e['id'].split('-')[-1])<=end]
    previous.sort(key=lambda e:int(e['id'].split('-')[-1]))
    ids={e['id'] for e in previous};maths=[];ko=[];src=[]
    for e in previous:
        offset=len(maths)
        convert=lambda m:f'[[{int(m[1])+offset}]]'
        ko.append(re.sub(r'\[\[(\d+)\]\]',convert,e['ko']))
        src.append(re.sub(r'\[\[(\d+)\]\]',convert,e['source']))
        maths.extend(e['math'])
    data['entries']=[e for e in data['entries'] if e['id'] not in ids]
    data['entries'].append(fit_math_leading({'id':f'{page+1}-{name}','page':page,'rect':bounds,
        'size':10.9,'source':' '.join(src),'math':maths,'ko':' '.join(ko),
        'original_entry_ids':sorted(ids)}))

def replace_math_fragments(data,source,work,key,indices,bounds):
    entry=next(e for e in data['entries'] if e['id']==key)
    rect=fitz.Rect(bounds);filename=key+'-whole-math.png'
    clean_math_image(source,entry['page'],rect,work/filename)
    number=len(entry['math'])
    entry['math'].append({'file':filename,'width':rect.width,'height':rect.height})
    pattern=r'\s*'.join(re.escape(f'[[{i}]]') for i in indices)
    for field in ('source','ko'):
        entry[field],count=re.subn(pattern,f'[[{number}]]',entry[field])
        if count!=1:raise ValueError(f'Math repair {key}/{field}: {count} matches')
    fit_math_leading(entry)

def main():
    source = ROOT / "tmp/source-audit/CPhO_2025_T_EN.pdf"
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        url = "https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-cpho/CPhO_2025_T_EN.pdf"
        source.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    work = ROOT / "tmp/cpho-build/2025"
    layout.extract(source, work)
    translations = ROOT / "tools/ko/cpho/2025/problem/korean.txt"
    ko = dict(line.split("|", 1) for line in translations.read_text(encoding="utf8").splitlines() if "|" in line)
    manifest = work / "translation.json"
    data = json.loads(manifest.read_text(encoding="utf8"))
    for e in data["entries"]:
        e["ko"] = "CPhO 제42회 (2025) - 결선 - 이론시험 문제                              한국어판" if e["id"].endswith("-0") else ko.get(e["id"], "")
        if e["id"] == "4-16":
            e["insert_rect"] = [e["rect"][0], e["rect"][1], 527, e["rect"][3]]
        if e["id"] == "9-42":
            e["ko"] = e["ko"].replace(" [[0]] [[1]] [[2]] [[3]] [[4]]", "")
            e["preserved_math"] = [0, 1, 2, 3, 4]
            e["rect"][3] = 620
        if e['id']=='4-5':
            e['rect'][3]=306.9
        if e['id']=='9-22':
            e['rect'][3]=422.5
            e['insert_rect']=[e['rect'][0],e['rect'][1],e['rect'][2],412.5]
    data["preserve_rects"] = [{"page": 8, "rect": [241, 621, 369, 695]}]
    # The source splits fractions across PDF text objects. Recompose this
    # paragraph with whole original formula crops, keeping the stated ratio
    # Delta n / n and the two characteristic frequencies unambiguous.
    source_doc = fitz.open(source)
    crops = [(233,424,268,452),(213,457,251,486),(300,457,318.5,486),
             (417,443.5,506,487),(510.5,465,527,479),(94,483,140,520),
             (164,498,177,512),(373,491,437,519),(94,525,136,538),
             (159,523,249,539),(359,517,377,546)]
    maths=[]
    for i, bounds in enumerate(crops):
        rect=fitz.Rect(bounds);name=f'9-clause3-m{i}.png'
        source_doc[8].get_pixmap(matrix=fitz.Matrix(4,4),clip=rect).save(work/name)
        maths.append({'file':name,'width':rect.width,'height':rect.height})
    data['entries']=[e for e in data['entries'] if not(e['page']==8 and e['id'].split('-')[1].isdigit() and 23<=int(e['id'].split('-')[1])<=40)]
    data['entries'].append(fit_math_leading({'id':'9-clause3','page':8,'rect':[94,414,528,548],
        'size':10.9,'source':' '.join(f'[[{i}]]' for i in range(len(maths))),
        'math':maths,'ko':'기울기 특성길이는 [[0]]이며, 계의 운동의 특성각진동수를 [[1]]로 둔다. 밀도차의 비 [[2]]를 [[3]], [[4]][[5]], [[6]]을 이용하여 근사적으로 나타내어라. 특성진동수 [[7]] 자기장 [[8]], 수밀도 [[9]]일 때 [[10]]의 값을 어림하여라.'},cap=32))

    whole_paragraph(data,source_doc,work,2,14,17,'phonon-edge',[91,496,528,569],
        [(421.5,510,427.4,522),(118.9,523.8,125.2,535.5),
         (369.1,523.8,376.6,535.5),(481.8,523.8,491.9,535.5),
         (317.6,539.1,327.7,550.8),(369.5,531.7,409.5,558.3),
         (454.9,539.1,526.8,551.8),(123.1,555.5,169.7,568.5)],
        '(4.3) 결정 속 기계적 파동의 전파 모드에 대응하는 준입자를 ‘포논’이라 한다. 1차원 포논 결정에서 포논의 에너지 [[0]]와 운동량 [[1]]은 드브로이 관계를 통해 각진동수 [[2]], 파수벡터 [[3]]과 연결된다. 파수벡터 [[4]]가 [[5]] 부근, 즉 [[6]] ([[7]])이면 포논 에너지는 다음과 같이 나타낼 수 있다.')

    whole_paragraph(data,source_doc,work,3,6,9,'helium-data',[68,307,528,401],
        [{'rect':[240.3,336,416,362.6],'roman':'kgmsd'}],
        '주어진 값: 표준 대기압 p₀ = 1.0 × 10⁵ Pa에서 액체 헬륨의 밀도는 ρ₀ = 125 kg/m³, 표면장력 계수는 σ = 3.7 × 10⁻⁴ N/m, 상대유전율은 εᵣ = 1.0556, 체적탄성률은 [[0]]이다. 여기서 V는 부피, p는 압력이다. 전자 질량은 mₑ = 9.11 × 10⁻³¹ kg, 진공 유전율은 ε₀ = 8.854 × 10⁻¹² F/m, 플랑크 상수는 h = 6.626 × 10⁻³⁴ m²kg/s, 기본 전하량은 e = 1.602 × 10⁻¹⁹ C, 헬륨 원자 질량은 M = 6.646 × 10⁻²⁷ kg이다.')

    whole_paragraph(data,source_doc,work,3,13,16,'helium-polarizability',[75.9,473.8,528,533],
        [(134.9,487.4,172.7,499.2),(212,487.4,219.8,499.2),
         {'rect':[242,495.3,315.4,522.9], 'pieces':[
             [242,502.4,279.6,515.9],[282.9,495.3,304.9,522.9],[307.6,502.7,315.4,514.5]]},
         (237.1,520.4,246.1,532.1)],
        '(2) 전기장 E에 의해 헬륨 원자가 분극되어 각 원자의 전기 쌍극자 모멘트는 [[0]]가 된다. [[1]]는 헬륨 원자의 분극률이며, 상대유전율과 근사 관계 [[2]]를 만족한다. 전자가 거리 [[3]]에 있는 원자 하나에 가하는 인력을 구하여라.')

    whole_paragraph(data,source_doc,work,3,23,26,'electron-pressure',[75.9,705.1,528,766],
        [(469.5,718.9,475.2,730.6),(317.5,729.7,328.7,756.2)],
        '(6) 불확정성 원리에 따라 전자는 끊임없이 움직이며 기포 벽과 계속 충돌하여 압력을 만든다. 반지름 [[0]]인 기포 안에서 전자의 평균 운동량 크기는 [[1]]이다. 전자가 기포 벽에 가하는 압력을 구하여라.')

    whole_paragraph(data,source_doc,work,4,3,5,'added-mass',[75.9,132.2,528,193],
        [(188.3,132.5,195.2,144.2),(376.3,132.5,384.9,145.3),
         (290.6,143.6,348.3,170.2)],
        '(8) 부피가 [[0]]인 구가 밀도 [[1]]인 액체 속에서 가속되면 주변 액체가 함께 움직인다. 이는 구의 질량이 [[2]]만큼 증가한 것과 같다. 액체 헬륨 속에서 가속되는 전자의 총유효질량과 전자 질량의 비를 구하여라.')

    whole_paragraph(data,source_doc,work,4,7,9,'lagrange-model',[68,232.7,528,360],
        [{'rect':[454.3,322.1,523,350.3], 'pieces':[
             [454.3,329.4,475.4,341.2],[480.7,322.1,523,350.3]]}],
        '라그랑주점은 우주과학에서 중요한 역할을 한다. 이 부근에서 탐사선은 적은 연료로 오랫동안 머물 수 있어 지속적인 천문관측을 위한 망원경과 우주정거장 배치에 적합하다. 세 천체 S₁, S₂, S₃의 질량을 각각 m₁, m₂, m₃라 하자. m₃는 m₁, m₂보다 매우 작아 S₃가 큰 천체 S₁, S₂에 미치는 영향은 무시한다. S₁과 S₂는 공통 질량중심 O 주위를 등속 원운동하며 두 천체 사이 거리는 R이다. 작은 천체 S₃가 공간의 특정 지점에 놓이면 S₁, S₂에 대해 정지할 수 있다. 이를 라그랑주점이라 한다. 중력상수는 G이고 [[0]], β = 1 − α로 둔다. (2), (3), (4)에서는 α ≪ 1을 가정한다.')

    whole_paragraph(data,source_doc,work,5,5,6,'deuteron-isotope',[75.9,192.2,528,220],
        [(193.6,193.9,200.8,205.6),{'rect':[404.2,192.2,445.3,208],'roman':'HD'}],
        '(3) 온도 [[0]]에서 중수소핵 [[1]]의 광분해와 그 역반응인 합성이 다음과 같은 동적 평형에 도달한다.')
    whole_paragraph(data,source_doc,work,5,8,10,'deuteron-ratio',[95,250.8,528,305],
        [(378.6,250.7,402.4,278.1),(443.3,258.1,455.2,270.8),
         (205.4,278,212,289.7),(113.1,291.5,130,304.1),
         (154.5,291.5,170,304.1)],
        '수밀도 비 [[0]]의 식을 구하여라. [[1]]는 입자 [[2]] (a = D, p, n)의 수밀도이다. 중수소핵의 질량과 결합에너지는 각각 [[3]], [[4]]이다.')
    whole_paragraph(data,source_doc,work,5,15,17,'helium-isotope',[75.9,534.3,528,601],
        [{'rect':[506.1,546.5,525.6,562.1],'roman':'He'}],
        '(5) 우주의 온도가 더 낮아지면 중성자와 양성자가 결합하기 시작하여 일련의 핵반응을 거쳐 최종적으로 안정한 헬륨핵 [[0]]를 만든다. 모든 중성자가 헬륨핵에 결합한다고 가정하고, 헬륨의 질량비, 즉 모든 원자핵의 질량 중 헬륨핵이 차지하는 비율을 어림하여라. 중성자 붕괴는 무시한다.')
    join_existing(data,8,19,20,'debye-values',[91.4,306.4,528,337])

    whole_paragraph(data,source_doc,work,9,1,4,'ion-sound-order',[75.9,66.7,528,132],
        [(177,72.4,192.2,85.8),(216,66.7,250.8,94.1),
         (361.9,74.1,372.8,86.6),(396.5,74.1,405.9,86.6),(432,91.6,488.3,105)],
        '(5) [[0]]와 [[1]]가 같은 차수([[2]]와 [[3]]가 같은 차수)일 때, (4)의 일반적 관계에서 간략화된 식 [[4]], 즉 분산관계를 유도하여라. 지배적인 항만 남긴다. 이 식이 아래의 고전적인 이온 음파 분산관계로 환원되는 조건을 구하여라.')
    data['preserve_rects'].append({'page':9,'rect':[93,131,211,159]})
    whole_paragraph(data,source_doc,work,9,8,12,'electron-order',[75.9,165.1,528,233],
        [(177,170.8,192.2,184.2),(216,165.1,250.8,192.5),
         (361.9,172.5,372.8,185),(396.5,172.5,405.9,185),
         (402.5,204.4,412.8,216.9),(119.8,216.3,135.8,231.5)],
        '(6) [[0]]와 [[1]]가 같은 차수([[2]]와 [[3]]가 같은 차수)일 때, (4)의 일반적 관계에서 어떤 간략화된 분산관계가 나오는가? 지배적인 항만 남긴다. 파동의 군속도 [[4]]의 식도 [[5]] 및 그 밖의 주어진 양으로 나타내어라.')
    whole_paragraph(data,source_doc,work,9,13,17,'quasineutral-order',[75.9,240.2,528,314],
        [(218.4,248.9,310.1,276.5),(94.9,274.1,135.6,286.6),(94.9,286,150,299.3)],
        '(7) 약결합 조건에서 전자가 볼츠만 분포를 따른다고 가정하자. (4)의 식 [[0]]을 준중성 조건 [[1]]으로 바꾸고 이온 방정식은 그대로 둔다. 이 경우 이온 음파의 분산관계 [[2]]를 유도하고, 이 결과가 (5)의 고전적인 이온 음파 분산관계로부터 어떻게 나오는지 설명하여라.')
    replace_math_fragments(data,source_doc,work,'1-16',[18,19,20],[347.8,528.8,398.5,545.6])
    replace_math_fragments(data,source_doc,work,'2-31',[0,1],[152.8,622.3,164.2,636.8])
    replace_math_fragments(data,source_doc,work,'2-33',[0,1],[239.5,703.5,259.4,718.9])
    replace_math_fragments(data,source_doc,work,'3-3',[0,1],[241.2,130.5,265.3,146])
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")
    target = ROOT / "pdfx/cpho"
    target.mkdir(parents=True, exist_ok=True)
    korean = target / "CPhO_2025_T_KO.pdf"
    english = target / "CPhO_2025_T_BAUPC_EN.pdf"
    layout.build(work, korean)
    # The first displayed dispersion relation touches a preceding source line.
    # Reuse only its original mathematical paths, keeping the formula vector.
    rect=fitz.Rect(93,131,211,159)
    svg=clean_math_image(source_doc,9,rect,work/'10-classical-dispersion.png')
    art=fitz.open(stream=svg.encode(),filetype='svg')
    vector=fitz.open(stream=art.convert_to_pdf(),filetype='pdf')
    checked=fitz.open(korean);checked[9].draw_rect(rect,color=None,fill=(1,1,1))
    checked[9].show_pdf_page(rect,vector,0)
    revised=korean.with_name(korean.stem+'.formula-fixed.pdf')
    checked.save(revised,garbage=4,deflate=True);checked.close();revised.replace(korean)
    shutil.copyfile(source, english)
    figures.replace(korean, "ko")
    figures.replace(english, "en")

if __name__ == "__main__":
    main()
