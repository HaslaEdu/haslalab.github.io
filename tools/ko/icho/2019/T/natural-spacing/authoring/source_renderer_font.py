"""Read the font buffer loaded by MuPDF from an exact unembedded source font.

There is no font-name fallback table, PDF rewrite, font insertion or system-font
lookup here. The original PDF font dictionary itself is passed to pdf_load_font.
This captures the same source-resolved program that paints the original PDF.
"""
from io import BytesIO
import hashlib,json
import pikepdf
import pymupdf as fitz

def semantic(value,depth=0):
    if depth>16:raise ValueError('Excessive source font dictionary depth')
    if isinstance(value,pikepdf.Stream):return dict(stream_sha256=hashlib.sha256(value.read_bytes()).hexdigest(),dictionary=semantic(pikepdf.Dictionary(value),depth+1))
    if isinstance(value,pikepdf.Dictionary):return{str(k):semantic(v,depth+1)for k,v in value.items()}
    if isinstance(value,pikepdf.Array):return[semantic(v,depth+1)for v in value]
    if isinstance(value,pikepdf.String):return dict(string_bytes=bytes(value).hex())
    if isinstance(value,pikepdf.Name):return dict(pdf_name=str(value))
    if value is None or isinstance(value,(bool,int,float)):return value
    return str(value)

def fingerprint(font):return hashlib.sha256(json.dumps(semantic(font),sort_keys=True,separators=(',',':')).encode()).hexdigest()

class SourceRendererFontReader:
    def __init__(self,source):
        self.source=bytes(source);self.pdf=pikepdf.Pdf.open(BytesIO(self.source));self.doc=fitz.open(stream=self.source,filetype='pdf');self.native=fitz._as_pdf_document(self.doc);self.candidates={};self.cache={};self.audit=[]
        for obj in self.pdf.objects:
            if not isinstance(obj,pikepdf.Dictionary)or str(obj.get('/Type'))!='/Font'or str(obj.get('/Subtype'))!='/TrueType':continue
            desc=obj.get('/FontDescriptor',{})
            if any(k in desc for k in['/FontFile','/FontFile2','/FontFile3']):continue
            self.candidates.setdefault(fingerprint(obj),[]).append(obj.objgen[0])
    def resolve(self,font):
        key=fingerprint(font)
        if key in self.cache:return self.cache[key]
        if str(font.get('/Subtype'))!='/TrueType'or str(font.get('/Encoding'))!='/WinAnsiEncoding':raise ValueError('Unembedded source renderer profile requires explicit simple TrueType WinAnsi')
        xrefs=self.candidates.get(key,[])
        if not xrefs:raise ValueError('Unembedded font dictionary is not exactly present in the original source')
        rows=[]
        for xref in xrefs:
            obj=self.native.pdf_load_object(xref)
            desc=fitz.mupdf.ll_pdf_load_font(self.native.m_internal,None,obj.m_internal)
            try:
                if desc.is_embedded:raise ValueError('Source renderer adapter must not intercept embedded fonts')
                flags=desc.font.flags
                if any(getattr(flags,k)for k in['fake_bold','fake_italic','ft_stretch','ft_substitute']):raise ValueError('Source renderer synthetic/stretched font needs a separate exact profile')
                buf=fitz.mupdf.FzBuffer(fitz.mupdf.ll_fz_keep_buffer(desc.font.buffer));raw=fitz.mupdf.fz_buffer_extract_copy(buf)
                if not raw:raise ValueError('Original source renderer exposes no font buffer')
                kind='CFFType1'if raw[:1]==b'\x01'else'TrueType'
                rows.append((raw,kind,str(desc.font.name)))
            finally:fitz.mupdf.ll_pdf_drop_font(desc)
        if len({(hashlib.sha256(raw).hexdigest(),kind)for raw,kind,name in rows})!=1:raise ValueError('Identical source font dictionaries resolve to different original programs')
        raw,kind,name=rows[0]
        if self.doc.is_dirty:raise ValueError('Reading source renderer font unexpectedly dirtied the source PDF')
        self.audit.append(dict(source_font_dictionary_sha256=key,source_xrefs=xrefs,source_base_font=str(font.get('/BaseFont')),source_font_program_embedded=False,source_renderer_font_name=name,source_renderer_program_sha256=hashlib.sha256(raw).hexdigest(),source_renderer_program_bytes=len(raw),program_kind=kind,source_pdf_unmodified=True,manual_font_name_fallback=False,font_substitution_in_output=False,synthetic_bold_italic_or_stretch=False))
        self.cache[key]=(raw,kind);return raw,kind

def unembedded_programs_on_page(raw,page_number):
    reader=SourceRendererFontReader(raw);rows={}
    try:
        for item in reader.doc[page_number-1].get_fonts(full=True):
            xref=item[0]
            if not xref:continue
            font=reader.pdf.get_object((xref,0))
            if str(font.get('/Subtype'))!='/TrueType':continue
            desc=font.get('/FontDescriptor',{})
            if any(k in desc for k in ['/FontFile','/FontFile2','/FontFile3']):continue
            key=fingerprint(font);packet,kind=reader.resolve(font)
            rows[key]=dict(source_font_dictionary_sha256=key,base_font=str(font.get('/BaseFont')),program_kind=kind,renderer_program_sha256=hashlib.sha256(packet).hexdigest(),renderer_program_bytes=len(packet),font_program_embedded=False)
        return rows
    finally:
        reader.doc.close();reader.pdf.close()

def verify_unembedded_preservation(source,page_number,final):
    before=unembedded_programs_on_page(source,page_number)
    after=unembedded_programs_on_page(final,1)
    if before!=after:raise ValueError('Original unembedded font dictionaries or actual renderer programs changed')
    return dict(passed=True,original_unembedded_font_dictionaries_verified=len(before),source_and_final_original_font_dictionary_and_renderer_programs_identical=True,output_font_program_insertions_for_unembedded_originals=0,manual_font_name_fallback=False,fonts=[before[k]for k in sorted(before)])
