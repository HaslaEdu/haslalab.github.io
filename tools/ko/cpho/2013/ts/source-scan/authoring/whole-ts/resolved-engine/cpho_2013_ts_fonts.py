"""TS-only actual SimHei donor, retaining every live source Latin outline.

Original PDF fonts are never modified. Only new translated prose uses this
retained-source-glyph subset, filled from the official matching SimHei face.
The older Deng-Light fallback remains preserved for historical proof identity.
"""
from pathlib import Path
from io import BytesIO
from functools import lru_cache
import json,hashlib,os
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.scaleUpem import scale_upem
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
SOURCE=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tmp/original-style-sources/CPhO_2013_Chinese_original.pdf')
SOURCE_SHA='612d676f525ddc35ad3b417a8f25141d3467f48309d52dfdbcab7bd222201d68'
SIMHEI_SHA='aa4560dd8fe5645745fed3ffa301c3ca4d6c03cbd738145b613303961ba733b8'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

@lru_cache(maxsize=2)
def english_face(face):
    if face=='SimSun':
        import cpho_2013_original_fonts as legacy
        legacy.OUT=BASE/'fonts-source'
        return legacy.english_face(face)
    if face!='SimHei':raise ValueError('Unknown original source face')
    if sha(SOURCE)!=SOURCE_SHA:raise ValueError('Original scanned/native source changed')
    folder=Path(os.environ.get('HASLA_OFFICIAL_HANS_FONT_DIR','D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces'))
    donor_path=folder/'simhei.ttf'
    if not donor_path.exists()or sha(donor_path)!=SIMHEI_SHA:raise FileNotFoundError('Acquire pinned official full SimHei5.03 with cpho_official_hans_fonts.py; full font is external and is never published in the repository.')
    out=BASE/'fonts-source/SimHei-actual-face-Latin-first.ttf';report=out.with_suffix('.font-provenance.json')
    author=dict(source_sha256=SOURCE_SHA,donor_sha256=SIMHEI_SHA,builder_sha256=sha(__file__))
    if out.exists()and report.exists()and json.loads(report.read_text('utf8')).get('authoring')==author:return out
    with fitz.open(SOURCE)as doc:
        resources=[r for r in doc[0].get_fonts()if r[3].split('+')[-1]==face]
        if len(resources)!=1:raise ValueError('Actual original prose face not unique')
        source_data=doc.extract_font(resources[0][0])[3]
        source_program_sha=hashlib.sha256(source_data).hexdigest()
        actual_used=[]
        for page_index,page in enumerate(doc):
            aliases=[]
            for resource in page.get_fonts():
                if resource[3].split('+')[-1]!=face:continue
                data=doc.extract_font(resource[0])[3]
                if hashlib.sha256(data).hexdigest()==source_program_sha:aliases.append(resource[4])
            if not aliases:continue
            for trace in page.get_texttrace():
                if trace['font'].split('+')[-1]!=face:continue
                for cp,gid,origin,bbox in trace['chars']:
                    actual_used.append(dict(source_page=page_index+1,font_aliases=aliases,c=chr(cp),gid=gid,origin=list(origin)))
    font=TTFont(BytesIO(source_data),recalcTimestamp=False);donor=TTFont(donor_path,recalcTimestamp=False)
    original_upem=font['head'].unitsPerEm;donor_upem=donor['head'].unitsPerEm
    if donor_upem%original_upem:raise ValueError('Need exact integer source-outline normalization, never rounded donor outlines')
    source_integer_scale=donor_upem//original_upem
    scale_upem(font,donor_upem)
    source_map=font.getBestCmap();donor_map=donor.getBestCmap();glyphs=font.getGlyphSet();donor_glyphs=donor.getGlyphSet();scale=font['head'].unitsPerEm/donor['head'].unitsPerEm
    kept=[];filled=[];used_keys={(r['c'],r['gid'])for r in actual_used}
    for c in ''.join(chr(n)for n in range(32,127))+'–—’“”−×°²³·':
        name=source_map.get(ord(c));bounds=None
        if name is not None:
            pen=BoundsPen(glyphs);glyphs[name].draw(pen);bounds=pen.bounds
        if name is not None and (c,font.getGlyphID(name)) in used_keys and (bounds is not None or c==' 'and font['hmtx'][name][0]>0):
            kept.append(dict(c=c,glyph=name,gid=font.getGlyphID(name),bounds=bounds,advance=font['hmtx'][name][0]));continue
        other=donor_map.get(ord(c))
        if other is None:
            if ord(c)<127:raise ValueError('Official same-face donor lacks Latin prose character')
            continue
        if name is None:name=f'newlatin{ord(c):04X}';font.setGlyphOrder(font.getGlyphOrder()+[name])
        rec=DecomposingRecordingPen(donor_glyphs);donor_glyphs[other].draw(rec);pen=TTGlyphPen(None);rec.replay(TransformPen(pen,(scale,0,0,scale,0,0)));glyph=pen.glyph()
        if hasattr(glyph,'coordinates'):glyph.coordinates.toInt()
        font['glyf'][name]=glyph;advance,lsb=donor['hmtx'][other];font['hmtx'][name]=(round(advance*scale),round(lsb*scale))
        for table in font['cmap'].tables:
            if table.isUnicode():table.cmap[ord(c)]=name
        filled.append(dict(c=c,glyph=name,donor_glyph=other,original_had_no_confirmed_used_source_outline=True,unused_cmap_outline_ignored=bounds is not None))
    font['head'].modified=font['head'].created;font.save(out);font.close();donor.close()
    report.write_text(json.dumps(dict(authoring=author,source_face=face,source_font_program_sha256=hashlib.sha256(source_data).hexdigest(),actual_source_glyphs_kept=kept,actual_used_source_trace_witness=actual_used,missing_actual_source_outlines_filled=filled,donor=str(donor_path),donor_face='SimHei',donor_version='5.03',donor_source='Official Microsoft Fonts-Hans package, independently SHA/AuthentiCode provenance in official-hans-fonts/fonts-provenance.json',source_face_priority='Actual used source Latin outline first, validated Unicode/GID/font-program/alias by all14 source-page traces; unused cmap outlines are not trusted. Missing actual-use witness is filled from official full matching face. No Deng fallback.',original_source_upem=original_upem,source_outline_exact_integer_normalization=source_integer_scale,new_font_upem=donor_upem,donor_outline_scale=scale,donor_coordinates_rounded=False,existing_source_glyph_normalized_outlines_and_advances_changed=False,original_pdf_font_programs_changed=False,output_sha256=sha(out)),ensure_ascii=False,indent=2),'utf8')
    return out
