"""Independent source-ink and source-program audit for 2023 figure-language proofs."""
from collections import Counter
from pathlib import Path
import argparse, gc, hashlib, json, math, re, subprocess
import numpy as np
import cv2
import pikepdf
import pymupdf as fitz
from PIL import Image, ImageDraw
import cpho_2023_original_labels as b
import pdf_original_style_audit as preservation
from pdf_original_graphics_ink import audit as graphics_audit
from pdf_original_image_ink import image_programs

cv2.setNumThreads(1)


def exact(g):
    return g['c'], g['gid'], g['font'], g['size'], tuple(g['origin']), tuple(g['color']), g['render_type']


def form_programs(path, number):
    result = Counter()
    with pikepdf.Pdf.open(path) as doc:
        def walk(node, resources):
            for instruction in pikepdf.parse_content_stream(node):
                if str(instruction.operator) != 'Do':
                    continue
                obj = resources.get('/XObject', {}).get(instruction.operands[0])
                if obj is None or str(obj.get('/Subtype')) != '/Form':
                    continue
                result[(hashlib.sha256(obj.read_raw_bytes()).hexdigest(), hashlib.sha256(obj.read_bytes()).hexdigest(), tuple(float(v) for v in obj.get('/BBox', [])), tuple(float(v) for v in obj.get('/Matrix', [])))] += 1
                walk(obj, obj.get('/Resources', resources))
        page = doc.pages[number - 1]
        walk(page, page.Resources)
    return result


def original_fonts(doc, page):
    result = Counter()
    for item in page.get_fonts(full=True):
        if item[4].startswith('FigureLanguage'):
            continue
        program = doc.extract_font(item[0])[3]
        result[(item[3], hashlib.sha256(program).hexdigest())] += 1
    return result


def audit(path, scale=4, pages=None):
    path = Path(path).resolve()
    data = json.loads(path.with_suffix('.json').read_text(encoding='utf8'))
    source = fitz.open(b.SOURCE)
    proof = fitz.open(path)
    report = dict(source_sha256=b.SOURCE_SHA, proof=path.relative_to(b.ROOT).as_posix(), proof_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), pages=[], passed=True)
    contacts = []
    for index, number in enumerate(data['source_pages']):
        if pages and number not in pages:
            continue
        current, old = proof[index], source[number - 1]
        labels = [label for label in data['labels'] if label['page'] == number]
        original = preservation.glyphs(old)
        remaining = Counter(exact(g) for g in original)
        added = []
        for glyph in preservation.glyphs(current):
            token = exact(glyph)
            if remaining[token]:
                remaining[token] -= 1
            else:
                added.append(glyph)
        missing = list(remaining.elements())
        old_regions = [label['erase_rect'] for label in labels]
        new_regions = [b.native_prose_ink(current, [glyph]) for glyph in added if not glyph['c'].isspace()]
        allowed = old_regions + [[r[0] - .125, r[1] - .125, r[2] + .125, r[3] + .125] for r in new_regions]
        form_prose = [g for label in labels for g in label.get('source_glyphs', [])]
        spec = dict(source_page=number, proof_page=index + 1, allowed_rects=allowed, erased_glyph_origins=[g['origin'] for g in form_prose])
        row = preservation.audit(b.SOURCE, path, spec, scale=scale)
        row['language_overlay_spec'] = spec
        row['original_nonspace_and_space_metadata_changed'] = missing
        row['original_form_raw_and_decoded_programs_identical'] = form_programs(b.SOURCE, number) == form_programs(path, index + 1)
        row['original_image_smask_programs_positions_identical'] = image_programs(source, old) == image_programs(proof, current)
        row['original_font_programs_identical'] = original_fonts(source, old) == original_fonts(proof, current)
        graphic = graphics_audit(b.SOURCE, path, number, index + 1, language_regions=old_regions, scale=scale)
        row['graphics'] = graphic
        row['unexpected_new_han_or_nul'] = [g for g in added if b.HAN.search(g['c']) or g['c'] == '\x00' or g['gid'] == 0]
        row['new_glyphs_checked'] = len(added)
        row['original_form_language_glyph_metadata_intentionally_retained'] = len(form_prose)
        row['passed'] = not (missing or row['native_glyphs_changed'] or row['changed_pixels_outside_prose'] or row['changed_pixels_in_native_glyph_neighborhood'] or row['unexpected_new_han_or_nul'] or graphic['original_graphics_ink_changed_pixels']) and row['original_form_raw_and_decoded_programs_identical'] and row['original_image_smask_programs_positions_identical'] and row['original_font_programs_identical']
        report['pages'].append(row)
        report['passed'] &= row['passed']
        b.write(b.AUTHOR / (path.stem + '-qa.partial.json'), report)
        print(path.stem, number, 'outside', row['changed_pixels_outside_prose'], 'native ink', row['changed_pixels_in_native_glyph_neighborhood'], 'graphics', graphic['original_graphics_ink_changed_pixels'], 'metadata', len(missing), 'programs', row['original_form_raw_and_decoded_programs_identical'], row['original_image_smask_programs_positions_identical'], row['original_font_programs_identical'], flush=True)
        # Small figure/word crops only: no redundant full-page QA raster cache.
        for label in labels:
            box = fitz.Rect(label['erase_rect'])
            for g in added:
                if any(abs(g['origin'][0] - run['origin'][0]) < .03 and abs(g['origin'][1] - run['origin'][1]) < .03 for run in label['placed_runs']):
                    line = [v for v in added if abs(v['origin'][1] - g['origin'][1]) < .03 and abs(v['origin'][0] - g['origin'][0]) < 180]
                    for v in line:
                        box |= fitz.Rect(v['bbox'])
            box += (-3, -3, 3, 3)
            crop = current.get_pixmap(matrix=fitz.Matrix(3, 3), clip=box, colorspace=fitz.csRGB)
            image = Image.frombytes('RGB', [crop.width, crop.height], crop.samples)
            image.thumbnail((450, 110))
            contacts.append((label['id'], number, image))
        gc.collect()
        fitz.TOOLS.store_shrink(100)
    height = ((len(contacts) + 1) // 2) * 145
    contact = Image.new('RGB', (960, max(145, height)), '#ddd')
    draw = ImageDraw.Draw(contact)
    for i, (identity, number, image) in enumerate(contacts):
        x, y = (i % 2) * 480 + 8, (i // 2) * 145 + 25
        draw.text((x, y - 20), identity + ' / p' + str(number), fill='black')
        contact.paste(image, (x, y))
    contact.save(b.BASE / (path.stem + '-contact.png'))
    b.write(b.AUTHOR / (path.stem + '-qa.json'), report)
    source.close()
    proof.close()
    return report


def poppler(paths, dpi=110):
    """Independent renderer: preserve every source ink pixel outside old prose."""
    folder = b.BASE / 'poppler'
    folder.mkdir(exist_ok=True)
    source_images = {}
    warnings = []

    def render(path, number, name):
        target = folder / name
        args = ['pdftoppm', '-f', str(number), '-l', str(number), '-r', str(dpi), '-singlefile', '-png', str(path), str(target)]
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if result.stderr:
            warnings.append(dict(file=Path(path).name, page=number, stderr=result.stderr.decode('utf8', errors='replace')))
        return target.with_suffix('.png')

    report = dict(source_sha256=b.SOURCE_SHA, renderer='Poppler pdftoppm 26.07.0', dpi=dpi, passed=True, files=[], warnings=warnings,
                  prose_antialias_guard_px=1, native_ink_method='Original source pixels darker than250; exclude only original language erasure rectangles. New prose rectangles are not excluded from native-ink protection.')
    scale = dpi / 72
    for path in paths:
        proof_data = json.loads(path.with_suffix('.json').read_text(encoding='utf8'))
        mupdf = json.loads((b.AUTHOR / (path.stem + '-qa.json')).read_text(encoding='utf8'))
        specs = {p['source_page']: p['language_overlay_spec'] for p in mupdf['pages']}
        row = dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), pages=[], passed=True)
        for index, number in enumerate(proof_data['source_pages']):
            if number not in source_images:
                source_images[number] = render(b.SOURCE, number, 'source-p' + str(number))
            proof_image = render(path, index + 1, path.stem + '-p' + str(number))
            with Image.open(source_images[number]) as image:
                old = np.asarray(image.convert('RGB'))
            with Image.open(proof_image) as image:
                new = np.asarray(image.convert('RGB'))
            if old.shape != new.shape:
                raise ValueError('Different page dimensions')
            allowed = np.zeros(old.shape[:2], np.uint8)
            language = np.zeros(old.shape[:2], np.uint8)

            def fill(mask, rect):
                x0, y0, x1, y1 = rect
                mask[max(0, math.floor(y0 * scale)):min(mask.shape[0], math.ceil(y1 * scale)), max(0, math.floor(x0 * scale)):min(mask.shape[1], math.ceil(x1 * scale))] = 1

            for rect in specs[number]['allowed_rects']:
                fill(allowed, rect)
            for label in proof_data['labels']:
                if label['page'] == number:
                    fill(language, label['erase_rect'])
            difference = np.any(old != new, axis=2)
            padded = cv2.dilate(allowed, np.ones((3, 3), np.uint8)).astype(bool)
            outside = difference & ~padded
            native_changes = difference & (old.min(axis=2) < 250) & ~language.astype(bool)
            item = dict(source_page=number, changed_pixels_outside_prose=int(outside.sum()), changed_pixels_in_original_nonlanguage_ink=int(native_changes.sum()))
            if native_changes.any():
                yy, xx = np.nonzero(native_changes)
                item['native_bbox'] = [float(xx.min() / scale), float(yy.min() / scale), float((xx.max() + 1) / scale), float((yy.max() + 1) / scale)]
            row['pages'].append(item)
            row['passed'] &= not outside.any() and not native_changes.any()
            print(path.stem, number, 'Poppler outside', item['changed_pixels_outside_prose'], 'native ink', item['changed_pixels_in_original_nonlanguage_ink'], flush=True)
        report['files'].append(row)
        report['passed'] &= row['passed']
    b.write(b.AUTHOR / 'qa-poppler.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path, nargs='+')
    parser.add_argument('--pages', nargs='+', type=int)
    parser.add_argument('--poppler', action='store_true')
    options = parser.parse_args()
    if options.poppler:
        result = poppler([p.resolve() for p in options.pdf])
        print('PASSED', result['passed'])
        raise SystemExit(not result['passed'])
    results = [audit(path, pages=options.pages) for path in options.pdf]
    print('PASSED', all(result['passed'] for result in results))
    raise SystemExit(not all(result['passed'] for result in results))
