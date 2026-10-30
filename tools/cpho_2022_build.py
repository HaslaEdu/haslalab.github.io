"""Bilingual CPhO 2022 problems with original mathematical glyphs and six vectors."""
from pathlib import Path
from collections import Counter
import argparse,json,re,copy,hashlib,shutil
import pymupdf as fitz
from PIL import Image,ImageChops
import cpho_cjk_translate as cjk
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'tools/ko/cpho/2022/problems'

def extract():
    # This booklet's 13.6-point prose rows need a shorter initial math link
    # distance, otherwise subsection numbers 1,2,3 form one vertical sprite.
    original=cjk.math_clusters
    def local(chars,vertical_limit=15.6,horizontal_limit=3.4):
        return original(chars,vertical_limit=9 if vertical_limit==14 else vertical_limit,horizontal_limit=horizontal_limit)
    cjk.math_clusters=local
    try:data=cjk.extract(ROOT/'tmp/source-audit/CPhO_2022_T_ZH.pdf',FOLDER,regions=FOLDER.parent/'regions.json',math_right=575)
    finally:cjk.math_clusters=original
    data['math_local_vertical_limit']=9
    (FOLDER/'raw-translation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

def snapshot(page,rect,target):
    rect=fitz.Rect(rect);pix=page.get_pixmap(matrix=fitz.Matrix(6,6),clip=rect,alpha=True)
    im=Image.frombytes('RGBA',[pix.width,pix.height],pix.samples)
    dark=im.convert('RGB').convert('L').point(lambda x:255 if x<170 else 0)
    mask=ImageChops.multiply(dark,im.getchannel('A'));ink=mask.getbbox()
    if not ink:raise ValueError('Empty original math snapshot')
    box=(max(0,ink[0]-3),max(0,ink[1]-3),min(im.width,ink[2]+3),min(im.height,ink[3]+3))
    im=im.crop(box);im.save(target)
    actual=fitz.Rect(rect.x0+box[0]/6,rect.y0+box[1]/6,rect.x0+box[2]/6,rect.y0+box[3]/6)
    return {'file':target.name,'width':im.width/6,'height':im.height/6,'source_rect':list(actual),
            'source_text':'ℏ','source_kind':'original_vector_snapshot','glyph_origins':[],'source_char_indices':[]}

def prepare():
    raw=FOLDER/'raw-translation.json'
    if not raw.exists():extract()
    data=json.loads(raw.read_text(encoding='utf8'));source=cjk.resolve_source(data);doc=fitz.open(source)
    by_id={e['id']:e for e in data['entries']}
    by_id['1-0']['insert_rect']=[36,by_id['1-0']['rect'][1]-1,560,by_id['1-0']['rect'][3]+4]
    by_id['1-0']['align']='center'
    # Keep the four Carnot processes on their four original rows.
    old=by_id['4-16'];rows=[];chars=cjk.characters(doc[3])
    for label,indices,source in [
        ('I',range(0,4),'过程[[0]]等温膨胀：温度为[[1]]，体积由[[2]]变为[[3]]'),
        ('II',range(4,9),'过程[[0]]绝热降温：温度由[[1]]降为[[2]]，体积由[[3]]变为[[4]]'),
        ('III',range(9,13),'过程[[0]]等温压缩：温度为[[1]]，体积由[[2]]变为[[3]]'),
        ('IV',range(13,18),'过程[[0]]绝热升温：温度由[[1]]升为[[2]]，体积由[[3]]变为[[4]]')]:
        baseline=old['source_row_baselines'][len(rows)];entry=copy.deepcopy(old)
        parts=[old['math'][i] for i in indices]
        natural=[c for c in chars if abs(c['origin'][1]-baseline)<1.3 and old['rect'][0]-.1<=c['origin'][0]<=old['rect'][2]+.1]
        rect=fitz.Rect(natural[0]['bbox'])
        for c in natural[1:]:rect|=fitz.Rect(c['bbox'])
        for m in parts:rect|=fitz.Rect(m['source_rect'])
        entry.update(id='4-16-'+label,rect=list(rect),source=source,math=parts,source_row_baselines=[baseline],insert_rect=[99.744,rect.y0,565,rect.y1])
        rows.append(entry)
    data['entries']=[e for e in data['entries'] if e['id']!='4-16']+rows
    # Extracted text visits the superscript 2 first; the original ink is a << pv².
    by_id['4-19']['math'][1]['source_text']='a ≪ p v²'
    by_id['4-11']['math_cap']=20
    by_id['4-11']['line_height']=2.1
    for key in ['3-4','4-10','4-18']:
        entry=by_id[key];entry['insert_rect']=[entry['rect'][0],entry['rect'][1],565,entry['rect'][3]]
    old=by_id['1-5'];a=copy.deepcopy(old);b=copy.deepcopy(old)
    a.update(id='1-5-a',rect=[36,222.57,400.9,250.6],math=old['math'][:1],source='（[[0]]）细杆静止在上述平衡位置。现有一只小白鼠，从静止开始由杆底端沿杆往上爬。在爬杆的过程中，细杆始终保持静止；假设小白鼠可视为质点，且小白鼠',source_row_baselines=old['source_row_baselines'][:2])
    b.update(id='1-5-b',rect=[36,250.7,559.66,276.46],math=old['math'][1:],source='在杆端不接触金属丝。求小白鼠在时刻[[0]]（以小白鼠开始爬杆的时刻为时刻零点）沿细杆的位移[[1]]，小白鼠是否可以爬到细杆顶端？如果可以，小白鼠爬到细杆顶端，最少用时多少？',source_row_baselines=old['source_row_baselines'][2:])
    data['entries']=[e for e in data['entries'] if e['id']!='1-5']+[a,b]
    # The charge constant is a separate Word equation object with no matching
    # native block owner. Include its complete original equation explicitly.
    entry=by_id['3-0'];positions={tuple(c['origin']) for c in entry['review_uncovered_math']}
    chars=[c for c in cjk.characters(doc[2]) if tuple(c['origin']) in positions]
    bounds=fitz.Rect(chars[0]['bbox'])
    for c in chars[1:]:bounds|=fitz.Rect(c['bbox'])
    cluster={'chars':chars,'rect':list(bounds),'y':81.62568664550781,'text':'e = 1.60 × 10^−19 C'}
    entry['math'].append(cjk.math_image(doc[2].get_svg_image(text_as_path=True),cluster,FOLDER/'3-0-elementary-charge.png'))
    entry['source']+='[[6]]';entry['review_uncovered_math']=[];entry['math_reviewed']=True
    # Word draws this solitary h-bar as paths; no PDF character is extractable.
    entry=by_id['4-0'];entry['math'].append(snapshot(doc[3],[58.2,35.5,65.9,49.8],FOLDER/'4-0-hbar.png'))
    entry['source']='其中[[0]]为约化普朗克常量。'
    entry['insert_rect']=[36,34.5,350,50]
    entry['math_reviewed']=True;entry['math_review_note']='Actual source h-bar vector ink restored as an inline original image.'
    entry=by_id['3-9'];old=entry['math'][2]
    entry['math'][2]=snapshot(doc[2],[522.7,744.6,552.2,758.1],FOLDER/'3-9-complete-photon-momentum.png')
    entry['math'][2]['source_text']='p = ℏ k';entry['math'][2]['source_char_indices']=old['source_char_indices']
    # Translate descriptive Chinese subscripts while keeping the original
    # vector letters. cf/cor are defined in the surrounding translated prose.
    entry=by_id['2-4'];chars=cjk.characters(doc[1])
    for mi,subscript in [(4,'cf'),(5,'cor'),(6,'cf'),(7,'cor')]:
        old=entry['math'][mi];ids=set(old['source_char_indices'])
        selected=[c for c in chars if c['index'] in ids];labels=[c for c in selected if cjk.HAN.search(c['c'])]
        base=[c for c in selected if not cjk.HAN.search(c['c'])]
        if not labels or not base:raise ValueError('Expected source force/torque subscript')
        x=min(c['origin'][0] for c in labels);y=sum(c['origin'][1] for c in labels)/len(labels);size=min(c['size'] for c in labels)
        svg=doc[1].get_svg_image(text_as_path=True)
        label=f'<text x="{x}" y="{y}" font-family="Times New Roman" font-size="{size}" fill="black">{subscript}</text>'
        svg=svg.replace('</svg>',label+'</svg>')
        cluster={'chars':base,'rect':old['source_rect'],'y':base[0]['origin'][1],'text':old['source_text'].replace('离心','cf').replace('科氏','cor')}
        entry['math'][mi]=cjk.math_image(svg,cluster,FOLDER/f'2-4-translated-subscript-{mi}.png')
        entry['math'][mi]['source_char_indices']=old['source_char_indices']
        entry['math'][mi]['translated_subscript']={'original':''.join(c['c'] for c in labels),'replacement':subscript}
    manual=FOLDER.parent/'problems.tsv'
    if manual.exists():
        rows={key:(ko,en) for key,ko,en in (line.split('\t') for line in manual.read_text(encoding='utf8').splitlines() if line.strip())}
        for entry in data['entries']:
            if entry['id'] not in rows:continue
            entry['ko'],entry['en']=rows[entry['id']]
            expected=Counter(re.findall(r'\[\[\d+\]\]',entry['source']))
            for lang in ['ko','en']:
                actual=Counter(re.findall(r'\[\[\d+\]\]',entry[lang]))
                if actual!=expected:raise ValueError(f'{entry["id"]}/{lang}: expected {expected}, got {actual}')
    (FOLDER/'translation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    (FOLDER/'source-reviewed.txt').write_text('\n'.join(f'{e["id"]}|{e["source"]}|MATH '+str([(i,m['source_text']) for i,m in enumerate(e['math'])]) for e in data['entries']),encoding='utf8')
    return data

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--extract',action='store_true');parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--publish-problems',action='store_true')
    args=parser.parse_args()
    if args.extract:extract()
    data=prepare()
    if not args.prepare_only:
        from cpho_2022_figures import replace
        inventory=[]
        for lang in ['ko','en']:
            target=ROOT/f'tmp/cpho-build/2022-{lang}-problems-preview.pdf'
            if target.exists():target.unlink()
            cjk.build(FOLDER,target,lang);replace(target,lang)
            if args.publish_problems:
                canonical=ROOT/'pdfx/cpho'/f'CPhO_2022_T_{"KO" if lang=="ko" else "BAUPC_EN"}.pdf'
                shutil.copy2(target,canonical);doc=fitz.open(canonical)
                missing=[]
                for pi,page in enumerate(doc):
                    if cjk.HAN.search(page.get_text()):raise ValueError(f'Untranslated native Han on page {pi+1}')
                    for block in page.get_text('dict')['blocks']:
                        if block['type']!=0:continue
                        for line in block['lines']:
                            for span in line['spans']:
                                if any(n in span['font'] for n in ['NotoSansKR','Droid']) and any(c in span['text'] for c in ['\x00','�']):missing.append({'page':pi+1,'text':span['text']})
                if missing:raise ValueError(missing)
                inventory.append(dict(file=canonical.name,pages=len(doc),bytes=canonical.stat().st_size,sha256=hashlib.sha256(canonical.read_bytes()).hexdigest(),missing_glyph_spans=missing))
        if args.publish_problems:
            source=cjk.resolve_source(data)
            report=dict(year=2022,source=source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_pages=[1,2,3,4],problems=6,typeset_regions=len(data['entries']),redrawn_figures=6,figure_languages=['ko','en'],files=inventory,
                source_note='The source omits a point total from the heading of problem 6. Original mathematical equations, units and notation are retained; descriptive force and torque subscripts are translated as cf and cor and defined in prose. Original h-bar image accents are restored from the source ink.',
                review='All four pages in each language visually reviewed. Figure axes, lattice spacing and angles checked against the original. Native translated-font missing glyphs, Hangul visibility loss and actual inline-image clipping checked independently.')
            (ROOT/'tools/cpho_2022_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            print(json.dumps(inventory))
