"""Extract the user-supplied 200 Puzzling Physics Problems statement chapter.

No provider calls. Keep outputs outside a public source repository. Source crops,
not the PDF's imperfect OCR layer, are authoritative until human review.
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


TOPIC_SUBJECTS = {
    'Kinematics': ['classical_mechanics'],
    'Dynamics': ['classical_mechanics'],
    'Gravitation': ['classical_mechanics'],
    'Mechanical energy': ['classical_mechanics'],
    'Collisions': ['classical_mechanics'],
    'Mechanics of rigid bodies': ['classical_mechanics'],
    'Statics': ['classical_mechanics'],
    'Ropes, chains': ['classical_mechanics'],
    'Liquids, gases': ['classical_mechanics', 'thermodynamics'],
    'Surface tension': ['classical_mechanics', 'thermodynamics'],
    'Thermodynamics': ['thermodynamics'],
    'Phase transitions': ['thermodynamics'],
    'Optics': ['optics'],
    'Electrostatics': ['electromagnetism'],
    'Magnetostatics': ['electromagnetism'],
    'Electric currents': ['electromagnetism'],
    'Electromagnetism': ['electromagnetism'],
    'Atoms and particles': ['quantum_atomic_particle_physics'],
    'Dimensional analysis, scaling, estimations': ['mathematical_methods'],
}
LABEL = re.compile(r'P([0-9IlOtSo]{1,3})[*.\u2022]*$')
LABEL_DIGITS = str.maketrans({'l': '1', 'I': '1', 'O': '0', 'o': '0', 'S': '5', 't': '1'})


def topics_from_index(text):
    sections, current = {}, None
    for line in text.splitlines():
        if ':' in line:
            topic, rest = line.split(':', 1)
            if topic in TOPIC_SUBJECTS:
                current = topic
                sections[current] = rest
                continue
        if current and re.match(r'^[\d\s*,.]+$', line):
            sections[current] += ' ' + line
        elif line.startswith('*'):
            current = None
    mapping = collections.defaultdict(list)
    stars = collections.defaultdict(int)
    for topic, body in sections.items():
        for match in re.finditer(r'\b(\d{1,3})\s*(\*{0,2})', body):
            number = int(match[1])
            if not 1 <= number <= 200:
                raise ValueError(f'Out-of-range number in source index: {number}')
            mapping[number].append(topic)
            stars[number] = max(stars[number], len(match[2]))
    return mapping, stars, sections


def extract(source, output, first_page=14, last_page=62, index_page=10, dpi=170):
    output = private_directory(output)
    output.mkdir(parents=True, exist_ok=True)
    images = output / 'images'
    images.mkdir(exist_ok=True)
    document = fitz.open(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    mapping, stars, index_sections = topics_from_index(document[index_page - 1].get_text())
    labels = []
    for page_index in range(first_page - 1, last_page):
        page = document[page_index]
        for word in page.get_text('words'):
            match = LABEL.fullmatch(word[4])
            # Labels share a fixed left margin in this scan. This excludes an
            # ordinary paragraph word "Plot", which the OCR confuses with P101.
            if match and 38.5 <= word[0] <= 46 and word[7] == 0:
                labels.append({'number': int(match[1].translate(LABEL_DIGITS)),
                               'page_index': page_index, 'bbox': list(word[:4]),
                               'source_label_ocr': word[4]})
    labels.sort(key=lambda label: (label['page_index'], label['bbox'][1]))
    numbers = [label['number'] for label in labels]
    expected = list(range(1, 201))
    if numbers != expected:
        raise ValueError('Source labels are not exactly P1–P200 in order: '
                         + str({'missing': sorted(set(expected)-set(numbers)),
                                'duplicates': [n for n, c in collections.Counter(numbers).items() if c > 1]}))
    sentinel = {'page_index': last_page, 'bbox': [0, 40, 0, 40]}
    questions, page_regions = [], collections.defaultdict(list)
    for position, label in enumerate(labels):
        next_label = labels[position + 1] if position + 1 < len(labels) else sentinel
        segments = []
        for page_index in range(label['page_index'], next_label['page_index'] + 1):
            if page_index >= last_page:
                break
            top = max(40, label['bbox'][1] - 2.5) if page_index == label['page_index'] else 40
            bottom = min(603, next_label['bbox'][1] - 4) if page_index == next_label['page_index'] else 603
            # A new question near the top of the next page leaves only the
            # blank inter-header strip for the previous question, not a
            # continuation. Never count that strip as a second statement page.
            if bottom - top < 10:
                continue
            box = fitz.Rect(25, top, 402, bottom)
            page = document[page_index]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=box, alpha=False)
            image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
            name = f'p{label["number"]:03}-pdf{page_index + 1:03}.webp'
            destination = images / name
            image.save(destination, 'WEBP', quality=91, method=5)
            raw_text = page.get_text('text', clip=box, sort=False).strip()
            segment = {'pdf_page': page_index + 1, 'printed_page': page_index - first_page + 2,
                       'bbox_pt': [round(value, 3) for value in box],
                       'page_size_pt': list(page.rect)[2:],
                       'image': 'images/' + name, 'image_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                       'image_size_px': [pixmap.width, pixmap.height],
                       'text_ocr_raw': raw_text}
            segments.append(segment)
            page_regions[page_index + 1].append({'number': label['number'], 'bbox_pt': segment['bbox_pt']})
        topics = mapping[label['number']]
        subjects = sorted({subject for topic in topics for subject in TOPIC_SUBJECTS[topic]})
        flags = ['ocr_text_unreviewed', 'math_transcription_unreviewed', 'diagram_embedded_in_statement_crop']
        if len(segments) > 1:
            flags.append('multi_page_question')
        if re.search(r'[IlOtSo]', label['source_label_ocr'][1:].rstrip('*.\u2022')):
            flags.append('ocr_label_normalized')
        if not topics:
            flags.append('missing_source_topic')
        question = {'id': f'puzzling-200:P{label["number"]}', 'original_number': f'P{label["number"]}',
                    'source_label_ocr': label['source_label_ocr'], 'statement_segments': segments,
                    'text_en_ocr_raw': '\n\n'.join(segment['text_ocr_raw'] for segment in segments),
                    'canonical_representation': 'source_statement_images',
                    'topics_source': topics, 'subjects': subjects,
                    'classification_provenance': {'pdf_page': index_page, 'kind': 'book_thematic_index'},
                    'difficulty_source_asterisks': stars[label['number']],
                    'review_status': 'pending', 'translation_status': {'en': 'ocr_pending_review', 'ko': 'not_started'},
                    'flags': flags}
        questions.append(question)
    manifest = {'schema_version': 1, 'title': '200 Puzzling Physics Problems', 'source_filename': source.name,
                'source_sha256': source_hash, 'source_page_count': len(document),
                'statement_pdf_pages': [first_page, last_page], 'hints_start_pdf_page': last_page + 1,
                'topic_index_pdf_page': index_page, 'visibility': 'private', 'review_status': 'pending',
                'question_count': len(questions), 'questions': questions}
    (output / 'questions-raw.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    empty = [q['original_number'] for q in questions if not q['text_en_ocr_raw']]
    audit = {'source_sha256': source_hash, 'questions_expected': 200, 'questions_extracted': len(questions),
             'number_sequence_exact': numbers == expected, 'missing_numbers': sorted(set(expected)-set(numbers)),
             'duplicate_numbers': [n for n, count in collections.Counter(numbers).items() if count > 1],
             'empty_ocr_questions': empty,
             'multi_page_questions': [q['original_number'] for q in questions if len(q['statement_segments']) > 1],
             'topic_coverage_count': sum(bool(q['topics_source']) for q in questions),
             'image_count': sum(len(q['statement_segments']) for q in questions),
             'topic_index_transcribed': index_sections, 'page_regions': dict(page_regions),
             'limitations': ['Text is the supplied PDF OCR layer and may contain incorrect units, symbols and equations.',
                             'All text and translations remain pending review; no problem is marked fully verified.',
                             'Figures are preserved within source statement crops rather than heuristically redrawn.',
                             'Multiple source topics are preserved; broad subject mapping is conservative.',
                             'Hints and solutions are intentionally excluded from question statements.']}
    (output / 'coverage-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: audit[key] for key in ['questions_extracted', 'image_count', 'number_sequence_exact',
                                               'topic_coverage_count', 'empty_ocr_questions']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--first-page', type=int, default=14)
    parser.add_argument('--last-page', type=int, default=62)
    parser.add_argument('--index-page', type=int, default=10)
    parser.add_argument('--dpi', type=int, default=170)
    arguments = parser.parse_args()
    extract(arguments.source, arguments.output, arguments.first_page, arguments.last_page,
            arguments.index_page, arguments.dpi)
