"""Locate numeric labels in narrow column margins using local OCR only.

The private profile binds source hash, page ranges and crop geometry. This
produces candidates for source-image review, never a complete question count.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import pymupdf
from PIL import Image, ImageOps
import tesserocr

from private_paths import private_directory


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def detect(pdf, profile_path, output, tessdata):
    output = private_directory(output)
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    source_hash = digest(pdf)
    if source_hash != profile['source_sha256']:
        raise ValueError('Profile source hash mismatch')
    training_hash = digest(tessdata / 'eng.traineddata')
    document = pymupdf.open(pdf)
    if len(document) != profile['page_count']:
        raise ValueError('Profile page count mismatch')
    cache = output / 'numeric-label-ocr'
    cache.mkdir(exist_ok=True)
    scale, padding = 4, 20
    sections = []
    with tesserocr.PyTessBaseAPI(path=str(tessdata), lang='eng',
                               psm=tesserocr.PSM.SINGLE_BLOCK) as engine:
        engine.SetVariable('tessedit_char_whitelist', '0123456789.')
        for section in profile['sections']:
            candidates = []
            for number in range(section['first_page'], section['last_page'] + 1):
                page = document[number - 1]
                columns = profile.get('page_label_columns', {}).get(str(number), profile['label_columns'])
                for column, bounds in enumerate(columns):
                    box = pymupdf.Rect(bounds[0], profile['body_top'], bounds[1], profile['body_bottom'])
                    if not page.rect.contains(box) or box.is_empty:
                        raise ValueError('Label strip lies outside the source page')
                    target = cache / f'page-{number:05d}-column-{column}.json'
                    identity = {'source_sha256': source_hash, 'page': number, 'column': column,
                                'bbox_points': list(box), 'scale': scale, 'padding': padding,
                                'training_sha256': training_hash, 'mode': 'single_block_numeric_v1'}
                    if target.is_file():
                        record = json.loads(target.read_text(encoding='utf-8'))
                        if any(record.get(key) != value for key, value in identity.items()):
                            raise ValueError('Numeric OCR cache source/geometry mismatch')
                    else:
                        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=box,
                                              colorspace=pymupdf.csGRAY, alpha=False)
                        image = ImageOps.expand(Image.frombytes('L', (pix.width, pix.height), pix.samples),
                                                border=padding, fill=255)
                        image.save(target.with_suffix('.png'))
                        engine.SetImage(image)
                        text = engine.GetUTF8Text()
                        words = []
                        iterator = engine.GetIterator() if text.strip() else None
                        if iterator:
                            while True:
                                word = iterator.GetUTF8Text(tesserocr.RIL.WORD)
                                if word and word.strip():
                                    x0, y0, x1, y1 = iterator.BoundingBox(tesserocr.RIL.WORD)
                                    words.append({'text': word.strip(), 'bbox': [
                                        box.x0 + (x0 - padding) / scale, box.y0 + (y0 - padding) / scale,
                                        box.x0 + (x1 - padding) / scale, box.y0 + (y1 - padding) / scale]})
                                if not iterator.Next(tesserocr.RIL.WORD):
                                    break
                        record = dict(identity, text=text, words=words,
                                      source_image_checked=False, review_status='pending', paid_api_calls=0)
                        save(target, record)
                        engine.Clear()
                    for word in record['words']:
                        match = re.fullmatch(r'(\d{1,2})(\.)?', word['text'])
                        if match and not match[2]:
                            # Border-clipped prose can be misread as a numeral.
                            width = word['bbox'][2] - word['bbox'][0]
                            if (width > 6 * len(match[1]) + 1
                                    or word['bbox'][2] >= box.x1 - .2):
                                continue
                        if match and int(match[1]) > 0:
                            candidates.append(dict(word, page=number, column=column, number=int(match[1])))
            candidates.sort(key=lambda item: (item['page'], item['column'], item['bbox'][1]))
            first = next((item for item in candidates if item['text'] == '1.'), None)
            if first is None:
                first = next((item for item in candidates if item['number'] == 1), None)
            if first:
                origin = (first['page'], first['column'], first['bbox'][1])
                candidates = [item for item in candidates
                              if (item['page'], item['column'], item['bbox'][1]) >= origin
                              and (item['page'] != first['page']
                                   or item['bbox'][1] >= first['bbox'][1] - 4)]
            sequence = [item['number'] for item in candidates]
            sections.append({'chapter': section['chapter'], 'first': first, 'candidates': candidates,
                             'consecutive': bool(sequence) and sequence == list(range(1, len(sequence) + 1)),
                             'review_status': 'pending'})
            print(json.dumps({'chapter': section['chapter'], 'numbers': sequence}), flush=True)
    save(output / 'numeric-label-candidates.json', {'source_sha256': source_hash, 'sections': sections,
         'publication_ready': False, 'paid_api_calls': 0})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--tessdata', type=Path, required=True)
    args = parser.parse_args()
    detect(args.pdf, args.profile, args.out, args.tessdata)
