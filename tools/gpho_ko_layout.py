"""Korean GPhO solutions, retaining original page geometry and untouched figures.

The region translations are deliberately explicit and reviewable. No online
machine-translation service is used. Rebuild with ``python tools/gpho_ko_layout.py``.
Original PDF input files live in tmp/gpho/originals (downloaded from the archive).
"""
import html
import json
import pathlib
import re
import urllib.request
import pymupdf as fitz

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tmp/gpho/originals'
DATA = ROOT / 'tools/ko/gpho'
OUT = ROOT / 'pdf/gpho'
PARTS = {2016: [(0, 2), (3, 4), (5, 6)],
         2017: [(0, 1), (2, 2), (3, 4)],
         2019: [(1, 3), (4, 6), (7, 10)],
         2022: [(1, 2), (3, 4), (5, 7)]}
FIGURE_CLIPS = {2017: {2: [(200, 175, 292, 339)],
                       3: [(204, 243, 283, 386)]}}
MATH_CLIPS = {2016: {0: [(105,742,203,781), (385,284,485,323)],
                     5: [(110,356,198,395)]},
              2019: {5: [(120,518,169,558)]},
              2022: {1: [(345,123,527,160)]}}
NARROW = {(2017, '3.3'), (2017, '3.4'), (2017, '3.7'),
          (2017, '3.11'), (2017, '4.8'), (2017, '4.11'),
          (2017, '4.12'), (2017, '4.13')}
# A tall radical/integral from the following equation can touch the preceding
# paragraph's bounding box. These original glyphs are restored as PDF vectors.
PARTIAL_MATH = {(2016, '1.47'), (2016, '1.58'), (2016, '6.11'),
                (2019, '6.21'), (2022, '2.37')}

def groups(doc):
    common = set(('the and that then this with from for can has are was will when but which where have into than not any before after during now since because thus hence points part problem page const '
                  'angle taking time derivative obtain writing get straightforward integration yields negative substituting numerically boltzmann law formula nuber number units lost furthermore value therefore shock wave one other words phase diagram correctly drawn figure arrow shown start end alternatively instead using kepler student could write days bringing all expressions together point within leads negligible change temperature approach energy considerations exact answer propelling rotation subtract subtracting liquid be').split())
    output = []
    for pi, page in enumerate(doc):
        blocks = [b for b in page.get_text('blocks') if b[6] == 0]
        parent = list(range(len(blocks)))
        def root(i):
            while parent[i] != i:
                i = parent[i]
            return i
        def column(block):
            return 0 if block[0] < 294 else 1
        for i, a in enumerate(blocks):
            for j, b in enumerate(blocks[i+1:], i+1):
                if column(a) == column(b) and min(a[3], b[3]) + .2 >= max(a[1], b[1]):
                    parent[root(j)] = root(i)
        merged = {}
        for i in range(len(blocks)):
            merged.setdefault(root(i), []).append(i)
        for indices in merged.values():
            text = '\n'.join(blocks[i][4].strip() for i in indices)
            if not set(re.findall(r'[A-Za-z]{2,}', text.lower())) & common:
                continue
            rect = [min(blocks[i][0] for i in indices), min(blocks[i][1] for i in indices),
                    max(blocks[i][2] for i in indices), max(blocks[i][3] for i in indices)]
            output.append({'id': f'{pi+1}.{min(indices)}', 'rect': rect, 'text': text,
                           'blocks': indices})
    return output

def automatic(text):
    t = text.strip()
    m = re.fullmatch(r'— page (\d+) of (\d+) —', t)
    if m:
        return f'- {m[1]} / {m[2]} -'
    m = re.fullmatch(r'PROBLEM (\d+)', t)
    if m:
        return f'문제 {m[1]}'
    return {'Hence,':'따라서,', 'and so':'따라서', 'Then':'그러면',
            'Therefore,':'따라서,', 'and numerically':'수치로 계산하면',
            'Full mark for correct values within 25%':'오차가 25% 이내이면 만점.',
            'Const.':'상수', 'to be':'다음과 같다.'}.get(t)

def build(year):
    SOURCE.mkdir(parents=True, exist_ok=True)
    source_path = SOURCE / f'GPhO_{year}_TS.pdf'
    if not source_path.exists():
        url = f'https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-gpho/{source_path.name}'
        req = urllib.request.Request(url, headers={'User-Agent':'HaslaLab GPhO translation builder'})
        data = urllib.request.urlopen(req, timeout=60).read()
        if not data.startswith(b'%PDF'):
            raise ValueError('Archive response is not a PDF')
        source_path.write_bytes(data)
    original = fitz.open(SOURCE / f'GPhO_{year}_TS.pdf')
    regions = groups(original)
    mapping = json.loads((DATA / f'{year}.json').read_text(encoding='utf8'))
    missing = [r['id'] for r in regions if r['id'] not in mapping and automatic(r['text']) is None]
    if missing:
        raise ValueError(f'{year}: untranslated regions {missing}')
    translated = fitz.open(stream=original.tobytes(), filetype='pdf')
    # Local fonts are embedded, making the PDF portable and searchable.
    archive = fitz.Archive(str(ROOT / 'tools/ko/fonts'))
    css = '''@font-face {font-family: Korean; src: url(NotoSansKR-Regular.ttf);}
      @font-face {font-family: Latin; src: url(DejaVuSans.ttf);}
      * {margin:0;padding:0;} body {font-family:Korean,Latin,sans-serif;
      font-size:9.1pt;line-height:1.12;} sup,sub{font-size:70%;}'''
    stats = []
    notes = json.loads((DATA / 'notes.json').read_text(encoding='utf8')).get(str(year), {})
    for pi, page in enumerate(translated):
        changes = []
        restores = []
        rawblocks = original[pi].get_text('blocks')
        for r in regions:
            if int(r['id'].split('.')[0]) != pi + 1:
                continue
            text = mapping.get(r['id'], automatic(r['text']))
            if text is None:
                raise ValueError(r['id'])
            rect = fitz.Rect(r['rect'])
            if isinstance(text, dict):
                for en, ko in text['words'].items():
                    for found in original[pi].search_for(en):
                        if found.intersects(rect):
                            changes.append((r, found, ko))
                            page.add_redact_annot(found, fill=(1,1,1))
                continue
            # Whole columns retain their original boundaries.
            if (year, r['id']) in NARROW:
                rect.x0, rect.x1 = 19.2, 193.0
            elif rect.x0 < 22 and rect.y0 < 810:
                rect.x0 = 19.2 if rect.x0 < 294 else 299.85
                rect.x1 = 290.6 if rect.x0 < 294 else 571.1
            elif 294 < rect.x0 < 310 and rect.y0 < 810:
                rect.x0, rect.x1 = 299.85, 571.1
            if (year, r['id']) in PARTIAL_MATH:
                for bi in r['blocks']:
                    block = rawblocks[bi]
                    if not re.search(r'[A-Za-z]{3,}', block[4]):
                        restores.append(fitz.Rect(block[:4]))
            changes.append((r, rect, text))
            page.add_redact_annot(fitz.Rect(r['rect']), fill=(1,1,1))
        if changes:
            page.apply_redactions(images=0, graphics=0)
        for r, rect, text in changes:
            # A slightly larger line box avoids shaving Korean glyph ascenders.
            rect.y1 += .3
            text = re.sub(r'<b>(.*?)</b>', lambda m: '<b style="color:#0000ff">'+m[1]+'</b>'
                          if ('문제 T' in m[1] or 'Part ' in m[1]) else m[0], text, flags=re.S)
            text = re.sub(r'Part ([A-D])\.', r'\1부.', text)
            body = '<div>' + text + '</div>'
            spare, scale = page.insert_htmlbox(rect, body, css=css, archive=archive, scale_low=.50)
            if spare < 0:
                raise ValueError(f"Text overflow {year}/{r['id']}")
            stats.append({'id': r['id'], 'scale': round(scale, 4), 'rect': list(rect)})
            if r['id'] in notes:
                note = page.add_text_annot((page.rect.width-17, rect.y0), notes[r['id']], icon='Note')
                note.set_info(title='HaslaLab 번역주', subject=f"원문 대조: {r['id']}")
        for rect in restores:
            page.show_pdf_page(rect, original, pi, clip=rect, overlay=True)
        # Extensible TeX glyphs extend beyond their nominal text bounding boxes.
        # Restore the complete original expression, not just the nominal glyph.
        for bounds in MATH_CLIPS.get(year, {}).get(pi, []):
            rect = fitz.Rect(bounds)
            page.draw_rect(rect, color=None, fill=(1,1,1), overlay=True)
            page.show_pdf_page(rect, original, pi, clip=rect, overlay=True)
        for bounds in FIGURE_CLIPS.get(year, {}).get(pi, []):
            rect = fitz.Rect(bounds)
            page.draw_rect(rect, color=None, fill=(1,1,1), overlay=True)
            page.show_pdf_page(rect, original, pi, clip=rect, overlay=True)
        score_rects = page.search_for('pts')
        score_rects += [r for r in page.search_for('pt') if not any(r.intersects(s) for s in score_rects)]
        score_changes = [(rect, '점') for rect in score_rects]
        for rect, ko in score_changes:
            page.add_redact_annot(rect, fill=(1,1,1))
        if score_changes:
            page.apply_redactions(images=0, graphics=0)
        for rect, ko in score_changes:
            page.insert_htmlbox(rect + (0,-.2,1,.5), ko, css=css, archive=archive, scale_low=.5)
    OUT.mkdir(parents=True, exist_ok=True)
    generated = []
    for part, (start, end) in enumerate(PARTS[year], 1):
        d = fitz.open()
        d.insert_pdf(translated, from_page=start, to_page=end)
        name = f'GPhO_{year}_T{part}_S_KO.pdf'
        path = OUT / name
        d.set_metadata({'title':f'GPhO {year} T{part} 한국어 해설',
                        'subject':'원문 해설 한국어 번역 · 원문 오탈자에 대한 번역주 포함', 'author':'HaslaLab'})
        d.subset_fonts()
        d.save(path, garbage=4, deflate=True)
        generated.append({'file':name,'pages':len(d),'bytes':path.stat().st_size})
    (SOURCE / f'{year}-layout-report.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf8')
    return generated

if __name__ == '__main__':
    import sys
    years = [int(y) for y in sys.argv[1:]] or list(PARTS)
    for year in years:
        print(json.dumps({'year':year,'files':build(year)},ensure_ascii=False))
