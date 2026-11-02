"""Language-only overlays in the original CPhO 2023 scientific figures.

The source Forms, native scientific symbols, image/SMask programs and diagram
geometry remain intact. This module owns figure prose only; it never edits the
body translation module or its TSV. Raster font metadata is not recoverable and
must be recorded as measured inference rather than claimed as exact.
"""
from pathlib import Path
from io import BytesIO
import argparse, gc, hashlib, json, math, re, xml.etree.ElementTree as ET
import numpy as np
import pikepdf
import pymupdf as fitz
from PIL import Image, ImageDraw
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
from pdf_original_text_ops import native_form_glyphs
from pdf_original_style_fonts import subset_font

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tmp/source-audit/CPhO_2023_T_ZH.pdf'
SOURCE_SHA = '956f132218ce6591d418a1faa998648b00a6195b2f2b522e6e16c1a405a418f0'
AUTHOR = ROOT / 'tools/ko/cpho/2023/original-labels'
BASE = ROOT / 'tmp/original-style-repair/2023/figure-language'
HAN = re.compile('[\u3400-\u9fff]')

# These rectangles were read from the 4x source-page crops, not from an OCR
# reconstruction. Digits 0/1/2, Greek alpha, /MeV and all physical paths are
# deliberately outside the language rectangles.
RECIPES = [
    ('incident', 3, [20, 29, 142, 74], '入射光', '입사광', 'Incident', 'serif', 'left'),
    ('order-zero', 3, [517, 128, 611, 174], '级光', '차광', 'th ray', 'serif', 'left'),
    ('order-two', 3, [66, 163, 146, 207], '级光', '차광', 'nd', 'serif', 'left'),
    ('order-one', 3, [193, 344, 273, 392], '级光', '차광', 'st ray', 'serif', 'left'),
    ('incident-direction', 3, [449, 340, 644, 389], '入射光方向', '입사광 방향', 'Incident direction', 'serif', 'left'),
    ('deviation', 3, [316, 395, 431, 434], '偏向角', '편향각', 'Deviation', 'serif', 'center'),
    ('violet-upper', 5, [140, 111, 173, 140], '紫', '보라', 'Violet', 'serif', 'center'),
    ('rainbow-secondary', 5, [246, 190, 278, 221], '虹', '무지개', 'Rainbow', 'serif', 'center'),
    ('red-upper', 5, [358, 198, 391, 228], '红', '빨강', 'Red', 'serif', 'center'),
    ('red-lower', 5, [412, 251, 446, 282], '红', '빨강', 'Red', 'serif', 'center'),
    ('rainbow-primary', 5, [435, 397, 469, 431], '虹', '무지개', 'Rainbow', 'serif', 'center'),
    ('violet-lower', 5, [520, 483, 552, 518], '紫', '보라', 'Violet', 'serif', 'center'),
    ('radioactive-source', 8, [40, 278, 128, 312], '放射源', '방사선원', 'Rad. source', 'serif', 'left'),
    ('alpha-beam', 8, [151, 236, 230, 267], '粒子束', '입자빔', 'beam', 'serif', 'left'),
    ('gold-foil', 8, [207, 343, 268, 376], '金箔', '금박', 'Gold foil', 'serif', 'center'),
    ('fluorescent-screen', 8, [299, 263, 390, 299], '荧光屏', '형광막', 'Fluor. screen', 'serif', 'center'),
    ('microscope', 8, [453, 263, 544, 298], '显微镜', '현미경', 'Microscope', 'serif', 'left'),
    ('differential-cross-section', 9, [7, 84, 47, 346], '微分截面（相对值）', '미분 단면적 (상대값)', 'Diff. cross section (relative)', 'serif', 'rotate90'),
    ('alpha-kinetic-energy', 9, [105, 421, 231, 454], '粒子动能', '입자 KE', 'part. KE', 'serif', 'left'),
    ('target', 14, [490, 28, 530, 63], '靶', '표적', 'Target', 'serif', 'center'),
    ('alpha-source', 14, [36, 369, 120, 404], '粒子源', '입자원', 'source', 'serif', 'left'),
    ('alpha-detector', 14, [878, 367, 1025, 405], '粒子探测器', '입자 검출기', 'detector', 'serif', 'left'),
    ('magnetic-deflection-region', 14, [445, 480, 596, 516], '磁场偏转区', '자기장 편향 영역', 'Magnetic deflection region', 'serif', 'center'),
    ('electron-source', 18, [0, 125, 30, 212], '电子源', '전자원', 'Electron source', 'sans', 'vertical'),
    ('infinite-solenoid', 18, [222, 210, 373, 240], '无限长螺线管', '무한 솔레노이드', 'Infinite solenoid', 'sans', 'center'),
]


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def survey():
    """Read-only original-page figure crops and native Form-language inventory."""
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Unreviewed source PDF')
    BASE.mkdir(parents=True, exist_ok=True)
    AUTHOR.mkdir(parents=True, exist_ok=True)
    # Reviewed original coordinates travel with this module. There is no
    # dependency on the superseded diagram-redrawing code or SVG assets.
    placements = json.loads((AUTHOR / 'source-survey.json').read_text(encoding='utf8'))['figures']
    doc = fitz.open(SOURCE)
    previews = []
    for item in placements:
        page = doc[item['page'] - 1]
        crop = page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=fitz.Rect(item['rect']), colorspace=fitz.csRGB)
        image = Image.frombytes('RGB', [crop.width, crop.height], crop.samples)
        image.save(BASE / (item['id'] + '-source.png'))
        image.thumbnail((490, 400))
        previews.append((item, image.copy()))
    forms = []
    for number in range(1, 37):
        glyphs = native_form_glyphs(SOURCE, number)
        han = [g for g in glyphs if HAN.search(g['c'])]
        if han:
            forms.append(dict(page=number, glyphs=han))
        print('Survey page', number, 'Form Han', len(han), flush=True)
        gc.collect()
    contact = Image.new('RGB', (1020, ((len(previews) + 1) // 2) * 440), '#ddd')
    draw = ImageDraw.Draw(contact)
    for i, (item, image) in enumerate(previews):
        x, y = (i % 2) * 510 + 10, (i // 2) * 440 + 28
        draw.text((x, y - 20), item['id'] + ' / source p' + str(item['page']), fill='black')
        contact.paste(image, (x, y))
    contact.save(BASE / 'source-figures-contact.png')
    write(AUTHOR / 'source-survey.json', dict(source=SOURCE.name, source_sha256=SOURCE_SHA, figures=placements, native_form_han=forms))
    doc.close()


def song_font(doc):
    """Embedded same-document Song outlines for empirical raster-size comparison."""
    for page in doc:
        for record in page.get_fonts(full=True):
            if record[3].split('+')[-1] == 'SimSun':
                return TTFont(BytesIO(doc.extract_font(record[0])[3]))
    raise ValueError('No original Song font reference')


def glyph_bounds(font, text):
    gs = font.getGlyphSet()
    result = []
    cmap = font.getBestCmap()
    for char in text:
        if not HAN.search(char) or ord(char) not in cmap:
            continue
        pen = BoundsPen(gs)
        gs[cmap[ord(char)]].draw(pen)
        if pen.bounds:
            result.append((char, pen.bounds))
    if not result:
        raise ValueError('No source-font ink comparison for ' + text)
    return result


def native_prose_ink(page, glyphs):
    """Exact original Form glyph outlines, without oversized font-metric boxes."""
    root = ET.fromstring(page.get_svg_image(text_as_path=True))
    paths = {e.get('id'): e.get('d') for e in root.iter() if e.tag.endswith('path') and e.get('id')}
    result = None
    for element in root.iter():
        if not element.tag.endswith('use') or 'data-text' not in element.attrib:
            continue
        match = re.search(r'matrix\(([^)]+)\)', element.get('transform', ''))
        if not match:
            continue
        matrix = tuple(float(v) for v in match[1].replace(',', ' ').split())
        if not any(abs(matrix[-2] - g['origin'][0]) < .03 and abs(matrix[-1] - g['origin'][1]) < .03 and element.get('data-text') == g['c'] for g in glyphs):
            continue
        identity = element.get('{http://www.w3.org/1999/xlink}href', '').lstrip('#')
        if identity not in paths:
            raise ValueError('Original glyph has no outline path')
        pen = BoundsPen(None)
        parse_path(paths[identity], TransformPen(pen, matrix))
        if pen.bounds:
            result = fitz.Rect(pen.bounds) if result is None else result | fitz.Rect(pen.bounds)
    if result is None:
        raise ValueError('Original language glyph outline not found')
    return list(result)


def prepare():
    """Freeze manually located prose masks, source-style evidence and translations."""
    inventory = json.loads((AUTHOR / 'source-survey.json').read_text(encoding='utf8'))
    panels = {p['audit_index']: p for p in inventory['figures'] if 'audit_index' in p}
    doc = fitz.open(SOURCE)
    reference = song_font(doc)
    units = reference['head'].unitsPerEm
    rows = []
    for identity, index, roi, text, ko, en, family, align in RECIPES:
        panel = panels[index]
        path = BASE / ('figure-' + str(index) + '-source.png')
        with Image.open(path) as image:
            pixels = np.asarray(image.convert('RGB'))
        x0, y0, x1, y1 = roi
        yy, xx = np.nonzero(pixels[y0:y1, x0:x1].min(axis=2) < 210)
        if not len(xx):
            raise ValueError('Empty source text ROI: ' + identity)
        crop_origin = np.floor(np.array(panel['rect'][:2]) * 4) / 4
        ink = np.array([x0 + xx.min(), y0 + yy.min(), x0 + xx.max() + 1, y0 + yy.max() + 1]) / 4 + np.tile(crop_origin, 2)
        comparison = glyph_bounds(reference, text)
        if align == 'vertical':
            native_ink = max(b[2] - b[0] for c, b in comparison) / units
            actual_ink = ink[2] - ink[0]
        elif align == 'rotate90':
            native_ink = max(b[3] - b[1] for c, b in comparison) / units
            actual_ink = ink[2] - ink[0]
        else:
            native_ink = max(b[3] - b[1] for c, b in comparison) / units
            actual_ink = ink[3] - ink[1]
        size = round(actual_ink / native_ink * 20) / 20
        padding = 1.5 if identity in ['radioactive-source', 'fluorescent-screen', 'gold-foil'] else .75
        rows.append(dict(id=identity, kind='raster-language', figure=index, page=panel['page'], source=text, ko=ko, en=en,
                         source_roi_pixels=roi, source_ink_rect=ink.tolist(), erase_rect=(ink + np.array([-padding, -padding, padding, padding])).tolist(),
                         raster_fringe_padding_pt=padding,
                         size=size, family=family, bold=False, color=0, align=align,
                         baseline=float(ink[3] + min(b[1] for c, b in comparison) / units * size), font_metadata_available=False,
                         font_inference=dict(reference='Embedded same-document SimSun actual outline bounds',
                                             source_ink_dimension_pt=float(actual_ink), reference_dimension_per_em=float(native_ink),
                                             unrounded_inferred_size=float(actual_ink / native_ink), used_nominal_size=size,
                                             limitation='Raster font/size/baseline metadata are absent. Serif/sans and size are empirical matching; no fit-dependent scaling is used.')))
    for number, word, ko, en in [(5, '图', '도', 'Fig.'), (32, '任意常数', '임의상수', 'arb.const.'), (33, '任意常数', '임의상수', 'arb.const.')]:
        gs = [g for p in inventory['native_form_han'] if p['page'] == number for g in p['glyphs'] if g['c'] in word]
        gs.sort(key=lambda g: g['origin'][0])
        if ''.join(g['c'] for g in gs) != word:
            raise ValueError('Unexpected source Form language: ' + str(number))
        box = fitz.Rect(gs[0]['bbox'])
        for g in gs[1:]:
            box |= fitz.Rect(g['bbox'])
        ink = native_prose_ink(doc[number - 1], gs)
        rows.append(dict(id='form-' + str(number) + '-' + word, kind='native-form-language', page=number, source=word, ko=ko, en=en,
                         source_glyphs=gs, source_metric_rect=list(box), source_ink_rect=ink, erase_rect=list(fitz.Rect(ink) + (-.3, -.3, .3, .3)),
                         size=gs[0]['size'], family='serif', bold=False, color=0, origin=list(gs[0]['origin']), align='right' if number == 5 else 'left', font_metadata_available=True))
    condition_glyphs = [g for p in inventory['native_form_han'] if p['page'] == 34 for g in p['glyphs'] if g['c'] == '当']
    for i, glyph in enumerate(condition_glyphs):
        ink = native_prose_ink(doc[33], [glyph])
        rows.append(dict(id='form-34-condition-' + str(i + 1), kind='native-form-language', page=34, source='当', ko='단', en='if',
                         source_glyphs=[glyph], source_metric_rect=glyph['bbox'], source_ink_rect=ink, erase_rect=list(fitz.Rect(ink) + (-.3, -.3, .3, .3)),
                         size=glyph['size'], family='serif', bold=False, color=0, origin=list(glyph['origin']), align='left', font_metadata_available=True))
    for label in rows:
        if label['id'] == 'violet-lower':
            label['en_origin_dx'] = -2.0
        if label['id'] == 'fluorescent-screen':
            # JPEG fringes of the original 屏 extend right of its dark-ink
            # bounds. Stay within the manually reviewed label-only ROI.
            label['erase_rect'][2] += 1.0
            label['raster_fringe_extra_right_pt'] = 1.0
    write(AUTHOR / 'label-plan.json', dict(source=SOURCE.name, source_sha256=SOURCE_SHA, labels=rows,
        delegated_labels=[dict(page=2, source='附属虹→', body_slot='2-8-0', ko='간섭띠', en='Fringes',
                              policy='Root body CID suppression restores exact original photograph background; original white arrow remains. Never overlay twice.')],
        unchanged_physical_notation='Native Form 红/紫/初/末 physical subscripts, all Greek/Latin variables, units, digits and diagram geometry remain original.',
        source_caption_ownership='Ordinary figure captions belong to the root body translation; only the native-Form 图 in p5 图2a is handled here.'))
    print('Prepared', len(rows), 'language-only labels', flush=True)
    doc.close()


def plan():
    data = json.loads((AUTHOR / 'label-plan.json').read_text(encoding='utf8'))
    if data['source_sha256'] != hashlib.sha256(SOURCE.read_bytes()).hexdigest():
        raise ValueError('Source PDF changed')
    return data


def fonts(lang):
    """Subset only the new prose fonts; original font programs are never touched."""
    texts = {family: ''.join(l[lang] for l in plan()['labels'] if l['family'] == family) for family in ['serif', 'sans']}
    paths = {}
    for family, text in texts.items():
        source = (ROOT / 'tools/ko/fonts' / ('NotoSerifCJKkr-Regular.otf' if family == 'serif' else 'NotoSansCJKkr-Regular.otf')) if lang == 'ko' else Path('C:/Windows/Fonts/' + ('times.ttf' if family == 'serif' else 'arial.ttf'))
        cache = BASE / 'fonts'
        if lang == 'en' and family == 'serif':
            from cpho_2023_original_style import prose_symbol_font, FONT_CACHE
            source = prose_symbol_font()
            cache = FONT_CACHE
        paths[family] = subset_font(source, text, cache)
    return paths


def label_runs(label, text, font, lang=None):
    size = label['size']
    box = fitz.Rect(label['source_ink_rect'])
    width = font.text_length(text, fontsize=size)
    align = label['align']
    if label['kind'] == 'native-form-language':
        x, y = label['origin']
        if align == 'right':
            # Preserve the original native 2a; the longer Fig. prefix grows
            # into its original empty left margin at the same baseline/size.
            x = label['source_metric_rect'][2] - width - .4
        return [dict(text=text, origin=[x, y], rotate=0)]
    if align == 'vertical':
        if HAN.search(text) or re.search('[가-힣]', text):
            leading = size * 1.01
            first = (box.y0 + box.y1) / 2 - (len(text) - 1) * leading / 2 + size * .35
            return [dict(text=char, origin=[(box.x0 + box.x1 - font.text_length(char, fontsize=size)) / 2, first + i * leading], rotate=0) for i, char in enumerate(text)]
        return [dict(text=text, origin=[(box.x0 + box.x1) / 2 + size * .30, (box.y0 + box.y1 + width) / 2], rotate=90)]
    if align == 'rotate90':
        return [dict(text=text, origin=[(box.x0 + box.x1) / 2 + size * .30, (box.y0 + box.y1 + width) / 2], rotate=90)]
    x = box.x0 if align == 'left' else (box.x0 + box.x1 - width) / 2
    x += label.get(str(lang) + '_origin_dx', 0)
    gap = label.get(str(lang) + '_word_gap_adjustment', 0)
    if not gap:
        return [dict(text=text, origin=[x, label['baseline']], rotate=0)]
    runs = []
    for chunk in re.split('( )', text):
        if not chunk:
            continue
        runs.append(dict(text=chunk, origin=[x, label['baseline']], rotate=0))
        x += font.text_length(chunk, fontsize=size) + (gap if chunk == ' ' else 0)
    return runs


def apply(page, source_page, lang, font_paths=None):
    """Apply figure prose to an already composed page; return the QA journal.

    No source text/Form/image object is redacted or rewritten. Native Form
    language is white-masked only at its actual outline bounds. The original
    photograph's page text is delegated to the root's existing body slot2-8-0.
    Call after body composition and before the final preservation audit.
    """
    if lang not in ['ko', 'en']:
        raise ValueError('Unsupported language')
    items = [label for label in plan()['labels'] if label['page'] == source_page]
    if not items:
        return []
    if any(font[4].startswith('FigureLanguage') for font in page.get_fonts()):
        raise ValueError('Figure-language overlays already applied to this page')
    paths = font_paths or fonts(lang)
    report = []
    for label in items:
        path = paths[label['family']]
        font = fitz.Font(fontfile=str(path))
        runs = label_runs(label, label[lang], font, lang)
        page.draw_rect(fitz.Rect(label['erase_rect']), color=None, fill=(1, 1, 1), width=0, overlay=True)
        name = 'FigureLanguage' + label['family'].title()
        for run in runs:
            page.insert_text(fitz.Point(*run['origin']), run['text'], fontsize=label['size'], fontname=name, fontfile=str(path), color=(0, 0, 0), fill=(0, 0, 0), rotate=run['rotate'], overlay=True)
        try:
            recorded_path = str(path.relative_to(ROOT))
        except ValueError:
            recorded_path = str(path)
        report.append(dict(label, translation=label[lang], language=lang, placed_runs=runs, font_path=recorded_path))
    return report


def audit_spec(source_page):
    """Language-only exceptions for the final body+figure preservation audit.

    Form language glyphs stay in their original streams and retain metadata;
    only their ink is intentionally covered. Exclude these exact prose origins
    from physical/math ink locks, never from raw Form-program preservation.
    Every other original Form glyph remains protected.
    """
    data = plan()
    labels = [label for label in data['labels'] if label['page'] == source_page]
    return dict(source_language_regions=[label['erase_rect'] for label in labels],
                mutable_form_prose_origins=[g['origin'] for label in labels for g in label.get('source_glyphs', [])],
                original_form_programs_retained=True,
                delegated_body_slot_ids=[item['body_slot'] for item in data['delegated_labels'] if item['page'] == source_page])


def proofs(lang):
    """Internal label-only original-page proof; body remains Chinese by design."""
    paths = fonts(lang)
    journal = []
    pages = sorted({l['page'] for l in plan()['labels']})
    # insert_pdf intentionally omits source Page /Group. On pages with alpha
    # images that changes native antialiasing across the entire page. Clone
    # complete source page dictionaries, as the native text suppressor does.
    with pikepdf.Pdf.open(SOURCE) as source:
        copied = pikepdf.Pdf.new()
        for number in pages:
            copied.pages.append(source.pages[number - 1])
        buffer = BytesIO()
        copied.save(buffer, compress_streams=False)
        copied.close()
    result = fitz.open(stream=buffer.getvalue(), filetype='pdf')
    for index, number in enumerate(pages):
        journal.extend(apply(result[index], number, lang, paths))
    target = BASE / ('CPhO_2023_figure_language_' + lang.upper() + '_proof.pdf')
    result.save(target, garbage=0, deflate=False)
    result.close()
    write(target.with_suffix('.json'), dict(source_sha256=SOURCE_SHA, source_pages=pages, labels=journal))
    print(target, flush=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['survey', 'prepare', 'proof'])
    parser.add_argument('--lang', choices=['ko', 'en'])
    arguments = parser.parse_args()
    if arguments.command == 'survey':
        survey()
    elif arguments.command == 'prepare':
        prepare()
    else:
        for language in [arguments.lang] if arguments.lang else ['ko', 'en']:
            proofs(language)
