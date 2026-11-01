"""Private exercise/problem extraction for a checked Morin manuscript edition.

Each chapter restarts numbering in Exercises and Problems. Locators preserve
both sections. Running Roman page numbers identify the alternating text margin;
explicitly referenced margin figures are stored separately from statement text.
All output remains pending visual and mathematical review. No provider calls.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image
from private_paths import private_directory

SOURCE_SHA = '35b819ce8529f7c90ac95fd50a1649084060c6b243558dc1e1e92b67ba79cd7b'


def line_text(line):
    return ''.join(span['text'] for span in line['spans']).strip()


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def extract(source, output, manifest, dpi=170, overrides_path=None):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Unexpected source edition')
    output = private_directory(output)
    overrides = json.loads(overrides_path.read_text(encoding='utf-8')) if overrides_path else {}
    if overrides and (overrides.get('version') != 1 or overrides.get('source_sha256') != SOURCE_SHA):
        raise ValueError('Private geometry overrides must match the checked source edition')
    exclusions, body_boxes = {}, {}
    for key, destination in (('exclude_body_pages', exclusions), ('body_bboxes', body_boxes)):
        for item in overrides.get(key, []):
            token = (item['locator'], item['page'])
            if item.get('source_image_checked') is not True or token in destination:
                raise ValueError('Geometry overrides require unique, visually checked locators/pages')
            destination[token] = item
    figure_boxes = overrides.get('figure_bboxes', {})
    if any(item.get('source_image_checked') is not True for item in figure_boxes.values()):
        raise ValueError('Figure geometry overrides must be visually checked')
    applied_exclusions, applied_bodies, applied_figures = set(), set(), set()
    (output / 'crops').mkdir(parents=True, exist_ok=True)
    (output / 'figures').mkdir(exist_ok=True)
    document = fitz.open(source)
    if len(document) != 623:
        raise ValueError('Unexpected page count')
    sources = json.loads(manifest.read_text(encoding='utf-8'))['sources']
    matches = [item for item in sources if item['sha256'] == SOURCE_SHA]
    if len(matches) != 1:
        raise ValueError('Source revision must be registered uniquely')
    origin = {key: matches[0][key] for key in ('drive_id', 'revision')}
    chapters = [(int(match[1]), page) for _, title, page in document.get_toc()
                if (match := re.fullmatch(r'ch(\d+)\.pdf', title))]
    if [chapter for chapter, _ in chapters] != list(range(1, 14)):
        raise ValueError('Expected the thirteen source chapters')
    lines_by_page, sections, captions, topics = {}, [], {}, []
    for index in range(13, len(document)):
        lines = [line for block in document[index].get_text('dict')['blocks'] if 'lines' in block
                 for line in block['lines']]
        lines_by_page[index] = lines
        page_captions = []
        for line in lines:
            text = line_text(line)
            if text in ('Exercises', 'Problems', 'Solutions') and any(span['size'] > 14 for span in line['spans']):
                chapter = next(number for number, start in reversed(chapters) if start <= index + 1)
                sections.append({'chapter': chapter, 'kind': text, 'page': index + 1,
                                 'bbox': list(line['bbox'])})
            caption = re.fullmatch(r'Figure\s+(\d+\.\d+)', text)
            if caption and any(span['font'].startswith('CMBX') for span in line['spans']):
                item = {'number': caption[1], 'page': index + 1, 'bbox': list(line['bbox'])}
                page_captions.append(item)
            if re.match(r'^Section\s+\d+\.\d+', text) and any('CMTI' in span['font'] for span in line['spans']):
                topics.append({'page': index + 1, 'bbox': list(line['bbox']), 'text': text})
        for position, caption in enumerate(sorted(page_captions, key=lambda item: item['bbox'][1])):
            if caption['number'] in captions:
                raise ValueError('Repeated figure label needs an explicit source override')
            side = 'left' if caption['bbox'][0] < 145 else 'right' if caption['bbox'][0] > 465 else 'inline'
            previous = [other for other in page_captions if other['bbox'][3] < caption['bbox'][1]
                        and (other['bbox'][0] < 145 if side == 'left' else other['bbox'][0] > 465)]
            caption['side'] = side
            # Margin art can extend above the running header (e.g. a loop).
            # Headers sit in the body column, outside these margin crops.
            caption['crop_top'] = max((item['bbox'][3] + 3 for item in previous), default=0)
            captions[caption['number']] = caption
    if collections.Counter(section['kind'] for section in sections) != {
            'Exercises': 13, 'Problems': 13, 'Solutions': 13}:
        raise ValueError('Exercise, problem and solution boundaries are incomplete')
    sections.sort(key=lambda item: (item['page'], item['bbox'][1]))

    def render(page_number, box, destination, role):
        page = document[page_number - 1]
        box = fitz.Rect(box) & page.rect
        pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=box, alpha=False)
        picture = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
        if picture.convert('L').point(lambda value: 255 if value < 230 else 0).getbbox() is None:
            return None
        picture.save(destination, 'WEBP', lossless=True, method=4)
        span = {'page': page_number, 'bbox': [round(box.x0 / page.rect.width, 8),
                round(box.y0 / page.rect.height, 8), round(box.x1 / page.rect.width, 8),
                round(box.y1 / page.rect.height, 8)]}
        return {'role': role, 'local_path': str(destination), 'mime_type': 'image/webp',
                'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'spans': [span]}

    def text_margin(page_number):
        running = [line for line in lines_by_page[page_number - 1]
                   if line['bbox'][1] < 72 and re.fullmatch(r'[IVX]+-\d+', line_text(line))]
        if len(running) != 1:
            raise ValueError(f'Unknown running-page text margin on PDF {page_number}')
        return 57.6 if running[0]['bbox'][0] > 300 else 151.2

    # Source footnotes have a six-point marker followed by nine-point prose.
    # Exponents in mathematical lines must not be mistaken for note starts.
    footnotes_by_page = {}
    for number in sorted({item['page'] for item in sections} | set(
            page for section in sections if section['kind'] != 'Solutions'
            for page in range(section['page'], next(
                item['page'] for item in sections if
                (item['page'], item['bbox'][1]) > (section['page'], section['bbox'][1])) + 1))):
        left = text_margin(number)
        definitions = []
        for line in lines_by_page[number - 1]:
            nonempty = [span for span in line['spans'] if span['text'].strip()]
            if not nonempty:
                continue
            marker = nonempty[0]
            if (marker['text'].isdigit() and marker['size'] < 6.1
                    and line['bbox'][1] > 300
                    and abs(marker['bbox'][2] - left - 16.5) < 2
                    and any(8.8 < span['size'] < 9.1 and re.search(r'[A-Za-z]{2}', span['text'])
                            for span in nonempty[1:])):
                definitions.append({'number': marker['text'], 'page': number,
                                    'top': line['bbox'][1] - 0.1})
        if definitions:
            footnotes_by_page[number] = sorted(definitions, key=lambda item: item['top'])

    figures, questions, coverage = {}, [], []
    for position, section in enumerate(sections):
        if section['kind'] == 'Solutions':
            continue
        end = sections[position + 1]
        labels = []
        for number in range(section['page'], end['page'] + 1):
            for line in lines_by_page[number - 1]:
                text = line_text(line)
                match = re.match(r'^(\d+)\.\s+(.+)', text)
                if not match or not any(span['font'].startswith('CMBX') and 10.8 < span['size'] < 11.1
                                        for span in line['spans']):
                    continue
                if number == section['page'] and line['bbox'][1] <= section['bbox'][3]:
                    continue
                if number == end['page'] and line['bbox'][1] >= end['bbox'][1]:
                    continue
                left = text_margin(number)
                expected_x = left + 13.3 - 5.45 * (len(match[1]) - 1)
                if abs(line['bbox'][0] - expected_x) > 3:
                    raise ValueError(f'Unexpected title position on PDF {number}, label {match[1]}: '
                                     f'{line["bbox"][0]} versus {expected_x}')
                labels.append({'number': int(match[1]), 'title': match[2].rstrip(' *'),
                               'stars': len(match[2]) - len(match[2].rstrip('*')),
                               'page': number, 'bbox': list(line['bbox'])})
        if not labels or [label['number'] for label in labels] != list(range(1, len(labels) + 1)):
            raise ValueError('Printed numbers are not consecutive within their own section')
        for item_position, label in enumerate(labels):
            following = labels[item_position + 1] if item_position + 1 < len(labels) else end
            kind = 'exercise' if section['kind'] == 'Exercises' else 'problem'
            locator = f'chapter-{section["chapter"]}/{kind}-{label["number"]}'
            basename = locator.replace('/', '-')
            parts, body = [], []
            for number in range(label['page'], following['page'] + 1):
                token = (locator, number)
                if token in exclusions:
                    applied_exclusions.add(token)
                    continue
                top = label['bbox'][1] - 2 if number == label['page'] else 72
                bottom = following['bbox'][1] - 4 if number == following['page'] else 740
                headings = [topic['bbox'][1] - 3 for topic in topics
                            if topic['page'] == number and top < topic['bbox'][1] < bottom]
                if headings:
                    bottom = min(headings)
                if number in footnotes_by_page:
                    bottom = min(bottom, footnotes_by_page[number][0]['top'] - 6)
                if bottom - top < 4:
                    continue
                left = text_margin(number)
                box = fitz.Rect(body_boxes[token]['bbox']) if token in body_boxes else fitz.Rect(
                    left - 2, top, left + 399, bottom)
                if token in body_boxes:
                    applied_bodies.add(token)
                asset = render(number, box, output / 'crops' / f'{basename}-pdf{number:03}.webp', 'question_crop')
                if asset:
                    parts.append(asset)
                    body.append(document[number - 1].get_text('text', clip=box).strip())
            if not parts:
                raise ValueError('Empty question')
            text = '\n\n'.join(body)
            refs = sorted(set(re.findall(r'(?:Fig(?:ure)?s?\.?\s*)(\d+\.\d+)', text)))
            missing = []
            for reference in refs:
                caption = captions.get(reference)
                override = figure_boxes.get(reference)
                if not override and (not caption or caption['side'] == 'inline'):
                    missing.append(reference)
                    continue
                if reference not in figures:
                    if override:
                        figure_page, figure_box = override['page'], override['bbox']
                        applied_figures.add(reference)
                    else:
                        x0, x1 = (0, 145) if caption['side'] == 'left' else (465, 612)
                        figure_page = caption['page']
                        figure_box = [x0, caption['crop_top'], x1, caption['bbox'][3] + 3]
                    figures[reference] = render(figure_page, figure_box,
                        output / 'figures' / f'figure-{reference}.webp', 'figure')
                    if figures[reference] is None:
                        raise ValueError('A referenced figure cannot be blank')
                parts.append(figures[reference])
            topics_before = [topic for topic in topics if
                             (topic['page'], topic['bbox'][1]) < (label['page'], label['bbox'][1])]
            cross_refs = re.findall(r'\b(?:Problem|Exercise|Claim)\s+\d+(?:\.\d+)?', text)
            subjects = ['relativity'] if section['chapter'] >= 10 else ['classical_mechanics']
            if section['chapter'] == 3:
                subjects.append('oscillations_waves')
            questions.append({'source': origin, 'source_language': 'en', 'locator': locator,
                'original_number': str(label['number']), 'chapter': str(section['chapter']),
                'kind': kind, 'subjects': subjects, 'level': 'undergraduate', 'review_status': 'pending',
                'spans': [asset['spans'][0] for asset in parts if asset['role'] == 'question_crop'],
                'assets': parts, 'versions': [{'language': 'en', 'role': 'original',
                                              'text': text, 'review_status': 'pending'}],
                'context': {'title_en': label['title'], 'printed_section': section['kind'],
                    'difficulty_source_asterisks': label['stars'],
                    'topic_heading': topics_before[-1]['text'] if topics_before else None,
                    'source_figure_references': refs, 'missing_figure_isolation': missing,
                    'cross_question_references': cross_refs,
                    'unresolved_source': bool(missing or cross_refs),
                    'quality_flags': ['native_math_transcription_unreviewed',
                                      'margin_figure_boundaries_need_visual_review']}})
        coverage.append({'chapter': section['chapter'], 'section': section['kind'], 'count': len(labels),
                         'pdf_pages': [section['page'], end['page']], 'numbers_consecutive': True})
    if len(questions) != 496:
        raise ValueError('Expected all 496 independently inventoried section labels')
    if (set(exclusions) != applied_exclusions or set(body_boxes) != applied_bodies
            or set(figure_boxes) != applied_figures):
        raise ValueError('Some private geometry overrides did not match extracted source content')
    footnote_audit = []
    for number, definitions in footnotes_by_page.items():
        page = document[number - 1]
        left = text_margin(number)
        for index, definition in enumerate(definitions):
            candidates = []
            for line in lines_by_page[number - 1]:
                if line['bbox'][1] >= definitions[0]['top'] - 3:
                    continue
                for marker in line['spans']:
                    if (marker['text'].strip() != definition['number']
                            or not 7.8 < marker['size'] < 8.1):
                        continue
                    baseline = max((span['origin'][1] for span in line['spans']
                                    if span['size'] > 10), default=marker['origin'][1])
                    for question in questions:
                        if any(span['page'] == number
                               and span['bbox'][0] * page.rect.width <= marker['bbox'][0]
                               <= span['bbox'][2] * page.rect.width
                               and span['bbox'][1] * page.rect.height <= baseline
                               <= span['bbox'][3] * page.rect.height
                               for span in question['spans']):
                            score = sum(len(re.findall(r'[A-Za-z]{3,}', span['text']))
                                        for span in line['spans'] if span['size'] > 10
                                        and span['font'].startswith('CMR'))
                            candidates.append((score, question['locator']))
            owners = sorted({locator for score, locator in candidates
                             if score == max((item[0] for item in candidates), default=-1)})
            record = {**definition, 'candidate_owners': owners}
            if not owners:
                record['status'] = 'outside_question_body_excluded'
                footnote_audit.append(record)
                continue
            if len(owners) != 1:
                raise ValueError(f'Ambiguous source footnote owner: {record}')
            owner = next(question for question in questions if question['locator'] == owners[0])
            bottom = definitions[index + 1]['top'] if index + 1 < len(definitions) else 740
            box = [left - 2, definition['top'], left + 399, bottom]
            asset = render(number, box, output / 'crops' /
                           f'{owner["locator"].replace("/", "-")}-pdf{number:03}-fn{definition["number"]}.webp',
                           'source_footnote')
            if asset is None:
                raise ValueError(f'Empty source footnote: {record}')
            owner['assets'].append(asset)
            owner['context'].setdefault('source_footnotes', []).append(
                {'number': definition['number'], 'page': number, 'association': 'superscript_in_body'})
            text = page.get_text('text', clip=fitz.Rect(box)).strip()
            owner['versions'][0]['text'] += f'\n\n[Source footnote {definition["number"]}]\n{text}'
            record.update(status='attached', owner=owner['locator'], sha256=asset['sha256'])
            footnote_audit.append(record)
    raw = {'version': 1, 'source_sha256': SOURCE_SHA, 'questions': questions}
    atomic_json(output / 'questions.raw.json', raw)
    audit = {'source_sha256': SOURCE_SHA, 'question_count': len(questions), 'coverage': coverage,
             'asset_references': sum(len(question['assets']) for question in questions),
             'isolated_figures': len(figures), 'questions_with_context_pending': sum(
                 question['context']['unresolved_source'] for question in questions),
             'review_status': 'pending', 'paid_api_calls': 0}
    audit['source_footnotes_attached'] = sum(item['status'] == 'attached' for item in footnote_audit)
    atomic_json(output / 'coverage-audit.json', audit)
    atomic_json(output / 'footnote-audit.json', footnote_audit)
    if overrides_path:
        atomic_json(output / 'geometry-override-audit.json', {
            'source_sha256': SOURCE_SHA, 'overrides_path': str(overrides_path),
            'excluded_body_pages': [exclusions[key] for key in sorted(applied_exclusions)],
            'adjusted_body_boxes': [body_boxes[key] for key in sorted(applied_bodies)],
            'adjusted_figures': {key: figure_boxes[key] for key in sorted(applied_figures)},
            'all_overrides_applied': True, 'paid_api_calls': 0})
    document.close()
    print(json.dumps({key: audit[key] for key in ('question_count', 'asset_references', 'isolated_figures', 'paid_api_calls')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--dpi', type=int, default=170)
    parser.add_argument('--overrides', type=Path)
    args = parser.parse_args()
    extract(args.source, args.output, args.manifest, args.dpi, args.overrides)
