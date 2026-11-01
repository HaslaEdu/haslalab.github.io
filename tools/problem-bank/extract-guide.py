"""Source-image extraction for user-supplied A Guide to Physics Problems PDFs.

Keep question content outside the public checkout. No OCR or translation API
calls are made. The book's text layer omits mathematical expressions, so crops
remain canonical and extracted text is explicitly incomplete until reviewed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image
from private_paths import private_directory


def number_key(value):
    return tuple(map(int, value.split('.')))


def normalized_page_text(text):
    return '\n'.join(line.strip() for line in text.splitlines()
                     if line.strip() and line.strip().casefold() != 'tlfebook').strip()


def split_provenance(text):
    result, start, depth = [], 0, 0
    for index, char in enumerate(text):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char in ',;' and depth == 0:
            result.append(text[start:index].strip())
            start = index + 1
    result.append(text[start:].strip())
    return [item for item in result if item]


def heading_at(page, label):
    spans = [span for block in page.get_text('dict')['blocks'] if 'lines' in block
             for line in block['lines'] for span in line['spans']]
    candidates = [span for span in spans if span['bbox'][1] >= label['bbox'][1] - 6
                  and span['bbox'][1] < label['bbox'][1] + 85]
    body_ys = [span['bbox'][1] for span in candidates
               if 8.5 < span['size'] < 11.5 and span['bbox'][1] > label['bbox'][1] + 9
               and span['text'].strip()]
    end = min(body_ys) if body_ys else label['bbox'][3] + 2
    title_spans = [span for span in candidates if 11.5 <= span['size'] < 14.5
                   and span['bbox'][1] < end
                   and not (span['bbox'][0] < label['bbox'][2] + 1
                            and span['bbox'][2] <= label['bbox'][2] + 1)]
    # Font metrics give adjacent fragments slightly different top coordinates.
    # Group the visual line before sorting left-to-right, including its label.
    title_spans.sort(key=lambda span: span['bbox'][1])
    lines = []
    for span in title_spans:
        if not lines or span['bbox'][1] - lines[-1][0]['bbox'][1] > 3:
            lines.append([span])
        else:
            lines[-1].append(span)
    title_spans = [span for line in lines for span in sorted(line, key=lambda item: item['bbox'][0])]
    line_texts = []
    for line in lines:
        fragments, previous = [], None
        for span in sorted(line, key=lambda item:item['bbox'][0]):
            if previous and span['bbox'][0] - previous['bbox'][2] > 1.5 and not previous['text'].endswith(' ') and not span['text'].startswith(' '):
                fragments.append(' ')
            fragments.append(span['text'])
            previous = span
        line_texts.append(''.join(fragments).strip())
    text = ' '.join(line_texts)
    text = re.sub(r'\s+', ' ', text).strip()
    label_pattern = r'\s*'.join(re.escape(char) for char in label['number'])
    text = re.sub(r'^' + label_pattern + r'\s*', '', text)
    text = re.sub(r'\s*-\s*', '-', text)
    # Some headings attribute different named subproblems separately.
    title_parts, provenance_parts, depth, start = [], [], 0, 0
    for index, char in enumerate(text):
        if char == '(':
            if depth == 0:
                title_parts.append(text[start:index])
                start = index + 1
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                provenance_parts.append(text[start:index])
                start = index + 1
    title_parts.append(text[start:])
    title = re.sub(r'\s+', ' ', ' '.join(title_parts)).strip()
    provenance = '; '.join(provenance_parts)
    top = min([label['bbox'][1]] + [span['bbox'][1] for span in title_spans])
    return title, provenance, end, top


def extract(arguments):
    source = arguments.source.resolve()
    output = private_directory(arguments.output)
    image_directory = output / 'images'
    image_directory.mkdir(exist_ok=True)
    document = fitz.open(source)
    texts = [page.get_text() for page in document]
    problem_divider = next(index for index, text in enumerate(texts)
                           if normalized_page_text(text) == 'PROBLEMS')
    solution_divider = next(index for index, text in enumerate(texts)
                            if index > problem_divider and normalized_page_text(text) == 'SOLUTIONS')
    first_page = arguments.first_page - 1 if arguments.first_page else problem_divider + 1
    last_page = arguments.last_page - 1 if arguments.last_page else solution_divider - 1
    toc = '\n'.join(texts[:problem_divider])
    start = re.search(r'PART\s+I\s*:\s*PROBLEMS', toc, re.I)
    if start:
        toc = toc[start.end():]
        toc = re.split(r'PART\s+II\s*:\s*SOLUTIONS', toc, flags=re.I)[0]
    toc_numbers = sorted(set(re.findall(r'(?<!\d)([1-9]\.\d{1,3})\.', toc)), key=number_key)
    labels = []
    for page_index in range(first_page, last_page + 1):
        for word in document[page_index].get_text('words'):
            if re.fullmatch(r'[1-9]\.\d{1,3}', word[4]) and 49 <= word[0] <= 60 and word[7] == 0:
                labels.append({'number': word[4], 'page_index': page_index, 'bbox': list(word[:4])})
    labels.sort(key=lambda label: (label['page_index'], label['bbox'][1]))
    numbers = [label['number'] for label in labels]
    duplicates = [number for number, count in collections.Counter(numbers).items() if count > 1]
    if duplicates or set(numbers) != set(toc_numbers) or numbers != sorted(numbers, key=number_key):
        raise ValueError('Question sequence failed TOC comparison: ' + str({
            'duplicates': duplicates, 'missing': sorted(set(toc_numbers) - set(numbers), key=number_key),
            'extra': sorted(set(numbers) - set(toc_numbers), key=number_key)}))
    part = arguments.part
    chapter_subjects = ({1: 'classical_mechanics', 2: 'relativity', 3: 'electromagnetism'}
                        if part == 1 else {4: 'thermodynamics_statistical_physics', 5: 'quantum_mechanics'})
    chapter_titles = {}
    sections = []
    for page_index in range(first_page, last_page + 1):
        spans = [span for block in document[page_index].get_text('dict')['blocks'] if 'lines' in block
                 for line in block['lines'] for span in line['spans']]
        candidates = sorted([span for span in spans if 14 <= span['size'] < 20 and span['text'].strip()],
                            key=lambda span: (span['bbox'][1], span['bbox'][0]))
        for span in candidates:
            if sections and sections[-1]['page_index'] == page_index and abs(sections[-1]['bbox'][1] - span['bbox'][1]) < 3:
                sections[-1]['text'] += ' ' + span['text'].strip()
                sections[-1]['bbox'][2] = max(sections[-1]['bbox'][2], span['bbox'][2])
            else:
                sections.append({'page_index': page_index, 'bbox': list(span['bbox']), 'text': span['text'].strip()})
    for label in labels:
        chapter = number_key(label['number'])[0]
        if chapter not in chapter_titles:
            spans = [span for block in document[label['page_index']].get_text('dict')['blocks'] if 'lines' in block
                     for line in block['lines'] for span in line['spans']
                     if 24 < span['size'] and span['bbox'][0] < 100 and span['bbox'][1] < label['bbox'][1] - 3]
            chapter_titles[chapter] = ' '.join(span['text'].strip() for span in sorted(spans, key=lambda s:s['bbox'][1])).strip()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    opening_pages = {next(label['page_index'] for label in labels
                          if number_key(label['number'])[0] == chapter)
                     for chapter in chapter_titles}
    overrides = (json.loads(arguments.metadata_overrides.read_text(encoding='utf-8'))
                 if arguments.metadata_overrides else {})
    heading_information = {label['number']:heading_at(document[label['page_index']], label) for label in labels}
    records = []
    for position, label in enumerate(labels):
        next_label = labels[position + 1] if position + 1 < len(labels) else {
            'number': '', 'page_index': last_page + 1, 'bbox': [0, 53, 0, 53]}
        changed_chapter = bool(next_label['number']) and number_key(next_label['number'])[0] != number_key(label['number'])[0]
        end_page = next_label['page_index'] - int(changed_chapter)
        title, provenance, heading_end, heading_top = heading_information[label['number']]
        segments = []
        for page_index in range(label['page_index'], min(end_page, last_page) + 1):
            if normalized_page_text(texts[page_index]).casefold() == 'this page intentionally left blank':
                continue
            top = max(53, heading_top - 2) if page_index == label['page_index'] else 53
            # Only chapter-opening pages have a centered footer number. Regular
            # pages can contain text/equation descenders below 559 points.
            body_bottom = 555 if page_index in opening_pages else 580
            next_top = heading_information[next_label['number']][3] if next_label['number'] else next_label['bbox'][1]
            bottom = min(body_bottom, next_top - 4) if page_index == next_label['page_index'] else body_bottom
            for section in sections:
                if section['page_index'] == page_index and section['bbox'][3] > top:
                    bottom = min(bottom, section['bbox'][1] - 4)
            if bottom - top < 10:
                continue
            box = fitz.Rect(45, top, min(390, document[page_index].rect.width - 20), bottom)
            pix = document[page_index].get_pixmap(matrix=fitz.Matrix(arguments.dpi / 72, arguments.dpi / 72),
                                                 clip=box, alpha=False)
            name = label['number'].replace('.', '-') + f'-pdf{page_index + 1:03}.webp'
            path = image_directory / name
            Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(path, 'WEBP', quality=93, method=5)
            text = document[page_index].get_text(clip=box).strip()
            segments.append({'pdf_page': page_index + 1, 'bbox_pt': [round(value, 3) for value in box],
                             'image': 'images/' + name, 'image_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'image_size_px': [pix.width, pix.height], 'text_ocr_raw': text})
        chapter = number_key(label['number'])[0]
        raw = '\n\n'.join(segment['text_ocr_raw'] for segment in segments)
        records.append({'id': f'guide-part{part}:{label["number"]}', 'original_number': label['number'],
                        'chapter': chapter, 'chapter_title_en': chapter_titles.get(chapter, ''),
                        'title_en': title, 'institution_provenance_text': provenance,
                        'institutions_source': split_provenance(provenance),
                        'heading_source': {'pdf_page': label['page_index'] + 1, 'bbox_pt': label['bbox'],
                                           'body_starts_y_pt': heading_end, 'visual_top_y_pt':heading_top},
                        'subjects': [chapter_subjects.get(chapter, 'unclassified')],
                        'level_source': 'graduate_qualifying_exam_collection',
                        'statement_segments': segments, 'text_en_ocr_raw': raw,
                        'canonical_representation': 'source_statement_images', 'review_status': 'pending',
                        'translation_status': {'en': 'text_layer_math_incomplete', 'ko': 'not_started'},
                        'flags': ['math_text_layer_incomplete', 'equations_and_diagrams_preserved_in_crops']
                                 + (['multi_page_question'] if len(segments) > 1 else [])})
        records[-1].update(overrides.get(label['number'], {}))
        prior_sections = [section for section in sections
                          if (section['page_index'], section['bbox'][1]) < (label['page_index'], label['bbox'][1])]
        if prior_sections:
            section = prior_sections[-1]
            records[-1]['section_title_en'] = section['text']
            records[-1]['section_heading_source'] = {'pdf_page':section['page_index'] + 1, 'bbox_pt':section['bbox']}
    result = {'schema_version': 1, 'visibility': 'private', 'source_id': arguments.source_id or source.stem,
              'source_revision': arguments.revision, 'title': f'A Guide to Physics Problems Part {part}',
              'source_filename': source.name, 'source_sha256': source_hash, 'source_page_count': len(document),
              'statement_pdf_pages': [labels[0]['page_index'] + 1, last_page + 1],
              'solution_divider_pdf_page': solution_divider + 1, 'review_status': 'pending',
              'question_count': len(records), 'questions': records}
    (output / 'questions-raw.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    audit = {'source_sha256': source_hash, 'toc_expected_count': len(toc_numbers), 'question_count': len(records),
             'expected_numbers': toc_numbers, 'found_numbers': numbers, 'missing': [], 'duplicates': duplicates,
             'chapter_counts': dict(collections.Counter(str(record['chapter']) for record in records)),
             'statement_pdf_pages': result['statement_pdf_pages'], 'solution_divider_pdf_page': solution_divider + 1,
             'missing_title': [record['original_number'] for record in records if not record['title_en']],
             'missing_provenance': [record['original_number'] for record in records if not record['institution_provenance_text']],
             'image_count': sum(len(record['statement_segments']) for record in records),
             'limitations': ['The PDF text layer omits mathematical expressions; source crops are authoritative.',
                             'All statements, provenance and translations remain pending independent review.',
                             'New chapter title pages are excluded from the preceding question.',
                             'The worked-solutions part is excluded; inline hints printed with statements are preserved.']}
    (output / 'coverage-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: audit[key] for key in ['toc_expected_count', 'question_count', 'chapter_counts',
                                               'missing_title', 'missing_provenance', 'image_count']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-id')
    parser.add_argument('--revision')
    parser.add_argument('--part', type=int, choices=[1, 2], default=1)
    parser.add_argument('--first-page', type=int)
    parser.add_argument('--last-page', type=int)
    parser.add_argument('--dpi', type=int, default=170)
    parser.add_argument('--metadata-overrides', type=Path,
                        help='Private source-image-reviewed metadata corrections, never book text in this script.')
    extract(parser.parse_args())
