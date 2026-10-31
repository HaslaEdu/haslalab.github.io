"""New prose fonts, prioritising actual source Latin and then the same face.

No original PDF resource is changed. A new prose-only copy keeps every live
source glyph untouched, and fills only unavailable Latin from the installed
same-version SimSun face. Missing SimHei Latin uses the source's explicit
same-run Latin prose counterpart DengXian Light, not a generic sans face.
"""
from pathlib import Path
from io import BytesIO
from functools import lru_cache
import hashlib,json,os
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
import pymupdf as fitz
import cpho_2013_original_extract as source

OUT=source.BASE/'fonts'
DENG_CACHE=Path(os.environ.get('HASLA_CPHO2013_FONT_CACHE',
    'D:/CodexBuilds/Hasla-original-style-20261031/2013-fonts'if Path('D:/CodexBuilds').exists()else str(source.BASE/'fonts-source')))
DENG_LIGHT_SHA='fc1cfb6ff7b8126aeaacfb0d55e0fdd29cc8a2bee9c312554f5d3953feace08b'

def acquire_deng_light():
    """Reuse verified, read-only official pack extraction; never run setup."""
    import subprocess,shutil,types
    import cpho_2024_original_fonts as official
    old_base,old_subprocess=official.BASE,official.subprocess
    def current_shell(args,*a,**kw):
        if args[0]=='powershell'and shutil.which('pwsh'):args=['pwsh',*args[1:]]
        return subprocess.check_output(args,*a,**kw)
    try:
        official.BASE=DENG_CACHE
        official.subprocess=types.SimpleNamespace(run=subprocess.run,check_output=current_shell)
        official.acquire()
        subprocess.run(['expand.exe','-F:DENGL.TTF',str(DENG_CACHE/'font-data-0.cab'),str(DENG_CACHE/'faces')],check=True)
    finally:official.BASE,official.subprocess=old_base,old_subprocess
    path=DENG_CACHE/'faces/DENGL.TTF'
    if sha(path)!=DENG_LIGHT_SHA:raise ValueError('Official DengXian Light SHA mismatch')
    return path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@lru_cache(maxsize=2)
def english_face(face):
    if face not in ['SimSun','SimHei']:raise ValueError('Unreviewed original prose face')
    OUT.mkdir(parents=True,exist_ok=True)
    donor_path=Path('C:/Windows/Fonts/simsun.ttc')if face=='SimSun'else DENG_CACHE/'faces/DENGL.TTF'
    if face=='SimHei'and(not donor_path.exists()or sha(donor_path)!=DENG_LIGHT_SHA):
        raise FileNotFoundError('Verified original-run Latin counterpart needed: python tools/cpho_2013_original_fonts.py acquire')
    target=OUT/(face+'-original-Latin-first.ttf');report=target.with_suffix('.font-provenance.json')
    author=dict(source_sha256=source.SOURCE_SHA,donor_sha256=sha(donor_path),builder_sha256=sha(__file__))
    if target.exists()and report.exists()and json.loads(report.read_text('utf8')).get('authoring')==author:return target
    with fitz.open(source.SOURCE)as doc:
        candidates=[r for r in doc[0].get_fonts()if r[3].split('+')[-1]==face]
        if not candidates:raise ValueError('Original prose face absent')
        font_data=doc.extract_font(candidates[0][0])[3]
    font=TTFont(BytesIO(font_data),recalcTimestamp=False)
    donor=TTFont(donor_path,fontNumber=0,recalcTimestamp=False)
    source_map=font.getBestCmap();donor_map=donor.getBestCmap();glyphset=font.getGlyphSet();donor_set=donor.getGlyphSet()
    kept=[];filled=[];scale=font['head'].unitsPerEm/donor['head'].unitsPerEm
    # Fixed Latin repertoire, independent of translated text or fitting.
    repertoire=''.join(chr(n)for n in range(32,127))+'–—’“”−×°²³·'
    for char in repertoire:
        code=ord(char);name=source_map.get(code);bounds=None
        if name is not None:
            pen=BoundsPen(glyphset);glyphset[name].draw(pen);bounds=pen.bounds
        if name is not None and(bounds is not None or char==' 'and font['hmtx'][name][0]>0):
            kept.append(dict(char=char,glyph=name,gid=font.getGlyphID(name),bounds=bounds));continue
        donor_name=donor_map.get(code)
        if donor_name is None:
            if code<127:raise ValueError('Explicit face donor lacks '+repr(char))
            continue
        if name is None:
            name=f'newlatin{code:04X}';font.setGlyphOrder(font.getGlyphOrder()+[name])
        recording=DecomposingRecordingPen(donor_set);donor_set[donor_name].draw(recording)
        pen=TTGlyphPen(None);recording.replay(TransformPen(pen,(scale,0,0,scale,0,0)))
        glyph=pen.glyph()
        if hasattr(glyph,'coordinates'):glyph.coordinates.toInt()
        font['glyf'][name]=glyph
        width,lsb=donor['hmtx'][donor_name];font['hmtx'][name]=(round(width*scale),round(lsb*scale))
        for table in font['cmap'].tables:
            if table.isUnicode():table.cmap[code]=name
        filled.append(dict(char=char,glyph=name,source_missing_actual_outline=True,donor_glyph=donor_name))
    font['head'].modified=font['head'].created
    font.save(target);font.close();donor.close()
    report.write_text(json.dumps(dict(authoring=author,source_face=face,
        source_font_program_sha256=hashlib.sha256(font_data).hexdigest(),
        actual_source_glyphs_kept=kept,missing_actual_glyphs_filled=filled,donor=str(donor_path),
        donor_role='Same face and version SimSun5.24'if face=='SimSun'else'Original same-run Latin prose counterpart DengXian-Light. Official1.14 matches all four live source1.21 numeral contours, bbox and advance exactly; see deng-light-source-comparison.json. Source SimHei5.05 itself is not installed.',
        changed_original_pdf_font_programs=False,existing_source_glyph_outlines_modified=False,
        source_to_donor_upem_scale=scale,output_sha256=sha(target)),ensure_ascii=False,indent=2),'utf8')
    return target

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('command',choices=['acquire','verify']);a=p.parse_args()
    if a.command=='acquire':print(acquire_deng_light())
    else:
        for face in ['SimSun','SimHei']:print(face,english_face(face))
