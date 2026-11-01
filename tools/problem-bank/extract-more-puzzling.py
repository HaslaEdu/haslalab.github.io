"""Extract one privately supplied edition of 200 More Puzzling Physics Problems.

Preserves source statement images and attaches each printed footnote to its own
question. Embedded PDF text is an unreviewed transcription, never verified math.
No network or model calls. No source statements belong in this tool's code.
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

SOURCE_SHA = 'c76d9690a3b44bef0a2c20efd6db26fdb4db8aeb81fa467dc0fb37e6c38f71e4'
FIRST, LAST = 19, 82
LABEL = re.compile(r'P(\d{1,3})(∗*)$')
TOPICS = {
    **dict.fromkeys(['Kinematics', 'Dynamics', 'Gravitation', 'Mechanical energy',
                    'Collisions', 'Rigid-body mechanics', 'Elasticity', 'Statics',
                    'Ropes and chains'], ['classical_mechanics']),
    'Liquids and gases': ['classical_mechanics', 'thermodynamics'],
    'Surface tension': ['classical_mechanics', 'thermodynamics'],
    'Thermodynamics': ['thermodynamics'], 'Phase transitions': ['thermodynamics'],
    'Optics': ['optics'],
    **dict.fromkeys(['Electrostatics', 'Magnetostatics', 'Electric circuits',
                    'Electromagnetism'], ['electromagnetism']),
    'Relativity and particles': ['relativity', 'quantum_mechanics'],
    'Dimensional analysis': ['mathematical_methods'],
}


def topic_index(document):
    sections, current = {}, None
    for page_index in (16, 17):
        for line in document[page_index].get_text().splitlines():
            if ':' in line and line.split(':', 1)[0] in TOPICS:
                current, rest = line.split(':', 1)
                sections[current] = rest
            elif current and re.fullmatch(r'[\d\s,∗.]+', line):
                sections[current] += ' ' + line
            else:
                current = None
    mapping, stars = collections.defaultdict(list), collections.defaultdict(int)
    for topic, text in sections.items():
        for match in re.finditer(r'\b(\d+)\s*(∗{0,3})', text):
            number = int(match[1])
            if not 1 <= number <= 200:
                raise ValueError('Out-of-range problem in thematic index')
            mapping[number].append(topic)
            stars[number] = max(stars[number], len(match[2]))
    if set(mapping) != set(range(1, 201)) or len(sections) != len(TOPICS):
        raise ValueError('Thematic index coverage is incomplete')
    return mapping, stars


def extract(source, output, dpi=170):
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_sha != SOURCE_SHA:
        raise ValueError('This adapter requires the independently checked PDF edition')
    output = private_directory(output)
    (output / 'images').mkdir(parents=True, exist_ok=True)
    document = fitz.open(source)
    if len(document) != 498:
        raise ValueError('Unexpected page count')
    mapping, stars = topic_index(document)
    labels, all_spans, all_lines, footnotes = [], {}, {}, {}
    for index in range(FIRST - 1, LAST):
        page = document[index]
        lines = [line for block in page.get_text('dict')['blocks'] if 'lines' in block
                 for line in block['lines']]
        all_lines[index] = lines
        spans = [span for line in lines for span in line['spans']]
        all_spans[index] = spans
        for word in page.get_text('words'):
            match = LABEL.fullmatch(word[4])
            if match and 70 < word[0] < 87 and word[7] == 0:
                labels.append({'number': int(match[1]), 'page_index': index,
                               'bbox': list(word[:4]), 'stars': len(match[2])})
        starts = sorted([span for span in spans if 6.7 < span['size'] < 6.9
                         and span['text'].isdigit() and 1 <= int(span['text']) <= 12
                         and span['bbox'][0] < 80 and span['bbox'][1] > 500],
                        key=lambda span: span['bbox'][1])
        footnotes[index] = [dict(number=int(span['text']),
                           bbox=[50, span['bbox'][1] + 1.2,
                                 443, starts[position + 1]['bbox'][1] + 1.2
                                 if position + 1 < len(starts) else 628],
                           next_marker_top=starts[position + 1]['bbox'][1]
                           if position + 1 < len(starts) else None)
                           for position, span in enumerate(starts)]
    labels.sort(key=lambda label: (label['page_index'], label['bbox'][1]))
    if [label['number'] for label in labels] != list(range(1, 201)):
        raise ValueError('Printed statement labels are not exactly P1–P200')
    if sorted(note['number'] for notes in footnotes.values() for note in notes) != list(range(1, 13)):
        raise ValueError('Expected exactly the twelve printed footnotes')

    def save_segment(number, page_index, bbox, role='body', note_number=None, next_marker_top=None):
        page, box = document[page_index], fitz.Rect(bbox)
        if box.height < 4:
            return None
        pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=box, alpha=False)
        image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
        # The adjacent note's raised left marker overlaps the preceding note's
        # last-line font box. Exclude only that otherwise unrelated marker;
        # the complete preceding text and its subscript remain in the crop.
        excluded = None
        if next_marker_top is not None:
            excluded = [50, next_marker_top - 1, 68.5, box.y1]
            scale = dpi / 72
            image.paste('white', (0, max(0, int((excluded[1] - box.y0) * scale)),
                                 int((excluded[2] - box.x0) * scale) + 1, image.height))
        # Ignore only genuinely empty white strips, never a diagram with no OCR.
        ink = image.convert('L').point(lambda value: 255 if value < 235 else 0)
        if ink.getbbox() is None:
            return None
        suffix = f'-fn{note_number}' if role == 'footnote' else ''
        name = f'p{number:03}-pdf{page_index + 1:03}{suffix}.webp'
        path = output / 'images' / name
        image.save(path, 'WEBP', quality=91, method=5)
        return {'pdf_page': page_index + 1, 'printed_page': page_index + 2 - FIRST,
                'bbox_pt': [round(value, 3) for value in box],
                'page_size_pt': [page.rect.width, page.rect.height],
                'image': 'images/' + name, 'image_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'image_size_px': [pixmap.width, pixmap.height], 'segment_role': role,
                'footnote_number': note_number,
                'excluded_adjacent_marker_bbox_pt': excluded,
                'text_ocr_raw': page.get_text('text', clip=box).strip()}

    questions, assigned_notes = [], []
    for position, label in enumerate(labels):
        following = labels[position + 1] if position + 1 < len(labels) else {
            'page_index': LAST, 'bbox': [0, 58, 0, 58]}
        segments = []
        for index in range(label['page_index'], min(following['page_index'], LAST - 1) + 1):
            top = label['bbox'][1] - 2 if index == label['page_index'] else 58
            bottom = following['bbox'][1] - 3 if index == following['page_index'] else 628
            if footnotes[index]:
                bottom = min(bottom, footnotes[index][0]['bbox'][1] - 6)
            segment = save_segment(label['number'], index, [50, top, 443, bottom])
            if segment:
                segments.append(segment)
        for index in range(label['page_index'], min(following['page_index'], LAST - 1) + 1):
            for note in footnotes[index]:
                references = [span for span in all_spans[index]
                              if span['text'] == str(note['number']) and 7.5 < span['size'] < 7.7
                              and span['font'] == 'Times-Roman'
                              and span['bbox'][1] < footnotes[index][0]['bbox'][1] - 6]
                if len(references) != 1:
                    raise ValueError('Footnote must have one unambiguous source reference')
                reference_line = next(line for line in all_lines[index] if references[0] in line['spans'])
                main_baselines = [span['origin'][1] for span in reference_line['spans']
                                  if span['size'] > 9 and span['text'].strip()]
                if not main_baselines:
                    raise ValueError('Footnote reference must belong to a normal-size statement line')
                # A raised reference on the first statement line can sit above
                # its printed problem label. Its enclosing baseline identifies
                # the correct question without assigning it to the prior one.
                reference_y = max(main_baselines)
                owner = next((candidate for candidate in reversed(labels)
                              if candidate['page_index'] < index or
                              candidate['page_index'] == index and candidate['bbox'][1] <= reference_y), None)
                if owner == label:
                    segment = save_segment(label['number'], index, note['bbox'], 'footnote',
                                           note['number'], note['next_marker_top'])
                    if segment is None:
                        raise ValueError('A printed footnote crop cannot be empty')
                    segments.append(segment)
                    assigned_notes.append({'number': note['number'], 'problem': label['number'],
                                           'pdf_page': index + 1})
        if not segments:
            raise ValueError('Empty question')
        if label['stars'] != stars[label['number']]:
            raise ValueError('Statement/index asterisks disagree')
        questions.append({'original_number': f'P{label["number"]}',
            'statement_segments': segments,
            'text_en_ocr_raw': '\n\n'.join(segment['text_ocr_raw'] for segment in segments),
            'subjects': sorted({subject for topic in mapping[label['number']] for subject in TOPICS[topic]}),
            'topics_source': mapping[label['number']],
            'difficulty_source_asterisks': stars[label['number']],
            'classification_provenance': {'pdf_pages': [17, 18], 'kind': 'book_thematic_index'},
            'flags': ['ocr_text_unreviewed', 'math_transcription_unreviewed',
                      'diagram_embedded_in_statement_crop'],
            'review_status': 'pending'})
    if len(assigned_notes) != 12 or len({note['number'] for note in assigned_notes}) != 12:
        raise ValueError('Every footnote must be attached to exactly one question')
    raw = {'schema_version': 1, 'source_sha256': source_sha, 'source_page_count': len(document),
           'title': '200 More Puzzling Physics Problems', 'questions': questions,
           'visibility': 'private', 'review_status': 'pending'}
    (output / 'questions-raw.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
    audit = {'question_count': len(questions), 'expected_question_count': 200,
             'number_sequence_exact': True, 'source_sha256': source_sha,
             'statement_pdf_pages': [FIRST, LAST], 'hints_start_pdf_page': 83,
             'image_count': sum(len(question['statement_segments']) for question in questions),
             'source_footnote_assignments': assigned_notes, 'paid_api_calls': 0,
             'review_status': 'pending', 'limitations': [
                 'Source crops require visual boundary review.',
                 'Embedded text and equations are unreviewed until checked against the page image.',
                 'Korean translations have not been generated by this extractor.']}
    (output / 'coverage-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    document.close()
    print(json.dumps({key: audit[key] for key in ('question_count', 'image_count', 'paid_api_calls')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--dpi', type=int, default=170)
    args = parser.parse_args()
    extract(args.source, args.output, args.dpi)
