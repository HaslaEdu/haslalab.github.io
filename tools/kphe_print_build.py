"""Build reproducible A4 study editions without rasterising equations or figures.

python -X utf8 tools/kphe_print_build.py
Sources are downloaded by tools/kphe_archive_import.py into tmp/kphe_archive/originals.
Original manifests retain provenance; tools/kphe_print.json overlays the local editions.
"""
import hashlib
import json
import re
import sys
import copy
from functools import lru_cache
from pathlib import Path

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'tmp/kphe_archive/originals'
OUTPUT = ROOT / 'pdfx/kphe'
A4 = fitz.paper_rect('a4')
FONT = ROOT / 'tools/ko/fonts/NotoSansKR-Regular.ttf'
MATH_FONT = ROOT / 'tools/ko/fonts/DejaVuSans.ttf'
FONTS = {'noto': fitz.Font(fontfile=str(FONT)), 'math': fitz.Font(fontfile=str(MATH_FONT))}
QUESTION = re.compile(r'^\s*(?:【\s*문제\s*(\d+)\s*】|(\d+)\s*[.．])')
LEVELS = {'a': '초급과정', 'b': '중급과정', 'c': '고급과정', 'd': '전문가과정'}


@lru_cache(maxsize=None)
def font_for(ch):
    for name, font in FONTS.items():
        if font.has_glyph(ord(ch)):
            return name
    raise ValueError(f'Unsupported output glyph U+{ord(ch):04X}: {ch}')


@lru_cache(maxsize=None)
def glyph_width(ch, size):
    return FONTS[font_for(ch)].text_length(ch, fontsize=size)


def measure(value, size):
    return sum(glyph_width(ch, size) for ch in value)


def text(page, box, value, size=9, align=0, color=(0, 0, 0)):
    page.insert_font(fontname='noto', fontfile=str(FONT))
    page.insert_font(fontname='math', fontfile=str(MATH_FONT))
    rect = fitz.Rect(box)
    for i, line in enumerate(value.split('\n')):
        width = measure(line, size)
        y = rect.y0 + size * 1.15 + i * size * 1.5
        if width > rect.width or y > rect.y1:
            raise ValueError(f'Text overflow: {value!r}')
        x = rect.x0 + (rect.width - width) * ({0: 0, 1: .5, 2: 1}[align])
        runs = []
        for ch in line:
            name = font_for(ch)
            if runs and runs[-1][0] == name:
                runs[-1][1] += ch
            else:
                runs.append([name, ch])
        for name, run in runs:
            page.insert_text((x, y), run, fontname=name, fontsize=size, color=color)
            x += measure(run, size)


def frame(page, title, subtitle, number, total, source_note=True):
    text(page, (34, 18, 145, 40), 'HaslaLab', 11)
    text(page, (145, 18, 561, 40), title, 10, 2)
    text(page, (34, 42, 561, 62), subtitle, 12, 1)
    page.draw_line((34, 66), (561, 66), color=(0, 0, 0), width=1.5)
    text(page, (34, 812, 561, 830), f'{number} / {total}', 8, 1)
    if source_note:
        note = source_note if isinstance(source_note, str) else '한국물리학회 원문 · 수식/그림 보존 · HaslaLab A4 학습용 편집본'
        text(page, (34, 795, 561, 808), note, 6.5)


def identity(manifest, year, part):
    y = str(year['y'])
    if year.get('display_title'):
        return year['display_title'], dict((p['id'], p['title']) for p in year.get('problems', [])).get(part, '문제지')
    if manifest['prefix'] == 'KPhE':
        return f'{y[:4]}년 제{y[-1]}회 물리대회 (The Physics League)', LEVELS[part[-1]]
    return f'{y}년 한국 중학생 물리대회', dict((p['id'], p['title']) for p in year.get('problems', [])).get(part, '문제지')


def source_path(file):
    path = INPUT / file['file']
    # The collector originally saved official key PDFs with A rather than K.
    if not path.exists() and file['kind'] == 'key':
        path = INPUT / re.sub(r'K\.pdf$', 'A.pdf', file['file'])
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def regions(doc, expected=None):
    """Find actual numbered starts; never infer a page from a question count."""
    starts = []
    for pi, page in enumerate(doc):
        for block in page.get_text('dict')['blocks']:
            if block['type'] != 0:
                continue
            for line in block['lines']:
                content = ''.join(s['text'] for s in line['spans'])
                match = QUESTION.match(content)
                if match:
                    rect = fitz.Rect(line['bbox'])
                    # Exclude numbered answer-table items, headers and centered footers.
                    if 65 < rect.y0 < page.rect.height - 65:
                        starts.append((int(match.group(1) or match.group(2)), pi, rect))
    # Read columns in order. A question may contain a numbered 1./2. procedure;
    # accept only the next expected question, never a repeated list number.
    candidates = sorted(starts, key=lambda s: (s[1], s[2].x0 > doc[s[1]].rect.width / 2, s[2].y0))
    starts = []
    for candidate in candidates:
        if candidate[0] == len(starts) + 1:
            starts.append(candidate)
    if not starts:
        return [], []
    if expected and len(starts) != expected:
        raise ValueError(f'Question/key mismatch: {len(starts)} != {expected}')
    result, pages = [], []
    for n, pi, box in starts:
        page = doc[pi]
        w, h = page.rect.width, page.rect.height
        # Current TPL has two columns; legacy KPhC has one full-width column.
        two = w * .42 < box.x0 or any(p == pi and b.x0 > w * .5 for _, p, b in starts)
        left = 34 if not two or box.x0 < w / 2 else w / 2 + 5
        right = w / 2 - 5 if two and box.x0 < w / 2 else w - 34
        following = [b.y0 for _, p, b in starts if p == pi and b.y0 > box.y0 + 2 and left <= b.x0 < right]
        bottom = min(following) - 6 if following else h - 48
        result.append({'page': pi + 1, 'rect': [round(left / w, 6), round((box.y0 - 2) / h, 6),
                                                round(right / w, 6), round(bottom / h, 6)]})
        pages.append(pi + 1)
    return result, pages


def edition(source, target, title, label, corrections=None, recall=False, source_note=None, author=None):
    original = fitz.open(source)
    out = fitz.open()
    for i, pg in enumerate(original):
        page = out.new_page(width=A4.width, height=A4.height)
        note = source_note or ('비공식 복기·재수록본 · 수치/문항 누락 가능 · 원문 수식/그림 보존' if recall else True)
        frame(page, title, label, i + 1, len(original) + bool(corrections), note)
        # Keep diagrams and equations as PDF vector objects. Replace the running
        # TPL heading/footer, retain legacy covers (including copyright/instructions).
        if source.name.startswith('KPhE'):
            clip = fitz.Rect(50, 86, pg.rect.width - 46, pg.rect.height - 70)
        else:
            clip = fitz.Rect(60, 74, pg.rect.width - 60, pg.rect.height - 62)
        page.show_pdf_page(fitz.Rect(35, 72, 560, 790), original, i, clip=clip, keep_proportion=True)
    if corrections:
        page = out.new_page(width=A4.width, height=A4.height)
        frame(page, title, label + ' · 공식 정정 안내', len(out), len(out))
        y = 90
        for fix in corrections:
            answer = '미응답을 포함하여 전원 정답' if fix.get('full_credit') else ' / '.join('①②③④⑤'[n - 1] for n in fix['accepted_answers'])
            text(page, (38, y, 555, y + 22), f'{fix["number"]}번 최종 인정 답안: {answer}', 11)
            text(page, (38, y + 30, 555, y + 50), f'한국물리학회 공식 정정 공지 · {fix.get("date", "")}', 9)
            text(page, (38, y + 58, 555, y + 79), fix['source'], 8)
            page.insert_link({'kind': fitz.LINK_URI, 'from': fitz.Rect(38, y + 58, 555, y + 79), 'uri': fix['source']})
            y += 105
    out.set_metadata({'title': f'{title} {label}', 'author': author or ('비공식 복기 작성자; HaslaLab 학습용 편집' if recall else '한국물리학회; HaslaLab 학습용 편집'),
                      'subject': 'A4 portrait study edition; original equations and diagrams preserved'})
    out.subset_fonts()
    out.save(target, garbage=4, deflate=True)
    out.close()


def answer_sheet(target, title, level, count):
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    frame(page, title, level + ' · 답안지', 1, 1, False)
    text(page, (38, 78, 555, 101), '성명: ____________________   응시일: ____________________', 10)
    text(page, (38, 108, 555, 145), '본 시험 60분 · 추가 답안 작성 시간 없음\n한 문항에 하나의 답을 선택하세요. 이 답안지는 HaslaLab 연습용입니다.', 9)
    row_h = min(31, 585 / max(1, (count + 1) // 2))
    per_col = (count + 1) // 2
    for q in range(1, count + 1):
        col, row = (q - 1) // per_col, (q - 1) % per_col
        x, y = 43 + col * 265, 161 + row * row_h
        text(page, (x, y, x + 30, y + 22), str(q), 10)
        for option in range(1, 6):
            cx = x + 49 + (option - 1) * 34
            page.draw_circle((cx, y + 9), 8, width=.6)
            text(page, (cx - 7, y + .3, cx + 7, y + 20), str(option), 9, 1)
    page.draw_line((297.6, 151), (297.6, 770), color=(.7, .7, .7), width=.5)
    doc.subset_fonts()
    doc.save(target, garbage=4, deflate=True)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    overlay, report = {}, []
    overlay_path = ROOT / 'tools/kphe_print.json'
    previous = json.loads(overlay_path.read_text(encoding='utf-8')) if overlay_path.exists() else {}
    manifests = [ROOT / 'tools/theory/kphe.json', ROOT / 'tools/theory/kphc.json']
    if (ROOT / 'tools/theory/kphrecall.json').exists():
        manifests.append(ROOT / 'tools/theory/kphrecall.json')
    if sys.argv[1:]:
        selected = set(sys.argv[1:])
        manifests = [p for p in manifests if p.stem in selected]
        overlay = copy.deepcopy(previous)
        old_report = ROOT / 'tools/kphe_print_report.json'
        prefixes = {json.loads(p.read_text(encoding='utf-8'))['prefix'] for p in manifests}
        report = [r for r in json.loads(old_report.read_text(encoding='utf-8')) if r['file'].split('_')[0] not in prefixes] if old_report.exists() else []
    for path in manifests:
        m = json.loads(path.read_text(encoding='utf-8'))
        for year in m['years']:
            y, slots = str(year['y']), {}
            record = {'f': {}}
            overlay.setdefault(m['comp'], {})[y] = record
            for file in year['files']:
                if file['kind'] not in ('paper', 'key'):
                    continue
                source = source_path(file)
                part = file['part']
                title, level = identity(m, year, part)
                target = OUTPUT / file['file']
                corrections = [c for c in year.get('corrections', []) if c['part'] == part] if file['kind'] == 'key' else []
                edition(source, target, title, level + (' · 정답표' if file['kind'] == 'key' else ' · 문제지'), corrections,
                        year.get('source_type') == 'recall', year.get('source_note'), year.get('author'))
                slot = record['f'].setdefault(part, {})
                slot['paper' if file['kind'] == 'paper' else 'key'] = 'pdfx/kphe/' + target.name
                report.append({'file': target.name, 'source': file.get('url'), 'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                               'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'pages': len(fitz.open(target))})
                if file['kind'] == 'paper' and m['prefix'] == 'KPhE':
                    key = year['keys'][part]
                    doc = fitz.open(target)
                    rs, ps = regions(doc, len(key))
                    if len(rs) != len(key):
                        raise ValueError(f'Unmapped questions: {target.name}')
                    record.setdefault('questionRegions', {})[part] = rs
                    record.setdefault('questionPages', {})[part] = ps
                    blank = OUTPUT / (source.stem.replace('_KO', '') + 'A.pdf')
                    answer_sheet(blank, title, level, len(key))
                    slot['answer'] = 'pdfx/kphe/' + blank.name
            if m['prefix'] == 'KPhE':
                record['exam'] = {'minutes': 60, 'penaltyRate': .25, 'policySource': 'https://kphe.kps.or.kr/notice/notice_detail/386'}
            for part, old in previous.get(m['comp'], {}).get(y, {}).get('f', {}).items():
                if part in record['f'] and old.get('sol') and (ROOT / old['sol']).is_file():
                    record['f'][part]['sol'] = old['sol']
    overlay_path.write_text(json.dumps(overlay, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (ROOT / 'tools/kphe_print_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'A4 editions: {len(report)}; answer sheets: 24; mapped exams: 24')


if __name__ == '__main__':
    main()
