"""Extract private source problem regions using native font and page geometry.

Standalone bold problem identities, lecture boundaries, figures and footnotes
are indexed separately. All extracted text/math and automatic diagram geometry
remain pending review. Source-specific manual regions belong in a private,
source-SHA-bound JSON file, never in this script. No network/model API is used.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile

import pymupdf as fitz
from PIL import Image, ImageChops
from private_paths import private_directory

PROBLEM = re.compile(r'^Problem\s+(\d{1,2})\.(\d{1,3})(?!\d)')
CAPTION = re.compile(r'^FIGURE\s+(\d{1,2}\.\d{1,3})(?!\d)')


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.extract-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def json_write(path, data):
    write(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf8'))


def lines(page):
    result = []
    for block in page.get_text('dict', flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)['blocks']:
        if block['type'] != 0:
            continue
        for line in block['lines']:
            text = ''.join(span['text'] for span in line['spans']).strip()
            if not text:
                continue
            # A displayed expression can have several baselines. Keep native
            # line geometry, with prose baseline used only for row ordering.
            spans = [{key: span[key] for key in ('text', 'font', 'size', 'bbox', 'origin')}
                     for span in line['spans']]
            usual = [s for s in spans if s['size'] >= 8 and s['font'].startswith('Times')]
            baseline = usual[0]['origin'][1] if usual else spans[0]['origin'][1]
            result.append({'text': text, 'bbox': list(line['bbox']), 'spans': spans,
                           'baseline': baseline, 'block_bbox': list(block['bbox'])})
    return sorted(result, key=lambda line: (round(line['baseline'], 1), line['bbox'][0]))


def identity(line):
    prefix = ''
    for span in line['spans']:
        if span['font'] != 'Times-Bold' or abs(span['size'] - 8.9664) > .08:
            break
        prefix += span['text']
    match = PROBLEM.match(prefix.strip())
    if not match or not 165 < line['bbox'][0] < 177:
        return None
    return f'{int(match[1])}.{int(match[2])}'


def lecture(line):
    if line['bbox'][1] < 55:
        return False
    for span in line['spans']:
        if not span['text'].strip():
            continue
        if span['font'].startswith('Optima') and span['size'] >= 9.8:
            return True
        if span['font'] in ('Times-Roman', 'Times-Bold', 'Times-Italic') and 9.7 < span['size'] < 10.3:
            return True
    return False


def normalize(rect, page):
    return [round(rect.x0/page.rect.width, 8), round(rect.y0/page.rect.height, 8),
            round(rect.x1/page.rect.width, 8), round(rect.y1/page.rect.height, 8)]


def region_from_private(region, document):
    number = int(region['page'])
    page = document[number - 1]
    rect = fitz.Rect(region['bbox'])
    if region.get('units', 'points') == 'normalized':
        rect = fitz.Rect(rect.x0*page.rect.width, rect.y0*page.rect.height,
                         rect.x1*page.rect.width, rect.y1*page.rect.height)
    if rect.is_empty or rect.x0 < 0 or rect.y0 < 0 or rect.x1 > page.rect.width+.01 or rect.y1 > page.rect.height+.01:
        raise ValueError('Invalid private source region')
    return number, rect


def render(document, filename, number, rect, dpi, role, cache):
    page = document[number - 1]
    rect = fitz.Rect(rect) & page.rect
    requested = normalize(rect, page)
    prior = cache.get(str(filename.resolve()))
    if (prior and prior.get('requested_bbox') == requested and prior.get('render_dpi') == dpi
            and filename.exists() and hashlib.sha256(filename.read_bytes()).hexdigest() == prior['sha256']):
        return dict(prior, role=role)
    scale = dpi/72
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
    picture = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    ink = picture.convert('L').point(lambda value: 255 if value < 240 else 0).getbbox()
    if ink is None:
        return None
    padding = max(2, int(scale*2))
    box = (max(0,ink[0]-padding), max(0,ink[1]-padding),
           min(pix.width,ink[2]+padding), min(pix.height,ink[3]+padding))
    picture = picture.crop(box)
    actual = fitz.Rect((pix.x+box[0])/scale, (pix.y+box[1])/scale,
                       (pix.x+box[2])/scale, (pix.y+box[3])/scale) & page.rect
    buffer = io.BytesIO()
    picture.save(buffer, 'WEBP', quality=94, method=4)
    data = buffer.getvalue()
    write(filename, data)
    return {'role':role, 'local_path':str(filename.resolve()), 'mime_type':'image/webp',
            'sha256':hashlib.sha256(data).hexdigest(), 'spans':[{'page':number,'bbox':normalize(actual,page)}],
            'requested_bbox':requested, 'render_dpi':dpi, 'review_status':'pending'}


def graphic_groups(page):
    rects = [fitz.Rect(item['bbox']) for item in page.get_image_info()]
    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing['rect'])
        if rect.y0 < 55 or (abs(rect.width-322.8) < 1 and rect.height < 2):
            continue
        if rect.width >= 10 or rect.height >= 10:
            rects.append(rect)
    groups = []
    for rect in rects:
        joined, changed = rect, True
        while changed:
            changed = False
            for old in groups[:]:
                if (joined+(-5,-5,5,5)).intersects(old):
                    joined |= old
                    groups.remove(old)
                    changed = True
        groups.append(joined)
    return groups


def subtract_region(rect, cut):
    """Keep source text around a separately stored figure rectangle."""
    overlap=rect&cut
    if overlap.is_empty:return [rect]
    return [r for r in [fitz.Rect(rect.x0,rect.y0,rect.x1,overlap.y0),
                        fitz.Rect(rect.x0,overlap.y1,rect.x1,rect.y1),
                        fitz.Rect(rect.x0,overlap.y0,overlap.x0,overlap.y1),
                        fitz.Rect(overlap.x1,overlap.y0,rect.x1,overlap.y1)]
            if r.width>3 and r.height>3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-info', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pdf', type=Path)
    parser.add_argument('--dpi', type=int, default=130)
    parser.add_argument('--overrides', type=Path)
    args = parser.parse_args()
    output = private_directory(args.out)
    if not 80 <= args.dpi <= 180:
        raise ValueError('Use 80 to 180 dpi')
    source = json.loads(args.source_info.read_text(encoding='utf-8-sig'))
    pdf = args.pdf or Path(source['local_path'])
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != source['sha256']:
        raise ValueError('Source SHA mismatch')
    overrides = {}
    if args.overrides and args.overrides.exists():
        overrides = json.loads(args.overrides.read_text(encoding='utf-8-sig'))
        if overrides.get('source_sha256') != digest:
            raise ValueError('Private override SHA mismatch')
    cache = {}
    old = output/'questions.raw.json'
    if old.exists():
        previous = json.loads(old.read_text(encoding='utf-8-sig'))
        if previous.get('source_sha256') == digest:
            cache.update({a['local_path']:a for q in previous['questions'] for a in q['assets']})
    old_figures = output/'figure-index.json'
    if old_figures.exists():
        cache.update({a['local_path']:a for a in json.loads(old_figures.read_text(encoding='utf8')).get('figures',{}).values()})
    document = fitz.open(pdf)
    page_lines = [lines(page) for page in document]
    chapters = []
    for level,title,number in document.get_toc():
        match = re.match(r'^(\d{1,2}) (.+)$', title)
        if level == 1 and match:
            chapters.append({'number':match[1],'title':match[2],'page':number})
    if [int(c['number']) for c in chapters] != list(range(1,13)):
        raise ValueError('Expected twelve numbered TOC chapters')
    starts, rejected, captions, footnotes, stops, rules = [], [], {}, {}, [], []
    for number, text in enumerate(page_lines,1):
        for line in text:
            if line['bbox'][1] < 55:
                continue
            label = identity(line)
            if label:
                starts.append({**line,'page':number,'number':label,'chapter':label.split('.')[0]})
            elif PROBLEM.match(line['text']):
                rejected.append({'page':number,'text':line['text'],'reason':'not_standalone_bold_problem_font'})
            if lecture(line):
                stops.append({'page':number,'top':line['bbox'][1],'reason':'lecture_font'})
            match = CAPTION.match(line['text'])
            if match and line['spans'][0]['font']=='Times-Bold':
                if match[1] in captions:
                    raise ValueError('Duplicate source figure label')
                captions[match[1]]={**line,'page':number}
        # Footnotes have a small leading numerical marker on the lecture-text
        # left margin. Math superscripts farther right are not identities.
        note_heads=[]
        for line in text:
            first=line['spans'][0]
            if (line['bbox'][1]>300 and 143<first['bbox'][0]<149 and first['font']=='Times-Roman'
                    and first['size']<6.1 and re.fullmatch(r'\d{1,2}',first['text'].strip())
                    and any(7.8<s['size']<8.1 and len(s['text'].strip())>3 for s in line['spans'])):
                note_heads.append((line,first['text'].strip()))
        for i,(head,label) in enumerate(note_heads):
            end=note_heads[i+1][0]['bbox'][1] if i+1<len(note_heads) else document[number-1].rect.height-28
            group=[line for line in text if head['bbox'][1]-.1<=line['bbox'][1]<end
                   and not lecture(line)]
            rect=fitz.Rect(head['bbox'])
            for line in group:rect|=fitz.Rect(line['bbox'])
            footnotes[number,label]={'page':number,'bbox':list(rect+(-1,-1,2,2)),
                                    'text':'\n'.join(line['text']for line in group)}
        for drawing in document[number-1].get_drawings():
            rect=drawing['rect']
            if abs(rect.width-322.8)<1 and rect.height<2 and 55<rect.y0<document[number-1].rect.height-25:
                rules.append({'page':number,'top':rect.y0,'reason':'problem_group_rule'})
    starts.sort(key=lambda s:(s['page'],s['bbox'][1]))
    coverage={}
    for chapter in chapters:
        numbers=[int(s['number'].split('.')[1])for s in starts if s['chapter']==chapter['number']]
        if not numbers:raise ValueError('Missing chapter problems')
        counts=collections.Counter(numbers)
        missing=sorted(set(range(1,max(numbers)+1))-set(numbers))
        duplicates=[n for n,count in counts.items()if count>1]
        coverage[chapter['number']]={'first':min(numbers),'last':max(numbers),'count':len(numbers),
                                     'missing':missing,'duplicates':duplicates}
        if missing or duplicates or min(numbers)!=1:raise ValueError('Nonconsecutive problem labels')
    if overrides.get('expected_chapter_endpoints'):
        if {k:v['last']for k,v in coverage.items()}!=overrides['expected_chapter_endpoints']:
            raise ValueError('Reviewed chapter endpoint mismatch')
    figure_assets,figure_issues={},[]
    groups={}
    for label,cap in captions.items():
        number=cap['page'];page=document[number-1]
        manual=overrides.get('figures',{}).get(label)
        if manual:
            p,rect=region_from_private(manual,document)
            if p!=number:raise ValueError('Figure caption/override page mismatch')
            flags=['source_rectangle_visually_reviewed']
        else:
            if number not in groups:groups[number]=graphic_groups(page)
            caption_rect=fitz.Rect(cap['bbox'])
            neighbours=[c for c in captions.values()if c['page']==number and abs(c['bbox'][1]-cap['bbox'][1])<20]
            centres=sorted((c['bbox'][0]+c['bbox'][2])/2 for c in neighbours)
            centre=(caption_rect.x0+caption_rect.x1)/2
            left=max([140]+[(x+centre)/2 for x in centres if x<centre-1])
            right=min([472]+[(x+centre)/2 for x in centres if x>centre+1])
            candidates=[g for g in groups[number]if g.y1<=caption_rect.y0+6 and g.y1>=caption_rect.y0-220
                        and g.x1>left and g.x0<right]
            if not candidates:
                figure_issues.append({'figure':label,'page':number,'reason':'no_graphic_group'})
                continue
            candidates.sort(key=lambda g:max(0,caption_rect.y0-g.y1)+max(0,left-g.x1,g.x0-right)*2)
            best=max(0,caption_rect.y0-candidates[0].y1)
            rect=fitz.Rect(candidates[0])
            # Parallel panels often have disconnected paths. Seed all panels
            # ending near the same caption row before growing components.
            for candidate in candidates:
                if max(0,caption_rect.y0-candidate.y1)<=best+30:
                    rect|=candidate
            # A long multi-panel figure can extend much farther upward than
            # its bottom path. Long prose rows supply a top boundary without
            # treating short native diagram labels as lecture paragraphs.
            prose=[line for line in page_lines[number-1]if line['bbox'][3]<rect.y0-3
                   and line['bbox'][2]>rect.x0+10 and line['bbox'][0]<rect.x1-10
                   and line['bbox'][2]-line['bbox'][0]>120
                   and sum(ch.isalpha()for ch in line['text'])>15
                   and any(s['font']=='Times-Roman'and s['size']>8.8 for s in line['spans'])]
            upper=max([55]+[line['bbox'][3]+3 for line in prose])
            for candidate in groups[number]:
                if (candidate.y0>=upper and candidate.y1<=caption_rect.y0+6
                        and candidate.x1>left and candidate.x0<right):
                    rect|=candidate
            changed=True
            while changed:
                changed=False
                for g in candidates:
                    if g.intersects(rect+(-12,-20,12,12)) and not rect.contains(g):
                        rect|=g;changed=True
            # Paths omit coordinate labels and axis letters. Expand to native
            # short glyph spans near the geometry, inside the caption's cell.
            nearby=rect+(-40,-10,40,12)
            for line in page_lines[number-1]:
                for span in line['spans']:
                    box=fitz.Rect(span['bbox']);label_text=span['text'].strip()
                    if (label_text and len(label_text)<35 and not label_text.startswith(('FIGURE','Problem'))
                            and box.y0>=upper-.5 and box.y1<caption_rect.y0
                            and left<=(box.x0+box.x1)/2<=right and box.intersects(nearby)):
                        rect|=box
            rect=fitz.Rect(max(left,min(rect.x0-3,caption_rect.x0-2)),max(upper,rect.y0-3),
                           min(right,max(rect.x1+3,caption_rect.x1+2)),caption_rect.y1+3)
            flags=['automatic_figure_geometry_pending_review']
        asset=render(document,output/'figures'/f'figure-{label}.webp',number,rect,args.dpi,'source_figure',cache)
        if asset:
            asset.update(figure_label=label,quality_flags=flags)
            figure_assets[label]=asset
    note_assets={}
    for (number,label),note in footnotes.items():
        asset=render(document,output/'footnotes'/f'pdf{number:03}-note{label}.webp',number,note['bbox'],
                     args.dpi,'source_footnote',cache)
        if asset:note_assets[number,label]=asset
    questions=[]
    points=lambda p:(p['page'],p['top'])
    for index,start in enumerate(starts):
        next_start=starts[index+1]if index+1<len(starts)else {'page':594,'bbox':[0,55,0,55]}
        end=(next_start['page'],next_start['bbox'][1]-1)
        point=(start['page'],start['bbox'][1])
        boundaries=[p for p in stops+rules if point<points(p)<end]
        boundary=min(boundaries,key=points)if boundaries else None
        if boundary:end=points(boundary)
        edit=overrides.get('questions',{}).get(start['number'],{})
        rectangles=[]
        if 'statement_regions'in edit:
            rectangles=[region_from_private(r,document)for r in edit['statement_regions']]
        else:
            for number in range(start['page'],end[0]+1):
                top=start['bbox'][1]-2 if number==start['page']else 55
                page_bottom=document[number-1].rect.height-28
                bottom=end[1]-1 if number==end[0]else page_bottom
                # A footer is skipped on this page, without terminating a
                # question whose statement continues on the following page.
                note_top=min([page_bottom]+[n['bbox'][1]-1 for(p,_),n in footnotes.items()if p==number])
                bottom=min(bottom,note_top)
                if bottom>top:rectangles.append((number,fitz.Rect(140,top,472,bottom)))
        excluded_figures=[]
        if start['chapter']in overrides.get('separate_figures_for_chapters',[]):
            separated=[]
            for number,rect in rectangles:
                parts=[rect]
                for label,figure in figure_assets.items():
                    if figure['spans'][0]['page']!=number:continue
                    page=document[number-1];b=figure['requested_bbox']
                    cut=fitz.Rect(b[0]*page.rect.width,b[1]*page.rect.height,b[2]*page.rect.width,b[3]*page.rect.height)
                    if not rect.intersects(cut):continue
                    excluded_figures.append(label)
                    parts=[piece for part in parts for piece in subtract_region(part,cut)]
                separated.extend((number,part)for part in sorted(parts,key=lambda r:(r.y0,r.x0)))
            rectangles=separated
        assets=[];body=[];markers={}
        for i,(number,rect)in enumerate(rectangles,1):
            asset=render(document,output/'crops'/f'problem-{start["number"]}-{i:02}.webp',number,rect,args.dpi,'question_crop',cache)
            if not asset:continue
            assets.append(asset)
            selected=[line for line in page_lines[number-1]if rect.y0<=(line['bbox'][1]+line['bbox'][3])/2<rect.y1
                      and line['bbox'][2]>rect.x0 and line['bbox'][0]<rect.x1]
            body.extend(line['text']for line in selected)
            markers[number]=sorted({s['text'].strip()for line in selected for s in line['spans']
                if s['size']<6.1 and s['font']=='Times-Roman'and re.fullmatch(r'\d{1,2}',s['text'].strip())
                and (number,s['text'].strip())in footnotes})
        if not assets:raise ValueError('Empty problem crop')
        text='\n'.join(body)
        figure_refs=sorted(set(re.findall(r'(?:Fig(?:ure)?\.?\s*)(\d{1,2}\.\d+)',text)))
        formula_refs=sorted(set(re.findall(r'(?:Eq(?:uation)?s?\.?\s*\(?)(\d{1,2}\.\d+)',text)))
        for ref in figure_refs:
            if ref in figure_assets:assets.append(figure_assets[ref])
        linked_notes=[]
        for number,labels in markers.items():
            for label in labels:
                if label in edit.get('exclude_footnotes',{}).get(str(number),[]):continue
                if(number,label)in note_assets:
                    assets.append(note_assets[number,label]);linked_notes.append(footnotes[number,label])
        for i,region in enumerate(edit.get('context_regions',[]),1):
            number,rect=region_from_private(region,document)
            asset=render(document,output/'context'/f'problem-{start["number"]}-{i:02}.webp',number,rect,args.dpi,'source_context',cache)
            if asset:
                asset.update(reference=region.get('reference'),quality_flags=['source_rectangle_visually_reviewed'])
                assets.append(asset)
        missing=[r for r in figure_refs if r not in figure_assets]
        chapter=next(c for c in chapters if c['number']==start['chapter'])
        # The problem's own printed heading is an identity, not a dependency.
        heading_match=PROBLEM.search(text)
        if heading_match is None:
            # Leading difficulty glyphs can occupy a separate native line.
            heading_match=re.search(r'\bProblem\s+\d+\.\d+',text)
        reference_body=text[heading_match.end():]if heading_match else text
        context_pending=bool(formula_refs or re.search(r'\b(?:Ex\.|Example|Prob\.|Problem|Section|Table)\s+\d+\.',reference_body))
        if edit.get('context_recovery_complete'):context_pending=False
        questions.append({'source':{'drive_id':source['drive_id'],'revision':source['revision']},
            'source_language':'en','locator':f'chapter-{start["chapter"]}/problem-{start["number"]}',
            'original_number':start['number'],'chapter':chapter['title'],'kind':'problem',
            'subjects':['electromagnetism']+(['mathematical_methods']if start['chapter']=='1'else [])
                +(['relativity']if start['chapter']=='12'else []),
            'level':'undergraduate','review_status':'pending',
            'spans':[a['spans'][0]for a in assets if a['role']=='question_crop'],
            'assets':assets,'versions':[{'language':'en','role':'original','text':text,'review_status':'pending',
                                      'extraction_method':'native_font_and_geometry'}],
            'context':{'chapter_id':start['chapter'],'source_author':'David J. Griffiths',
                'source_figure_references':figure_refs,'source_formula_references':formula_refs,
                'source_footnote_markers':markers,'source_footnotes':linked_notes,
                'figures_separated_from_statement_crop':sorted(set(excluded_figures)),
                'source_inline_answer_present':bool(re.search(r'\bAnswer\s*:',text)
                    or edit.get('source_inline_answer_present', False)),
                'missing_figures':missing,'source_context_recovery_pending':context_pending,
                'unresolved_source':bool(missing)or context_pending,
                'boundary_reason':boundary['reason']if boundary else 'next_problem_label',
                'quality_flags':['native_math_unreviewed','crop_boundary_pending_review','footnote_association_pending_review'],
                'manual_review_notes':edit.get('review_notes',[])}})
    unknown=set(overrides.get('questions',{}))-set(q['original_number']for q in questions)
    if unknown:raise ValueError('Unknown private question overrides')
    raw={'version':1,'profile':'griffiths-em-native-font','source_sha256':digest,'questions':questions}
    audit={'source_sha256':digest,'page_count':len(document),'standalone_problem_count':len(questions),
        'chapter_counts':coverage,'expected_basis':'Consecutive standalone printed labels, with TOC chapter ownership; maximum observed identity is not a publisher-declared count.',
        'excluded_prose_references':rejected,'figure_caption_count':len(captions),'figure_asset_count':len(figure_assets),
        'figure_isolation_issues':figure_issues,'footnote_regions':len(note_assets),
        'question_crop_references':sum(a['role']=='question_crop'for q in questions for a in q['assets']),
        'asset_references':sum(len(q['assets'])for q in questions),
        'context_recovery_pending':sum(q['context']['source_context_recovery_pending']for q in questions),
        'review_status':'pending','paid_api_calls':0,'not_ready_for_publication':True}
    json_write(output/'questions.raw.json',raw)
    json_write(output/'coverage-audit.json',audit)
    json_write(output/'figure-index.json',{'source_sha256':digest,'figures':figure_assets,'issues':figure_issues})
    json_write(output/'source-label-index.json',{'source_sha256':digest,'labels':starts,'captions':captions})
    print(json.dumps({key:audit[key]for key in ('standalone_problem_count','figure_caption_count','figure_asset_count',
                                             'footnote_regions','question_crop_references','asset_references','context_recovery_pending')}))


if __name__=='__main__':
    main()
