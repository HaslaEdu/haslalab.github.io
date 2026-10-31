"""Natural spacing on immutable 2005/2013 original-Chinese-based T editions.

All new output is on D:. The original editions, source plans and journals are
immutable. This adapter reuses the proven native-CID composer, never the old
third-party English-layout editions.
"""
from pathlib import Path
from collections import defaultdict
import json,hashlib,os,time
import pikepdf
import pymupdf as fitz
import cpho_natural_spacing as core
from pdf_korean_natural_composer import normalize_placements

BASE=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ['HASLALAB_SOURCE_ROOT'])
REGISTRY={r['year']:r for r in json.loads((BASE/'immutable-inputs.json').read_text('utf8'))}
OLD_BASELINE,OLD_ORIGINAL,OLD_SOURCE_PLAN=core.baseline,core.original,core.source_plan
LAST_SPEC=None

def baseline(year,language):
    return Path(REGISTRY[year]['baselines'][language]['path'])if year in REGISTRY else OLD_BASELINE(year,language)

def original(year):
    return Path(REGISTRY[year]['source'])if year in REGISTRY else OLD_ORIGINAL(year)

def source_plan(year,number):
    if year not in REGISTRY:return OLD_SOURCE_PLAN(year,number)
    data=json.loads(Path(REGISTRY[year]['plans']['path']).read_text('utf8'))
    return next(p for p in data['pages']if p['source_page']==number)

def placements(year,language,number):
    data=json.loads((BASE/f'immutable-input-journals/{year}/{language}/page{number:02}.build.json').read_text('utf8'))
    slots={p['id']:p for p in source_plan(year,number)['slots']};rows=[]
    for p in data['placements']:
        if not p['text'].strip():continue
        s=slots[p['id']]
        rows.append(dict(p,point=p['origin'],family=s['family'],italic=s.get('italic',False),
            source_font=s['source_font'],source_rect=s['source_rect'],
            border_width=p.get('line_width',0),align=s.get('align'),
            original_role=s.get('original_paragraph_role'),overlay=True))
    for p in (data.get('raster_overlay')or{}).get('placements',[]):
        if not p['text'].strip():continue
        rows.append(dict(p,point=p['point'],family='serif'if'Serif'in p['font_path']else'sans',
            italic=False,source_font='Measured bitmap prose face',source_rect=None,
            border_width=0,align=p.get('align','left'),original_role='figure-language',
            raster_label=True,overlay=True))
    with fitz.open(baseline(year,language))as doc:
        return normalize_placements(doc[number-1],rows)

def prepare(year,language,number,input_path=None,input_page=None,prose_placements=None):
    global LAST_SPEC
    numeric=BASE/f'numeric-stage/{year}/{language}/complete-source-number-faces.pdf'
    input_path=Path(input_path or (numeric if numeric.exists()else baseline(year,language)));input_page=input_page or number
    pp=prose_placements or placements(year,language,number)
    source=original(year);data=source_plan(year,number);by_y=defaultdict(list)
    for p in pp:
        y=p['point'][1];near=[v for v in by_y if abs(v-y)<.12]
        by_y[near[0]if near else y].append(p)
    with fitz.open(source)as doc:
        page=doc[number-1]
        images=[list(i['bbox'])for i in page.get_image_info()if i['width']>8 and i['height']>8]
        right=541.32 if year==2005 else 539.65
        header_right=max([q['source_rect'][2]for q in data['slots']if q.get('original_paragraph_role')=='header']or[right])
        regions=[];centers=[];captions=[];labels=[];rights=[]
        for y,items in sorted(by_y.items()):
            inside=[p for p in items if p.get('raster_label')or any(fitz.Rect(r).contains(fitz.Point(p['point']))for r in images)]
            outside=[p for p in items if p not in inside]
            for p in inside:
                x=p['point'][0];size=p['size']
                labels.append(dict(rect=[x-size,y-.85*size,x+p['width']+size,y+.32*size],
                    baseline=y,placements=[p['id']],caption=False,alignment=p.get('align')or'left',
                    center=x+p['width']/2,right=None))
            if not outside:continue
            size=max(p['size']for p in outside);x0,x1=54.,right
            role={p.get('original_role')for p in outside}
            centered='title'in role or'footer'in role or ('header'in role and year==2005)
            aligned_right='header'in role and year==2013
            if centered:
                x0,x1=24.,page.rect.width-24.;centers.append(dict(baseline=y,center=page.rect.width/2))
            if aligned_right:
                x0,x1=24.,header_right;rights.append(dict(baseline=y,right=header_right))
            if not centered and not aligned_right:
                for r in images:
                    if r[1]<y+size*.2 and r[3]>y-size*.85:
                        if all(p['point'][0]+p['width']<=r[0]+.1 for p in outside):x1=min(x1,r[0])
                        elif all(p['point'][0]>=r[2]-.1 for p in outside):x0=max(x0,r[2])
            regions.append(dict(rect=[x0,y-.85*size,x1,y+.32*size],baseline=y,
                placements=[p['id']for p in outside],caption=False))
    starts=[]
    if (year,language,number)in((2005,'ko',2),(2005,'ko',3)):
        slot_id='2-7-0'if number==2 else'3-12-0'
        first=next(s for s in data['slots']if s['id']==slot_id)
        starts=[dict(baseline=first['origin'][1],left=first['source_rect'][0],source_prose_slot=slot_id,reason='Align the complete translated line to its original first source prose glyph. The preceding translated clause absorbed this source prefix, so the old fixed native-variable position leaves an unintended leading blank. Original native glyphs move only horizontally.')]
    LAST_SPEC=dict(reviewed_line_starts=starts,year=year,language=language,page=number,input=str(input_path),input_page=input_page,
        input_sha256=core.sha(input_path),original=str(source),original_sha256=core.sha(source),
        regions=regions,caption_regions=captions,picture_label_regions=labels,
        centered_lines=centers,right_aligned_lines=rights,excluded_figure_rects=images,prose_placements=pp)
    return LAST_SPEC

def install():
    core.OUT=BASE/'output'
    core.baseline=baseline;core.original=original;core.source_plan=source_plan
    core.placements=placements;core.prepare=prepare
    import cpho_natural_prose_edits as prose
    for edit in json.loads((BASE/'prose-edits.json').read_text('utf8')):
        table=prose.EDITS if edit['language']=='ko'else prose.EN_EDITS
        table.setdefault((edit['year'],edit['page']),{})[edit['id']]=(edit['before'],edit['after'])
    import cpho_natural_english_fonts
    from cpho_early_english_faces import prepare_english_faces
    cpho_natural_english_fonts.prepare_english_faces=prepare_english_faces
    import cpho_natural_rotated_labels
    cpho_natural_rotated_labels.apply=lambda raw,year,language,number:(raw,None)
    import cpho_natural_atoms
    cpho_natural_atoms.ROOT=BASE/'authoring-root'

def build(year,language,number):
    install()
    numeric=BASE/f'numeric-stage/{year}/{language}/complete-source-number-faces.pdf'
    if not numeric.exists():raise ValueError('Prepare the reviewed numeric-prose input stage before body composition')
    # Pass original running-header alignment through the generic body call.
    # Figure-language passes already provide their own alignment explicitly.
    saved=core.compose_page
    def compose(*args,**kwargs):
        if 'right_aligned_lines'not in kwargs:
            kwargs['right_aligned_lines']=LAST_SPEC['right_aligned_lines']
            kwargs['reviewed_line_starts']=LAST_SPEC.get('reviewed_line_starts',[])
        return saved(*args,**kwargs)
    core.compose_page=compose
    try:return core.build(year,language,number)
    finally:core.compose_page=saved


def prepare_numeric_input(year,language):
    from cpho_early_heading_numbers import page
    from pdf_memory_gate import page_worker
    folder=BASE/f'numeric-stage/{year}/{language}';folder.mkdir(parents=True,exist_ok=True)
    reports=[];proofs=[]
    for n in (1,2,3):
        with page_worker():
            path,report=page(original(year),baseline(year,language),n,source_plan(year,n)['slots'],
                placements(year,language,n),folder)
        reports.append(report);proofs.append(path);time.sleep(.6)
    target=folder/'complete-source-number-faces.pdf'
    with pikepdf.Pdf.new()as out:
        for path in proofs:
            with pikepdf.open(path)as one:out.pages.append(one.pages[0])
        out.save(target,compress_streams=False)
    target.with_suffix('.json').write_text(json.dumps(dict(year=year,language=language,
        source=str(original(year)),source_sha256=core.sha(original(year)),
        immutable_input=str(baseline(year,language)),immutable_input_sha256=core.sha(baseline(year,language)),
        output=str(target),output_sha256=core.sha(target),source_original_numerical_prose_faces_restored=True,
        pages=reports),ensure_ascii=False,indent=2),'utf8')
    return target

