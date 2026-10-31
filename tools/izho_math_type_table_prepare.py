"""Prepare immutable original MathType mathematics in reviewed IZhO score cells.

Only source-native glyphs also present in the old Korean PDF are mathematical
candidates. Authored translated prose/ASCII is removed from that set. This
module changes plan data only; it never writes a PDF or rewrites a font.
"""
from pathlib import Path
from collections import defaultdict
import sys,json,hashlib,os
import pymupdf as fitz
from pdf_original_text_ops import glyph_key
from pdf_native_inline_reposition import _traces
from izho_natural_spacing import ROOT,BUILD,records,token,visible,annotate_placements
from pdf_korean_natural_composer import normalize_placements
import izho_natural_spacing_rebuild as rebuild


def original_math_rows(original,translated,placements):
    old=_traces(translated)
    original_keys={(glyph_key(g),g['trace_gid'])for g in old if g['c'].strip()and g['trace_gid']>=0}
    authors=set();groups=defaultdict(list);normalized=normalize_placements(translated,placements)
    for row in records(translated):groups[row['trace']].append(row)
    for rows in groups.values():
        if not visible(rows):continue
        item=token(rows,'native');annotate_placements([item],normalized)
        if 'placement'in item and any('가'<=c<='힣'for c in normalized[item['placement']]['text']):authors.update(glyph_key(g)for g in rows if g['c'].strip())
    source=_traces(original)
    kept=[g for g in source if g['c'].strip()and g['trace_gid']>=0 and(glyph_key(g),g['trace_gid'])in original_keys and glyph_key(g)not in authors]
    anchors={(g['font'],round(g['size'],4),round(g['origin'][0],3),round(g['origin'][1],3))for g in kept}
    kept.extend(g for g in source if g['c'].strip()and g['trace_gid']<0 and(g['font'],round(g['size'],4),round(g['origin'][0],3),round(g['origin'][1],3))in anchors)
    return kept


def cell_groups(page,scopes,drawings,native):
    result=[];seen=set()
    for scope in scopes:
        cell=scope.get('original_grid_cell_rect')
        if not cell:continue
        key=tuple(round(v,3)for v in cell)
        if key in seen:continue
        seen.add(key);box=fitz.Rect(cell)
        glyphs=[g for g in native if box.contains(fitz.Point(g['origin']))]
        physical=[g for g in glyphs if g['trace_gid']>=0]
        if not physical:continue
        bounds=fitz.Rect()
        for g in physical:bounds|=fitz.Rect(g['bbox'])
        for drawing in drawings:
            r=fitz.Rect(drawing['rect'])
            if box.contains(r)and r.height<2 and r.width<box.width*.8:bounds|=r
        result.append(dict(source_at=scope['source_at'],cell=cell,rect=list(bounds),glyphs=len(physical),
            native_glyphs=[{k:g[k]for k in('c','font','size','origin')}for g in glyphs],baseline=scope['baseline'],
            native_source_fonts=sorted({g['font']for g in glyphs}),
            policy='Exact original native MathType/Latin/Symbol glyphs in the original grading cell remain at source coordinates. Original mathematical operators, units, scripts and image programs are unchanged; authored translated prose is packed only in the adjacent original gaps.'))
    return result


def prepare(year=2023,kind='TS'):
    if(year,kind)!=(2023,'TS'):raise ValueError('This reviewed source profile is only IZhO2023TS')
    edition=next(v for v in rebuild.inventory()if v['year']==year and v['kind']==kind)
    base=ROOT/edition['pdf'];old=ROOT/f'tools/ko/izho/{year}/{kind}/original_style';mapping={}
    for final,path in enumerate(sorted(old.glob('page*.json'),key=lambda p:int(p.stem[4:])),1):
        data=json.loads(path.read_text('utf8'));qa=ROOT/f'tmp/original-style-repair/{year}/{kind}/{path.stem}.qa.json'
        if not qa.exists():qa=ROOT/f'tmp/izho-original-style/{year}/{kind}/{path.stem}.qa.json'
        mapping[data['page']]=(final,json.loads(qa.read_text('utf8'))['placements'])
    original_function=rebuild.stationary_table_math
    with fitz.open(base)as translated:
        def reviewed(page,scopes,drawings):
            final,placements=mapping[page.number]
            return cell_groups(page,scopes,drawings,original_math_rows(page,translated[final-1],placements))
        rebuild.stationary_table_math=reviewed
        try:plans=rebuild.prepare(year,kind)
        finally:rebuild.stationary_table_math=original_function
    audit=[]
    for path in plans:
        data=json.loads(path.read_text('utf8'));audit.append(dict(page=data['page'],original_source_page=data['source_page'],cells=len(data['stationary_table_math']),native_glyphs=sum(len(v['native_glyphs'])for v in data['stationary_table_math']),fonts=sorted({font for v in data['stationary_table_math']for font in v.get('native_source_fonts',[])})))
    report=dict(source_profile='Original English source-native MathType plus old-Korean physical-glyph intersection, excluding authored translated prose',preparer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),pages=audit)
    out=BUILD/str(year)/kind/'math-type-stationary-table-prepare.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
    return plans

if __name__=='__main__':prepare()
