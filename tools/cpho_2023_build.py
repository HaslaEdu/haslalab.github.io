"""Reviewed CPhO 2023 combined problem/solution booklet, bilingual editions."""
from pathlib import Path
from collections import Counter
import argparse,copy,hashlib,html,json,re
import pymupdf as fitz
import cpho_cjk_translate as cjk

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'tmp/cpho-build/2023'
MANUAL=ROOT/'tools/ko/cpho/2023/combined/manual.txt'


def join(data,ids,name,bounds=None):
    previous=[next(e for e in data['entries'] if e['id']==key) for key in ids]
    maths=[];parts={k:[] for k in ['source','ko','en']};rect=fitz.Rect(previous[0]['rect'])
    for e in previous:
        offset=len(maths);rect|=fitz.Rect(e['rect'])
        for key in parts:parts[key].append(re.sub(r'\[\[(\d+)\]\]',lambda m:f'[[{int(m[1])+offset}]]',e[key]))
        maths.extend(e['math'])
    entry={**previous[0],'id':name,'rect':list(fitz.Rect(bounds) if bounds else rect),
           'math':maths,'original_entry_ids':ids,'review_uncovered_math':[c for e in previous for c in e.get('review_uncovered_math',[])]}
    for key in parts:entry[key]=' '.join(parts[key])
    data['entries']=[e for e in data['entries'] if e['id'] not in ids];data['entries'].append(entry)
    return entry


def local_label(data,source,key,ko,en):
    """Keep a display equation in place, translating only its prose label."""
    e=next(e for e in data['entries'] if e['id']==key);old=fitz.Rect(e['rect'])
    chars=[c for c in cjk.characters(source[e['page']]) if cjk.natural(c) and cjk.HAN.search(c['c'])
           and old.contains(fitz.Point(c['origin']))]
    if not chars:raise ValueError('No local label '+key)
    r=fitz.Rect(chars[0]['bbox'])
    for ch in chars[1:]:r|=fitz.Rect(ch['bbox'])
    opening=[c for c in cjk.characters(source[e['page']])if c['c']in ['（','(']
             and r.x0-12<c['origin'][0]<r.x0 and abs(c['origin'][1]-chars[0]['origin'][1])<1.3]
    if opening:
        r|=fitz.Rect(opening[-1]['bbox']);ko='('+ko;en='('+en
    e.update({'original_rect':list(old),'rect':list(r),'insert_rect':[r.x0,r.y0-.5,r.x1+6,r.y1+2],
       'ko':ko,'en':en,'preserved_math':list(range(len(e['math']))),'line_height':1.18,
       'review_uncovered_math':[],'math_reviewed':True,
       'math_review_note':'All original displayed mathematics retained; only native Chinese label replaced.'})


def preserve_tail(data,source,key,indices):
    """Detach a displayed equation accidentally assigned to the preceding prose."""
    e=next(e for e in data['entries'] if e['id']==key)
    e['preserved_math']=indices
    for lang in ['ko','en']:
        for i in indices:e[lang]=e[lang].replace(f'[[{i}]]','')
    chars=[c for c in cjk.characters(source[e['page']]) if cjk.natural(c)
           and fitz.Rect(e['rect']).contains(fitz.Point(c['origin']))]
    r=fitz.Rect(chars[0]['bbox'])
    for c in chars[1:]:r|=fitz.Rect(c['bbox'])
    for i,m in enumerate(e['math']):
        if i not in indices:r|=fitz.Rect(m['source_rect'])
    e['rect']=list(r)
    e['review_uncovered_math']=[];e['math_reviewed']=True
    e['math_review_note']='Displayed equation retained at source coordinates; only preceding prose reflowed.'


LABELS={'红':'R','紫':'V','初':'i','末':'f'}


def labeled_math_svg(page):
    """Translate tiny native math indices consistently in inline source crops."""
    svg=page.get_svg_image(text_as_path=True);doc=fitz.open();p=doc.new_page(width=page.rect.width,height=page.rect.height)
    for c in cjk.characters(page):
        if c['c']in LABELS and c['size']<9:
            p.insert_text(fitz.Point(c['origin']),LABELS[c['c']],fontsize=c['size'],fontname='tiit')
    extra=p.get_svg_image(text_as_path=True).replace('font_','translated_label_font_')
    defs=re.search(r'<defs>([\s\S]*?)</defs>',extra)
    if defs:svg=svg.replace('</defs>',defs[1]+'</defs>',1)
    svg=re.sub(r'<use\b[^>]*data-text="([^"]*)"[^>]*?/?>',
               lambda m:'' if html.unescape(m[1])in LABELS else m[0],svg)
    uses=''.join(re.findall(r'<use\b[^>]*data-text=[^>]*?/?>',extra))
    doc.close();return svg.replace('</svg>',uses+'</svg>')


def replace_native_math_labels(path):
    """Replace untranslated six-point color/state indices in display equations."""
    original=fitz.open(path);doc=fitz.open(path);count=0
    for pi,page in enumerate(doc):
        chars=cjk.characters(original[pi]);selected=[c for c in chars if c['c']in LABELS and c['size']<9]
        stale=[c for c in chars if pi==29 and c['c']in '（）' and
               any(abs(c['origin'][0]-x)<.05 for x in [185.09,382.03])and abs(c['origin'][1]-198.5)<.05]
        if stale:
            # Word's ActualText for these surviving parentheses still names
            # the removed Chinese word next to each. Outline the same two
            # original parenthesis glyphs, keeping their exact appearance.
            for c in stale:page.add_redact_annot(fitz.Rect(c['bbox'])+(-.1,-.1,.1,.1),fill=None)
            page.apply_redactions(images=0,graphics=0)
            cjk.restore_math(page,original[pi],chars,set())
            cjk.restore_math(page,original[pi],[{**c,'font':'SymbolMT'}for c in stale],set())
        hidden=[c for c in chars if pi==1 and c['color']==16777215 and fitz.Rect(393,257,437,269).contains(fitz.Point(c['origin']))]
        if hidden:
            # The redrawn rainbow owns this white photographic annotation.
            # Remove its hidden text without masking the new vector drawing.
            page.add_redact_annot(fitz.Rect(393,257,437,269),fill=None)
            page.apply_redactions(images=0,graphics=0)
            cjk.restore_math(page,original[pi],chars,{c['index']for c in hidden})
        if not selected:continue
        for c in selected:page.add_redact_annot(fitz.Rect(c['bbox'])+(-.2,-.2,.2,.2),fill=(1,1,1))
        page.apply_redactions(images=0,graphics=0)
        cjk.restore_math(page,original[pi],chars,{c['index']for c in selected})
        for c in selected:page.insert_text(fitz.Point(c['origin']),LABELS[c['c']],fontsize=c['size'],fontname='tiit')
        count+=len(selected)
    temp=Path(str(path)+'.labels.pdf');doc.save(temp,garbage=4,deflate=True);doc.close();original.close();temp.replace(path)
    return count


def retain_tall_native_formulas(data,source):
    """Keep two tall inline formulas at full original size, translate labels."""
    specifications={
      '21-0':[(89,112,'이때','Here','这里'),(232,382,'따라서 아인슈타인 진동수는','The Einstein frequency is','由此可以得到爱因斯坦频率为')],
      '30-1':[(89,133,'【주:','【Note: from','【注：由'),(195,207,'곧','i.e.','即'),(392,405,'얻는다.','gives','得')]}
    for key,runs in specifications.items():
        e=next(e for e in data['entries']if e['id']==key);old=fitz.Rect(e['rect']);allchars=cjk.characters(source[e['page']]);new=[]
        for ri,(left,right,ko,en,src) in enumerate(runs):
            chars=[c for c in allchars if cjk.natural(c)and left<=c['origin'][0]<right and old.contains(fitz.Point(c['origin']))]
            if not chars:raise ValueError('Missing native label run '+key)
            r=fitz.Rect(chars[0]['bbox'])
            for c in chars[1:]:r|=fitz.Rect(c['bbox'])
            entry={**e,'id':key if ri==0 else key+f'-label-{ri}','source':src,
                   'ko':ko,'en':en,'rect':list(r),'insert_rect':[r.x0,r.y0-1,(506 if(key=='21-0'and ri==1)else r.x1+30 if(key=='30-1'and ri==2)else right),r.y1+3],
                   'line_height':1.18,'review_uncovered_math':[],'math_reviewed':True,
                   'math_review_note':'Tall formula retained at source size and coordinates; only separate Chinese label runs translated.'}
            if ri==0:
                entry['preserved_math']=list(range(len(e['math'])))
                entry['source']+=' '+''.join(f'[[{i}]]'for i in range(len(e['math'])))
            else:entry['math']=[];entry['preserved_math']=[]
            new.append(entry)
        data['entries']=[x for x in data['entries']if x['id']!=key]+new


def wrap_ab_question(data):
    """Match the source's full-width introduction and narrow figure-side text."""
    old=next(e for e in data['entries']if e['id']=='33-0')
    marker=old['source'].index('一根无限长')
    specs=[
      ('33-0',list(range(9)),old['source'][:marker],
       '([[0]]) 아하라노프[[1]]봄([[2]]) 효과 실험은 자기장이 0이어도 [[3]]이면 자기 효과가 생김을 보여, 벡터 퍼텐셜 [[4]]의 물리적 의미를 드러낸다. 자유 전자 이중 슬릿 간섭으로 [[5]] 효과를 확인한다. 좁은 슬릿과 스크린의 거리는 [[6]], 슬릿 간격은 [[7]]([[8]])이다.',
       '([[0]]) Experiments on the Aharonov[[1]]Bohm ([[2]]) effect show magnetic effects at zero field when [[3]], revealing the physical significance of [[4]]. A free-electron double-slit interference experiment verifies [[5]]. The narrow slits are [[6]] from the screen and separated by [[7]] ([[8]]).',
       [89.904,73.17,505.77,117.5],[89.904,73,505.77,118]),
      ('33-solenoid',list(range(9,17)),old['source'][marker:],
       '단위 길이당 감은 수 [[9]], 단면적 [[10]]인 무한히 긴 가는 직선 솔레노이드를 슬릿 뒤 두 경로 사이에 수직으로 둔다(그림 [[11]]). 전자 운동량 크기는 [[12]], 전하는 [[13]]([[14]])이다. 전류가 [[15]]에서 [[16]]로 변할 때 중앙 밝은 무늬의 이동 거리를 구하여라. 운동량',
       'A thin infinite straight solenoid of turn density [[9]] and area [[10]] is placed normally between the paths beyond the slits (Fig. [[11]]). Electrons have momentum magnitude [[12]] and charge [[13]] ([[14]]). Find the central bright fringe displacement when current changes from [[15]] to [[16]]. For momentum',
       [89.904,119.5,338.5,196.38],[89.904,119,334.35,200])]
    new=[]
    for key,indices,source,ko,en,rect,insert in specs:
        mapping={original:i for i,original in enumerate(indices)}
        def renumber(s):return re.sub(r'\[\[(\d+)\]\]',lambda m:f'[[{mapping[int(m[1])]}]]',s)
        e={**old,'id':key,'math':[old['math'][i]for i in indices],
           'source':renumber(source),'ko':renumber(ko),'en':renumber(en),
           'rect':rect,'insert_rect':insert,'original_entry_ids':['33-0']}
        new.append(e)
    data['entries']=[e for e in data['entries']if e['id']!='33-0']+new


def prepare():
    if not (BASE/'translation.json').is_file():
        cjk.extract(ROOT/'tmp/source-audit/CPhO_2023_T_ZH.pdf',BASE,regions=MANUAL.parent/'source_regions.json')
    data=json.loads((BASE/'translation.json').read_text(encoding='utf8'))
    manual={}
    for row in MANUAL.read_text(encoding='utf8').splitlines():
        if not row.strip():continue
        key,ko,en=row.split('|',2);manual[key]={'ko':ko,'en':en}
    for e in data['entries']:
        if re.match(r'^\[\[\d+\]\]）',e['source']):
            e['source']='（'+e['source'];e['rect'][0]=min(89.9,e['rect'][0])
        if e['id'] in manual:e.update(manual[e['id']])
        else:
            routine={
              '参考解答：':('참고 해설','Reference solutions'),
              '解得':('이를 풀면','Solving gives'),
              '即':('즉','That is,'),'所以':('따라서','Hence'),
              '因此':('따라서','Therefore'), '于是':('따라서','Thus'),
              '可得':('다음을 얻는다.','We obtain'),
              '角宽度':('각너비는','The angular width is'),
              '考虑到':('다음 관계를 고려하면','Using'),
              '得':('다음을 얻는다.','We obtain'),
              '其中':('여기서','where'),
              '【解法一】':('【풀이 1】','【Method 1】'),
              '【解法二】':('【풀이 2】','【Method 2】'),
              '【解法三】':('【풀이 3】','【Method 3】')}
            src=e['source'].strip()
            if src in routine:e['ko'],e['en']=routine[src]
            if re.fullmatch(r'第\[\[0\]\]页共\[\[1\]\]页',src):e['ko']='[[0]] / [[1]]쪽';e['en']='Page [[0]] of [[1]]';e['align']='center'
            if src in {'代入[[0]]式得','代入[[0]]式可得'}:e['ko']='식 [[0]]에 대입하면';e['en']='Substituting into Eq. [[0]] gives'
            if src in {'由[[0]]式可得','由[[0]]式得','利用[[0]]式可得'}:e['ko']='식 [[0]]으로부터';e['en']='Equation [[0]] gives'
            if src=='将[[0]]式代入得':e['ko']='식 [[0]]을 대입하면';e['en']='Substitution of Eq. [[0]] gives'
            if src.startswith('评分参考：本题'):
                e['ko']=src.replace('评分参考：本题','채점 기준: 총').replace(' 分。','점.')
                e['en']=src.replace('评分参考：本题','Marking guide:').replace(' 分。',' points total.')
            if (src.startswith(('第（','【解法')) and '分' in src and '式' in src):
                for lang in ['ko','en']:
                    s=src
                    replacements=({'第（':'(', '）问':')','【解法一】':'【풀이 1】','【解法二】':'【풀이 2】','【解法三】':'【풀이 3】','【解法四】':'【풀이 4】','【解法五】':'【풀이 5】','式各':'각 식 ', '式':'식 ', ' 分':'점','各':'각각 '} if lang=='ko' else {'第（':'(', '）问':')','【解法一】':'【Method 1】','【解法二】':'【Method 2】','【解法三】':'【Method 3】','【解法四】':'【Method 4】','【解法五】':'【Method 5】','式各':' (each)', '式':'', ' 分':' points','各':' each'})
                    for old,new in replacements.items():s=s.replace(old,new)
                    e[lang]=s.replace('；',';').replace('，',',').replace('。','.').replace('、',',')
        if e['id']=='10-3' and len(e['math'])==2:
            for lang in ['ko','en']:e[lang]=e[lang].replace('+','[[1]]').replace('＋','[[1]]')
        for lang in ['ko','en']:
            if e[lang] and Counter(re.findall(r'\[\[\d+\]\]',e['source']))!=Counter(re.findall(r'\[\[\d+\]\]',e[lang])):
                raise ValueError(f'Math placeholders {e["id"]}/{lang}')
    next(e for e in data['entries'] if e['id']=='27-10')['en']='.'
    next(e for e in data['entries'] if e['id']=='34-6').update(ko='따라서',en='Hence')
    join(data,['1-9','1-10','1-11'],'1-dispersion')
    join(data,['1-12','1-13'],'1-rainbow-width')
    join(data,['2-0','2-1','2-2'],'2-polarization')
    source=cjk.resolve_source(data)
    data['source_filename']=source.name;data['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    if data['source_sha256']!='956f132218ce6591d418a1faa998648b00a6195b2f2b522e6e16c1a405a418f0':raise ValueError('CPhO2023 source changed')
    original=fitz.open(source)
    e=next(e for e in data['entries']if e['id']=='10-3')
    if len(e['math'])==1:
        selected=[c for c in cjk.characters(original[9])if c['c']=='＋']
        if len(selected)!=1:raise ValueError('Expected one native fullwidth plus')
        cluster={'chars':selected,'rect':selected[0]['bbox'],'y':selected[0]['origin'][1],'text':'＋'}
        e['math'].append(cjk.math_image(original[9].get_svg_image(text_as_path=True),cluster,BASE/'10-3-plus-m1.png'))
        e['source']=e['source'].replace('＋','[[1]]')
        for lang in ['ko','en']:e[lang]=e[lang].replace('+','[[1]]').replace('＋','[[1]]')
    for e in data['entries']:
        for mi,m in enumerate(e['math']):
            if not any(c in LABELS for c in m['source_text']):continue
            selected=[c for c in cjk.characters(original[e['page']])if c['index']in m['source_char_indices']]
            r=fitz.Rect(selected[0]['bbox'])
            for c in selected[1:]:r|=fitz.Rect(c['bbox'])
            cluster={'chars':selected,'rect':list(r),'y':e['source_row_baselines'][0],'text':m['source_text']}
            e['math'][mi]=cjk.math_image(labeled_math_svg(original[e['page']]),cluster,BASE/(e['id']+f'-labels-m{mi}.png'))
            e['math'][mi]['label_replacements']=LABELS
    # These fields contain no fraction rule or radical: nearby graphic rules
    # must not inflate their visible bounds or enter the translated line.
    for key,mi in [('4-1',2),('5-4',3),('22-2',0),('27-8',6)]:
        e=next(e for e in data['entries']if e['id']==key);m=e['math'][mi]
        selected=[c for c in cjk.characters(original[e['page']])if c['index']in m['source_char_indices']]
        svg=original[e['page']].get_svg_image(text_as_path=True)
        end=svg.index('</defs>')+7
        svg=svg[:end]+re.sub(r'<path\b[^>]*?/?>','',svg[end:])
        r=fitz.Rect(selected[0]['bbox'])
        for c in selected[1:]:r|=fitz.Rect(c['bbox'])
        cluster={'chars':selected,'rect':list(r),'y':e['source_row_baselines'][0],'text':m['source_text']}
        e['math'][mi]=cjk.math_image(svg,cluster,BASE/(key+f'-reviewed-m{mi}.png'))
    join(data,['5-1','5-2'],'5-frame')
    join(data,['5-4','5-5','5-6'],'5-fast-slow')
    join(data,['5-17','5-18'],'5-time-average')
    join(data,['9-5','9-6'],'9-first-barrier')
    join(data,['9-8','9-9'],'9-second-barrier')
    join(data,['10-10','10-11'],'10-equilibrium-marking')
    local_label(data,original,'6-2','미정','unknown')
    next(e for e in data['entries']if e['id']=='6-2')['insert_rect']=[342,194.5,375.5,207.7]
    local_label(data,original,'6-10','조건:','using')
    local_label(data,original,'7-6','조건:','using')
    local_label(data,original,'8-5','조건:','if')
    local_label(data,original,'16-10','또는','or')
    local_label(data,original,'25-2','따라서','Hence')
    local_label(data,original,'33-11','임의의 상수','constant')
    for key in ['34-7','34-8','34-13','34-14','34-16','34-17']:
        local_label(data,original,key,'조건:','if')
    for key,indices in [('13-11',[2]),('14-12',[1,2]),('24-14',[2]),('28-5',[0,2]),('28-6',[2]),('29-10',[2]),('33-13',[0]),('34-4',[1]),('36-2',[1])]:
        preserve_tail(data,original,key,indices)
    e=next(e for e in data['entries']if e['id']=='34-4')
    e.update(ko='[[0]]는 전하에서 면요소의 점으로 향하는 벡터이다.',en='Here [[0]] points from the charge to the area element;',insert_rect=[90,255.5,331.5,272])
    e=next(e for e in data['entries'] if e['id']=='13-11')
    e.update(ko='식 [[0]]의 산란각 [[1]]:',en='Eq. [[0]] gives [[1]]:',insert_rect=[90,677,236,693])
    e=next(e for e in data['entries'] if e['id']=='28-5')
    e.update(ko='일정 전기장 [[1]]에서 전자의 운동 방정식은',en='In constant field [[1]], the electron equation of motion is',rect=[111,292,262.5,303],insert_rect=[111,292,506,305])
    e=next(e for e in data['entries'] if e['id']=='29-10')
    e.update(ko='【주: 전도도 [[0]], 유전율 [[1]]의 관계:',en='【Note: [[0]] and [[1]] obey',insert_rect=[90,506.5,316.5,522])
    # Keep three external native captions centered under their own panels.
    e=next(e for e in data['entries']if e['id']=='11-1');parts=[]
    for i,m in enumerate(e['math']):
        r=fitz.Rect(m['source_rect']);x=(r.x0+r.x1)/2-6
        parts.append({**e,'id':f'11-caption-{i}','source':'图[[0]]','ko':'그림 [[0]]','en':'Fig. [[0]]','math':[m],
                      'rect':[r.x0-12,r.y0-1,r.x1+1,r.y1+1],'insert_rect':[x-40,r.y0-1,x+40,r.y1+3],'align':'center'})
    data['entries']=[e for e in data['entries']if e['id']!='11-1']+parts
    e=next(e for e in data['entries']if e['id']=='3-8')
    e['ko']=e['ko'].replace('적색','R(적색)').replace('보라색','V(보라색)')
    e['en']=e['en'].replace('red','red (R)').replace('violet','violet (V)')
    # Word stores these two inline h-bars as soft-masked images, without PDF text.
    # Preserve the actual source ink rather than silently losing the symbols.
    for key,pi,rect in [('23-3',22,[110.6,272.9,119.1,284.4]),('33-3',32,[100.3,191.8,109.3,205.0])]:
        e=next(e for e in data['entries']if e['id']==key);r=fitz.Rect(rect)
        if key=='33-3':
            chars=[c for c in cjk.characters(original[pi])if cjk.natural(c)and fitz.Rect(e['rect']).contains(fitz.Point(c['origin']))]
            # The symbol lies between 中 and 为, so infer its gap from source.
            left=next(c for c in chars if c['c']=='中');right=next(c for c in chars if c['c']=='为')
            r=fitz.Rect(left['bbox'][2],left['origin'][1]-10,right['origin'][0],left['origin'][1]+2)
        file=BASE/(key+'-hbar.png');original[pi].get_pixmap(matrix=fitz.Matrix(4,4),clip=r,alpha=False).save(file)
        index=len(e['math']);e['math'].append({'file':file.name,'width':r.width,'height':r.height,'source_rect':list(r),'source_text':'hbar (native source ink)','source_char_indices':[],'glyph_origins':[]})
        e['source']+=' [['+str(index)+']]'
        if key=='23-3':
            e['ko']=e['ko'].replace('줄인 플랑크 상수','줄인 플랑크 상수 [['+str(index)+']]')
            e['en']=e['en'].replace('reduced Planck constant','reduced Planck constant [['+str(index)+']]')
        else:
            e['ko']='[['+str(index)+']]는 줄인 플랑크 상수이다.';e['en']='[['+str(index)+']] is the reduced Planck constant.'
    # The label of Eq.16 is a separate source object, not part of the paragraph.
    e=next(e for e in data['entries'] if e['id']=='16-4');e['math_reviewed']=True
    e['math_review_note']='Only uncovered glyph is the source equation number 16, retained at its original coordinates.'
    e['insert_rect']=[90,284.2,416,330]
    # One inline field was joined to the beginning of the following display.
    e=next(e for e in data['entries'] if e['id']=='35-6');m=e['math'][0]
    selected=[c for c in cjk.characters(original[34]) if c['index'] in m['source_char_indices'] and c['origin'][1]<350]
    r=fitz.Rect(selected[0]['bbox'])
    for c in selected[1:]:r|=fitz.Rect(c['bbox'])
    cluster={'chars':selected,'rect':list(r),'y':341.45,'text':''.join(c['c']for c in selected)}
    e['math'][0]=cjk.math_image(original[34].get_svg_image(text_as_path=True),cluster,BASE/'35-6-reviewed-m0.png')
    preserve_tail(data,original,'35-6',[])
    join(data,['27-9','27-10'],'27-permittivity')
    e=next(e for e in data['entries']if e['id']=='27-permittivity')
    e['ko']='[[0]]을 [[1]], [[2]], [[3]]으로 나타내어라.'
    e['en']='Find [[0]] in terms of [[1]], [[2]] and [[3]].'
    e=next(e for e in data['entries']if e['id']=='1-dispersion')
    e['en']='([[0]]) Dispersion makes water\'s index [[1]] wavelength-dependent. At incidence [[2]], derive [[6]] for order-[[3]] deviation [[4]] versus index [[5]], as a function of [[7]]. Give explicit [[11]] at [[8]]=[[10]] from part ([[9]]).'
    retain_tall_native_formulas(data,original)
    # Root's redrawn figures include these three native captions.
    data['entries']=[e for e in data['entries'] if e['id'] not in ['2-5','32-10','32-17']]
    e=next(e for e in data['entries'] if e['id']=='32-1')
    e['ko']=e['ko'].replace('; 그림 [[4]]','').replace(' (그림 [[4]])','').replace('; 그림 [[4]]','')
    e['en']=e['en'].replace('; Fig. [[4]]','')
    # Caption token appears inside the wide native paragraph bounding box.
    e['ko']=e['ko'].replace('그림 [[4]]','');e['en']=e['en'].replace('Fig. [[4]]','')
    e['preserved_math']=[4]
    # A short frame label has only one original line of vertical space.
    e=next(e for e in data['entries'] if e['id']=='5-11')
    e['en']='([[0]]) In the frame translating with pivot [[1]], the inertial force (upward positive) is'
    e['line_height']=1.15
    e=next(e for e in data['entries']if e['id']=='32-1')
    e['insert_rect']=[89.904,135.7,355.45,260]
    e['ko']='[[0]]는 진공 투자율, [[1]]은 자기 전하에서 장점으로 향하는 위치 벡터이다. 통상 전자기학은 자기 홀극이 없다고 보며 아직 실험에서도 발견되지 않았다. [[2]]년 디랙은 무수한 자기 전하 쌍극자를 머리와 꼬리가 이어지게 배열하여, 한 끝점에서 무한대까지 뻗는 디랙 끈을 제안했다(그림 [[3]] 왼쪽). 각 쌍극자를 작은 전류 고리로 바꾸면 단면이 일정하고 균일하게 조밀히 감은 매우 가는 반무한 솔레노이드와 같다(그림 [[5]] 오른쪽). 이 등가는'
    e['en']='Here [[0]] is vacuum permeability and [[1]] points from the magnetic charge to the field point. Ordinary electromagnetism excludes monopoles, which have not been observed experimentally. In [[2]], Dirac proposed a string of infinitely many head-to-tail magnetic-charge dipoles, extending from one endpoint to infinity (Fig. [[3]], left). Replacing each dipole by a small current loop gives a very thin, uniformly wound semi-infinite solenoid of constant cross section (Fig. [[5]], right). This equivalence means'
    wrap_ab_question(data)
    from cpho_native_math_accents import restore
    restore(data,original,BASE)
    for e in data['entries']:
        if e['id']=='1-0':e['insert_rect']=[90,73.9,506,94];e['align']='center'
        if e['id']=='1-1':e['align']='center'
        if e['id']=='1-3':e['insert_rect']=[327,241,505,257];e['align']='center'
        if e['id']=='1-5':e['insert_rect']=[90,428,506,457]
        if e['id']=='2-5':e['insert_rect']=[385,254,503,275]
        if e['id']=='3-9':e['insert_rect']=[187,601,410,615];e['align']='center'
        if e['id']=='3-13':e['insert_rect']=[90,721,331,735];e['align']='center'
        if re.fullmatch(r'(?:解题图|题解图|图)\[\[\d+\]\]',e['source']):
            r=fitz.Rect(e['rect']);cx=(r.x0+r.x1)/2;e['insert_rect']=[cx-38,r.y0-1,cx+38,r.y1+2];e['align']='center'
        if e['id'].endswith('-14') and e['page']==0:e['align']='center'
        if e['id']=='2-17':e['align']='center'
        if 'insert_rect' not in e and e['rect'][0]<140 and e['rect'][2]-e['rect'][0]<320 and not e['source'].startswith(('图','解题图','题解图')):
            r=fitz.Rect(e['rect']);right=506
            for image in original[e['page']].get_image_info():
                box=fitz.Rect(image['bbox'])
                if image['width']>50 and image['height']>50 and box.x0>r.x0 and box.y0<r.y1 and box.y1>r.y0:right=min(right,box.x0-6)
            for omitted in data.get('source_exclusions',[]):
                box=fitz.Rect(omitted['rect'])
                if omitted['page']==e['page']+1 and box.x0>r.x0 and box.y0<r.y1 and box.y1>r.y0:right=min(right,box.x0-1)
            e['insert_rect']=[r.x0,r.y0,max(r.x1,right),r.y1+1]
        # MuPDF centers inline images on the text baseline but omits their
        # lower overhang from Story's reported line height. Lift the first
        # baseline into the original mathematical bounding area and retain
        # the source bottom edge, giving the complete fraction room to draw.
        heights=[min(m['height'],e.get('math_cap',26))for i,m in enumerate(e['math'])if i not in e.get('preserved_math',[])]
        if heights:
            lift=max(0,(max(heights)-e['size'])/2)+.5
            ir=list(e.get('insert_rect',e['rect']));ir[1]-=lift;e['insert_rect']=ir
            e['math_baseline_lift']=lift
        if e['id']in ['5-time-average','36-13']:
            e['insert_rect'][1]-=3.5
        r=fitz.Rect(e['rect']);e['erase_rects']=[[r.x0-.7,r.y0-.7,r.x1+.7,r.y1+.8]]
        # Some native radical/fraction rules extend beyond Word's glyph
        # metrics. Mask the source math's actual ink too, leaving no rule
        # fragments after that field is moved into translated prose.
        for i,m in enumerate(e['math']):
            if i not in e.get('preserved_math',[]) and not r.contains(fitz.Rect(m['source_rect'])):
                e['erase_rects'].append(list(fitz.Rect(m['source_rect'])+(-.35,-.35,.35,.35)))
    folder=ROOT/'tmp/cpho-build/2023-reviewed';folder.mkdir(parents=True,exist_ok=True)
    # The base folder contains all reproducible source glyph sprites.
    data['asset_roots']=[str(BASE.resolve())]
    for e in data['entries']:
        for m in e['math']:
            m['file']=Path(m['file']).name
    (folder/'translation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    return folder


def main():
    p=argparse.ArgumentParser();p.add_argument('--pages',nargs='*',type=int);p.add_argument('--lang',choices=['ko','en']);p.add_argument('--prepared',action='store_true');args=p.parse_args()
    folder=ROOT/'tmp/cpho-build/2023-reviewed' if args.prepared else prepare()
    target=ROOT/('tmp/cpho-build/2023-preview' if args.pages else 'pdfx/cpho');target.mkdir(parents=True,exist_ok=True)
    for lang in ([args.lang] if args.lang else ['ko','en']):
        path=target/('CPhO_2023_Combined_'+lang.upper()+'.pdf')
        manifest_sha256=hashlib.sha256((folder/'translation.json').read_bytes()).hexdigest()
        cjk.build(folder,path,lang,args.pages)
        if not args.pages:
            from cpho_2023_figures import replace
            replace(path,lang)
            print('Translated native math labels:',replace_native_math_labels(path),flush=True)
        path.with_suffix('.build.json').write_text(json.dumps({'manifest_sha256':manifest_sha256,'source_sha256':'956f132218ce6591d418a1faa998648b00a6195b2f2b522e6e16c1a405a418f0','pages':args.pages or list(range(1,37))},indent=2),encoding='utf8')


if __name__=='__main__':main()
