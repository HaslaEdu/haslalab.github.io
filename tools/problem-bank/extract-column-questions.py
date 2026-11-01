"""Crop privately profiled column exercises with source-bound OCR text.

Number inventories and exceptional page bounds must be reviewed separately.
No model service, translation or publication is performed by this extractor.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path

import pymupdf
from PIL import Image
from private_paths import private_directory


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def point(header):
    return header['page'], header['column'], header['bbox'][1]


def chapter_key(chapter):
    if isinstance(chapter,int) and not isinstance(chapter,bool) and chapter > 0:
        return f'{chapter:02}'
    if isinstance(chapter,str) and len(chapter) == 1 and 'A' <= chapter <= 'Z':
        return chapter.lower()
    raise ValueError('Chapter identity must be a positive integer or appendix letter')


def native_words(page):
    return [{'text':word[4], 'line':(word[5],word[6]), 'bbox':list(word[:4])}
            for word in page.get_text('words')]


def crop_scale(rect, dpi, maximum_side):
    if maximum_side != 0 and not 512 <= maximum_side <= 6000:
        raise ValueError('Crop render cap must be zero or between 512 and 6000 pixels')
    scale = dpi/72
    return min(scale,maximum_side/max(rect.width,rect.height)) if maximum_side else scale


def section_stop(section, profile):
    page = section['last_page']
    columns = profile['page_statement_columns'][str(page)]
    if not columns:
        raise ValueError('Final source page has no statement column')
    return {'page':page, 'column':len(columns)-1,
            'y':section.get('last_body_bottom', profile['body_bottom'])}


def reviewed_stop(locator, start, natural_stop, profile):
    override = profile.get('question_end_overrides',{}).get(locator)
    if override is None:
        return natural_stop
    if override.get('source_image_checked') is not True or not override.get('review_note'):
        raise ValueError('Question end override requires source-image review')
    point_end = (override['page'],override['column'],override['y'])
    if not point(start) < point_end <= (natural_stop['page'],natural_stop['column'],natural_stop['y']):
        raise ValueError('Question end override escapes its source interval')
    return override


def reviewed_regions(locator, selected, profile):
    override = profile.get('question_region_overrides',{}).get(locator)
    if override is None:
        return selected
    if override.get('source_image_checked') is not True or not override.get('review_note'):
        raise ValueError('Primary region override requires source-image review')
    originals = {(r['page'],r['column']):r for r in selected}
    replacement, used = override['regions'], set()
    if not replacement:
        raise ValueError('Primary region override cannot remove the entire question')
    for region in replacement:
        cell = (region['page'],region['column'])
        original = originals.get(cell)
        if original is None or cell in used:
            raise ValueError('Primary region override must retain unique original source cells')
        used.add(cell)
        old, new = original['bbox_points'], region['bbox_points']
        if (len(new) != 4 or not old[0] <= new[0] < new[2] <= old[2]
                or not old[1] <= new[1] < new[3] <= old[3]):
            raise ValueError('Primary region override escapes its original source bounds')
    if [(r['page'],r['column']) for r in replacement] != sorted(used):
        raise ValueError('Primary region overrides must preserve source reading order')
    return replacement


def regions(start, stop, section, profile):
    result = []
    for page in range(start['page'], stop['page'] + 1):
        for column, bounds in enumerate(profile['page_statement_columns'][str(page)]):
            cell = (page, column)
            if cell < point(start)[:2] or cell > (stop['page'], stop['column']):
                continue
            page_top = profile.get('page_body_top',{}).get(str(page),profile['body_top'])
            top = (start['bbox'][1] - 4 if cell == point(start)[:2] else
                   section['first_body_top'] if page == section['first_page'] else page_top)
            page_bottom = profile.get('page_body_bottom', {}).get(str(page), profile['body_bottom'])
            bottom = min(stop['y'],page_bottom) if cell == (stop['page'], stop['column']) else page_bottom
            if bottom > top + 2:
                result.append({'page': page, 'column': column,
                               'bbox_points': [bounds[0], top, bounds[1], bottom]})
    return result


def words(record, source_hash, page, size, language):
    if (record.get('source_sha256') != source_hash or record.get('page') != page
            or record.get('engine') != 'tesseract-local' or record.get('language') != language):
        raise ValueError('Source OCR identity/language mismatch')
    if (len(record.get('page_size_pt', [])) != 2
            or any(abs(a-b) > .01 for a,b in zip(record['page_size_pt'], size))):
        raise ValueError('Source OCR page geometry mismatch')
    fields = ['level','page_num','block_num','par_num','line_num','word_num',
              'left','top','width','height','conf','text']
    pixels = record['render_size_px']
    if len(pixels) != 2 or not all(isinstance(value,int) and value>0 for value in pixels):
        raise ValueError('Source OCR render geometry mismatch')
    result = []
    for word in csv.DictReader(io.StringIO(record['tsv']), delimiter='\t', quoting=csv.QUOTE_NONE,
                               fieldnames=None if record['tsv'].startswith('level\t') else fields):
        if word['level'] != '5' or not word.get('text', '').strip():
            continue
        x, y, width, height = [int(word[key]) for key in ['left','top','width','height']]
        if not (0 <= x < x+width <= pixels[0] and 0 <= y < y+height <= pixels[1]):
            raise ValueError('Source OCR word escapes its rendered page')
        result.append({'text':word['text'], 'line':tuple(word[key] for key in ['block_num','par_num','line_num']),
                       'bbox':[x*size[0]/pixels[0], y*size[1]/pixels[1],
                               (x+width)*size[0]/pixels[0], (y+height)*size[1]/pixels[1]]})
    return result


def text_in(box, page_words):
    groups = collections.defaultdict(list)
    for word in page_words:
        x0,y0,x1,y1 = word['bbox']
        if box[0] <= (x0+x1)/2 <= box[2] and box[1] <= (y0+y1)/2 <= box[3]:
            groups[word['line']].append(word)
    lines = sorted(groups.values(), key=lambda group:min(word['bbox'][1] for word in group))
    return '\n'.join(' '.join(word['text'] for word in sorted(group,key=lambda word:word['bbox'][0]))
                     for group in lines)


def extract(args):
    output = private_directory(args.out)
    profile, inventory = read(args.profile), read(args.headers)
    source_hash = digest(args.pdf)
    if (source_hash != profile['source_sha256'] or inventory['source_sha256'] != source_hash
            or inventory.get('errors') or len(inventory['headers']) != profile['expected_question_count']):
        raise ValueError('Profile/header identity or coverage mismatch')
    source = next(s for s in read(args.manifest)['sources'] if s['drive_id'] == profile['drive_id'])
    if source['sha256'] != source_hash:
        raise ValueError('Registered source revision mismatch')
    document = pymupdf.open(args.pdf)
    maximum_side = getattr(args,'max_render_side',0)
    crop_scale(document[0].rect,args.dpi,maximum_side)
    if len(document) != profile['page_count'] or not 96 <= args.dpi <= 180:
        raise ValueError('Unexpected page count or crop scale')
    images = output / 'crops'
    images.mkdir(exist_ok=True)
    cache = {}
    if args.reuse_matching_crops and (output/'crop-audit.json').is_file():
        old = read(output/'crop-audit.json')
        if (old['source_sha256'] == source_hash and old['dpi'] == args.dpi
                and old.get('max_render_side',0) == maximum_side):
            cache = {entry['path']:entry for entry in old['assets']}
    page_words, audits, questions = {}, [], []
    language = profile['source_language']
    text_method = profile.get('source_text_method','local_ocr')
    if text_method not in ('local_ocr','native'):
        raise ValueError('Unknown source text extraction method')
    for section in profile['sections']:
        headers = sorted((h for h in inventory['headers'] if h['chapter'] == section['chapter']), key=point)
        if [h['number'] for h in headers] != list(range(1, section['expected_count']+1)):
            raise ValueError('Source header sequence is incomplete or duplicated')
        for index, start in enumerate(headers):
            key = chapter_key(section['chapter'])
            locator = f"chapter-{key}/problem-{start['number']:02}"
            stop = ({'page':headers[index+1]['page'], 'column':headers[index+1]['column'],
                     'y':headers[index+1]['bbox'][1]-4} if index+1<len(headers) else
                    section_stop(section,profile))
            stop = reviewed_stop(locator,start,stop,profile)
            selected = reviewed_regions(locator,regions(start,stop,section,profile),profile)
            if not selected:
                raise ValueError('Source question has no canonical regions')
            assets, spans, texts = [], [], []
            extras = profile.get('question_context_regions', {}).get(locator, [])
            for asset_index, region in enumerate(selected+extras, 1):
                page = document[region['page']-1]
                box = pymupdf.Rect(region['bbox_points'])
                if box.is_empty or not page.rect.contains(box):
                    raise ValueError('Question crop escapes source page bounds')
                auxiliary = asset_index > len(selected)
                if auxiliary and region.get('source_image_checked') is not True:
                    raise ValueError('Auxiliary source contexts require explicit source-image review')
                path = images/f"chapter-{key}-problem-{start['number']:02}-{asset_index:02}.webp"
                prior = cache.get(str(path))
                if not (prior and prior['region'] == region and path.is_file() and digest(path) == prior['sha256']):
                    scale = crop_scale(box,args.dpi,maximum_side)
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),clip=box,alpha=False)
                    Image.frombytes('RGB',(pix.width,pix.height),pix.samples).save(path,'WEBP',lossless=True,method=4)
                checksum = digest(path)
                span = {'page':region['page'],'bbox':[box.x0/page.rect.width,box.y0/page.rect.height,
                                                     box.x1/page.rect.width,box.y1/page.rect.height]}
                role = region.get('role','source_context') if auxiliary else 'question_crop'
                asset = {'role':role,'local_path':str(path),'sha256':checksum,
                         'mime_type':'image/webp','spans':[span]}
                for field in ['figure_label','quality_flags']:
                    if auxiliary and field in region:
                        asset[field] = region[field]
                assets.append(asset)
                audits.append({'path':str(path),'region':region,'sha256':checksum,'locator':locator})
                if not auxiliary:
                    spans.append(span)
                    if region['page'] not in page_words:
                        if text_method == 'native':
                            page_words[region['page']] = native_words(page)
                        else:
                            record = read(Path(profile['source_ocr_directory'])/f"page-{region['page']:05}.json")
                            page_words[region['page']] = words(record,source_hash,region['page'],
                                [page.rect.width,page.rect.height],{'ko':'kor','en':'eng'}[language])
                    texts.append(text_in(list(box),page_words[region['page']]))
            original_number = str(start.get('original_number',start['number']))
            context = {'source_author':profile['source_author'],
                    'source_primary_regions':spans,'number_origin':start['origin'],
                    'quality_flags':[text_method+'_math_unverified','source_reference_context_requires_review'],
                    'unresolved_source':False,'source_image_checked':False}
            if locator in profile.get('question_region_overrides',{}):
                context['primary_region_review_note'] = profile['question_region_overrides'][locator]['review_note']
            for key in ['title_ko','title_en']:
                if section.get(key):
                    context['chapter_'+key] = section[key]
            if section.get('source_unit_system'):
                context['source_unit_system'] = section['source_unit_system']
                context['unit_system_provenance'] = section.get('unit_system_provenance')
            for field in ['source_section_kind','source_difficulty_stars','source_title']:
                if field in start:
                    context[field] = start[field]
            questions.append({'source':{key:source[key] for key in ['drive_id','revision']},
                'source_language':language,'locator':locator,'original_number':original_number,
                'chapter':str(section['chapter']),'kind':start.get('kind','problem'),
                'subjects':section.get('subjects',profile['subjects']),
                'level':profile['level'],'spans':spans,'assets':assets,'review_status':'pending',
                'versions':[{'language':language,'role':'original','text':original_number+'\n\n'+'\n\n'.join(texts),
                             'review_status':'pending','extraction_method':text_method+'_with_canonical_source_crops'}],
                'context':context})
        print(json.dumps({'chapter':section['chapter'],'questions':len(headers)}),flush=True)
    if len(questions) != profile['expected_question_count']:
        raise ValueError('Profile total disagrees with extracted questions')
    save(output/'questions.raw.json',{'version':1,'source_sha256':source_hash,'questions':questions,'paid_api_calls':0})
    save(output/'crop-audit.json',{'source_sha256':source_hash,'dpi':args.dpi,
                                 'max_render_side':maximum_side,'assets':audits})
    save(output/'coverage-audit.json',{'source_sha256':source_hash,'found_question_count':len(questions),
         'asset_count':len(audits),'source_geometry_review_complete':False,'publication_ready':False,'paid_api_calls':0})
    print(json.dumps({'questions':len(questions),'assets':len(audits),'publication_ready':False}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ['pdf','manifest','profile','headers','out']:
        parser.add_argument('--'+field,type=Path,required=True)
    parser.add_argument('--dpi',type=int,default=160)
    parser.add_argument('--max-render-side',type=int,default=0,
                        help='Cap crop render dimensions for oversized scanned page boxes')
    parser.add_argument('--reuse-matching-crops',action='store_true')
    extract(parser.parse_args())
