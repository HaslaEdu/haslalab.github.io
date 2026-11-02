"""CPhO 2024: fixed prose slots in the actual Chinese question/answer PDFs.

Original fonts/resources, mathematical text, graphics and page geometry remain
native. This profile interprets the problem PDF's anonymised CIDFont aliases
using the embedded TrueType family/style records, never by guessing the alias.
The earlier third-party English 10/30-page layouts are not design templates.
"""
from pathlib import Path
from collections import defaultdict
from io import BytesIO
from functools import lru_cache
import argparse, gc, hashlib, json, os, re, statistics, xml.etree.ElementTree as ET
import pikepdf
import pymupdf as fitz
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
import cpho_cjk_translate as cjk
from cpho_original_style import source_characters
from pdf_original_text_ops import native_form_glyphs
from pdf_original_image_ink import image_ink_regions
from pdf_original_text_ops import suppress_prose
from pdf_original_style_fonts import subset_font
from cpho_2024_original_fonts import font_paths as dengxian_faces
from cpho_2024_original_fonts import simsun_path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'tmp/original-style-repair/cpho2024'
BUILD = Path(os.environ.get('CPHO_2024_BUILD_DIR', 'D:/CodexBuilds/Hasla-original-style-20261031/cpho2024'))
AUTHOR = ROOT / 'tools/ko/cpho/2024/original'
SOURCES = {
    'T': ('CPhO_2024_Chinese_original.pdf', '894111e1298dc785e9447252219e1f72fe0bb3fdf35b7573affec64f844ff6f6'),
    'TS': ('CPhO_2024_TS_ZH.pdf', '30c2e4b88055147628193bccc11cf4137ac55124b8c1ea79df6a1801170ad818'),
}
HAN = re.compile('[\u3400-\u9fff]')
PUNCTUATION = '，。；：！？、（）【】《》“”‘’…—,.():;!?[]'


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def source_path(kind):
    name, expected = SOURCES[kind]
    path = ROOT / 'tmp/original-style-sources' / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Original Chinese source SHA mismatch')
    return path


def normalize_font(name):
    # CIDFont+F4 is a real alias; only a six-capital-letter subset tag is stripped.
    return re.sub(r'^[A-Z]{6}\+', '', name)


def font_profiles(kind):
    records = json.loads((AUTHOR / 'source-fonts.json').read_text(encoding='utf8'))
    result = {}
    for item in records:
        if item['kind'] != kind:
            continue
        alias = normalize_font(item['font'])
        if not item.get('names'):
            continue
        family = next((n for n in item['names']['1'] if n.isascii()), item['names']['1'][0])
        is_cjk = family in ['SimSun', 'SimHei', 'DengXian', 'Dengxian', 'Microsoft YaHei', 'MS Gothic', 'MS Mincho']
        sans = family in ['SimHei', 'DengXian', 'Dengxian', 'Microsoft YaHei', 'MS Gothic', 'Calibri', 'Arial']
        profile = dict(actual_family=family, family='sans' if sans else 'serif', cjk=is_cjk,
                       bold=item['weight'] >= 700, italic=abs(item['italicAngle']) > .01,
                       italic_angle=item['italicAngle'], program_sha256=item['program_sha256'])
        if alias in result and result[alias] != profile:
            # Separate subsets of a family may have different raw programs;
            # the stylistic fields must nevertheless agree exactly.
            before = {k: v for k, v in result[alias].items() if k != 'program_sha256'}
            after = {k: v for k, v in profile.items() if k != 'program_sha256'}
            if before != after:
                raise ValueError('Ambiguous font style: ' + alias)
        result[alias] = profile
    return result


def natural(char, profiles):
    value = char['c']
    if char['size'] < 8.9 or value in '−－＋＝＜＞±×÷':
        return False
    info = profiles.get(normalize_font(char['font']))
    if not info or not info['cjk']:
        return False
    return bool(HAN.search(value)) or value.isspace() or value in PUNCTUATION


def prose_rows(chars, profiles):
    """Original visible baselines; local font-aware punctuation classifier."""
    rows = []
    for char in sorted((c for c in chars if natural(c, profiles) and HAN.search(c['c'])), key=lambda c: (c['origin'][1], c['origin'][0])):
        row = next((r for r in rows[-4:] if abs(r['baseline'] - char['origin'][1]) < 1.2), None)
        if row is None:
            row = dict(baseline=char['origin'][1], chars=[])
            rows.append(row)
        row['chars'].append(char)
    used = {c['index'] for r in rows for c in r['chars']}
    for char in chars:
        if char['index'] in used or not natural(char, profiles):
            continue
        candidates = [r for r in rows if abs(r['baseline'] - char['origin'][1]) < 1.2 and
                      (any(c['block'] == char['block'] and c['line'] == char['line'] for c in r['chars']) or
                       min(c['origin'][0] for c in r['chars']) - 32 <= char['origin'][0] <= max(c['bbox'][2] for c in r['chars']) + 18)]
        if candidates:
            min(candidates, key=lambda r: abs(r['baseline'] - char['origin'][1]))['chars'].append(char)
    for row in rows:
        row['chars'].sort(key=lambda c: c['origin'][0])
        row['size'] = statistics.median(c['size'] for c in row['chars'])
    return sorted(rows, key=lambda r: (r['baseline'], min(c['origin'][0] for c in r['chars'])))


def traced_style(page, char):
    found = [s for s in page.get_texttrace() if normalize_font(s['font']) == normalize_font(char['font']) and
             any(chr(g[0]) == char['c'] and abs(g[2][0] - char['origin'][0]) < .03 and abs(g[2][1] - char['origin'][1]) < .03 for g in s['chars'])]
    if not found:
        raise ValueError('Original glyph has no actual text trace: ' + repr(char))
    modes = {s['type'] for s in found}
    mode = 2 if {0, 1} <= modes else found[0]['type']
    stroke = next((s['linewidth'] for s in found if s['type'] == 1), None)
    return dict(render_mode=mode, line_width=stroke, miter_limit=10)


def trace_style_map(page):
    result = {}
    for trace in page.get_texttrace():
        for cp, gid, origin, bbox in trace['chars']:
            key = chr(cp), normalize_font(trace['font']), round(origin[0], 3), round(origin[1], 3)
            item = result.setdefault(key, dict(modes=set(), line_width=None))
            item['modes'].add(trace['type'])
            if trace['type'] == 1:
                item['line_width'] = trace['linewidth']
    for item in result.values():
        modes = item.pop('modes')
        item['render_mode'] = 2 if {0, 1} <= modes else min(modes)
        item['miter_limit'] = 10
    return result


def glyph_outline_boxes(page):
    root = ET.fromstring(page.get_svg_image(text_as_path=True))
    paths = {e.get('id'): e.get('d') for e in root.iter() if e.tag.endswith('path') and e.get('id')}
    result = {}
    for use in root.iter():
        if not use.tag.endswith('use') or 'data-text' not in use.attrib:
            continue
        found = re.search(r'matrix\(([^)]+)\)', use.get('transform', ''))
        if not found:
            continue
        matrix = tuple(float(v) for v in found[1].replace(',', ' ').split())
        name = use.get('{http://www.w3.org/1999/xlink}href', '').lstrip('#')
        if name not in paths:
            continue
        pen = BoundsPen(None)
        parse_path(paths[name], TransformPen(pen, matrix))
        if pen.bounds:
            key = use.get('data-text'), round(matrix[-2], 3), round(matrix[-1], 3)
            result[key] = list(fitz.Rect(result[key]) | fitz.Rect(pen.bounds)) if key in result else list(pen.bounds)
    return result


def extract(kind):
    source = source_path(kind)
    profiles = font_profiles(kind)
    doc = fitz.open(source)
    out = BASE / kind
    text = AUTHOR / kind
    out.mkdir(parents=True, exist_ok=True)
    text.mkdir(parents=True, exist_ok=True)
    pages = []
    summaries = []
    for index, page in enumerate(doc):
        chars = source_characters(page)
        styles = trace_style_map(page)
        outlines = glyph_outline_boxes(page)

        def char_style(char):
            key = char['c'], normalize_font(char['font']), round(char['origin'][0], 3), round(char['origin'][1], 3)
            if key not in styles:
                return traced_style(page, char)
            return styles[key]

        def ink_box(char):
            key = char['c'], round(char['origin'][0], 3), round(char['origin'][1], 3)
            return fitz.Rect(outlines.get(key, char['bbox']))

        forms = native_form_glyphs(source, index + 1)
        protected = {c['index'] for c in chars if any(abs(c['origin'][0] - g['origin'][0]) < .03 and abs(c['origin'][1] - g['origin'][1]) < .03 for g in forms)}
        rows = prose_rows([c for c in chars if c['index'] not in protected], profiles)
        slots = []
        descriptions = []
        # Conservative preliminary image obstacles; final proof uses the
        # clip-aware nontext control, not un-clipped SMask projection.
        images = image_ink_regions(doc, page)
        column_right = 566.5 if kind == 'T' else 540.0
        for row_index, row in enumerate(rows):
            owned = [c for c in row['chars'] if not c['c'].isspace()]
            owned_ids = {c['index'] for c in owned}
            locked = [c for c in chars if c['index'] not in owned_ids and not c['c'].isspace() and
                      ink_box(c).y0 < row['baseline'] + row['size'] * .15 and ink_box(c).y1 > row['baseline'] - row['size']]
            groups = []
            for char in sorted(owned, key=lambda c: c['origin'][0]):
                current_state = char_style(char)
                style = normalize_font(char['font']), char['size'], char['color'], current_state['render_mode'], current_state['line_width']
                previous = char_style(groups[-1][-1]) if groups else None
                same = groups and style == (normalize_font(groups[-1][-1]['font']), groups[-1][-1]['size'], groups[-1][-1]['color'], previous['render_mode'], previous['line_width'])
                obstacle = groups and any(groups[-1][-1]['origin'][0] + .1 < c['origin'][0] < char['origin'][0] - .1 for c in locked)
                if same and not obstacle and char['origin'][0] - groups[-1][-1]['bbox'][2] < 3:
                    groups[-1].append(char)
                else:
                    groups.append([char])
            row_slots = []
            for group_index, group in enumerate(groups):
                first = group[0]
                profile = profiles[normalize_font(first['font'])]
                box = fitz.Rect(first['bbox'])
                for char in group[1:]:
                    box |= fitz.Rect(char['bbox'])
                future = [c for c in locked if c['origin'][0] > group[-1]['origin'][0] + .1]
                right = min([column_right, *[ink_box(c).x0 - .4 for c in future]])
                # A separately styled prose run is also an original boundary;
                # do not fill over its bold/regular or serif/sans counterpart.
                later = [g[0]['origin'][0] - .4 for g in groups[group_index + 1:]]
                right = min([right, *later])
                for image in images:
                    image_box = fitz.Rect(image['ink_rect'])
                    if image_box.x0 > group[-1]['origin'][0] + .1 and image_box.y0 < box.y1 and image_box.y1 > box.y0:
                        right = min(right, image_box.x0 - .4)
                value = ''.join(c['c'] for c in group)
                keep = all(c in '，；：！？、（）【】《》“”‘’…—,.():;!?[]' for c in value)
                if value in ['。', '；']:
                    keep = False
                if value == '一':
                    keep = True  # Potential CJK-font mathematical minus; review in context.
                slot = dict(id=f'{index + 1}-{row_index}-{group_index}', source_page=index + 1, row=row_index,
                            source=value, source_font=first['font'], actual_source_family=profile['actual_family'],
                            family=profile['family'], bold=profile['bold'], italic=profile['italic'], italic_angle=profile['italic_angle'],
                            size=first['size'], flags=first['flags'], color=first['color'], origin=list(first['origin']),
                            source_rect=list(box), right=right, source_characters=group, retain_native=keep,
                            allowed_rect=[box.x0, first['origin'][1] - first['size'] * 1.1, max(box.x0, right), first['origin'][1] + first['size'] * .3],
                            **char_style(first))
                slots.append(slot)
                row_slots.append(slot['id'])
            neighbors = [c for c in chars if abs(c['origin'][1] - row['baseline']) < row['size'] * .32]
            descriptions.append(dict(row=row_index, baseline=row['baseline'], source=''.join(c['c'] for c in sorted(neighbors, key=lambda c: c['origin'][0])), slots=row_slots))
        pages.append(dict(source_page=index + 1, page_rect=list(page.rect), slots=slots, rows=descriptions,
                          protected_form_glyph_origins=[g['origin'] for g in forms], form_han=[g for g in forms if HAN.search(g['c'])]))
        summaries.append(dict(page=index + 1, rows=len(rows), slots=len(slots), untranslated_slots=sum(not s['retain_native'] for s in slots)))
        print(kind, summaries[-1], flush=True)
        gc.collect()
        fitz.TOOLS.store_shrink(100)
    data = dict(kind=kind, source=source.relative_to(ROOT).as_posix(), source_sha256=SOURCES[kind][1], pages=pages,
                extraction_status='PRELIMINARY: review native glyph/image actual ink boundaries and figure-language ownership before typesetting.')
    write(out / 'slots.json', data)
    write(text / 'extraction-summary.json', summaries)
    lines = []
    for page in pages:
        lines.append('\nPAGE ' + str(page['source_page']))
        byid = {s['id']: s for s in page['slots']}
        for row in page['rows']:
            lines.append('ROW ' + str(row['row']) + ' | ' + row['source'])
            for identity in row['slots']:
                s = byid[identity]
                lines.append(identity + '\t' + s['source'] + '\t' + str(round(s['right'] - s['origin'][0], 2)))
        target = text / f'page{page["source_page"]:02}.tsv'
        replace_empty = not target.exists()
        if target.exists():
            existing = [line.split('\t', 2) for line in target.read_text(encoding='utf8').splitlines() if line.strip()]
            old_ids = {line[0] for line in existing}
            new_ids = {s['id'] for s in page['slots']}
            if old_ids != new_ids:
                if any(part for line in existing for part in line[1:]):
                    raise ValueError('Manual translation IDs need an explicit migration: ' + str(target))
                replace_empty = True
        if replace_empty:
            target.write_text('\n'.join(s['id'] + '\t\t' for s in page['slots']) + '\n', encoding='utf8')
    (out / 'source-slots.txt').write_text('\n'.join(lines), encoding='utf8')
    doc.close()
    return data


def data(kind):
    document = json.loads((BASE / kind / 'slots.json').read_text(encoding='utf8'))
    overrides_path = AUTHOR / kind / 'slot-overrides.json'
    overrides = json.loads(overrides_path.read_text(encoding='utf8')) if overrides_path.exists() else {}
    for page in document['pages']:
        for slot in page['slots']:
            slot.update(overrides.get(slot['id'], {}))
    heading_path = AUTHOR / kind / 'heading-recipe.json'
    if heading_path.exists():
        recipe = json.loads(heading_path.read_text(encoding='utf8'))
        document['pages'][recipe['source_page'] - 1]['heading_recipe'] = recipe
    return document


def translations(kind, document):
    result = {}
    for page in document['pages']:
        path = AUTHOR / kind / f'page{page["source_page"]:02}.tsv'
        for line in path.read_text(encoding='utf8').splitlines():
            if not line.strip():
                continue
            identity, ko, en = line.split('\t', 2)
            if identity in result:
                raise ValueError('Duplicate translation slot ' + identity)
            result[identity] = dict(ko=ko, en=en)
    required = {s['id'] for p in document['pages'] for s in p['slots']}
    if set(result) != required:
        raise ValueError('Source/translation slot IDs differ')
    return result


@lru_cache(maxsize=1)
def verified_deng_faces():
    return dengxian_faces()


@lru_cache(maxsize=1)
def verified_simsun_face():
    return simsun_path()


def source_translation_font(slot, lang, kind):
    if lang == 'ko':
        family = 'NotoSerifCJKkr' if slot['family'] == 'serif' else 'NotoSansCJKkr'
        return ROOT / 'tools/ko/fonts' / (family + ('-Bold' if slot['bold'] else '-Regular') + '.otf')
    family = slot['actual_source_family']
    if family == 'SimSun':
        if slot['bold'] or slot['italic']:
            raise ValueError('An unverified SimSun style must not be substituted silently')
        return verified_simsun_face()
    if family in ['DengXian', 'Dengxian', 'SimHei']:
        if slot['italic']:
            raise ValueError('DengXian has no source italic face for this prose')
        return verified_deng_faces()[700 if slot['bold'] else 400]
    if family in ['Microsoft YaHei', 'MS Gothic', 'Calibri', 'Arial']:
        if family == 'Calibri':
            name = 'calibriz' if slot['bold'] and slot['italic'] else 'calibrib' if slot['bold'] else 'calibrii' if slot['italic'] else 'calibri'
        else:
            name = 'arialbi' if slot['bold'] and slot['italic'] else 'arialbd' if slot['bold'] else 'ariali' if slot['italic'] else 'arial'
        return Path('C:/Windows/Fonts') / (name + '.ttf')
    name = 'timesbi' if slot['bold'] and slot['italic'] else 'timesbd' if slot['bold'] else 'timesi' if slot['italic'] else 'times'
    return Path('C:/Windows/Fonts') / (name + '.ttf')


def prepared_fonts(kind, document, texts, lang, subset_files=True):
    needed = defaultdict(str)
    for page in document['pages']:
        for slot in page['slots']:
            if not slot['retain_native']:
                value = texts[slot['id']][lang]
                if value:
                    needed[source_translation_font(slot, lang, kind)] += value
        if page.get('heading_recipe'):
            needed[verified_deng_faces()[700]] += page['heading_recipe']['native_number_text']
    result = {}
    cache = BASE / kind / 'fonts'
    for source, text in needed.items():
        result[source] = subset_font(source, text, cache) if subset_files else source
    return result


def fitting(kind, document, texts, lang, fonts, pages=None):
    objects = {path: fitz.Font(fontfile=str(target)) for path, target in fonts.items()}
    report = []
    for page in document['pages']:
        if pages and page['source_page'] not in pages:
            continue
        for slot in page['slots']:
            text = '' if slot['retain_native'] else texts[slot['id']][lang].strip()
            path = source_translation_font(slot, lang, kind)
            if slot['retain_native'] or not text:
                width = 0
            else:
                width = objects[path].text_length(text, fontsize=slot['size'])
            gap = slot.get(lang + '_word_gap_adjustment', 0)
            width += text.count(' ') * gap
            x, y = slot['origin']
            x += slot.get(lang + '_origin_dx', 0)
            available = slot['right'] - x
            if slot.get('align') == 'right':
                x = slot['right'] - width
            if slot.get('align') == 'center':
                x += (available - width) / 2
            report.append(dict(id=slot['id'], page=page['source_page'], source=slot['source'], text=text, size=slot['size'],
                               font=str(path), width=width, available=available, overflow=max(0, width - available), origin=[x, y],
                               word_gap_adjustment=gap, retain_native=slot['retain_native'], language=lang))
    return report


def preflight(kind, pages=None):
    document = data(kind)
    texts = translations(kind, document)
    report = []
    for lang in ['ko', 'en']:
        fonts = prepared_fonts(kind, document, texts, lang, False)
        rows = fitting(kind, document, texts, lang, fonts, pages)
        report.extend(rows)
        print(kind, lang, 'overflows', sum(r['overflow'] > .02 for r in rows), flush=True)
    write(BASE / kind / 'preflight.json', report)
    return report


def native_page(kind, page):
    source = source_path(kind)
    selected = [c for s in page['slots'] if not s['retain_native'] for c in s['source_characters'] if not c['c'].isspace() and c['index'] not in s.get('retained_source_indices', [])]
    if page.get('heading_recipe'):
        selected.extend(page['heading_recipe']['source_number_glyphs'])
    digest = hashlib.sha256(json.dumps(selected, ensure_ascii=False, sort_keys=True).encode('utf8')).hexdigest()
    core_sha = hashlib.sha256((ROOT / 'tools/pdf_original_text_ops.py').read_bytes()).hexdigest()
    folder = BUILD / kind / 'native'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'page{page["source_page"]:02}.pdf'
    metadata = path.with_suffix('.json')
    expected = dict(source_sha256=SOURCES[kind][1], selection_sha256=digest, suppressor_sha256=core_sha)
    if path.exists() and metadata.exists() and json.loads(metadata.read_text(encoding='utf8')) == expected:
        return path
    raw, count = suppress_prose(source, page['source_page'], selected)
    if count != len(selected):
        raise ValueError('Prose suppression count mismatch')
    path.write_bytes(raw)
    write(metadata, expected)
    return path


def insert_run(page, point, text, slot, path, name):
    mode = slot['render_mode']
    stroke = slot.get('line_width') or 0
    color = tuple(((slot['color'] >> shift) & 255) / 255 for shift in [16, 8, 0])
    page.insert_text(fitz.Point(*point), text, fontsize=slot['size'], fontname=name, fontfile=str(path), color=color, fill=color,
                     render_mode=mode, border_width=stroke / slot['size'] if mode in [1, 2] else .05, miter_limit=slot['miter_limit'])


def compose_heading(page, recipe, source_slots, texts, fonts, lang, kind):
    byid = {s['id']: s for s in source_slots}
    prefix = byid[recipe['prefix_slot']]
    suffix = byid[recipe['suffix_slot']]
    numeric_style = dict(size=recipe['size'], render_mode=0, line_width=None, miter_limit=10, color=recipe['color'])
    parts = [(texts[prefix['id']][lang], prefix, source_translation_font(prefix, lang, kind)),
             (recipe['native_number_text'], numeric_style, verified_deng_faces()[700]),
             (texts[suffix['id']][lang], suffix, source_translation_font(suffix, lang, kind))]
    width = sum(fitz.Font(fontfile=str(fonts[path])).text_length(text, fontsize=style['size']) for text, style, path in parts)
    x = recipe['center_x'] - width / 2
    runs = []
    for text, style, source in parts:
        if not text:
            continue
        name = 'Translation' + hashlib.sha256(str(source).encode('utf8')).hexdigest()[:10]
        insert_run(page, [x, recipe['baseline']], text, style, fonts[source], name)
        runs.append(dict(text=text, source_font=str(source), size=style['size'], render_mode=style['render_mode'], line_width=style['line_width'], origin=[x, recipe['baseline']]))
        x += fitz.Font(fontfile=str(fonts[source])).text_length(text, fontsize=style['size'])
    return dict(source_page=recipe['source_page'], center_x=recipe['center_x'], width=width, runs=runs,
                purpose='Translate one existing centred heading; original title number41 is ordinary prose, not a physical/mathematical value.')


def compose(kind, lang, pages=None, draft=False):
    document = data(kind)
    if pages is None:
        pages = [p['source_page'] for p in document['pages']]
    if not draft:
        reviewed = json.loads((AUTHOR / kind / 'reviewed-pages.json').read_text(encoding='utf8'))
        if any(p not in reviewed for p in pages):
            raise ValueError('Unreviewed translation page')
    texts = translations(kind, document)
    fonts = prepared_fonts(kind, document, texts, lang)
    rows = fitting(kind, document, texts, lang, fonts, pages)
    if any(r['overflow'] > .02 for r in rows):
        write(BASE / kind / ('overflow-' + lang + '.json'), rows)
        raise ValueError('Translation exceeds fixed source slots')
    byid = {r['id']: r for r in rows}
    single_pages = []
    journal = []
    for page in document['pages']:
        if page['source_page'] not in pages:
            continue
        original = native_page(kind, page)
        result = fitz.open(original)
        target = result[0]
        heading = page.get('heading_recipe')
        for slot in page['slots']:
            if heading and slot['id'] in [heading['prefix_slot'], heading['suffix_slot']]:
                continue
            item = byid[slot['id']]
            if not item['text']:
                continue
            source_font = source_translation_font(slot, lang, kind)
            font_path = fonts[source_font]
            name = 'Translation' + hashlib.sha256(str(source_font).encode('utf8')).hexdigest()[:10]
            x, y = item['origin']
            font = fitz.Font(fontfile=str(font_path))
            chunks = re.split('( )', item['text']) if item['word_gap_adjustment'] else [item['text']]
            for chunk in chunks:
                if not chunk:
                    continue
                insert_run(target, [x, y], chunk, slot, font_path, name)
                x += font.text_length(chunk, fontsize=slot['size']) + (item['word_gap_adjustment'] if chunk == ' ' else 0)
        heading_journal = compose_heading(target, heading, page['slots'], texts, fonts, lang, kind) if heading else None
        raw = result.tobytes(garbage=0, deflate=False)
        result.close()
        single_pages.append(raw)
        journal.append(dict(source_page=page['source_page'], fit_report=[r for r in rows if r['page'] == page['source_page']], heading=heading_journal))
        gc.collect()
        fitz.TOOLS.store_shrink(100)
    # Copy complete source page dictionaries, especially /Group. Never merge
    # the completed pages through insert_pdf, which strips transparency groups.
    merged = pikepdf.Pdf.new()
    for raw in single_pages:
        with pikepdf.Pdf.open(BytesIO(raw)) as page_document:
            merged.pages.append(page_document.pages[0])
    folder = BUILD / kind / ('preview' if draft else 'editions')
    folder.mkdir(parents=True, exist_ok=True)
    suffix = '' if len(pages) == len(document['pages']) else '_p' + '-'.join(map(str, pages))
    path = folder / f'CPhO_2024_{kind}_{lang.upper()}{suffix}.pdf'
    merged.save(path, compress_streams=False)
    merged.close()
    write(path.with_suffix('.build.json'), dict(source_sha256=SOURCES[kind][1], source_pages=pages, pages=journal))
    print(path, flush=True)
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['extract', 'preflight', 'build'])
    parser.add_argument('--kind', choices=['T', 'TS'], required=True)
    parser.add_argument('--lang', choices=['ko', 'en'])
    parser.add_argument('--pages', nargs='+', type=int)
    parser.add_argument('--draft', action='store_true')
    args = parser.parse_args()
    if args.command == 'extract':
        extract(args.kind)
    elif args.command == 'preflight':
        preflight(args.kind, args.pages)
    else:
        for language in [args.lang] if args.lang else ['ko', 'en']:
            compose(args.kind, language, args.pages, args.draft)
