"""Measured KPS answer-key stationery and verified sitting dates.

This module does not modify official PDFs.  ``draw_exam_date`` pastes the
original dated key's native glyphs for 2025/26.  Earlier sittings use the latest
2026 key's exact embedded KoPub outlines, supplemented by the original full
KoPub font only for characters absent from that subset.  Font programs are
cached under tmp, never distributed as repository source files.

Public integration contract:
    exam_date_profile(year, part) -> measured dictionary
    draw_exam_date(page, year, part) -> destination Rect
    build_2023_key(year, part, answers, target, corrections=None) -> Path
    python tools/kphe_key_design.py --measure
"""
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import io
import json
import math
import re

import pymupdf as fitz
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen

from kphe_fonts import font_path, _family
from kphe_source_fonts import unicode_cids

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'tmp/kphe_archive/originals'
PROFILES = ROOT / 'tools/kphe_key_design_profiles.json'
DATES = ROOT / 'tools/kphe_exam_dates.json'
CACHE = ROOT / 'tmp/kphe-key-fonts'
A4 = fitz.paper_rect('a4')
NATIVE = fitz.Rect(0, 0, 728, 1031)
LATEST = INPUT / 'KPhE_2026_T2aK.pdf'
LEVELS = {'a': '초급과정', 'b': '중급과정', 'c': '고급과정', 'd': '전문가과정'}

SESSIONS = {
    '2023-1': ('2023-02-18', 'https://kphe.kps.or.kr/notice/notice_detail/34',
               '2023년 2월 18일 토요일에 개최 예정인 2023년 제1회 물리대회'),
    '2023-2': ('2023-09-02', 'https://kphe.kps.or.kr/notice/notice_detail/111',
               '2023년 9월 2일(토)에 온라인으로 시행되는 2023년 제2회 물리대회'),
    '2024-1': ('2024-02-24', 'https://kphe.kps.or.kr/board/board_detail/8',
               '2024년 제1회 물리대회(2024. 2. 24 시행) 기출문제&정답'),
    '2024-2': ('2024-08-31', 'https://kphe.kps.or.kr/board/board_detail/9',
               '2024년 제2회 물리대회(2024. 8. 31 시행) 기출문제&정답'),
    '2025-1': ('2025-02-22', 'https://kphe.kps.or.kr/board/board_detail/10',
               '2025년 제1회 물리대회(2025. 2. 22 시행) 기출문제&정답'),
    '2025-2': ('2025-08-30', 'https://kphe.kps.or.kr/board/board_detail/11',
               '2025년 제2회 물리대회(2025. 8. 30 시행) 기출문제&정답'),
    '2026-1': ('2026-02-28', 'https://kphe.kps.or.kr/board/board_detail/12',
               '2026년 제1회 물리대회(2026. 2. 28 시행) 기출문제&정답'),
    '2026-2': ('2026-09-05', 'https://kphe.kps.or.kr/board/board_detail/43',
               '2026년 제2회 물리대회(2026. 9. 5 시행) 기출문제&정답'),
}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _spans(page, raw=False):
    return [s for b in page.get_text('rawdict' if raw else 'dict')['blocks']
            if b['type'] == 0 for line in b['lines'] for s in line['spans']]


def _text(span):
    return span.get('text', ''.join(c['c'] for c in span.get('chars', [])))


def _mapped_box(box, source=NATIVE, destination=A4):
    sx, sy = destination.width / source.width, destination.height / source.height
    return [box[0]*sx, box[1]*sy, box[2]*sx, box[3]*sy]


def _span_record(span, page):
    result = {k: span[k] for k in ('font', 'size', 'bbox', 'origin')}
    result['text'] = _text(span)
    result['a4_bbox'] = _mapped_box(span['bbox'], page.rect)
    result['a4_origin'] = [span['origin'][0]*A4.width/page.rect.width,
                           span['origin'][1]*A4.height/page.rect.height]
    result['a4_point_x'] = span['size']*A4.width/page.rect.width
    result['a4_point_y'] = span['size']*A4.height/page.rect.height
    result['a4_point'] = math.sqrt(result['a4_point_x']*result['a4_point_y'])
    return result


@lru_cache(None)
def _native_font(source, name):
    """Restore original Unicode->CID->GID mappings without changing outlines."""
    source = Path(source)
    key = hashlib.sha256((str(source)+_sha(source)+name+'compact-unicode-v4-pdf-metrics').encode()).hexdigest()
    CACHE.mkdir(exist_ok=True)
    target = CACHE / (key+'.ttf')
    if target.is_file():
        return target
    pdf = fitz.open(source)
    xref = next(f[0] for f in pdf[0].get_fonts(full=True)
                if f[3].split('+')[-1] == name)
    src = TTFont(io.BytesIO(pdf.extract_font(xref)[3]))
    cmref = int(pdf.xref_get_key(xref, 'ToUnicode')[1].split()[0])
    cids = unicode_cids(pdf.xref_stream(cmref).decode())
    descendant = int(pdf.xref_get_key(xref, 'DescendantFonts')[1].split()[0][1:])
    mapping = pdf.xref_get_key(descendant, 'CIDToGIDMap')[1]
    if mapping != '/Identity':
        data = pdf.xref_stream(int(mapping.split()[0]))
        cids = {code: int.from_bytes(data[cid*2:cid*2+2], 'big') for code,cid in cids.items()}
    used = {ord(ch) for span in _spans(pdf[0]) if span['font'] == name
            for ch in span['text']}
    cids = {code: gid for code,gid in cids.items() if code in used}
    # Keep the tiny original subset and add only genuinely absent characters.
    # Copying the entire Korean font would needlessly add >10,000 glyphs.
    supplement = 'KoPubDotumBold' if name == 'KoPubDotumBold' else 'HCRBatang'
    full = TTFont(font_path(supplement))
    dst = src
    order = list(dst.getGlyphOrder())
    original_order = list(order)
    unicode_map = {}
    for code, gid in cids.items():
        if gid >= len(original_order):
            raise ValueError(f'Invalid original glyph {name} U+{code:04X}')
        unicode_map[code] = original_order[gid]
    needed = set('0123456789/')
    if name == 'Haansoft Batang':
        needed.update('전원 정답최종인정답안한국물리학회공식정정공지')
        needed.update(chr(n) for n in range(32,127))
    glyphs, full_cmap = full.getGlyphSet(), full.getBestCmap()
    scale = dst['head'].unitsPerEm / full['head'].unitsPerEm
    for ch in sorted(needed):
        code = ord(ch)
        if code in unicode_map:
            continue
        glyph_name = f'KPSKeySupplement_{code:04X}'
        if code not in full_cmap:
            raise ValueError(f'Missing original supplement glyph {ch!r}')
        record = DecomposingRecordingPen(glyphs)
        glyphs[full_cmap[code]].draw(record)
        pen = TTGlyphPen(None)
        record.replay(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
        dst['glyf'][glyph_name] = pen.glyph()
        advance, left = full['hmtx'][full_cmap[code]]
        dst['hmtx'][glyph_name] = round(advance*scale), round(left*scale)
        order.append(glyph_name)
        unicode_map[code] = glyph_name
    cmap = newTable('cmap')
    cmap.tableVersion = 0
    table = CmapSubtable.newSubtable(4)
    table.platformID, table.platEncID, table.language = 3, 1, 0
    table.cmap = unicode_map
    cmap.tables = [table]
    dst['cmap'] = cmap
    dst.setGlyphOrder(order)
    dst['maxp'].numGlyphs = dst['hhea'].numberOfHMetrics = len(order)
    family = f'KPS Key {name} {key[:12]}'
    if 'name' not in dst:
        dst['name'] = newTable('name')
        dst['name'].names = []
        for name_id in (1,3,4,6,16):
            dst['name'].setName(family.replace(' ','') if name_id==6 else family,
                                name_id,3,1,0x409)
    else:
        _family(dst, family)
    # The HWP PDF explicitly overrides the TTF's ascent/descent. Match those
    # source PDF metrics as well as its outlines and baseline coordinates.
    descriptor = int(pdf.xref_get_key(descendant,'FontDescriptor')[1].split()[0])
    for field, attribute in (('Ascent','ascent'),('Descent','descent')):
        kind,value = pdf.xref_get_key(descriptor,field)
        if kind in ('int','real'):
            setattr(dst['hhea'],attribute,round(float(value)*dst['head'].unitsPerEm/1000))
    dst.save(target)
    return target


def _font(page, face):
    path = _native_font(str(LATEST), face)
    resource = 'KPSKeyHead' if face == 'KoPubDotumBold' else 'KPSKeyBody'
    registry = getattr(page.parent, '_kphe_key_fonts', None)
    if registry is None:
        page.parent._kphe_key_fonts = registry = set()
    if (page.xref, resource) not in registry:
        page.insert_font(fontname=resource, fontfile=str(path))
        registry.add((page.xref, resource))
    return resource


def _put_chars(page, chars, values=None, dy=0, face='Haansoft Batang', size=15):
    values = values if values is not None else ''.join(c['c'] for c in chars)
    if len(values) != len(chars):
        raise ValueError('Original glyph placement requires the same character count')
    resource = _font(page, face)
    for char, value in zip(chars, values):
        x,y = char['origin']
        page.insert_text((x, y+dy), value, fontname=resource, fontsize=size)


def _date_text(year):
    y,m,d = SESSIONS[str(year)][0].split('-')
    return f'{y}. {int(m)}. {int(d)}'


def _new_date_native(page, year):
    """Use measured original character spacing, not a substitute text width."""
    ref = fitz.open(LATEST)
    donor = next(s for s in _spans(ref[0], True) if _text(s) == '2026. 9. 5')
    center = (donor['bbox'][0]+donor['bbox'][2])/2
    value = _date_text(year)
    # Retain every measured original origin through the first day digit. All
    # eight verified sittings have a one-digit month. A second day digit follows
    # the measured mean numeric advance; no generic font width is substituted.
    offsets = [c['origin'][0]-donor['origin'][0] for c in donor['chars']]
    if len(value)==11:
        offsets.append(offsets[-1]+(offsets[3]-offsets[0])/3)
    if len(value)!=len(offsets):
        raise ValueError('Unexpected verified date format')
    final_width=donor['chars'][-1]['bbox'][2]-donor['chars'][-1]['bbox'][0]
    width=offsets[-1]+final_width
    x, baseline = center-width/2, donor['origin'][1]
    resource = _font(page, 'KoPubDotumBold')
    for ch,offset in zip(value,offsets):
        page.insert_text((x+offset, baseline), ch, fontname=resource, fontsize=15)
    box = fitz.Rect(center-width/2, donor['bbox'][1], center+width/2, donor['bbox'][3])
    ref.close()
    return box


@lru_cache(None)
def _dates():
    if not DATES.exists():
        raise FileNotFoundError('Run tools/kphe_key_design.py --measure first')
    return json.loads(DATES.read_text(encoding='utf-8'))


def exam_date_profile(year, part):
    """The bbox is in 595x842 A4 points, matching kphe_template._paste."""
    return _dates()['profiles'][f'{year}:{part}']


def solution_header_prepared(page, year, part):
    profile=exam_date_profile(str(year),part)
    if not profile.get('header_rule_adjustment'):
        return True
    marker=page.parent.xref_get_key(page.xref,'KPhEDateHeaderRule')[1]
    return marker==profile['header_rule_adjustment']['idempotence_marker']


def prepare_solution_header(page, year, part):
    """Move only a colliding 2024 solution header rule, once per PDF page."""
    profile=exam_date_profile(str(year),part)
    adjustment=profile.get('header_rule_adjustment')
    if not adjustment or solution_header_prepared(page,year,part):
        return False
    sx,sy=page.rect.width/A4.width,page.rect.height/A4.height
    def box(values):
        return fitz.Rect(values[0]*sx,values[1]*sy,values[2]*sx,values[3]*sy)
    old,new=box(adjustment['old_a4_bbox']),box(adjustment['new_a4_bbox'])
    # Cover the entire original anti-aliased fringe. On a v1 document also
    # clear the previously drawn new rule before drawing it once, avoiding
    # darkened AA edges from painting the same black rectangle twice.
    padding=adjustment['cover_padding_pt']
    for region in (old,new):
        page.draw_rect(region+(-padding,-padding,padding,padding),color=None,fill=(1,1,1))
    page.draw_rect(new,color=None,fill=(0,0,0))
    page.parent.xref_set_key(page.xref,'KPhEDateHeaderRule',f'({adjustment["idempotence_marker"]})')
    return True


def draw_exam_date(page, year, part):
    """Add only the date in the original key's place; return its target box."""
    profile = exam_date_profile(str(year), part)
    prepare_solution_header(page,year,part)
    if profile['method'] == 'original_key_native_vector_clip':
        original = fitz.open(ROOT/profile['source_original'])
        source_box = fitz.Rect(profile['native_bbox'])
        source_page = original[0]
    else:
        original = fitz.open()
        source_page = original.new_page(width=NATIVE.width, height=NATIVE.height)
        source_box = _new_date_native(source_page, str(year))
    # Padding avoids numerical clipping of outlines at the measured span edge.
    source_box += (-.08, -.08, .08, .08)
    dest = fitz.Rect(_mapped_box(source_box, source_page.rect, page.rect))
    page.show_pdf_page(dest, original, 0, clip=source_box, keep_proportion=False)
    original.close()
    return fitz.Rect(_mapped_box(profile['native_bbox'], NATIVE, page.rect))


def build_2023_key(year, part, answers, target, corrections=None):
    """Reflow the existing answers on the latest official two-column key grid.

    ``answers`` stays authoritative: an integer is one answer and a list denotes
    alternate accepted answers. This function never recalculates or changes it.
    Existing correction records can be retained on an additional dated page.
    """
    year = str(year)
    if not year.startswith('2023-') or part not in ('T1b','T1c','T2b','T2c','T2d'):
        raise ValueError('Only the five supplied 2023 answer sets may be rebuilt')
    if not 1 <= len(answers) <= 26:
        raise ValueError('The measured key grid accommodates at most 26 answers')
    reference = fitz.open(INPUT/f'KPhE_2026_T2{part[-1]}K.pdf')
    native = fitz.open()
    page = native.new_page(width=NATIVE.width, height=NATIVE.height)
    page.show_pdf_page(fitz.Rect(0,0,728,86), reference, 0,
                       clip=fitz.Rect(0,0,728,86), keep_proportion=False)
    header = _spans(reference[0], True)
    title = next(s for s in header if '년 제' in _text(s))
    date = next(s for s in header if _text(s) == '2026. 9. 5')
    for span in (title, date):
        box = fitz.Rect(span['bbox']) + (-.15,-.15,.15,.15)
        page.add_redact_annot(box, fill=(1,1,1))
    page.apply_redactions(images=0, graphics=0)
    title_text = f'2023년 제{year[-1]}회 물리대회'
    _put_chars(page, title['chars'], title_text, face='KoPubDotumBold', size=18)
    _new_date_native(page, year)
    # The source is a list in two columns, not an invented answer-sheet table.
    page.draw_line((363.82000732421875,85.01702880859375),
                   (363.82000732421875,962.4110107421875), width=.12)
    footer = fitz.Rect(328,970,410,986)
    page.show_pdf_page(footer, reference, 0, clip=footer, keep_proportion=False)
    ref = fitz.open(LATEST)
    body = [s for s in _spans(ref[0], True) if re.match(r'^\d+\. 정답:', _text(s))]
    by_number = {int(_text(s).split('.')[0]): s for s in body}
    left = [by_number[n]['origin'][1] for n in range(1,14)]
    right = [by_number[n]['origin'][1] for n in range(14,26)] + [left[-1]]
    for i, answer in enumerate(answers, 1):
        column, row = divmod(i-1, 13)
        style = by_number[(1 if i < 10 else 10) if column == 0 else 14]
        glyphs = style['chars']
        prefix = f'{i}. 정답: '
        prefix_chars = glyphs[:-1]
        baseline = (left if column == 0 else right)[row]
        _put_chars(page, prefix_chars, prefix, baseline-style['origin'][1])
        accepted = answer if isinstance(answer, list) else [answer]
        if not accepted or any(not isinstance(n,int) or not 1 <= n <= 5 for n in accepted):
            raise ValueError(f'Invalid answer {i}: {answer!r}')
        label = ' / '.join('①②③④⑤'[n-1] for n in accepted)
        resource = _font(page, 'Haansoft Batang')
        x = glyphs[-1]['origin'][0]
        page.insert_text((x,baseline), label, fontname=resource, fontsize=15)
    if corrections:
        extra = native.new_page(width=NATIVE.width,height=NATIVE.height)
        resource = _font(extra, 'Haansoft Batang')
        y = 110.16
        for fix in corrections:
            label = '전원 정답' if fix.get('full_credit') else ' / '.join(
                '①②③④⑤'[n-1] for n in fix['accepted_answers'])
            for line in (f'{fix["number"]}번 최종 인정 답안: {label}',
                         f'한국물리학회 공식 정정 공지 {fix.get("date", "")}', fix['source']):
                extra.insert_text((56.76,y), line, fontname=resource, fontsize=12)
                y += 24
            y += 32
    out = fitz.open()
    for n in range(len(native)):
        result = out.new_page(width=A4.width,height=A4.height)
        result.show_pdf_page(A4,native,n,keep_proportion=False)
    out.set_metadata({'title':f'2023년 제{year[-1]}회 물리대회 {LEVELS[part[-1]]} 정답',
        'author':'한국물리학회 원문 정답 바탕 재조판',
        'subject':'2026 official key stationery; original accepted answers retained; '+
                   'exam date verified at '+SESSIONS[year][1]})
    out.subset_fonts()
    target = Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    out.save(target,garbage=4,deflate=True)
    out.close(); native.close(); reference.close(); ref.close()
    return target


def measure_profiles():
    manifest = json.loads((ROOT/'tools/theory/kphe.json').read_text(encoding='utf-8'))
    profiles, dates = {}, {}
    latest_doc = fitz.open(LATEST)
    latest_date = next(s for s in _spans(latest_doc[0]) if s['text']=='2026. 9. 5')
    latest_rule_y=next(d['rect'].y0 for d in latest_doc[0].get_drawings()
                       if d['rect'].width>600 and 80<d['rect'].y0<85)
    rule_audit=[]
    for entry in manifest['years']:
        year = str(entry['y'])
        if year not in SESSIONS:
            continue
        for f in entry['files']:
            if f['kind'] != 'key':
                continue
            part = f['part']
            original = ROOT/f['source_original'] if f.get('source_original') else INPUT/f['file']
            doc = fitz.open(original)
            page_records = []
            date_span = None
            for n,page in enumerate(doc):
                spans = _spans(page)
                header = [s for s in spans if s['bbox'][1]<90]
                date_parts = [s for s in header if re.match(r'^202\d[.]',s['text'])]
                if date_parts:
                    date_span = date_parts[0]
                page_records.append({'page':n+1,'native_size':[page.rect.width,page.rect.height],
                    'header':[_span_record(s,page) for s in header],
                    'answer_spans':[_span_record(s,page) for s in spans if s['bbox'][1]>=90],
                    'rules':[{'type':d['type'],'bbox':list(d['rect']),
                              'a4_bbox':_mapped_box(d['rect'],page.rect),'width':d.get('width'),
                              'a4_width':(d.get('width') or 0)*A4.width/page.rect.width}
                             for d in page.get_drawings()]})
            record = {'year':year,'part':part,'source_original':original.relative_to(ROOT).as_posix(),
                'source_sha256':_sha(original),'source_type':f.get('source_type','official_attachment'),
                'source_page':f.get('source_page'),'source_url':f.get('url'),
                'answer_count':len(entry['keys'][part]),'pages':page_records,
                'date_printed':bool(date_span)}
            if year=='2023-2' and part=='T2c':
                record['note']='The supplied standalone second advanced key repeats sitting 1; excluded. Answers come from the twenty red marks, not a standalone key design.'
            if year=='2023-1' and part=='T1b':
                record['note']='The supplied intermediate key has a wrong advanced heading on page 1; part identity follows the matched paper and page 2.'
            profiles[f'{year}:{part}'] = record
            generated = int(year[:4]) < 2025
            if generated:
                temp=fitz.open();page=temp.new_page(width=728,height=1031)
                box=_new_date_native(page,year)
                date_record={'method':'latest_2026_key_exact_subset_outlines_and_spacing',
                    'font':'KoPubDotumBold','native_point':15.0,'native_bbox':list(box),
                    'native_baseline':75.83999633789062,
                    'reference_original':LATEST.relative_to(ROOT).as_posix(),
                    'reference_sha256':_sha(LATEST),'date_printed_on_original_key':bool(date_span)}
                temp.close()
            else:
                if not date_span or date_span['text'] != _date_text(year):
                    raise ValueError(f'Official date mismatch: {year} {part}')
                date_record={'method':'original_key_native_vector_clip',
                    'font':date_span['font'],'native_point':date_span['size'],
                    'native_bbox':list(date_span['bbox']),'native_baseline':date_span['origin'][1],
                    'source_original':original.relative_to(ROOT).as_posix(),
                    'source_sha256':_sha(original),'date_printed_on_original_key':True}
            date_record.update({'year':year,'part':part,'text':_date_text(year),
                'exam_date':SESSIONS[year][0],'date_source_page':SESSIONS[year][1],
                'a4_bbox':_mapped_box(date_record['native_bbox']),
                'a4_baseline':date_record['native_baseline']*A4.height/1031,
                'a4_point_x':date_record['native_point']*A4.width/728,
                'a4_point_y':date_record['native_point']*A4.height/1031,
                'a4_point':date_record['native_point']*math.sqrt((A4.width/728)*(A4.height/1031))})
            if int(year[:4])>=2024:
                question=INPUT/f'KPhE_{year[:4]}_{part}_KO.pdf'
                qdoc=fitz.open(question);qp=qdoc[0]
                rules=[d for d in qp.get_drawings() if d['rect'].width>qp.rect.width*.75
                       and d['rect'].height<5 and qp.rect.height*.06<d['rect'].y0<qp.rect.height*.09]
                if len(rules)!=1:
                    raise ValueError(f'Ambiguous question-header rule {question.name}: {len(rules)}')
                old=fitz.Rect(_mapped_box(rules[0]['rect'],qp.rect))
                audit={'year':year,'part':part,'question_original':question.relative_to(ROOT).as_posix(),
                       'source_sha256':_sha(question),'native_bbox':list(rules[0]['rect']),
                       'a4_bbox':list(old),'type':rules[0]['type']}
                datebox=fitz.Rect(date_record['a4_bbox'])+(-.3,-.3,.3,.3)
                if old.intersects(datebox):
                    if rules[0]['type']!='f':
                        raise ValueError('Only the measured filled 2024 header rule may be moved')
                    center=latest_rule_y*A4.height/1031
                    new=fitz.Rect(old.x0,center-old.height/2,old.x1,center+old.height/2)
                    date_record['header_rule_adjustment']={
                        'scope':'independently typeset worked explanations only; never official P/K',
                        'reason':'The original 2024 question header rule crosses the latest official key date location. Move its center to the latest key lower-rule baseline, retaining original length/thickness.',
                        'old_a4_bbox':list(old),'new_a4_bbox':list(new),
                        'latest_key_rule_native_y':latest_rule_y,
                        'original_width_pt':old.width,'original_thickness_pt':old.height,
                        'cover_padding_pt':.7,'allowed_padding_pt':.8,
                        'idempotence_marker':f'{year}:{part}:v2'}
                    audit['adjustment']=date_record['header_rule_adjustment']
                rule_audit.append(audit);qdoc.close()
            dates[f'{year}:{part}']=date_record
            doc.close()
    data={'checked_on':'2026-10-30','a4_size':[A4.width,A4.height],
        'normalization':'x=A4.width/native.width; y=A4.height/native.height; matches kphe_template._paste, keep_proportion=False',
        'latest_reference':LATEST.relative_to(ROOT).as_posix(),
        'layout':'Two text columns separated by one vertical rule; no row/column answer-sheet grid.',
        'question_header_rule_audit':rule_audit,
        'profiles':profiles}
    # Keep the exhaustive per-span research reproducible without committing a
    # large raw dump. The small repository profile retains the measured contract.
    raw=ROOT/'tmp/kphe-key-design-qa/original-key-measurements.json'
    raw.parent.mkdir(exist_ok=True)
    raw.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raw_body=[s for s in _spans(latest_doc[0],True) if re.match(r'^\d+\. 정답:',_text(s))]
    latest_rows={int(_text(s).split('.')[0]):s for s in raw_body}
    data['latest_design_template']={
        'source_sha256':_sha(LATEST),'native_size':[728,1031],
        'headers':[_span_record(s,latest_doc[0]) for s in _spans(latest_doc[0]) if s['bbox'][1]<90],
        'body_font':'Haansoft Batang','native_body_point':15,
        'column_origins_native':[56.7599983215332,375.6000061035156],
        'left_baselines_native':[latest_rows[n]['origin'][1] for n in range(1,14)],
        'right_baselines_native':[latest_rows[n]['origin'][1] for n in range(14,26)]+[latest_rows[13]['origin'][1]],
        'last_right_row':'The 26th answer extends the 25-answer donor grid at the left 13th-row baseline.',
        'glyph_placement_examples':[
            {'number':n,'font':latest_rows[n]['font'],'native_point':latest_rows[n]['size'],
             'characters':[{'text':c['c'],'origin':c['origin'],'bbox':c['bbox']} for c in latest_rows[n]['chars']]}
            for n in (1,10,14)],
        'rules':data['profiles']['2026-2:T2a']['pages'][0]['rules']}
    summary={}
    for key,value in profiles.items():
        compact={k:v for k,v in value.items() if k!='pages'}
        compact['page_count']=len(value['pages'])
        compact['page_sizes']=[p['native_size'] for p in value['pages']]
        compact['header_faces']=sorted(set((s['font'],s['size']) for p in value['pages'] for s in p['header']))
        compact['answer_faces']=sorted(set((s['font'],s['size']) for p in value['pages'] for s in p['answer_spans']
                                           if '정답' in s['text'] or re.match(r'^\d+[.]',s['text'])))
        compact['answer_spans_measured']=sum(len(p['answer_spans']) for p in value['pages'])
        summary[key]=compact
    data['profiles']=summary
    data['raw_measurements']='tmp/kphe-key-design-qa/original-key-measurements.json (recreated by --measure; not committed)'
    PROFILES.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    DATES.write_text(json.dumps({'checked_on':'2026-10-30','a4_size':[A4.width,A4.height],
        'sessions':{year:{'exam_date':values[0],'source_page':values[1],
                          'evidence_text':values[2],'source_author':'한국물리학회',
                          'verified_by':'Opened official page using web tool, 2026-10-30'}
                    for year,values in SESSIONS.items()},
        'profiles':dates},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'key_profiles':len(profiles),'date_profiles':len(dates),'sessions':len(SESSIONS)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measure',action='store_true')
    args=parser.parse_args()
    if args.measure:
        print(json.dumps(measure_profiles(),ensure_ascii=False))
