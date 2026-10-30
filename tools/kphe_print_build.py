"""Restore official question bytes and build unbranded editions on KPS stationery.

2024--2026 official question papers are copied byte-for-byte. No blank answer
sheets are generated. The separate key slot always denotes an official key;
the sol slot denotes independently written explanations.
"""
import copy
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
import pymupdf as fitz
from kphe_template import A4, FONT, INPUT, OUTPUT, ROOT, frame, text, measure, ColumnFlow

QUESTION = re.compile(r'^\s*(?:【\s*문제\s*(\d+)\s*】|(\d+)\s*[.．])')
LEVELS = {'a': '초급과정', 'b': '중급과정', 'c': '고급과정', 'd': '전문가과정'}


def identity(manifest, year, part):
    y = str(year['y'])
    if year.get('display_title'):
        return year['display_title'], dict((p['id'], p['title']) for p in year.get('problems', [])).get(part, '문제지')
    if manifest['prefix'] == 'KPhE':
        return f'{y[:4]}년 제{y[-1]}회 물리대회 (The Physics League; TPL)', LEVELS[part[-1]]
    return f'{y}년 한국 중학생 물리대회', dict((p['id'], p['title']) for p in year.get('problems', [])).get(part, '문제지')


def source_path(file):
    path = ROOT / file['source_original'] if file.get('source_original') else INPUT / file['file']
    if not path.exists() and file['kind'] == 'key':
        path = INPUT / re.sub(r'K\.pdf$', 'A.pdf', file['file'])
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def regions(doc, expected=None):
    """Map actual question starts in an official paper, in its own page units."""
    candidates = []
    for pi, page in enumerate(doc):
        for block in page.get_text('dict')['blocks']:
            if block['type'] != 0:
                continue
            for line in block['lines']:
                match = QUESTION.match(''.join(s['text'] for s in line['spans']))
                if match:
                    box = fitz.Rect(line['bbox'])
                    if page.rect.height * .08 < box.y0 < page.rect.height * .93:
                        candidates.append((int(match.group(1) or match.group(2)), pi, box))
    candidates.sort(key=lambda s: (s[1], s[2].x0 > doc[s[1]].rect.width / 2, s[2].y0))
    starts = []
    for candidate in candidates:
        if candidate[0] == len(starts) + 1:
            starts.append(candidate)
    if expected and len(starts) != expected:
        raise ValueError(f'Question/key mismatch: {len(starts)} != {expected}')
    result, pages = [], []
    for n, pi, box in starts:
        page = doc[pi]
        w, h = page.rect.width, page.rect.height
        two = box.x0 > w * .42 or any(p == pi and b.x0 > w / 2 for _, p, b in starts)
        left = w * 50 / 728 if not two or box.x0 < w / 2 else w / 2 + w * 5 / 728
        right = w / 2 - w * 5 / 728 if two and box.x0 < w / 2 else w * 680 / 728
        following = [b.y0 for _, p, b in starts if p == pi and b.y0 > box.y0 + 2 and left <= b.x0 < right]
        bottom = min(following) - h * 6 / 1031 if following else h * 960 / 1031
        result.append({'page': pi + 1, 'rect': [round(left / w, 6), round((box.y0 - 2) / h, 6),
                                               round(right / w, 6), round(bottom / h, 6)]})
        pages.append(pi + 1)
    return result, pages


def key_edition(source, target, title, level, corrections):
    original = fitz.open(source)
    out = fitz.open()
    for i in range(len(original)):
        page = out.new_page(width=A4.width, height=A4.height)
        page.show_pdf_page(A4, original, i, keep_proportion=True)
    if corrections:
        page = out.new_page(width=A4.width, height=A4.height)
        frame(page, title, level, len(out), len(out), '공식 정정 공지의 내용 정리 · 원문 정답표는 앞쪽에 그대로 수록', columns=False)
        y = 90
        for fix in corrections:
            answer = '미응답을 포함하여 전원 정답' if fix.get('full_credit') else ' / '.join('①②③④⑤'[n - 1] for n in fix['accepted_answers'])
            text(page, (47, y, 549, y + 23), f'{fix["number"]}번 최종 인정 답안: {answer}', 11)
            text(page, (47, y + 32, 549, y + 50), f'한국물리학회 공식 정정 공지 · {fix.get("date", "")}', 9)
            text(page, (47, y + 58, 549, y + 80), fix['source'], 8)
            page.insert_link({'kind': fitz.LINK_URI, 'from': fitz.Rect(47, y + 58, 549, y + 80), 'uri': fix['source']})
            y += 105
    out.subset_fonts()
    out.save(target, garbage=4, deflate=True)


def source_edition(source, target, title, label, recall=False, source_note=None, author=None):
    """Keep historical source pages intact below the current vector header."""
    original = fitz.open(source)
    out = fitz.open()
    for i, pg in enumerate(original):
        page = out.new_page(width=A4.width, height=A4.height)
        note = source_note or ('비공식 복기·단편 재수록 · 문항/수치 누락 가능 · 공식 배포본 아님' if recall else '과거 기출 원문 재배치 · 당시 안내와 문항을 보존한 학습용 편집본')
        note = re.sub(r'\s*·\s*HaslaLab\s+A4\s+학습용\s+편집', '', note)
        frame(page, title, label, i + 1, len(original), note, columns=False)
        clip = fitz.Rect(50, 74, pg.rect.width - 50, pg.rect.height - 62)
        page.show_pdf_page(fitz.Rect(47, 76, 549, 785), original, i, clip=clip, keep_proportion=True)
    out.set_metadata({'title': f'{title} {label}', 'author': author or ('비공식 복기 작성자' if recall else '한국물리학회'),
                      'subject': 'Historical source on 2026 KPS stationery; not a new official publication'})
    out.subset_fonts()
    out.save(target, garbage=4, deflate=True)


def scan_2023_edition(source, target, title, level, part, year, expected):
    """Reflow verified transcriptions; equations and original diagrams remain unambiguous."""
    layout_path = ROOT / 'tools/kphe_2023_layout.json'
    layout = json.loads(layout_path.read_text(encoding='utf-8')) if layout_path.exists() else {}
    spec = layout.get(str(year), {}).get(part, layout.get(part, {}))
    questions = spec.get('questions', [])
    if not questions:
        for path in sorted((ROOT / 'tools/kphe_solutions').glob(str(year) + '*.json')):
            rows = json.loads(path.read_text(encoding='utf-8')).get(part, [])
            if rows:
                questions = [dict(row.get('problem', {}), number=row['number']) for row in rows]
                break
    if len(questions) != expected or any(not q.get('statement') and not q.get('paragraphs') for q in questions):
        raise ValueError(f'Incomplete 2023 problem transcription: {year} {part}; expected {expected}')
    original = fitz.open(source)
    out = fitz.open()
    note = False
    reference = INPUT / f'KPhE_2026_T2{part[-1]}_KO.pdf'
    flow = ColumnFlow(out, title, level, note, reference, False, kind='문제')
    for question in questions:
        if flow.y > 76:
            flow.new_column(False)
        figures = question.get('figures', []) or ([question['figure']] if question.get('figure') else [])
        keep = 25 + 9.8 * 1.6 * 2
        if figures:
            r = fitz.Rect(figures[0]['rect'])
            keep += min(220, flow.width * r.height / r.width) + 12
        flow.problem_start(question['number'])
        values = question.get('paragraphs', question.get('statement', []))
        for value in ([values] if isinstance(values, str) else values):
            if re.fullmatch(r'\s*\$[^$]+\$\s*', value):
                flow.display_math(value)
            else:
                flow.paragraph(value)
        for fig in figures:
            fig_doc = original if Path(fig['source']).name == source.name else fitz.open(INPUT / fig['source'])
            flow.figure(fig_doc, fig['page'], fig['rect'], max_height=220)
        for value in question.get('after_figure', []):
            flow.paragraph(value)
        values = question.get('givens', [])
        flow.boxed_givens([values] if isinstance(values, str) else values)
        for i, value in enumerate(question.get('options', question.get('choices', []))):
            flow.paragraph(f'{"①②③④⑤"[i]} {value}', gap=4)
        flow.y += 12
    flow.finish()
    out.set_metadata({'title': f'{title} {level}', 'author': '한국물리학회 문항; 첨부 스캔 편집',
                      'subject': 'Retypeset study edition on 2026 KPS stationery'})
    out.subset_fonts()
    out.save(target, garbage=4, deflate=True)
    mapped = [flow.region_records[q['number']] for q in questions]
    return [r[0] if len(r) == 1 else r for r in mapped], [r[0]['page'] for r in mapped]


def transcribed_key(target, title, level, values, marked=False, reference=None):
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    note = False
    frame(page, title, level, 1, 1, note, header_source=reference)
    rows = (len(values) + 1) // 2
    height = min(48, 680 / max(1, rows))
    for i, answer in enumerate(values):
        col, row = i // rows, i % rows
        x = 47 if col == 0 else 308
        label = ' / '.join('①②③④⑤'[a - 1] for a in answer) if isinstance(answer, list) else '①②③④⑤'[answer - 1]
        text(page, (x, 88 + row * height, x + 242, 110 + row * height), f'{i+1}. 정답: {label}', 10.5)
    doc.subset_fonts()
    doc.save(target, garbage=4, deflate=True)


def remove_blank_sheets(overlay):
    for comp, years in overlay.items():
        for edition in years.values():
            for slot in edition.get('f', {}).values():
                slot.pop('answer', None)
    root = OUTPUT.resolve()
    for path in OUTPUT.glob('KPhE_*A.pdf'):
        if path.resolve().parent != root:
            raise ValueError('Blank-sheet removal outside PDF directory')
        if re.fullmatch(r'KPhE_202[3-6]_T[12][abcd]A\.pdf', path.name):
            path.unlink()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    overlay_path = ROOT / 'tools/kphe_print.json'
    previous = json.loads(overlay_path.read_text(encoding='utf-8')) if overlay_path.exists() else {}
    manifests = [ROOT / f'tools/theory/{name}.json' for name in ('kphe', 'kphc')]
    manifests = [p for p in manifests if p.exists()]
    selected = {arg for arg in sys.argv[1:] if not arg.startswith('--')}
    selected_years = [arg.split('=', 1)[1] for arg in sys.argv[1:] if arg.startswith('--year=')]
    selected_parts = [arg.split('=', 1)[1] for arg in sys.argv[1:] if arg.startswith('--part=')]
    modern_only = '--modern-only' in sys.argv[1:]
    keys_only = '--keys-only' in sys.argv[1:]
    if selected:
        manifests = [p for p in manifests if p.stem in selected]
    overlay = copy.deepcopy(previous)
    old_report = ROOT / 'tools/kphe_print_report.json'
    reports = {row['file']: row for row in json.loads(old_report.read_text(encoding='utf-8'))} if old_report.exists() else {}
    for path in manifests:
        manifest = json.loads(path.read_text(encoding='utf-8'))
        for year in manifest['years']:
            y = str(year['y'])
            if modern_only and y.startswith('2023'):
                continue
            if selected_years and y not in selected_years:
                continue
            record = copy.deepcopy(previous.get(manifest['comp'], {}).get(y, {'f': {}}))
            overlay.setdefault(manifest['comp'], {})[y] = record
            for file in year['files']:
                if file['kind'] not in ('paper', 'key'):
                    continue
                if keys_only and file['kind'] != 'key':
                    continue
                if selected_parts and file['part'] not in selected_parts:
                    continue
                part = file['part']
                source = source_path(file)
                title, level = identity(manifest, year, part)
                target = OUTPUT / file['file']
                scan_maps = None
                official_copy = file['kind'] == 'paper' and manifest['prefix'] == 'KPhE' and 2024 <= int(y[:4]) <= 2026
                if official_copy:
                    shutil.copyfile(source, target)
                elif file['kind'] == 'key' and y.startswith('2023'):
                    transcribed_key(target, title, level, year['keys'][part],
                                    file.get('source_type') == 'user_supplied_marked_paper',
                                    INPUT/f'KPhE_2026_T2{part[-1]}_KO.pdf')
                elif file['kind'] == 'key':
                    fixes = [c for c in year.get('corrections', []) if c['part'] == part]
                    key_edition(source, target, title, level, fixes)
                elif manifest['prefix'] == 'KPhE' and y.startswith('2023'):
                    scan_maps = scan_2023_edition(source, target, title, level, part, y, len(year['keys'][part]))
                else:
                    source_edition(source, target, title, level, year.get('source_type') == 'recall',
                                   year.get('source_note'), year.get('author'))
                slot = record['f'].setdefault(part, {})
                slot[{'paper': 'paper', 'key': 'key', 'solution': 'sol'}[file['kind']]] = 'pdfx/kphe/' + target.name
                src_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                target_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                reports[target.name] = {'file': target.name, 'source': file.get('url'), 'sourceSha256': src_hash,
                               'sha256': target_hash, 'officialByteIdentical': official_copy and src_hash == target_hash,
                               'pages': len(fitz.open(target))}
                if official_copy or (manifest['prefix'] == 'KPhE' and y.startswith('2023') and file['kind'] == 'paper'):
                    rs, ps = scan_maps if scan_maps is not None else regions(fitz.open(target), len(year['keys'][part]))
                    record.setdefault('questionRegions', {})[part] = rs
                    record.setdefault('questionPages', {})[part] = ps
            if manifest['prefix'] == 'KPhE':
                record['exam'] = {'minutes': 60, 'penaltyRate': .25, 'policySource': 'https://kphe.kps.or.kr/notice/notice_detail/386'}
            for part, old in previous.get(manifest['comp'], {}).get(y, {}).get('f', {}).items():
                if part in record['f'] and old.get('sol') and (ROOT / old['sol']).is_file():
                    record['f'][part]['sol'] = old['sol']
    remove_blank_sheets(overlay)
    overlay_path.write_text(json.dumps(overlay, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    report = list(reports.values())
    (ROOT / 'tools/kphe_print_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Print outputs: {len(report)}; official byte copies: {sum(r["officialByteIdentical"] for r in report)}; blank answer sheets: 0')


if __name__ == '__main__':
    main()
