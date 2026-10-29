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
from kphe_print_build import identity
from kphe_template import A4, FONT, INPUT, OUTPUT, text, measure, ColumnFlow, readable_formula

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
        status_ok = q.get('status') == 'verified' or (q.get('status') == 'needs_review' and (q.get('caveat') or q.get('review_note')))
        if set(answers) != set(official) or not status_ok or not q.get('explanation'):
            raise ValueError(f'Unverified explanation: {year} {part} {q["number"]}')
    title, level = identity(manifest, entry, part)
    doc = fitz.open()
    source = fitz.open(INPUT / f'KPhE_{year[:4]}_{part}_KO.pdf')
    preserve = int(year[:4]) >= 2024
    flow = ColumnFlow(doc, title, level, '자체 작성 풀이 해설 · 한국물리학회 공식 배포 해설이 아님',
                      INPUT / f'KPhE_{year[:4]}_{part}_KO.pdf' if preserve else None, preserve)
    for i, q in enumerate(items):
        answers = q.get('accepted_answers', [q['answer']])
        label = ' / '.join('①②③④⑤'[a - 1] for a in answers)
        keep = 25 + 9.8 * 1.45 * 2
        if q.get('figure'):
            r = fitz.Rect(q['figure']['rect'])
            keep += min(172, flow.width * r.height / r.width) + 12
        elif q.get('diagram'):
            keep += 165
        answer_label = '제공 정답' if q.get('status') == 'needs_review' else '정답'
        flow.heading(q['number'], f'{answer_label} {label}', min(keep, 680))
        if q.get('status') == 'needs_review':
            flow.review_notice()
        figure = q.get('figure')
        if figure:
            fig_source = source if Path(figure['source']).name == f'KPhE_{year[:4]}_{part}_KO.pdf' else fitz.open(INPUT / figure['source'])
            clip = fitz.Rect(figure['rect'])
            if not (0 < figure['page'] <= len(fig_source)) or clip.is_empty:
                raise ValueError('Invalid figure rectangle')
            flow.figure(fig_source, figure['page'], clip)
        if q.get('diagram'):
            flow.reserve(165)
            flow.y += diagram(flow.page, flow.x, flow.y, flow.width, q['diagram'])
        caveat = q.get('caveat') or q.get('review_note')
        if caveat:
            prefix = '[원문·정답 검토 필요] ' if q.get('status') == 'needs_review' else '[원문·정답 유의사항] '
            flow.paragraph(prefix + caveat, 8.5)
        for value in q['explanation']:
            flow.paragraph(value)
        if q.get('formula'):
            formulas = [readable_formula(value) for value in q['formula']]
            group_height = 6 + sum(flow.paragraph_height(value, 8.5) for value in formulas)
            flow.reserve(min(group_height, 680))
            flow.reserve(min(6 + sum(flow.paragraph_height(value, 8.5) for value in formulas), 680))
            flow.page.draw_line((flow.x, flow.y), (flow.x + flow.width, flow.y), color=(.7, .7, .7), width=.4)
            flow.y += 6
            for value in formulas:
                flow.paragraph(value, 8.5)
        flow.y += 12
    flow.finish()
    target = OUTPUT / f'KPhE_{year[:4]}_{part}S.pdf'
    doc.set_metadata({'title': f'{title} {level} 풀이 해설', 'author': '자체 작성 해설',
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
        if '--modern-only' in sys.argv[1:] and int(year[:4]) < 2024:
            continue
        years = [arg.split('=', 1)[1] for arg in sys.argv[1:] if arg.startswith('--year=')]
        selected_parts = [arg.split('=', 1)[1] for arg in sys.argv[1:] if arg.startswith('--part=')]
        if years and year not in years:
            continue
        for part, items in parts.items():
            if selected_parts and part not in selected_parts:
                continue
            if sys.argv[1:] == ['ab'] and part[-1] not in 'ab':
                continue
            filename = build(year, part, items, manifest)
            overlay.setdefault('kphe', {}).setdefault(year, {}).setdefault('f', {}).setdefault(part, {})['sol'] = filename
            count += 1
    overlay_path.write_text(json.dumps(overlay, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Checked A4 solution sets: {count}')


if __name__ == '__main__':
    main()
