"""The 2026 KPS paper's vector stationery, with a two-column Ming/serif text flow.

Official 2024--2026 question PDFs are copied unchanged by kphe_print_build.py.
This stationery is only for independently typeset material, clearly labelled as such.
"""
from functools import lru_cache
from pathlib import Path
import io
import logging
import re
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'tmp/kphe_archive/originals'
OUTPUT = ROOT / 'pdfx/kphe'
A4 = fitz.paper_rect('a4')
FONT = ROOT / 'tools/ko/fonts/NotoSerifKR-Regular.ttf'
HEAD_FONT = ROOT / 'tools/ko/fonts/NotoSansKR-Bold.ttf'
MATH_FONT = ROOT / 'tools/ko/fonts/DejaVuSans.ttf'
REFERENCE = INPUT / 'KPhE_2026_T2c_KO.pdf'
if not REFERENCE.exists():
    REFERENCE = OUTPUT / 'KPhE_2026_T2c_KO.pdf'
STATIONERY = ROOT / 'tools/kphe_template_assets.pdf'
FONTS = {'body': fitz.Font(fontfile=str(FONT)), 'head': fitz.Font(fontfile=str(HEAD_FONT)),
         'math': fitz.Font(fontfile=str(MATH_FONT))}
FONT_PATHS = {'body': FONT, 'head': HEAD_FONT, 'math': MATH_FONT}
TOP, BOTTOM = 76.0, 786.0
COLUMNS = ((46.5, 291.5), (308.0, 549.0))


@lru_cache(maxsize=None)
def font_for(ch, style='body'):
    for name in (style, 'math', 'head'):
        if FONTS[name].has_glyph(ord(ch)):
            return name
    raise ValueError(f'Unsupported output glyph U+{ord(ch):04X}: {ch}')


@lru_cache(maxsize=None)
def glyph_width(ch, size, style='body'):
    return FONTS[font_for(ch, style)].text_length(ch, fontsize=size)


def measure(value, size, style='body'):
    return sum(glyph_width(ch, size, style) for ch in value)


def text(page, box, value, size=9.8, align=0, color=(0, 0, 0), style='body'):
    registry = getattr(page.parent, '_kphe_registered_fonts', None)
    if registry is None:
        registry = page.parent._kphe_registered_fonts = set()
    rect = fitz.Rect(box)
    for i, line in enumerate(value.split('\n')):
        width = measure(line, size, style)
        baseline = rect.y0 + size * 1.15 + i * size * 1.5
        if width > rect.width + .02 or baseline > rect.y1 + .02:
            raise ValueError(f'Text overflow: {value!r}')
        x = rect.x0 + (rect.width - width) * {0: 0, 1: .5, 2: 1}[align]
        runs = []
        for ch in line:
            name = font_for(ch, style)
            if runs and runs[-1][0] == name:
                runs[-1][1] += ch
            else:
                runs.append([name, ch])
        for name, run in runs:
            key = (page.xref, name)
            if key not in registry:
                page.insert_font(fontname=name, fontfile=str(FONT_PATHS[name]))
                registry.add(key)
            page.insert_text((x, baseline), run, fontname=name, fontsize=size, color=color)
            x += measure(run, size, style)


def wrap(value, width, size=9.8, style='body'):
    lines, line = [], ''
    for ch in value:
        if ch == '\n' or (line and measure(line + ch, size, style) > width):
            lines.append(line.rstrip())
            line = '' if ch == '\n' else ch
        else:
            line += ch
    if line:
        lines.append(line.rstrip())
    return lines


@lru_cache(maxsize=2048)
def math_pdf(expression, size):
    """Typeset inline fractions/radicals as vector PDF, preserving a real baseline."""
    import matplotlib
    from matplotlib.mathtext import MathTextParser, math_to_image
    from matplotlib.font_manager import FontProperties, fontManager
    korean = bool(re.search(r'[\u1100-\u11ff\u3130-\u318f가-힣]', expression))
    if korean:
        fontManager.addfont(str(FONT))
        matplotlib.rcParams['mathtext.fontset'] = 'custom'
        matplotlib.rcParams['mathtext.rm'] = 'Noto Serif KR'
        matplotlib.rcParams['mathtext.it'] = 'cmmi10'
        matplotlib.rcParams['mathtext.bf'] = 'Noto Serif KR'
        matplotlib.rcParams['mathtext.cal'] = 'cmsy10'
        expression = re.sub(r'[\u1100-\u11ff\u3130-\u318f가-힣]+', lambda m: r'\mathrm{' + m[0] + '}', expression)
    else:
        matplotlib.rcParams['mathtext.fontset'] = 'cm'
    matplotlib.rcParams['mathtext.fallback'] = 'stix'
    subs = str.maketrans('₀₁₂₃₄₅₆₇₈₉₊₋', '0123456789+-')
    supers = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻', '0123456789+-')
    expression = re.sub(r'[₀₁₂₃₄₅₆₇₈₉₊₋]+', lambda m: '_{' + m[0].translate(subs) + '}', expression)
    expression = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+', lambda m: '^{' + m[0].translate(supers) + '}', expression)
    expression = expression.replace('ħ', r'\hbar ').replace('ℏ', r'\hbar ')
    expression = expression.replace(r'\dfrac', r'\frac').replace(r'\tfrac', r'\frac').replace(r'\displaystyle', '')
    expression = re.sub(r'\\frac\s*([0-9A-Za-z])\s*([0-9A-Za-z])', r'\\frac{\1}{\2}', expression)
    expression = re.sub(r'\\frac\s*([0-9A-Za-z])\s*(\{)', r'\\frac{\1}\2', expression)
    expression = re.sub(r'(\\frac\{[^{}]+\})\s*([0-9A-Za-z])', r'\1{\2}', expression)
    expression = re.sub(r'\\sqrt\s*([0-9A-Za-z])', r'\\sqrt{\1}', expression)
    expression = re.sub(r'\\(mathbf|mathrm|mathit|mathsf|mathtt)\s+([A-Za-z])', r'\\\1{\2}', expression)
    expression = re.sub(r'\\le(?![a-z])', r'\\leq', expression)
    expression = re.sub(r'\\ge(?![a-z])', r'\\geq', expression)
    value, prop = '$' + expression + '$', FontProperties(size=size)
    missing = []
    class GlyphAudit(logging.Handler):
        def emit(self, record):
            if 'dummy symbol' in record.getMessage():
                missing.append(record.getMessage())
    logger, audit = logging.getLogger('matplotlib._mathtext'), GlyphAudit()
    propagation = logger.propagate
    logger.addHandler(audit)
    logger.propagate = False
    try:
        parsed = MathTextParser('path').parse(value, dpi=72, prop=prop)
        buffer = io.BytesIO()
        math_to_image(value, buffer, prop=prop, format='pdf', dpi=72)
        if missing:
            raise ValueError(f'Missing math glyph in {expression!r}: {missing[0]}')
    finally:
        logger.removeHandler(audit)
        logger.propagate = propagation
    doc = fitz.open(stream=buffer.getvalue(), filetype='pdf')
    return doc, doc[0].rect.width, doc[0].rect.height, float(parsed.depth)


def rich_tokens(value, size):
    tokens, offset = [], 0
    for match in re.finditer(r'\$([^$]+)\$', value):
        tokens.extend(('text', ch, 0 if ch == '\n' else glyph_width(ch, size), size * 1.15, size * .25) for ch in value[offset:match.start()])
        doc, width, height, descent = math_pdf(match.group(1), size)
        tokens.append(('math', doc, width, height - descent, descent))
        offset = match.end()
    tokens.extend(('text', ch, 0 if ch == '\n' else glyph_width(ch, size), size * 1.15, size * .25) for ch in value[offset:])
    return tokens


def readable_formula(value, size=8.5):
    """Safely improve legacy linear notation without interpreting its algebra."""
    if '$' in value or re.search(r'[\u1100-\u11ff\u3130-\u318f가-힣]', value):
        return value
    expression = value.replace('²', '^2').replace('³', '^3')
    expression = re.sub(r'\^\(([^()]*)\)', r'^{\1}', expression)
    expression = re.sub(r'\^(-?\d+)', r'^{\1}', expression)
    expression = re.sub(r'_([A-Za-z][A-Za-z0-9]*|\d+)',
                        lambda m: '_{' + (r'\mathrm{' + m[1] + '}' if len(m[1]) > 1 and m[1].isalpha() else m[1]) + '}', expression)
    expression = re.sub(r'_(\([^()]*\))', lambda m: '_{' + m[1][1:-1] + '}', expression)
    expression = re.sub(r'([μεσ])([0-9])', r'\1_{\2}', expression)
    # Square roots are bracketed syntactically; no simplification or precedence
    # inference is performed, so signs and physical factors remain unchanged.
    while 'sqrt(' in expression:
        begin = expression.rfind('sqrt(')
        depth, end = 1, begin + 5
        while end < len(expression) and depth:
            if expression[end] == '(': depth += 1
            elif expression[end] == ')': depth -= 1
            end += 1
        if depth: return value
        expression = expression[:begin] + r'\sqrt{' + expression[begin+5:end-1] + '}' + expression[end:]
    for symbol, macro in {'π':'pi','μ':'mu','ε':'epsilon','σ':'sigma','α':'alpha','β':'beta','γ':'gamma',
                          'δ':'delta','θ':'theta','λ':'lambda','ω':'omega','τ':'tau','η':'eta','Δ':'Delta',
                          'Φ':'Phi','ℏ':'hbar','ħ':'hbar','∞':'infty','≈':'approx','≤':'leq','≥':'geq',
                          '∝':'propto','∫':'int','Σ':'sum'}.items():
        expression = expression.replace(symbol, '\\' + macro + ' ')
    expression = expression.replace('*', r'\cdot ').replace('=>', r'\Rightarrow ')
    expression = re.sub(r'(?<![A-Za-z\\])(sin|cos|tan|ln|exp)(?=\()', r'\\\1', expression)
    try:
        math_pdf(expression, size)
    except (ValueError, RuntimeError):
        return value
    return '$' + expression + '$'


def _paste(page, original, clip):
    """Use the original PDF's rules, logo and footer as vector objects."""
    source = original[0]
    sx, sy = A4.width / source.rect.width, A4.height / source.rect.height
    clip = fitz.Rect(clip)
    dest = fitz.Rect(clip.x0 * sx, clip.y0 * sy, clip.x1 * sx, clip.y1 * sy)
    page.show_pdf_page(dest, original, 0, clip=clip, keep_proportion=False)


def frame(page, title, subtitle, number, total, source_note=True, header_source=None,
          preserve_header=False, columns=True):
    original = fitz.open(header_source if preserve_header and header_source else STATIONERY)
    w, h = original[0].rect.width, original[0].rect.height
    sx, sy = A4.width / w, A4.height / h
    _paste(page, original, (0, 0, w, h * 86 / 1031))
    if not preserve_header:
        # Preserve the official logo and thick horizontal rule. Only the varying
        # title/year and course line are replaced in their original positions.
        page.draw_rect(fitz.Rect(170 * sx, 27 * sy, 680 * sx, 80 * sy),
                       color=None, fill=(1, 1, 1))
        text(page, (175 * sx, 35 * sy, 625 * sx, 55 * sy), title, 12.0, 1, style='head')
        display_level = '    '.join(subtitle) if subtitle.endswith('과정') and ' ' not in subtitle else subtitle
        text(page, (55 * sx, 59 * sy, 673 * sx, 80 * sy), display_level, 12.0, 1, style='head')
    if columns:
        # The original separator is a PDF path, not an approximated new rule.
        reference = fitz.open(STATIONERY)
        _paste(page, reference, (363.60, 89.90, 364.04, 967.36))
        reference.close()
    reference = fitz.open(STATIONERY)
    _paste(page, reference, (328, 970, 410, 986))
    rsx, rsy = A4.width / 728, A4.height / 1031
    # Leave the original vector word '페이지'; change its changing numbers.
    page.draw_rect(fitz.Rect(367.4 * rsx, 970 * rsy, 410 * rsx, 986 * rsy),
                   color=None, fill=(1, 1, 1))
    text(page, (369 * rsx, 970 * rsy, 444 * rsx, 989 * rsy), f'{number} / {total}', 8.15)
    if source_note:
        note = source_note if isinstance(source_note, str) else '자체 편집 자료 · 한국물리학회 공식 배포본이 아님'
        text(page, (46.5, 820, 549, 834), note, 6.3, 1)
    reference.close()
    original.close()


class ColumnFlow:
    """Keep every explanation in the official two-column page grid, including continuations."""
    def __init__(self, doc, title, level, note, header_source=None, preserve_header=False, kind='해설'):
        self.doc, self.title, self.level, self.note = doc, title, level, note
        self.header_source, self.preserve_header = header_source, preserve_header
        self.kind, self.region_records, self.active_region = kind, {}, None
        self.column, self.y, self.page, self.question = 1, BOTTOM, None, None
        self.new_column()

    @property
    def x(self):
        return COLUMNS[self.column][0]

    @property
    def width(self):
        return COLUMNS[self.column][1] - self.x

    def new_column(self, continuation=False):
        self.end_region()
        if self.column == 1:
            self.page = self.doc.new_page(width=A4.width, height=A4.height)
            self.column = 0
        else:
            self.column = 1
        self.y = TOP
        if continuation and self.question is not None:
            self.start_region()
            text(self.page, (self.x, self.y, self.x + self.width, self.y + 17),
                 f'{self.question}번 {self.kind} (계속)', 8)
            self.y += 22

    def start_region(self):
        self.active_region = (len(self.doc), self.column, self.y)

    def end_region(self):
        if self.active_region is not None:
            page, column, top = self.active_region
            left, right = COLUMNS[column]
            rect = [left/A4.width, top/A4.height, right/A4.width, min(self.y, BOTTOM)/A4.height]
            self.region_records.setdefault(self.question, []).append({'page': page, 'rect': [round(v, 6) for v in rect]})
            self.active_region = None

    def reserve(self, height, continuation=True):
        if height > BOTTOM - TOP - 25:
            raise ValueError(f'Unbreakable block too high: {height}')
        if self.y + height > BOTTOM:
            self.new_column(continuation)

    def heading(self, number, label, keep=75):
        self.end_region()
        self.reserve(keep, False)
        self.question = number
        self.start_region()
        text(self.page, (self.x, self.y, self.x + self.width, self.y + 19),
             f'{number}. {label}', 10.3)
        self.y += 25

    def paragraph_height(self, value, size=9.8, gap=8):
        if '$' not in value:
            return len(wrap(value, self.width, size)) * size * 1.45 + gap
        tokens = rich_tokens(value, size)
        total = width = 0
        ascent, descent = size * 1.15, size * .25
        for token in tokens:
            if width and (width + token[2] > self.width or token[1] == '\n'):
                total += max(size * 1.45, ascent + descent + 2)
                width, ascent, descent = 0, size * 1.15, size * .25
            width += min(token[2], self.width)
            ascent, descent = max(ascent, token[3]), max(descent, token[4])
        return total + max(size * 1.45, ascent + descent + 2) + gap

    def paragraph(self, value, size=9.8, gap=8):
        if '$' in value:
            return self.rich_paragraph(value, size, gap)
        # Widths differ by four points. Rewrap the remaining text on a column
        # transition rather than carrying a line measured for another column.
        remaining = value
        while remaining:
            line = wrap(remaining, self.width, size)[0]
            if not line and remaining.startswith('\n'):
                remaining = remaining[1:]
                self.y += size * 1.45
                continue
            self.reserve(size * 1.45)
            if measure(line, size) > self.width:
                line = wrap(remaining, self.width, size)[0]
            text(self.page, (self.x, self.y, self.x + self.width, self.y + size * 1.4), line, size)
            remaining = remaining[len(line):].lstrip(' \n')
            self.y += size * 1.45
        self.y += gap

    def rich_paragraph(self, value, size, gap):
        remaining = rich_tokens(value, size)
        while remaining:
            line, width = [], 0
            for token in remaining:
                if token[0] == 'text' and token[1] == '\n':
                    break
                if line and width + token[2] > self.width:
                    break
                if token[2] > self.width:
                    factor = self.width / token[2]
                    token = (token[0], token[1], token[2] * factor, token[3] * factor, token[4] * factor)
                line.append(token)
                width += token[2]
            if not line:
                remaining = remaining[1:]
                self.y += size * 1.45
                continue
            ascent = max(t[3] for t in line)
            descent = max(t[4] for t in line)
            height = max(size * 1.45, ascent + descent + 2)
            old_column = self.column
            self.reserve(height)
            if old_column != self.column and width > self.width:
                continue
            baseline, x, run = self.y + ascent, self.x, ''
            def flush():
                nonlocal x, run
                if run:
                    text(self.page, (x, baseline-size*1.15, self.x+self.width+.02, baseline+size*.3), run, size)
                    x += measure(run, size)
                    run = ''
            for token in line:
                if token[0] == 'text':
                    run += token[1]
                else:
                    flush()
                    self.page.show_pdf_page(fitz.Rect(x, baseline-token[3], x+token[2], baseline+token[4]), token[1], 0)
                    x += token[2]
            flush()
            remaining = remaining[len(line):]
            while remaining and remaining[0][0] == 'text' and remaining[0][1] in ' \n':
                remaining = remaining[1:]
            self.y += height
        self.y += gap

    def figure(self, source, page, rect, max_height=172):
        clip = fitz.Rect(rect)
        h = min(max_height, self.width * clip.height / clip.width)
        self.reserve(h + 10)
        self.page.show_pdf_page(fitz.Rect(self.x, self.y, self.x + self.width, self.y + h),
                                source, page - 1, clip=clip, keep_proportion=True)
        self.y += h + 12

    def review_notice(self):
        height = 27
        self.reserve(height + 9)
        self.page.draw_rect(fitz.Rect(self.x, self.y, self.x + self.width, self.y + height), color=(0, 0, 0), width=.7)
        text(self.page, (self.x + 6, self.y + 5, self.x + self.width - 6, self.y + height - 3),
             '원문·정답 검토 필요', 9, style='head')
        self.y += height + 9

    def finish(self):
        self.end_region()
        for i, page in enumerate(self.doc):
            frame(page, self.title, self.level, i + 1, len(self.doc), self.note,
                  self.header_source, self.preserve_header)
