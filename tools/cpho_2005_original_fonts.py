"""Original prose-face selection for2005, with explicit source witnesses.

Windows collection faces are read/exported only; system fonts are not changed.
Chinese ordinal identifiers remain original PDF glyphs. Korean fallback faces
are used because the original Chinese faces have no Hangul.
"""
from pathlib import Path
from functools import lru_cache
from io import BytesIO
import hashlib,json,re
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
CACHE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/fonts')
WINDOWS=Path('C:/Windows/Fonts')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def simsun():
    collection=WINDOWS/'simsun.ttc';CACHE.mkdir(parents=True,exist_ok=True)
    target=CACHE/'installed-SimSun-5.24-face0.ttf'
    with TTFont(collection,fontNumber=0,recalcTimestamp=False)as font:
        if font['name'].getDebugName(6)!='SimSun'or font['name'].getDebugName(5)!='Version 5.24':
            raise ValueError('The reviewed original SimSun5.24 face is required')
        if font['OS/2'].usWeightClass!=400 or font['OS/2'].fsType&0x0102:raise ValueError('Unreviewed SimSun face weight/embedding profile')
        if not target.exists():font.save(target)
    return target


def source_face(slot):
    han=[c for c in slot['source_characters']if re.search('[\u3400-\u9fff]',c['c'])]
    return han[0]['font']if han else slot['source_font']


def select(slot,lang):
    if slot.get('retain_native'):return simsun() # unused zero-width fitting metric; no new font is embedded
    if lang=='ko':
        family='NotoSerifCJKkr'if slot['family']=='serif'else'NotoSansCJKkr'
        return ROOT/'tools/ko/fonts'/(family+('-Bold'if slot['bold']else'-Regular')+'.otf')
    face=source_face(slot)
    if face=='SimSun':return simsun()
    if face=='SimHei'and slot.get('original_paragraph_role')=='title':
        witnesses=[c for c in slot['source_characters']if c['c'].isdigit()and 'TimesNewRoman'in c['font']]
        if ''.join(c['c']for c in witnesses)!='22'or any(abs(c['size']-slot['size'])>.0001 or abs(c['origin'][1]-slot['origin'][1])>.02 for c in witnesses):
            raise ValueError('The same-run Latin prose counterpart is not the original22 title field')
        return WINDOWS/'times.ttf'
    raise ValueError('No reviewed exact-face or same-run prose counterpart for '+face)


def actual_source_face_comparisons():
    """Compare actual source-used outlines, never nominal unused cmap entries."""
    source=ROOT/'tmp/original-style-sources/CPhO_2005_Chinese_original.pdf';results=[]
    with fitz.open(source)as doc:
        for alias,target in [('F2',simsun()),('F1',WINDOWS/'times.ttf')]:
            resource=next(r for r in doc[0].get_fonts(full=True)if r[4]==alias)
            raw=doc.extract_font(resource[0])[3];actual={}
            family=re.sub(r'^[A-Z]{6}\+','',resource[3])
            for page in list(doc)[:3]:
                for trace in page.get_texttrace():
                    if re.sub(r'^[A-Z]{6}\+','',trace['font'])!=family:continue
                    for cp,gid,origin,bbox in trace['chars']:
                        if gid<0 or chr(cp).isspace():continue
                        if not(re.search('[\u3400-\u9fff]',chr(cp))if alias=='F2'else cp<128):continue
                        actual.setdefault(chr(cp),gid)
            rows=[]
            with TTFont(BytesIO(raw))as old,TTFont(target)as new:
                a=old.getGlyphSet();z=new.getGlyphSet();order=old.getGlyphOrder();cmap=new.getBestCmap()
                for character,gid in sorted(actual.items()):
                    old_name=order[gid];new_name=cmap[ord(character)];p=RecordingPen();q=RecordingPen()
                    a[old_name].draw(p);z[new_name].draw(q)
                    rows.append(dict(character=character,source_gid=gid,
                        source_advance=old['hmtx'][old_name],selected_advance=new['hmtx'][new_name],
                        advances_identical=old['hmtx'][old_name]==new['hmtx'][new_name],
                        actual_contours_identical=p.value==q.value,
                        source_contour_sha256=hashlib.sha256(repr(p.value).encode()).hexdigest(),
                        selected_contour_sha256=hashlib.sha256(repr(q.value).encode()).hexdigest()))
                results.append(dict(source_font_alias=alias,source_family=family,source_version=old['name'].getDebugName(5),
                    selected_version=new['name'].getDebugName(5),source_program_sha256=hashlib.sha256(raw).hexdigest(),
                    selected_program_sha256=sha(target),source_units_per_em=old['head'].unitsPerEm,
                    selected_units_per_em=new['head'].unitsPerEm,actual_source_used_glyphs_compared=len(rows),
                    unequal_advances_or_contours=[r for r in rows if not(r['advances_identical']and r['actual_contours_identical'])],glyph_comparisons=rows))
    return results


def provenance(slots):
    entries=[];known={}
    for slot in slots:
        if slot.get('retain_native'):continue
        face=source_face(slot);path=select(slot,'en')
        if path not in known:
            with TTFont(path)as font:
                info=dict(family=font['name'].getDebugName(1),postscript_name=font['name'].getDebugName(6),
                    version=font['name'].getDebugName(5),weight=font['OS/2'].usWeightClass,fsType=font['OS/2'].fsType)
            known[path]=dict(info,selected_font_sha256=sha(path))
        info=known[path]
        entries.append(dict(slot=slot['id'],original_prose_face=face,selected_font=str(path),
            selection_tier='same installed source face'if face=='SimSun'else'clear same-run Latin prose counterpart',
            latin_prose_witness=[dict(character=c['c'],font=c['font'],size=c['size'],origin=c['origin'])for c in slot['source_characters']if c['c'].isdigit()and'TimesNewRoman'in c['font']],
            **info))
    return dict(policy='Actual original glyphs, then the same installed/official face, then a clear same-run Latin prose counterpart; no generic Arial/Times replacement.',
        original_problem_identifiers='Original一、through七、glyphs and their original fonts remain native.',
        installed_collection=dict(path=str(WINDOWS/'simsun.ttc'),sha256=sha(WINDOWS/'simsun.ttc'),face_index=0),
        original_subset_caution='The original SimSun cmap nominally lists ASCII, but most unused Latin outlines/advances do not match the actual5.24 face. Positive widths/cmap entries are insufficient; the full installed same face is used.',
        actual_source_face_comparisons=actual_source_face_comparisons(),
        no_system_fonts_modified=True,entries=entries)
