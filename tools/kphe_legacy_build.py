"""Build the attributed 2021 Physics Certification fragment and our solution.

Run: python -X utf8 tools/kphe_legacy_build.py
The 67-page source book remains private under tmp/. Only its integral 16 is
retained, as PDF vectors, in the published single-question study edition.
"""
import hashlib
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

from kphe_print_build import A4, ROOT, fitz, frame, measure, text


SOURCE_URL = 'https://orbi.kr/download/united/57373007/1'
SOURCE_PAGE = 'https://orbi.kr/00057373007'
SCRIBD_URL = 'https://www.scribd.com/document/1005314514/%EC%A0%95%EC%A0%81%EB%B6%84-100%E9%A1%8C'
SOURCE_SHA256 = '34252b52b86768e955e9e46ecd9e26ee00d3595666605cd2d6ab00b2afcf0534'
SOURCE = ROOT / 'tmp/kphe_archive/legacy/2021_level1_hydrogen_fragment_Suzume_integrals_20220629.pdf'
ORIGINAL = ROOT / 'tmp/kphe_archive/originals/KPhR_2021_T1_KO.pdf'
PAPER = ROOT / 'pdfx/kphe/KPhR_2021_T1_KO.pdf'
SOLUTION = ROOT / 'pdfx/kphe/KPhR_2021_T1S.pdf'
MANIFEST = ROOT / 'tools/theory/kphrecall.json'
QA = ROOT / 'tmp/kphe_archive/legacy/qa-2021'
QUESTION_PAGE = 15  # Zero-based; printed/PDF page 16.
QUESTION_RECT = fitz.Rect(80, 135, 294, 176)
TITLE = '2021년 물리인증제 · 비공식 재수록 단편'
NOTE = '비공식 재수록 · 저자: 雀(Suzume) · 회차 미상 · HaslaLab A4 학습용 편집'


def paragraph(page, value, y, size=10, left=40, right=555, leading=1.65):
    """Use the shared glyph-aware font measurement for Korean and math text."""
    lines, line = [], ''
    for ch in value:
        if ch == '\n':
            lines.append(line)
            line = ''
        elif line and measure(line + ch, size) > right - left:
            lines.append(line.rstrip())
            line = ch.lstrip()
        else:
            line += ch
    if line:
        lines.append(line)
    for line in lines:
        text(page, (left, y, right, y + size * 1.6), line, size)
        y += size * leading
    return y


def formula(page, value, y, size=11):
    text(page, (45, y, 550, y + 24), value, size, 1)
    return y + 31


def sources(page, y):
    y = paragraph(page, '출처와 편집 범위', y, 9)
    y = paragraph(page, '雀(Suzume), 「정적분 100題」 ver. 20220629, 문항 16(16쪽). 자료집 풀이 26쪽의 [2021 물리인증 1급 기출] 표기를 근거로 한 단편입니다.', y + 3, 8)
    y = paragraph(page, '회차와 원래 시험 번호·선택지는 확인되지 않았습니다. 자료집의 16번은 원시험 번호를 뜻하지 않습니다. 이 편집본은 비공식 자료입니다.', y + 3, 8)
    links = [
        ('저자 게시글: orbi.kr/00057373007', SOURCE_PAGE),
        ('공개 원본: orbi.kr/download/united/57373007/1', SOURCE_URL),
        ('동일 자료 공개 열람: scribd.com/document/1005314514', SCRIBD_URL),
    ]
    for label, uri in links:
        y += 3
        text(page, (40, y, 555, y + 15), label, 8, color=(.15, .15, .15))
        page.insert_link({'kind': fitz.LINK_URI, 'from': fitz.Rect(40, y, 555, y + 15), 'uri': uri})
        y += 14
    if y > 785:
        raise ValueError(f'Source attribution exceeds the content area: {y}')


def save_pdf(doc, target, title, subject, author):
    target.parent.mkdir(parents=True, exist_ok=True)
    doc.set_metadata({'title': title, 'author': author, 'subject': subject,
                      'creator': 'HaslaLab kphe_legacy_build.py'})
    doc.subset_fonts()
    temporary = target.with_suffix('.tmp.pdf')
    doc.save(temporary, garbage=4, deflate=True, no_new_id=True)
    doc.close()
    temporary.replace(target)


def acquire_source():
    if not SOURCE.exists():
        SOURCE.parent.mkdir(parents=True, exist_ok=True)
        request = Request(SOURCE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=30) as response:
            content = response.read()
        if not content.startswith(b'%PDF-'):
            raise ValueError('Public source did not return a PDF')
        SOURCE.write_bytes(content)
    actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if actual != SOURCE_SHA256:
        raise ValueError(f'Source changed; visually review before updating its hash: {actual}')


def isolated_question():
    """Remove adjacent questions, rather than merely hiding them with a clip."""
    book = fitz.open(SOURCE)
    question = fitz.open()
    question.insert_pdf(book, from_page=QUESTION_PAGE, to_page=QUESTION_PAGE)
    book.close()
    page = question[0]
    w, h = page.rect.width, page.rect.height
    for outside in (
        fitz.Rect(0, 0, w, QUESTION_RECT.y0),
        fitz.Rect(0, QUESTION_RECT.y1, w, h),
        fitz.Rect(0, QUESTION_RECT.y0, QUESTION_RECT.x0, QUESTION_RECT.y1),
        fitz.Rect(QUESTION_RECT.x1, QUESTION_RECT.y0, w, QUESTION_RECT.y1),
    ):
        page.add_redact_annot(outside, fill=False)
    page.apply_redactions(images=2, graphics=1, text=0)
    # The original uses a legacy math font. Its text remains selectable and its
    # glyphs remain vector font objects; no page is converted to an image.
    remaining = page.get_text('text').strip()
    if not remaining or len(remaining) > 220:
        raise ValueError(f'Unexpected retained text after isolating one integral: {remaining!r}')
    return question


def build_original(question):
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    destination = fitz.Rect(80, 100, 80 + QUESTION_RECT.width, 100 + QUESTION_RECT.height)
    page.show_pdf_page(destination, question, 0, clip=QUESTION_RECT)
    save_pdf(doc, ORIGINAL, '2021 물리인증제 비공식 재수록 문항 단편',
             'Single isolated integral; source book item 16; original exam item number/session unknown',
             '雀(Suzume); HaslaLab fragment extraction')


def build_paper(question):
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    frame(page, TITLE, '1급 기출 재수록 단편 · 문제지', 1, 1, NOTE)
    y = paragraph(page, '문항 1. 수소 원자의 바닥상태 확률', 82, 11)
    y = paragraph(page, '다음 적분값을 구하시오. a₀는 보어 반지름이며 r은 핵에서 전자까지의 거리입니다.', y + 12)
    height = QUESTION_RECT.height * 1.6
    page.show_pdf_page(fitz.Rect(45, y + 14, 45 + QUESTION_RECT.width * 1.6, y + 14 + height),
                       question, 0, clip=QUESTION_RECT)
    y += height + 42
    paragraph(page, '위 수식은 자료집의 16번 문항을 그대로 보존한 것입니다. 수식 앞의 16은 자료집 번호입니다.', y, 8.5)
    paragraph(page, '풀이 및 답', y + 43, 10)
    for line_y in (y + 85, y + 125, y + 165, y + 205):
        page.draw_line((42, line_y), (553, line_y), color=(.78, .78, .78), width=.45)
    sources(page, 600)
    save_pdf(doc, PAPER, TITLE + ' · 문제지',
             'Unofficial attributed reprint fragment, one question; session and original exam number unknown',
             '雀(Suzume); HaslaLab A4 학습용 편집')


def build_solution():
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    frame(page, TITLE, '1급 기출 재수록 단편 · 직접 작성 해설', 1, 1,
          'HaslaLab 직접 유도 · 비공식 해설 · 문제 출처: 雀(Suzume) 「정적분 100題」')
    y = paragraph(page, '문항 1. 핵에서 a₀/2보다 먼 곳에서 전자를 발견할 확률', 82, 11)
    y = paragraph(page, '바닥상태 파동함수는 ψ(r)=exp(-r/a₀)/√(πa₀³)입니다. 원문 적분의 하한은 a₀/2, 상한은 무한대이며 구면 껍질의 부피 요소 4πr²dr이 포함됩니다.', y + 12)

    y = paragraph(page, '1. 확률 밀도에 부피 요소를 곱합니다.', y + 13, 10)
    y = formula(page, 'P = (4/a₀³) ∫[a₀/2, ∞] r² exp(-2r/a₀) dr', y + 5)
    y = paragraph(page, '파동함수의 절댓값 제곱이 단위 부피당 확률 밀도이므로 r² 인자를 포함해야 합니다.', y, 9.5)

    y = paragraph(page, '2. u=2r/a₀로 치환합니다.', y + 13, 10)
    y = paragraph(page, 'r²dr=(a₀³/8)u²du이며 적분 구간은 1부터 무한대까지입니다.', y + 4, 9.5)
    y = formula(page, 'P = (1/2) ∫[1, ∞] u² exp(-u) du', y + 4)

    y = paragraph(page, '3. 부분적분을 두 번 적용하여 경곗값을 계산합니다.', y + 9, 10)
    y = formula(page, '∫ u² exp(-u) du = -exp(-u)(u² + 2u + 2) + C', y + 5, 10.5)
    y = paragraph(page, 'u가 무한대로 갈 때 지수함수 때문에 경계항은 0이 됩니다. u=1에서 괄호 안의 값은 5이므로 적분값은 5/e입니다.', y + 1, 9.5)
    y = formula(page, 'P = 5/(2e) = 0.9196986… ≈ 91.97%', y + 8, 13)

    y = paragraph(page, '검산: r의 전 구간에서 같은 확률을 적분하면 1입니다. 따라서 r<a₀/2일 확률은 약 8.03%이며, 두 확률의 합은 100%입니다.', y + 5, 9)
    y = paragraph(page, '이 해설은 적분식에서 직접 유도한 HaslaLab 자체 해설입니다. 자료집의 풀이를 복사하지 않았습니다.', y + 8, 8.5)
    if y > 589:
        raise ValueError(f'Solution text overlaps sources: {y}')
    sources(page, 615)
    save_pdf(doc, SOLUTION, TITLE + ' · HaslaLab 직접 작성 해설',
             'Self-derived solution to the single attributed hydrogen probability fragment: 5/(2e)',
             'HaslaLab 자체 작성 (문제 출처: 雀/Suzume)')


def update_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    note = ('2021 물리인증 1급 기출로 표기된 비공식 재수록 단편 1문항입니다. '
            '출처는 雀(Suzume)의 정적분 100題 ver. 20220629입니다. 회차 및 원시험 번호·선택지는 미상이며, '
            '자료집 16번을 원시험 번호로 해석하지 않습니다. 문제 수식만 발췌했고 해설은 HaslaLab이 직접 유도했습니다.')
    common = {'part': 'T1', 'lang': 'KO', 'url': SOURCE_URL, 'source_url': SOURCE_URL,
              'source_page': SOURCE_PAGE, 'source_type': 'recall',
              'provenance_kind': 'reprint_fragment', 'source_author': '雀(Suzume)',
              'source_version': '20220629', 'source_mirror': SCRIBD_URL,
              'official': False, 'pages': 1, 'direct': True}
    paper = dict(common, file=PAPER.name, kind='paper', local='pdfx/kphe/' + PAPER.name,
                 author='雀(Suzume); HaslaLab 학습용 편집', bytes=PAPER.stat().st_size)
    solution = dict(common, file=SOLUTION.name, kind='solution', local='pdfx/kphe/' + SOLUTION.name,
                    author='HaslaLab 자체 작성', official_solution=False, bytes=SOLUTION.stat().st_size)
    year = {
        'y': '2021-r', 'display_title': TITLE,
        'host': {'ko': '1급 재수록 단편 · 회차 미상 · 비공식',
                 'en': 'Level 1 attributed fragment · session unknown · unofficial'},
        'cc': 'kr', 'source_type': 'recall', 'provenance_kind': 'reprint_fragment',
        'source_page': SOURCE_PAGE, 'source_url': SOURCE_URL, 'source_author': '雀(Suzume)',
        'source_note': NOTE, 'note': note,
        'problems': [{'id': 'T1', 'title': '물리인증제 1급 재수록 단편 · 회차 미상 · 비공식'}],
        'files': [paper, solution]
    }
    previous = [item for item in manifest['years'] if str(item['y']) != '2021-r']
    manifest['years'] = previous + [year]
    # Re-read/update only this year so all independently maintained legacy years
    # and their provenance survive repeated execution.
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def verify_and_render():
    assert abs(5 / (2 * math.e) - 0.9196986029286058) < 1e-14
    QA.mkdir(parents=True, exist_ok=True)
    report = []
    for path in (ORIGINAL, PAPER, SOLUTION):
        with fitz.open(path) as doc:
            if len(doc) != 1:
                raise ValueError(f'Unexpected page count: {path}')
            page = doc[0]
            if abs(page.rect.width - A4.width) > .01 or abs(page.rect.height - A4.height) > .01:
                raise ValueError(f'Not A4 portrait: {path}')
            if page.get_images():
                raise ValueError(f'Unexpected raster image: {path}')
            plain = page.get_text()
            if not plain.strip():
                raise ValueError(f'Empty PDF text: {path}')
            if path == ORIGINAL and len(plain.strip()) > 220:
                raise ValueError('Original contains more than the isolated integral')
            if path != ORIGINAL and ('비공식' not in plain or '2021' not in plain):
                raise ValueError(f'Missing attribution: {path}')
            if path == SOLUTION and ('5/(2e)' not in plain or '91.97%' not in plain):
                raise ValueError('Solution answer is missing')
            png = QA / (path.stem + ('-source' if path == ORIGINAL else '') + '.png')
            page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6)).save(png)
            report.append({'file': str(path.relative_to(ROOT)), 'pages': len(doc),
                           'bytes': path.stat().st_size, 'text_characters': len(plain.strip()),
                           'vector_only': True, 'preview': str(png.relative_to(ROOT))})
    return report


def main():
    acquire_source()
    question = isolated_question()
    try:
        build_original(question)
        build_paper(question)
    finally:
        question.close()
    build_solution()
    update_manifest()
    print(json.dumps(verify_and_render(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
