"""Build CPhO 2024 with reviewed Korean paragraphs and original formula crops.

The source PDF splits several fractions, nuclear isotope labels, and optical
intensity labels across overlapping text blocks. These paragraphs are composed
as a unit so that numerator/denominator and super/subscripts remain together.
"""
from pathlib import Path
import json
import re
import shutil
import urllib.request
import pymupdf as fitz
import pdf_layout_translate as layout
import cpho_2024_figures as figures

ROOT = Path(__file__).resolve().parents[1]

def paragraph(data, source, work, page, start, end, name, rect, crops, korean, size=10.9):
    previous = [e for e in data['entries'] if e['page']==page and
                e['id'].split('-')[-1].isdigit() and start<=int(e['id'].split('-')[-1])<=end]
    ids = {e['id'] for e in previous}
    data['entries'] = [e for e in data['entries'] if e['id'] not in ids]
    maths = []
    for i, bounds in enumerate(crops):
        clip = fitz.Rect(bounds)
        filename = f'{page+1}-{name}-m{i}.png'
        source[page].get_pixmap(matrix=fitz.Matrix(4,4),clip=clip).save(work/filename)
        maths.append({'file':filename,'width':clip.width,'height':clip.height})
    for image in maths:
        if image['height']>24:
            factor=24/image['height'];image['height']*=factor;image['width']*=factor
    leading=max(1.35,(max((m['height'] for m in maths),default=0)+2)/size)
    data['entries'].append({'id':f'{page+1}-{name}', 'page':page, 'rect':rect, 'size':size,
        'line_height':leading,
        'source':' '.join(re.findall(r'\[\[\d+\]\]', korean)),
        'original_entry_ids':sorted(ids),
        'english_source':' '.join(e['source'] for e in previous),
        'math':maths,'ko':korean})

def main():
    sourcepath = ROOT/'tmp/source-audit/CPhO_2024_T_EN.pdf'
    if not sourcepath.exists():
        sourcepath.parent.mkdir(parents=True,exist_ok=True)
        url='https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-cpho/CPhO_2024_T_EN.pdf'
        sourcepath.write_bytes(urllib.request.urlopen(url,timeout=60).read())
    source = fitz.open(sourcepath)
    work = ROOT/'tmp/cpho-build/2024'
    layout.extract(sourcepath, work)
    path = work/'translation.json'
    data = json.loads(path.read_text(encoding='utf8'))
    korean = dict(line.split('|',1) for line in (ROOT/'tools/ko/cpho/2024/problem/korean.txt').read_text(encoding='utf8').splitlines() if '|' in line)
    for entry in data['entries']:
        entry['ko'] = ('CPhO 제41회 (2024) - 결선 - 이론시험 문제                              한국어판'
                       if entry['id'].endswith('-0') else korean.get(entry['id'],''))
        entry['ko']=entry['ko'].replace('사분면 간섭계','직교위상 간섭계')
        if entry['id'] in {'4-4','6-12','10-9'}:
            entry['rect'][2] = 527.25
        if entry['id']=='6-12':
            entry['ko']='전파 도중의 광손실은 모두 무시한다.'
        if entry['id']=='9-8':
            entry['ko']='및 다음 적분 공식을 이용할 수 있다.'
            entry['preserved_math']=[0]
            entry['rect']=[68,262,528,276]
    data['preserve_rects']=[{'page':8,'rect':[250,264,342,304]}]

    paragraph(data, source, work, 0, 8, 9, 'nuclear-intro', [68,255,528,335],
        [(133.6,280.5,147.5,294),(260.7,294.2,285.1,310),
         (140.8,294.1,154.7,307.4),(440.4,294.2,464.8,310),
         (264.4,307.8,358.1,322.6)],
        '실험에 따르면 일부 원자핵은 전자를 방출하고 다른 종류의 원자핵으로 바뀌며, 방출 전자의 운동에너지는 연속 스펙트럼을 갖는다. 이를 원자핵의 [[0]]붕괴라 한다. 예를 들어 [[1]] 원자핵이 [[2]]붕괴하면서 방출하는 전자의 운동에너지 스펙트럼을 [[3]]의 정지계에서 측정하면 그림 1a와 같다. 전자의 정지질량은 [[4]]이다. 원자 내 전자의 결합에너지는 무시한다.')

    paragraph(data, source, work, 0, 14, 16, 'nuclear-masses', [68,673,528,744],
        [(190.5,673.2,215,689),(232.1,674.6,321.1,688.1),
         (87.2,686.7,216,701.5),(432.8,686.6,446.8,700),
         (495.6,688.4,527.4,701.7),(87.2,701.8,139.8,713.5),
         (360.4,700.1,374.3,713.5),(178.2,713.7,192.2,727),
         (419,713.7,433,727),(146.3,727.4,170.9,743)],
        '(2) 원자 [[0]]의 질량은 [[1]] amu이다. amu는 원자질량단위이며 [[2]]이다. [[3]]붕괴로 생성된 딸 원자의 질량은 [[4]][[5]] amu이다. 방출된 [[6]]전자 외에는 [[7]]붕괴에서 새로운 입자가 생성되지 않는다고 가정하자. 이때 [[8]]전자의 운동에너지를 MeV 단위로 구하여라. 처음에 [[9]] 원자는 정지해 있다고 가정한다.', size=10.5)

    paragraph(data, source, work, 1, 2, 6, 'half-spin', [68,103,528,248],
        [(336.1,103.5,350.1,116.8),(288.6,117.0,305.7,131.0),
         (145.9,169.8,159.6,196.8),(192.8,169.7,229.2,196.8),
         (237.6,177.6,244.5,189.3),(184,194.3,197.1,207.0),
         (428.2,194.2,443.2,207),(259,207.9,272.2,220.5),
         (505.4,207.9,520.4,220.5),(144.4,234.9,206.6,248.2)],
        '(4) 연구에 따르면 원자핵의 [[0]]붕괴를 이루는 기본 과정은 중성자 n 하나가 전자 [[1]], 양성자 p, 그리고 다른 입자 X로 바뀌는 것이다. 중성자·전자·양성자는 각각 스핀이라는 고유 각운동량을 갖는다. 이들의 스핀은 양자화되어 임의의 방향으로의 사영 크기가 [[2]]이다. 여기서 [[3]]이며 [[4]]는 플랑크 상수이다. 미시입자 1의 각운동량을 [[5]](임의의 방향으로의 최대 사영은 [[6]]), 미시입자 2의 각운동량을 [[7]](최대 사영은 [[8]])이라 하자. 두 입자의 총각운동량 [[9]]의 임의의 방향으로의 최대 사영이 가질 수 있는 값은 다음과 같다.')

    paragraph(data, source, work, 3, 22, 22, 'mirror-matrix', [68,631,528,646],
        [(453.9,631.3,465.3,645.8)],
        '(3) 그림 3c(a)는 전반사 거울의 개략도이다. 반사행렬 [[0]]을 써라.')
    paragraph(data, source, work, 3, 23, 25, 'quarter-wave', [68,656,528,700],
        [(190.9,664.7,197.9,691.3),(281.5,686.4,305.9,700),
         (385.4,688.3,392.6,700)],
        '(4) 사분파장판에서는 빠른축 방향으로 편광된 빛이 느린축 방향의 빛보다 통과 후 위상에서 [[0]]만큼 앞선다. 그림 3c(b)는 빠른축이 [[1]] 방향이며 [[2]]가 판에 수직인 사분파장판이다.')
    paragraph(data, source, work, 3, 26, 30, 'quarter-wave-matrix', [87,700,528,733],
        [(200.5,705.7,209.8,720.2),(449.7,699.9,523.2,731.8)],
        '이 판의 행렬 [[0]]를 쓰고 표준형 [[1]]로 나타내어라.')

    paragraph(data, source, work, 5, 2, 8, 'interference-labels', [68,124,528,234],
        [(98.5,137.8,111.7,150.5),(140.9,137.8,149.1,150.5),
         (156.2,137.8,164.4,150.5),(203.5,151.3,209.9,163),
         (260.1,163,276.6,179.3),(303.6,163,320.1,179.1),
         (282.6,205.5,298.9,217.2),(507.6,203.7,524.1,220),
         (146.3,217.2,162.8,233.5),(187.5,217.2,203.9,233.3),
         (262.8,217.2,286.5,230.8)],
        '(6) 레이저 빛이 빔분할기 1에 도달하기 직전의 진폭을 [[0]]라 하자. 빔분할기 1에서 2까지 광경로 1·2의 광학적 경로길이를 각각 [[1]], [[2]], 레이저 빛의 진공 파수벡터 크기를 [[3]]라 하자. 검출기 A·B에서의 광세기에 나타나는 간섭항 [[4]], [[5]]를 각각 써라. 간섭항은 두 빛이 함께 있을 때의 광세기에서 각 빛이 따로 있을 때의 광세기 합을 뺀 값이다. [[7]]의 결과에 나타나는 전체 위상을 [[6]]라 하고, [[8]], [[9]]를 [[10]]로 나타내어라.')
    paragraph(data, source, work, 5, 9, 10, 'phase-recovery', [68,239,528,256],
        [(274.9,241.4,291.3,253.2),(434,239.5,450.3,255.9),
         (474.5,239.5,491.3,255.9)],
        '(7) [[1]], [[2]]의 수치로부터 [[0]]를 구하는 방법을 간단히 설명하여라.',size=10.4)

    paragraph(data, source, work, 8, 13, 17, 'uncertainty', [68,339,528,467],
        [(363.4,339.7,419.5,366.6),(452.4,347.3,468.6,359.1),
         (493.6,347.3,509,359.1),(250.5,370.8,257.6,382.5),
         (373.1,370.8,379.3,382.5),(458.5,363.3,495.1,390),
         (207.7,387.4,214.6,399.1),(404.3,387.4,411.2,399.1),
         (509.2,387.4,515.8,399.1)],
        '양자역학의 불확정성 관계는 [[0]]이다. [[1]], [[2]]는 각각 입자의 변위 [[3]]와 운동량 [[4]]의 불확정도이며, [[5]]는 환산 플랑크 상수, [[6]]는 플랑크 상수이다. 조화진동자의 변위 [[7]]와 운동량 [[8]]는 동시에 0일 수 없으므로 바닥상태 에너지도 0일 수 없다. 같은 이유로 진공의 양자화된 전자기장의 최저에너지 상태, 즉 광자가 없는 상태도 에너지가 0일 수 없다. 따라서 흥미로운 현상이 생긴다. 진공에서 대전되지 않은 도체판 두 개를 일정한 거리로 평행하게 놓으면 둘 사이에 0이 아닌 전자기 상호작용력이 생긴다.')

    paragraph(data, source, work, 9, 2, 7, 'zero-point', [68,106,528,189],
        [(136.7,124.2,144.3,136),(160.3,116.9,180.8,143.5),
         (305.9,147.2,313.2,158.9),(378.4,139.8,399,166.4)],
        '(2) 양자효과에 따라 각진동수 [[0]]인 조화진동자의 바닥상태 에너지는 [[1]]이다. 마찬가지로 진공에서 각진동수 [[2]]인 모드 하나가 기여하는 진공 전자기장 에너지, 즉 영점에너지는 [[3]]이다. A와 C 사이의 총진공 전자기장 에너지를 나타내는 식을 써라. 힌트: 이 식은 발산하여 유한하지 않을 수 있다.')

    paragraph(data, source, work, 9, 10, 15, 'exponential-cutoff', [68,236,528,400],
        [(295.8,341.5,340.9,368.2),(376.5,348.9,384.8,360.6),
         (519.7,348.9,527.2,360.6),(150.1,364.8,188.6,391.4),
         (113.1,388.1,149.2,400),(155.1,388.1,191.3,400)],
        '(4) 자연계의 실제 힘의 크기는 언제나 유한하다. 앞의 결과가 발산하는 이유는 가정이 지나치게 단순하기 때문이다. 실제 도체판은 이상적인 도체가 아니므로 충분히 높은 진동수의 전자기파는 얇은 판을 통과하여 정상파 조건에 구속되지 않는다. 그러한 고진동수 모드는 판의 위치에 거의 영향을 받지 않아 계산하려는 전자기력에 기여하지 않는다. 이를 반영하기 위해 (1)의 정상파 조건은 유지하되, 각 모드가 총전자기장 에너지에 실제로 기여하는 양을 [[0]]로 둔다. [[1]]는 [[2]]와 같은 차원이며 [[3]]을 만족한다. [[4]], [[5]]인 극한에서 도체판 B에 작용하는 전자기력을 구하여라.')

    paragraph(data, source, work, 9, 19, 20, 'decay-condition', [95,502,528,530],
        [(124.4,509.4,159.3,521.4),(165.2,509.3,193.3,521.2),
         (318.4,502.2,325.4,528.8)],
        'B. [[0]]일 때 [[1]]는 [[2]]보다 빠르게 0으로 간다.')
    paragraph(data, source, work, 9, 21, 25, 'general-cutoff', [87,534,528,595],
        [(88.2,546.1,147.1,571.6),(87.1,568.4,125.4,580.3),
         (132.1,568.4,170.6,580.3),(129.8,582,151.8,593.9)],
        '각 전자기 모드가 총전자기장 에너지에 기여하는 양을 [[0]]로 둔다. [[1]], [[2]]인 극한에서 도체판 B에 작용하는 전자기력을 계산하고, 결과가 함수 [[3]]의 구체적인 형태에 의존하지 않음을 보여라.')

    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    target=ROOT/'pdfx/cpho';target.mkdir(parents=True,exist_ok=True)
    koreanpath=target/'CPhO_2024_T_KO.pdf'
    englishpath=target/'CPhO_2024_T_BAUPC_EN.pdf'
    layout.build(work,koreanpath)
    shutil.copyfile(sourcepath,englishpath)
    figures.replace(koreanpath,'ko');figures.replace(englishpath,'en')

if __name__=='__main__':
    main()
