from pathlib import Path
import sys,json,re,hashlib,time
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025')
ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools',str(ROOT/'tools')]
import pymupdf as fitz
import cpho2025_scan_fonts as shared
from pdf_original_raster_math import replay
from pdf_memory_gate import page_worker
shared.BASE=B;shared.ROOT=ROOT
SOURCE=B/'CPhO_2025_T_original-explicit-page-clip.pdf'
PLAN=B/'authoring/page01-draft-layout.json'
OUT=B/'page01-draft';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(lang):
    plan=json.loads(PLAN.read_text('utf8'));rows=plan['rows'];pool=''.join(re.sub(r'\[\[[^]]+\]\]','',r[lang])for r in rows)
    path=Path('C:/Windows/Fonts/batang.ttc')if lang=='ko'else Path('C:/Windows/Fonts/simsun.ttc')
    body=shared.new_font(path,pool)
    note_path=Path('C:/Windows/Fonts/batang.ttc')if lang=='ko'else B.parent/'official-hans-fonts/faces/simkai.ttf'
    note_pool=''.join(re.sub(r'\[\[[^]]+\]\]','',r[lang])for r in rows if r['font_role']=='note')
    note=shared.new_font(note_path,note_pool,2 if lang=='ko'else 0)
    faces={'body':body,'note':note}
    atoms=[];prose=[];placements=[];overflow=[]
    for row in rows:
        amap={a['id']:a for a in row['atoms']};used=[];tokens=[]
        in_note=False
        for part in re.split(r'(\[\[[^]]+\]\])',row[lang]):
            if not part:continue
            if part.startswith('[['):
                key=part[2:-2];a=amap[key];used.append(key)
                tokens.append(dict(kind='math',width=a['rect'][2]-a['rect'][0],atom=a))
            else:
                pieces=[part]
                if row['id']=='p2-convention'and '['in part:
                    k=part.index('[');pieces=[part[:k],part[k:]]
                for fragment in pieces:
                    if not fragment:continue
                    if row['id']=='p2-convention'and fragment.startswith('['):in_note=True
                    role=row['font_role'];size=row['size'];baseline=row['baseline']
                    if row['id']=='p2-convention'and not in_note:role='body';size=row['prefix_size'];baseline=row['prefix_baseline']
                    stroke=(.30 if lang=='ko'else .50)if role=='body'else row['printed_stroke_by_language'][lang]['regular']
                    tokens.append(dict(kind='text',text=fragment,width=shared.width(faces[role][1],fragment,size),font_role=role,size=size,baseline=baseline,stroke=stroke))
        if sorted(used)!=sorted(amap):raise ValueError(('Dropped/duplicated notation',row['id'],lang,used,list(amap)))
        total=sum(t['width']for t in tokens);left=row['left']
        if row['id'].startswith('figure-'):left=466.5-total/2
        if row['id']=='footer':left=301-total/2
        x=left
        for t in tokens:
            if t['kind']=='math':
                a=t['atom'];atoms.append(dict(id=row['id']+'-'+a['id'],rect=a['rect'],image_path=a['image_path'],dx=x-a['rect'][0],reviewed=True,reason=a['reason']))
            else:prose.append(dict(text=t['text'],point=[x,t['baseline']],size=t['size'],row=row['id'],stroke=t['stroke'],alias='DraftBody'if t['font_role']=='body'else'DraftNote',font_role=t['font_role']))
            x+=t['width']
        if not row['id'].startswith('figure-')and row['id']!='footer'and x>row['right']+.001:overflow.append(dict(row=row['id'],language=lang,right=x,limit=row['right'],overflow_pt=x-row['right'],text=row[lang]))
        placements.append(dict(id=row['id'],text=row[lang],point_size=row['size'],baseline=row['baseline'],left=left,right=x))
    (OUT/f'{lang}-layout-check.json').write_text(json.dumps(dict(overflow=overflow,placements=placements),ensure_ascii=False,indent=2)+'\n','utf8')
    if overflow:
        for r in overflow:print(json.dumps(r,ensure_ascii=False),flush=True)
        return False
    if '--layout-only'in sys.argv:return True
    with page_worker():
        header=B/f'hint-layout-prototypes/page01-{lang}-erased.pdf'
        h=json.loads((B/f'hint-layout-prototypes/page01-{lang}-header-hint-prototype.json').read_text('utf8'))
        hatoms=[dict(id='header-'+a['id'],rect=a['source_rect'],image_path=a['image_path'],dx=a['dx'],reviewed=True,reason=a['reason'])for a in h['original_numeric_and_math_bitmap_replay']['atoms']]
        erased=OUT/f'page01-{lang}-erased.pdf'
        with fitz.open(header)as d:
            for row in rows:
                for rect in row['erase_rects']:d[0].draw_rect(rect,color=None,fill=(1,1,1),overlay=True)
            for atom in atoms:d[0].draw_rect(atom['rect'],color=None,fill=(1,1,1),overlay=True)
            d.save(erased,garbage=0,deflate=False)
        replayed,journal=replay(SOURCE,1,erased,hatoms+atoms)
        target=OUT/f'page01-{lang}-draft.pdf'
        with fitz.open(stream=replayed,filetype='pdf')as d:
            page=d[0]
            derivative=next(a for a in hatoms if a['id']=='header-derivative')
            dx=derivative['dx'];page.draw_rect([427+dx,150.3,444+dx,161],color=None,fill=(1,1,1),overlay=True)
            control=OUT/f'page01-{lang}-pre-prose.pdf';d.save(control,garbage=0,deflate=False)
            ref=fitz.open();reference=ref.new_page(width=page.rect.width,height=page.rect.height)
            for role,(raw,metric,provenance)in faces.items():
                alias='DraftBody'if role=='body'else'DraftNote';page.insert_font(fontname=alias,fontbuffer=raw);reference.insert_font(fontname=alias,fontbuffer=raw)
            for face in['sans','serif']:
                hp=[p for p in h['placements']if p['face']==face]
                pool=''.join(p['text']for p in hp)
                if face=='serif':fp=Path('C:/Windows/Fonts/batang.ttc')if lang=='ko'else Path('C:/Windows/Fonts/simsun.ttc')
                else:fp=ROOT/'tools/ko/fonts/NotoSansCJKkr-Regular.otf'if lang=='ko'else B.parent/'official-hans-fonts/faces/simhei.ttf'
                hf,hm,_=shared.new_font(fp,pool);alias='Header'+face;page.insert_font(fontname=alias,fontbuffer=hf);reference.insert_font(fontname=alias,fontbuffer=hf)
                for p in hp:
                    shared.write_words(page,*p['point'],p['text'],hm,p['size'],alias,2,p['user_space_stroke_width_pt'])
                    shared.write_words(reference,*p['point'],p['text'],hm,p['size'],alias,2,p['user_space_stroke_width_pt'])
            for p in prose:
                metric=faces[p['font_role']][1]
                shared.write_words(page,*p['point'],p['text'],metric,p['size'],p['alias'],2,p['stroke'])
                shared.write_words(reference,*p['point'],p['text'],metric,p['size'],p['alias'],2,p['stroke'])
            d.save(target,garbage=0,deflate=False)
            ref.save(OUT/f'page01-{lang}-prose-only.pdf',garbage=0,deflate=False);ref.close()
        with fitz.open(target)as d:d[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(OUT/f'page01-{lang}-draft.png')
        evidence=dict(status='DRAFT_NOT_FOR_PUBLICATION',source_sha256=sha(SOURCE),authoring_sha256=sha(PLAN),proof_sha256=sha(target),placements=placements,prose_placements=prose,header_prose_placements=h['placements'],math_replay=journal,fonts={role:f[2]for role,f in faces.items()})
        target.with_suffix('.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n','utf8')
        print(json.dumps(dict(language=lang,status='DRAFT',proof=str(target),sha256=sha(target)),ensure_ascii=False),flush=True)
    time.sleep(.6)
    return True
all_passed=True
for lang in([s for s in sys.argv[1:]if not s.startswith('--')]or['ko','en']):
    if lang not in['ko','en']:raise ValueError(lang)
    passed=prepare(lang);all_passed=all_passed and passed
raise SystemExit(not all_passed)
