"""Private two-column exercise extraction for a checked thermal-physics edition.

Worked examples and biographies are excluded. Text and math remain unreviewed;
source figure/equation references are recorded for separate context recovery.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image
from private_paths import private_directory

SOURCE_SHA = '9f8fcf9666bf41e47b484ea32f958958b00ad55b9f79068ab5bc0b47d5c71d30'
LABEL = re.compile(r'\((\d+)\.(\d+)\)$')


def text_lines(page):
    return [line for block in page.get_text('dict')['blocks'] if 'lines' in block
            for line in block['lines']]


def line_text(line):
    return ''.join(span['text'] for span in line['spans']).strip()


def extract(source, output, manifest, dpi=170):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Unexpected PDF edition')
    output = private_directory(output)
    images = output / 'images'
    images.mkdir(parents=True, exist_ok=True)
    fitz.TOOLS.mupdf_display_errors(False)
    document = fitz.open(source)
    if len(document) != 512:
        raise ValueError('Unexpected page count')
    sources = json.loads(manifest.read_text(encoding='utf-8'))['sources']
    matches = [item for item in sources if item['sha256'] == SOURCE_SHA]
    if len(matches) != 1:
        raise ValueError('Source revision must be uniquely registered')
    origin = {key: matches[0][key] for key in ('drive_id', 'revision')}
    chapters, exercises = [], []
    for level, title, page in document.get_toc():
        chapter = re.match(r'^(\d+) (.+)$', title)
        if level == 2 and chapter:
            chapters.append({'number': int(chapter[1]), 'title': chapter[2], 'start': page})
        elif title == 'Exercises':
            if not chapters:
                raise ValueError('Exercise section has no chapter')
            exercises.append({**chapters[-1], 'exercise_start': page})
    if [item['number'] for item in exercises] != list(range(1, 38)):
        raise ValueError('Expected all 37 chapter exercise sections')

    questions, audits = [], []

    def segment(number, page_index, column, top, bottom, suffix=''):
        if bottom - top < 4:
            return None
        # Column edges lie in the actual gutter; equations must remain complete.
        left, right = (29, 268) if column == 0 else (268, 509)
        box, page = fitz.Rect(left, top, right, bottom), document[page_index]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=box, alpha=False)
        picture = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
        if picture.convert('L').point(lambda value: 255 if value < 230 else 0).getbbox() is None:
            return None
        filename = f'{number}-pdf{page_index + 1:03}-col{column + 1}{suffix}.webp'
        path = images / filename
        picture.save(path, 'WEBP', lossless=True, method=4)
        span = {'page': page_index + 1, 'bbox': [round(box.x0 / page.rect.width, 8),
                round(box.y0 / page.rect.height, 8), round(box.x1 / page.rect.width, 8),
                round(box.y1 / page.rect.height, 8)]}
        return {'asset': {'role': 'question_crop', 'local_path': str(path),
                         'mime_type': 'image/webp', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'spans': [span]}, 'text': page.get_text('text', clip=box).strip()}

    for chapter in exercises:
        first = chapter['exercise_start'] - 1
        page_indices = [first]
        for following in range(first + 1, len(document)):
            headers = [line_text(line) for line in text_lines(document[following]) if line['bbox'][1] < 48]
            if 'Exercises' not in headers:
                break
            page_indices.append(following)
        heading = [line for line in text_lines(document[first])
                   if line_text(line) == 'Exercises' and line['bbox'][1] > 48]
        if len(heading) != 1:
            raise ValueError('Expected one body exercise-section heading')
        labels = []
        for index in page_indices:
            for word in document[index].get_text('words'):
                match = LABEL.fullmatch(word[4])
                if (match and int(match[1]) == chapter['number'] and word[7] == 0
                        and ((30 < word[0] < 40) or (268 < word[0] < 279))
                        and word[1] > (heading[0]['bbox'][3] if index == first else 48)):
                    labels.append({'number': int(match[2]), 'page_index': index,
                                   'column': int(word[0] > 200), 'bbox': list(word[:4])})
        labels.sort(key=lambda label: (label['page_index'], label['column'], label['bbox'][1]))
        if not labels or [label['number'] for label in labels] != list(range(1, len(labels) + 1)):
            raise ValueError(f'Nonconsecutive chapter {chapter["number"]} printed labels')
        for position, label in enumerate(labels):
            following = labels[position + 1] if position + 1 < len(labels) else {
                'page_index': page_indices[-1] + 1, 'column': 0, 'bbox': [0, 60, 0, 60]}
            regions = []
            start_slot, end_slot = 2 * label['page_index'] + label['column'], 2 * following['page_index'] + following['column']
            number = f'{chapter["number"]}.{label["number"]}'
            for slot in range(start_slot, min(end_slot, 2 * (page_indices[-1] + 1)) + 1):
                index, column = divmod(slot, 2)
                if index > page_indices[-1]:
                    break
                top = label['bbox'][1] - 2 if slot == start_slot else (
                    heading[0]['bbox'][3] + 3 if index == first else 62)
                bottom = following['bbox'][1] - 3 if slot == end_slot else 680
                part = segment(number, index, column, top, bottom)
                if part:
                    regions.append(part)
            if not regions:
                raise ValueError('Empty question')
            body = '\n\n'.join(region['text'] for region in regions)
            figure_refs = sorted(set(re.findall(r'(?:Fig(?:ure)?\.?\s+)([\dA-C]+\.\d+)', body)))
            formula_refs = sorted(set(re.findall(r'(?:eqns?\s+)([\dA-C]+\.\d+)', body)))
            dependency = bool(figure_refs or formula_refs or re.search(
                r'\b(?:[Ee]xample|[Ss]ection|[Cc]hapter|[Aa]ppendix)\s+[\dA-C]|this chapter', body))
            subjects = ['thermodynamics', 'statistical_mechanics']
            if chapter['number'] in (1, 3, 15):
                subjects.append('mathematical_methods')
            if chapter['number'] in (23,):
                subjects.append('optics')
            if chapter['number'] in (29, 30, 36):
                subjects.append('quantum_mechanics')
            questions.append({'source': origin, 'source_language': 'en',
                'locator': f'chapter-{chapter["number"]}/exercise-{number}',
                'original_number': number, 'chapter': chapter['title'], 'kind': 'exercise',
                'subjects': subjects, 'level': 'undergraduate', 'review_status': 'pending',
                'spans': [part['asset']['spans'][0] for part in regions],
                'assets': [part['asset'] for part in regions],
                'versions': [{'language': 'en', 'role': 'original', 'text': body, 'review_status': 'pending'}],
                'context': {'chapter_id': str(chapter['number']), 'source_figure_references': figure_refs,
                    'source_formula_references': formula_refs, 'unresolved_source': dependency,
                    'quality_flags': ['embedded_text_and_math_unreviewed', 'two_column_boundaries_need_review',
                                      'source_pdf_has_six_invalid_embedded_math_font_programs'],
                    'source_context_recovery_pending': dependency}})
        audits.append({'chapter': chapter['number'], 'count': len(labels),
                       'pdf_pages': [page_indices[0] + 1, page_indices[-1] + 1],
                       'printed_numbers_consecutive': True})

    # Two genuine, unnumbered appendix exercises are also part of this edition.
    quick = []
    for index in range(len(document)):
        lines = text_lines(document[index])
        for line in lines:
            if re.fullmatch(r'Quick\s+exercise:?', line_text(line)):
                top = line['bbox'][1] + 0.3
                later_sections = [other for other in lines if other['bbox'][1] > line['bbox'][3]
                                  and any(span['size'] > 13 for span in other['spans'])]
                bottom = min((other['bbox'][1] - 3 for other in later_sections), default=680)
                left = line['bbox'][0] - 4
                right = 349 if left < 100 else 509
                page, box = document[index], fitz.Rect(left, top, right, bottom)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=box, alpha=False)
                filename = f'quick-pdf{index + 1:03}.webp'
                path = images / filename
                Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples).save(path, 'WEBP', lossless=True)
                span = {'page': index + 1, 'bbox': [box.x0 / page.rect.width, box.y0 / page.rect.height,
                                                box.x1 / page.rect.width, box.y1 / page.rect.height]}
                body = page.get_text('text', clip=box).strip()
                questions.append({'source': origin, 'source_language': 'en',
                    'locator': f'appendix/quick-exercise/pdf-{index + 1}', 'original_number': 'unnumbered',
                    'chapter': 'Useful mathematics', 'kind': 'exercise', 'subjects': ['mathematical_methods'],
                    'level': 'undergraduate', 'review_status': 'pending', 'spans': [span],
                    'assets': [{'role': 'question_crop', 'local_path': str(path), 'mime_type': 'image/webp',
                                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'spans': [span]}],
                    'versions': [{'language': 'en', 'role': 'original', 'text': body, 'review_status': 'pending'}],
                    'context': {'printed_number_absent': True, 'unresolved_source': True,
                                'source_context_recovery_pending': True,
                                'quality_flags': ['embedded_text_and_math_unreviewed',
                                                  'unnumbered_appendix_exercise_needs_visual_review']}})
                quick.append(index + 1)
    if quick != [493, 496]:
        raise ValueError('The two appendix exercises must be identified explicitly')
    raw = {'version': 1, 'source_sha256': SOURCE_SHA, 'questions': questions}
    (output / 'questions.raw.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
    audit = {'source_sha256': SOURCE_SHA, 'chapter_counts': audits, 'unnumbered_exercise_pdf_pages': quick,
             'question_count': len(questions), 'asset_references': sum(len(question['assets']) for question in questions),
             'numbered_exercises': len(questions) - len(quick), 'paid_api_calls': 0, 'review_status': 'pending',
             'source_render_warning': 'Six embedded math-font programs are invalid; page image and equation recovery require review.',
             'limitations': ['Referenced examples, formulae and figures still need source-context recovery.',
                            'Text is unreviewed embedded PDF extraction, with pending English and Korean editing.',
                            'Coverage is a numbering/section audit, not completed visual boundary verification.']}
    (output / 'coverage-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    document.close()
    print(json.dumps({key: audit[key] for key in ('question_count', 'numbered_exercises', 'asset_references', 'paid_api_calls')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--dpi', type=int, default=170)
    args = parser.parse_args()
    extract(args.source, args.output, args.manifest, args.dpi)
