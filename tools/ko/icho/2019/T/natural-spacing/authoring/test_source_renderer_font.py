"""Read-only regression for original unembedded source fonts, never an alias."""
from pathlib import Path
import hashlib,json,sys
import pikepdf,pymupdf as fitz
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'engine'))
from source_renderer_font import SourceRendererFontReader,fingerprint
from native_ink_bounds import measure_native_ink_bounds
import icho2019_write_guard as guard

def rejected(call,label):
    try:call()
    except ValueError as e:return dict(case=label,rejected=True,error=str(e))
    raise AssertionError('Negative test accepted: '+label)

guard.assert_protected_2024()
raw=guard.SOURCE.read_bytes();reader=SourceRendererFontReader(raw)
doc=fitz.open(stream=raw,filetype='pdf')
before=doc[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(70,775,540,805),colorspace=fitz.csGRAY,alpha=False).samples
positive=[];negative=[]
for key,xrefs in reader.candidates.items():
    font=reader.pdf.get_object((xrefs[0],0));packet,kind=reader.resolve(font)
    assert packet and fingerprint(font)==key
    positive.append(dict(source_font_dictionary_sha256=key,xrefs=xrefs,base_font=str(font.get('/BaseFont')),program_kind=kind,program_sha256=hashlib.sha256(packet).hexdigest(),bytes=len(packet)))
    changed=pikepdf.Dictionary(font);changed['/BaseFont']=pikepdf.Name('/DefinitelyNotTheOriginalFont')
    negative.append(rejected(lambda:reader.resolve(changed),'changed original font dictionary'))
    changed=pikepdf.Dictionary(font);changed['/Encoding']=pikepdf.Name('/MacRomanEncoding')
    negative.append(rejected(lambda:reader.resolve(changed),'unreviewed original Encoding'))
glyphs=[]
for trace in doc[0].get_texttrace():
    if trace['font']!='Arial':continue
    for cp,gid,origin,bbox in trace['chars']:
        if not chr(cp).isspace():glyphs.append(dict(c=chr(cp),font=trace['font'],size=trace['size'],gid=gid,origin=list(origin),bbox=list(bbox),paint=trace['type']))
assert glyphs
audit=[];bounds=measure_native_ink_bounds(raw,1,glyphs,audit_out=audit)
wrong=dict(glyphs[0],gid=glyphs[0]['gid']+1)
negative.append(rejected(lambda:measure_native_ink_bounds(raw,1,[wrong]),'changed requested original trace GID'))
after=doc[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(70,775,540,805),colorspace=fitz.csGRAY,alpha=False).samples
assert before==after and not reader.doc.is_dirty and not doc.is_dirty
assert hashlib.sha256(raw).hexdigest()==guard.SOURCE_SHA==hashlib.sha256(guard.SOURCE.read_bytes()).hexdigest()
result=dict(passed=True,source_sha256=guard.SOURCE_SHA,source_unmodified=True,source_font_dictionaries=len(positive),exact_original_renderer_programs=positive,negative_cases=negative,verified_outline_glyphs=len(bounds),source_footer_pixels_before_after_changed=0,source_renderer_resolution_audit=audit,measurement_only=True,font_alias_selection=False,output_font_program_insertions=0,test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(BASE/'source-renderer-font-regression.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(dict(passed=True,source_font_dictionaries=len(positive),negative_cases=len(negative),verified_outline_glyphs=len(bounds),source_footer_pixels_before_after_changed=0)),flush=True)
