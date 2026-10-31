"""Independent installed-face, real-outline and Poppler QA of repaired EN PDFs."""
from pathlib import Path
from collections import Counter
from io import BytesIO
import argparse, gc, hashlib, importlib, json, math, os, re, subprocess
import numpy as np
import cv2
import pymupdf as fitz
import pikepdf
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
import pdf_original_style_audit as native
from pdf_original_image_ink import image_programs
from cpho_original_latin_fonts import face, simsun

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path(os.environ.get('CPHO_EN_REPAIR_BASE', 'D:/CodexBuilds/Hasla-original-style-20261031/english-face-repair'))
cv2.setNumThreads(1)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def signature(g):
    return (g['c'], g['gid'], g['font'], g['size'], tuple(g['origin']), tuple(g['color']), g['render_type'])


def normal(name):
    return re.sub('[^a-z0-9]', '', name.lower())


def outline(font, gid):
    glyphs = font.getGlyphSet(); name = font.getGlyphOrder()[gid]
    pen = DecomposingRecordingPen(glyphs); glyphs[name].draw(pen)
    return pen.value


def embedded_ascii_coverage(b):
    """Explain why a nominal embedded cmap is not a full English donor."""
    plans = json.loads((b.BASE/'slots.json').read_text(encoding='utf8'))
    roles = {s['source_font']:s['family'] for p in plans['pages'][:4] for s in p['slots']}
    strip = lambda name: re.sub(r'^[A-Z]{6}\+', '', name)
    donor = TTFont(simsun()); donor_cmap = donor.getBestCmap()
    source = fitz.open(b.SOURCE); records = []; seen = set()
    for page in source:
        if page.number >= 4: break
        for resource in page.get_fonts(full=True):
            family_alias = strip(resource[3])
            if family_alias not in roles: continue
            raw = source.extract_font(resource[0])[3]; digest = hashlib.sha256(raw).hexdigest()
            if digest in seen: continue
            seen.add(digest)
            row = dict(resource=resource[4], source_alias=resource[3], role=roles[family_alias], program_sha256=digest,
                       requested_printable_ascii=95, mapped=0, nonempty=0, same_as_installed_simsun=0,
                       nominal_nonempty_but_different=[], empty_or_missing=[])
            font = TTFont(BytesIO(raw))
            cmap = font.getBestCmap() if 'cmap' in font else {}
            cmap = cmap or {}
            for cp in range(32,127):
                name = cmap.get(cp)
                if not name:
                    row['empty_or_missing'].append(chr(cp)); continue
                row['mapped'] += 1; value = outline(font,font.getGlyphID(name))
                if not value and cp != 32:
                    row['empty_or_missing'].append(chr(cp)); continue
                row['nonempty'] += 1
                if row['role']=='serif':
                    expected = outline(donor,donor.getGlyphID(donor_cmap[cp]))
                    width = font['hmtx'].metrics[name][0]/font['head'].unitsPerEm
                    target = donor['hmtx'].metrics[donor_cmap[cp]][0]/donor['head'].unitsPerEm
                    if value == expected and abs(width-target)<1e-9:
                        row['same_as_installed_simsun'] += 1
                    else: row['nominal_nonempty_but_different'].append(chr(cp))
            row['eligible_as_complete_english_face'] = row['nonempty']==95 and (row['role']!='serif' or row['same_as_installed_simsun']==95)
            font.close(); records.append(row)
    source.close(); donor.close()
    result = dict(source_sha256=b.SOURCE_SHA, source_font_resources_modified=False, embedded_resources=records,
                  selection_order=['Complete actual original prose face','Installed same family','Proven same-run Latin counterpart','Explicit last fallback'],
                  limitation='Nominal cmap/GID entries can be stub glyphs. Differing embedded outlines are not assumed semantically valid; only complete verified installed faces supply new prose. All original native resources remain untouched.')
    write(b.AUTHOR/'embedded-latin-coverage.json',result)
    return result


def actual_glyph_check(year, source_page, proof_doc, page, language='en'):
    originals = Counter(signature(g) for g in native.glyphs(source_page))
    additions = []
    for glyph in native.glyphs(page):
        key = signature(glyph)
        if originals[key]:
            originals[key] -= 1
        elif not glyph['c'].isspace():
            additions.append(glyph)
    fonts = []
    for record in page.get_fonts(full=True):
        if not record[4].startswith(('Translation', 'CaptionTranslation')):
            continue
        font = TTFont(BytesIO(proof_doc.extract_font(record[0])[3]))
        names = {normal(n.toUnicode()) for n in font['name'].names}
        names.add(normal(record[3])); fonts.append((names, font))
    donor_paths = [ROOT/'tools/ko/fonts'/name for name in ['NotoSerifCJKkr-Regular.otf','NotoSansCJKkr-Regular.otf']] if language=='ko' else [simsun()]
    if language=='en' and year in [2007, 2022]:
        donor_paths.append(face(year, 'sans'))
    donors = [TTFont(path) for path in donor_paths]
    failures = []; checked = 0; ascii_checked = 0; contours = {}
    def cached_outline(font, gid):
        key = id(font), gid
        if key not in contours: contours[key] = outline(font, gid)
        return contours[key]
    for glyph in additions:
        if glyph['c'] == '\x00':
            failures.append(dict(glyph=glyph, reason='new NUL')); continue
        matches = [font for names, font in fonts if normal(glyph['font']) in names]
        if not matches:
            failures.append(dict(glyph=glyph, reason='unrecognized added glyph resource')); continue
        font = matches[0]; actual = cached_outline(font, glyph['gid'])
        family = font['name'].getDebugName(1)
        donor = next((f for f in donors if f['name'].getDebugName(1) == family), None)
        if donor is None:
            failures.append(dict(glyph=glyph, reason='unreviewed donor family', family=family)); continue
        cmap = donor.getBestCmap(); glyph_name = cmap.get(ord(glyph['c']))
        if glyph_name is None:
            failures.append(dict(glyph=glyph, reason='donor has no semantic cmap glyph')); continue
        expected = cached_outline(donor, donor.getGlyphID(glyph_name))
        width = font['hmtx'].metrics[font.getGlyphOrder()[glyph['gid']]][0]
        expected_width = donor['hmtx'].metrics[glyph_name][0]
        if not actual or actual != expected or width != expected_width or width <= 0:
            failures.append(dict(glyph=glyph, reason='empty/different actual outline or advance', width=width, expected_width=expected_width))
        checked += 1; ascii_checked += ord(glyph['c']) < 128
    for names, font in fonts: font.close()
    for donor in donors: donor.close()
    return dict(new_nonspace_glyphs=len(additions), actual_outlines_and_advances_checked=checked,
                actual_ascii_outlines_checked=ascii_checked, failures=failures,
                method='Actual trace GID decomposed contours and hmtx compared with the complete verified donor face, not nominal cmap/hasGlyph alone')


def render(path, page, target, dpi):
    result = subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', str(dpi), '-singlefile', '-png', str(path), str(target)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    with Image.open(target.with_suffix('.png')) as image:
        data = np.array(image.convert('RGB'))
    return data, result.stderr.decode('utf8', errors='replace')


def region(mask, rect, scale):
    x0, y0, x1, y1 = rect
    mask[max(0, math.floor(y0*scale)):min(mask.shape[0], math.ceil(y1*scale)),
         max(0, math.floor(x0*scale)):min(mask.shape[1], math.ceil(x1*scale))] = True


def audit(year, dpi=110, language='en'):
    b = importlib.import_module(f'cpho_{year}_original_build')
    path = BUILD / str(year) / 'editions' / f'CPhO_{year}_T_{language.upper()}.pdf'
    folder = BUILD / str(year) / ('qa-poppler'if language=='en'else'qa-poppler-ko'); folder.mkdir(parents=True, exist_ok=True)
    report = dict(year=year, pdf=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), source_sha256=b.SOURCE_SHA,
                  renderer='Poppler pdftoppm', dpi=dpi, prose_antialias_guard_px=1, pages=[], passed=True, warnings=[])
    report['embedded_face_coverage'] = embedded_ascii_coverage(b)
    plans = json.loads((b.BASE/'slots.json').read_text(encoding='utf8'))
    build = json.loads(path.with_suffix('.build.json').read_text(encoding='utf8'))
    source = fitz.open(b.SOURCE); proof = fitz.open(path)
    def page_groups(file):
        with pikepdf.Pdf.open(file) as pdf:
            # These reviewed original groups contain only three Name values.
            # Dictionary key order has no PDF rendering semantics.
            return [None if p.obj.get('/Group') is None else {str(k):str(v) for k,v in p.obj.Group.items()} for p in pdf.pages]
    source_groups = page_groups(b.SOURCE); proof_groups = page_groups(path)
    for index in range(4):
        number = index + 1; scale = dpi/72
        spec = json.loads((BUILD/str(year)/'qa'/path.stem/f'page{number:02}-spec.json').read_text(encoding='utf8'))
        old, warning = render(b.SOURCE, number, folder/f'source-{number}', dpi)
        if warning: report['warnings'].append(dict(file=b.SOURCE.name, page=number, warning=warning))
        current, warning = render(path, number, folder/f'proof-{number}', dpi)
        if warning: report['warnings'].append(dict(file=path.name, page=number, warning=warning))
        unchanged, warning = render(b.BASE/'native'/f'page{number:02}.pdf', 1, folder/f'native-{number}', dpi)
        allowed = np.zeros(old.shape[:2], bool)
        for box in spec['allowed_rects']: region(allowed, box, scale)
        padded = cv2.dilate(allowed.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        difference = np.any(old != current, axis=2)
        outside = difference & ~padded
        mutable = np.zeros(old.shape[:2], bool)
        if year == 2022:
            from cpho_2022_original_qa import label_mask
            labels = [l for l in build['raster_label_translation'] if l['page'] == number]
            mutable = label_mask(mutable.shape, scale, labels)
        elif year == 2006:
            from cpho_2006_original_captions import CAPTIONS
            for caption in CAPTIONS:
                if caption['page'] == number: region(mutable, caption['comparison_rect'], scale)
        original_ink = (unchanged.min(axis=2) < 250) & ~mutable
        ink_change = np.any(unchanged != current, axis=2) & original_ink
        inherited_edge = np.zeros(ink_change.shape, bool)
        if year == 2006 and number == 2:
            edges = np.zeros(ink_change.shape, bool); footer = np.zeros(edges.shape, bool)
            for item in source[index].get_image_info():
                box = item['bbox']; whole = np.zeros(edges.shape, bool); region(whole, box, scale)
                inside = cv2.erode(whole.astype(np.uint8), np.ones((3,3), np.uint8)).astype(bool)
                edges |= whole & ~inside
            for slot in plans['pages'][index]['slots']:
                if slot.get('overlay') is False: region(footer, slot['allowed_rect'], scale)
            inherited_edge = ink_change & footer & edges
            ink_change &= ~inherited_edge
        glyphs = actual_glyph_check(year, source[index], proof, proof[index], language)
        row = dict(page=number, changed_pixels_outside_prose=int(outside.sum()), raw_unexpanded_outline_fringe_pixels=int((difference&~allowed).sum()),
                   changed_pixels_in_original_visible_ink=int(ink_change.sum()), inherited_under_image_footer_edge_pixels=int(inherited_edge.sum()),
                   original_prose_antialias_mix_pixels=int((np.any(unchanged != old, axis=2)&original_ink).sum()),
                   original_page_group_identical=source_groups[index]==proof_groups[index],
                   original_image_and_smask_programs_identical=image_programs(source, source[index])==image_programs(proof, proof[index]), real_glyphs=glyphs)
        row['passed'] = not (np.any(outside) or np.any(ink_change) or glyphs['failures']) and row['original_page_group_identical'] and row['original_image_and_smask_programs_identical']
        report['pages'].append(row); report['passed'] &= row['passed']
        write(folder/'audit.partial.json', report)
        print(year, number, 'Poppler outside', row['changed_pixels_outside_prose'], 'native ink', row['changed_pixels_in_original_visible_ink'],
              'outline failures', len(glyphs['failures']), flush=True)
        del old, current, unchanged, allowed, padded, difference, mutable, original_ink, ink_change, inherited_edge
        gc.collect(); fitz.TOOLS.store_shrink(100)
    source.close(); proof.close()
    write(folder/'audit.json', report)
    write(b.AUTHOR/f'qa-{language}-same-face-poppler.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--years', nargs='+', type=int, default=[2006,2007,2022]); parser.add_argument('--dpi', type=int, default=110); parser.add_argument('--language', choices=['en','ko'],default='en')
    args = parser.parse_args(); passed = True
    for year in args.years: passed &= audit(year, args.dpi,args.language)['passed']
    raise SystemExit(not passed)
