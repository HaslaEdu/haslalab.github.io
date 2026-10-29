"""Typeset checked, independently written explanations in the A4 study template.

No answer-only or incomplete set is advertised as a worked solution. Reuses
original vector figures, with the source's original coordinate rectangles.
"""
import json
import math
import re
import sys
from pathlib import Path

import pymupdf as fitz
from kphe_print_build import A4, FONT, INPUT, OUTPUT, frame, text, identity, measure

ROOT = Path(__file__).resolve().parents[1]
INK = (0.05, 0.05, 0.05)


def wrap(value, width, size=9):
    lines, line = [], ''
    for ch in value:
        if ch == '\n' or (line and measure(line + ch, size) > width):
            lines.append(line.rstrip())
            line = '' if ch == '\n' else ch
        else:
            line += ch
    if line:
        lines.append(line.rstrip())
    return lines


def paragraphs(page, x, y, width, values, size=9):
    for value in values:
        for line in wrap(value, width, size):
            text(page, (x, y, x + width, y + 15), line, size)
            y += size * 1.6
        y += 8
    return y


def arrow(page, start, end):
    page.draw_line(start, end, width=.8, color=INK)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    for off in (-.45, .45):
        p = (end[0] - 6 * math.cos(angle + off), end[1] - 6 * math.sin(angle + off))
        page.draw_line(end, p, width=.8, color=INK)


def diagram(page, x, y, width, spec):
    if spec['type'] == 'pv_cycle':
        ox, oy = x + 40, y + 130
        arrow(page, (ox, oy), (x + width - 10, oy))
        arrow(page, (ox, oy), (ox, y + 5))
        pts = {'A': (ox + 45, oy - 40), 'B': (ox + 45, oy - 95),
               'C': (ox + 135, oy - 95), 'D': (ox + 135, oy - 40)}
        for key, pos in pts.items():
            text(page, (pos[0] + 3, pos[1] - 17, pos[0] + 25, pos[1]), key, 8)
        for s, e in [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]:
            arrow(page, pts[s], pts[e])
        text(page, (x + width - 60, oy + 6, x + width, oy + 22), 'V/V₀', 8)
        text(page, (x + 5, y, x + 35, y + 20), 'P/P₀', 8)
        return 165
    return 0


def build(year, part, items, manifest):
    entry = next(y for y in manifest['years'] if y['y'] == year)
    key = entry['keys'][part]
    items = sorted(items, key=lambda q: q['number'])
    if [q['number'] for q in items] != list(range(1, len(key) + 1)):
        raise ValueError(f'Incomplete explanation set: {year} {part}')
    for q, expected in zip(items, key):
        answers = q.get('accepted_answers', [q['answer']])
        official = expected if isinstance(expected, list) else [expected]
        if set(answers) != set(official) or q.get('status') != 'verified' or not q.get('explanation'):
            raise ValueError(f'Unverified explanation: {year} {part} {q["number"]}')
    title, level = identity(manifest, entry, part)
    doc = fitz.open()
    source = fitz.open(INPUT / f'KPhE_{year[:4]}_{part}_KO.pdf')
    column = 2
    for i, q in enumerate(items):
        def paragraph_height(values, size):
            return sum(len(wrap(value, 246, size)) * size * 1.6 + 8 for value in values)
        estimated = 31 + paragraph_height(q['explanation'], 9)
        if q.get('caveat'):
            estimated += paragraph_height(['[원문·정답 유의사항] ' + q['caveat']], 8)
        if q.get('formula'):
            estimated += 6 + paragraph_height(q['formula'], 8)
        if q.get('figure'):
            r = fitz.Rect(q['figure']['rect'])
            estimated += min(155, 246 * r.height / r.width) + 12
        if q.get('diagram', {}).get('type') == 'pv_cycle':
            estimated += 165
        wide = estimated > 690
        if wide or column >= 2:
            page = doc.new_page(width=A4.width, height=A4.height)
            column = 0
            if not wide:
                page.draw_line((297.6, 76), (297.6, 782), color=(.7, .7, .7), width=.4)
        page = doc[-1]
        x, y, width = (38 if column == 0 else 310), 82, (519 if wide else 246)
        answers = q.get('accepted_answers', [q['answer']])
        label = ' / '.join('①②③④⑤'[a - 1] for a in answers)
        text(page, (x, y, x + width, y + 23), f'{q["number"]}. 정답 {label}', 11)
        y += 31
        figure = q.get('figure')
        if figure:
            fig_source = source if Path(figure['source']).name == f'KPhE_{year[:4]}_{part}_KO.pdf' else fitz.open(INPUT / figure['source'])
            clip = fitz.Rect(figure['rect'])
            if not (0 < figure['page'] <= len(fig_source)) or clip.is_empty:
                raise ValueError('Invalid figure rectangle')
            h = min(155, width * clip.height / clip.width)
            page.show_pdf_page(fitz.Rect(x, y, x + width, y + h), fig_source, figure['page'] - 1, clip=clip)
            y += h + 12
        if q.get('diagram'):
            y += diagram(page, x, y, width, q['diagram'])
        if q.get('caveat'):
            y = paragraphs(page, x, y, width, ['[원문·정답 유의사항] ' + q['caveat']], 8)
        y = paragraphs(page, x, y, width, q['explanation'])
        if q.get('formula'):
            page.draw_line((x, y), (x + width, y), color=(.7, .7, .7), width=.4)
            y = paragraphs(page, x, y + 6, width, q['formula'], 8)
        if y > 778:
            raise ValueError(f'Solution overflow {year} {part} #{q["number"]}: {y}')
        column = 2 if wide else column + 1
    for i in range(len(doc)):
        frame(doc[i], title, level + ' · 풀이 해설', i + 1, len(doc), False)
        text(doc[i], (34, 793, 561, 810), 'HaslaLab 자체 작성 해설 · 공식 해설 아님 · 정답은 한국물리학회 정답표와 대조', 6.5)
    target = OUTPUT / f'KPhE_{year[:4]}_{part}S.pdf'
    doc.set_metadata({'title': f'{title} {level} 풀이 해설', 'author': 'HaslaLab 자체 작성',
                      'subject': 'Independent worked explanations checked against the official answer key'})
    doc.subset_fonts()
    doc.save(target, garbage=4, deflate=True)
    return 'pdfx/kphe/' + target.name


def main():
    manifest = json.loads((ROOT / 'tools/theory/kphe.json').read_text(encoding='utf-8'))
    overlay_path = ROOT / 'tools/kphe_print.json'
    overlay = json.loads(overlay_path.read_text(encoding='utf-8'))
    collection = {}
    for path in sorted((ROOT / 'tools/kphe_solutions').glob('*.json')):
        match = re.match(r'(\d{4}-\d)', path.name)
        if not match:
            continue
        year = match.group(1)
        for part, items in json.loads(path.read_text(encoding='utf-8')).items():
            if not part.startswith('_'):
                if part in collection.setdefault(year, {}):
                    raise ValueError(f'Duplicate solutions {year} {part}')
                collection[year][part] = items
    count = 0
    for year, parts in collection.items():
        for part, items in parts.items():
            if sys.argv[1:] == ['ab'] and part[-1] not in 'ab':
                continue
            filename = build(year, part, items, manifest)
            overlay['kphe'][year]['f'][part]['sol'] = filename
            count += 1
    overlay_path.write_text(json.dumps(overlay, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Checked A4 solution sets: {count}')


if __name__ == '__main__':
    main()
