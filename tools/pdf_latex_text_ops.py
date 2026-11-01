"""Exact native PDF prose-CID suppression, preserving all text advances.

Supported profiles: horizontal Identity-H, WinAnsi, explicitly mapped
embedded symbolic simple TrueType, and embedded simple Type1 with explicit
single-byte ToUnicode/Widths; Tj/TJ, including Tc/Tw. This isolated fork also
allows removal of a whole verified Unicode ligature cluster, never a part.
This deliberately fails closed for unsupported source encodings/state.
Input glyph dictionaries carry c, font, size and origin from source extraction.
Return (single_page_pdf_bytes, hidden_logical_character_count). Selected source
codes remain in invisible Tr=3 runs with empty ActualText; their original PDF
advance is retained in every renderer, without guessing Type1 width rounding.
"""
from collections import Counter, defaultdict
from io import BytesIO
import re
import pikepdf
import pymupdf as fitz


def glyph_key(c):
    return (c['c'],c['font'],round(c['size'],6),round(c['origin'][0],5),round(c['origin'][1],5))


def source_code_bytes(font):
    """Return a verified source code width; never guess a font encoding."""
    encoding=str(font.get('/Encoding'))
    if encoding=='/WinAnsiEncoding':return 1
    if encoding=='/Identity-H':return 2
    if str(font.get('/Subtype'))=='/Type1':
        descriptor=font.get('/FontDescriptor')or{}
        required=['/FirstChar','/LastChar','/Widths','/ToUnicode']
        if not all(k in font for k in required):
            raise ValueError('Simple Type1 requires explicit Widths and ToUnicode')
        if '/FontFile'not in descriptor:
            raise ValueError('Simple Type1 requires its embedded Type1 font program')
        first,last=int(font.FirstChar),int(font.LastChar)
        if first!=font.FirstChar or last!=font.LastChar or not 0<=first<=last<=255 or len(font.Widths)!=last-first+1:
            raise ValueError('Simple Type1 has an invalid explicit Widths range')
        # A PDF simple font always consumes one byte. Its ToUnicode map is
        # the source's authoritative Unicode declaration, even when a TeX
        # font uses an implicit built-in Encoding or explicit Differences.
        # Every used code is separately matched to the original MuPDF trace.
        text=font.ToUnicode.read_bytes().decode('latin1')
        spaces=[pair for body in re.findall(r'begincodespacerange(.*?)endcodespacerange',text,re.S)for pair in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>',body)]
        if not spaces or any(len(a)!=2 or len(b)!=2 or int(a,16)>int(b,16)for a,b in spaces):
            raise ValueError('Simple Type1 requires an explicit single-byte ToUnicode code space')
        mapping=cmap(font)
        if not mapping or any(not 0<=code<=255 for code in mapping):
            raise ValueError('Simple Type1 has a non-single-byte ToUnicode map')
        if any(not any(int(a,16)<=code<=int(b,16)for a,b in spaces)for code in mapping):
            raise ValueError('Simple Type1 mapping lies outside its declared code space')
        return 1
    if font.get('/Encoding')is None and str(font.get('/Subtype'))=='/TrueType':
        descriptor=font.get('/FontDescriptor')or{}
        # ISO32000-1 9.6.6.4 permits symbolic embedded simple TrueType fonts
        # without /Encoding. Use their own single-byte ToUnicode and Widths,
        # then require exact CID/trace agreement; do not assume WinAnsi/Mac.
        # https://opensource.adobe.com/dc-acrobat-sdk-docs/standards/pdfstandards/pdf/PDF32000_2008.pdf
        required=['/FirstChar','/LastChar','/Widths','/ToUnicode']
        if not all(k in font for k in required)or '/FontFile2'not in descriptor or not int(descriptor.get('/Flags',0))&4:
            raise ValueError('Implicit simple TrueType requires embedded symbolic TTF, explicit Widths and ToUnicode')
        first,last=int(font.FirstChar),int(font.LastChar)
        if first!=font.FirstChar or last!=font.LastChar or not 0<=first<=last<=255 or len(font.Widths)!=last-first+1:
            raise ValueError('Implicit simple TrueType has an invalid explicit Widths range')
        text=font.ToUnicode.read_bytes().decode('latin1')
        spaces=[pair for body in re.findall(r'begincodespacerange(.*?)endcodespacerange',text,re.S)for pair in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>',body)]
        if not spaces or any(len(a)!=2 or len(b)!=2 or int(a,16)>int(b,16)for a,b in spaces):
            raise ValueError('Implicit simple TrueType requires an explicit single-byte ToUnicode code space')
        mapping=cmap(font)
        if not mapping or any(not 0<=code<=255 for code in mapping):
            raise ValueError('Implicit simple TrueType has a non-single-byte ToUnicode map')
        return 1
    raise ValueError('Unsupported source encoding: '+encoding)


def cmap(font):
    mapping={}
    if str(font.get('/Encoding'))=='/WinAnsiEncoding':
        for code in range(256):
            try:mapping[code]=bytes([code]).decode('cp1252')
            except UnicodeDecodeError:pass
    if '/ToUnicode'not in font:
        if mapping:return mapping
        raise ValueError('Identity-H requires an explicit ToUnicode map')
    text=font['/ToUnicode'].read_bytes().decode('latin1')
    for body in re.findall(r'beginbfchar(.*?)endbfchar',text,re.S):
        for a,b in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>',body):
            mapping[int(a,16)]=bytes.fromhex(b).decode('utf-16-be')
    for body in re.findall(r'beginbfrange(.*?)endbfrange',text,re.S):
        arrays=r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[([^\]]*)\]'
        for a,b,values in re.findall(arrays,body,re.S):
            values=re.findall(r'<([0-9A-Fa-f]+)>',values)
            if len(values)!=int(b,16)-int(a,16)+1:raise ValueError('Incomplete ToUnicode range array')
            for index,value in enumerate(values):mapping[int(a,16)+index]=bytes.fromhex(value).decode('utf-16-be')
        body=re.sub(arrays,'',body,flags=re.S)
        for a,b,z in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>',body):
            for code in range(int(a,16),int(b,16)+1):
                # A ToUnicode destination is UTF-16BE, including surrogate
                # pairs for mathematical alphanumeric symbols above BMP.
                target=int(z,16)+code-int(a,16)
                mapping[code]=target.to_bytes(len(z)//2,'big').decode('utf-16-be')
    return mapping


def widths(font):
    if source_code_bytes(font)==1:
        if '/Widths'not in font:raise ValueError('WinAnsi requires explicit glyph Widths')
        start=int(font.get('/FirstChar',0))
        return {start+i:float(w)for i,w in enumerate(font['/Widths'])},None
    descendant=font['/DescendantFonts'][0];values=list(descendant.get('/W',[]));result={};i=0
    while i<len(values):
        start=int(values[i]);part=values[i+1];i+=2
        if isinstance(part,pikepdf.Array):
            for j,w in enumerate(part):result[start+j]=float(w)
        else:
            end=int(part);w=float(values[i]);i+=1
            for code in range(start,end+1):result[code]=w
    return result,float(descendant.get('/DW',1000))


def family_name(value):
    return re.sub(r'^[A-Z]{6}\+','',str(value).lstrip('/'))


def replace_show_regions(page,replacements):
    """Keep every untouched content token byte-for-byte, including cm/Tm.

    Re-serializing high-precision source transformation numbers changes
    antialiasing inside nested native equation Forms. Token boundaries allow
    replacing only the reviewed text-show operands/operator instead.
    """
    class Tokens(pikepdf.TokenFilter):
        def __init__(self):super().__init__();self.items=[]
        def handle_token(self,token):self.items.append((token.type_,token.raw_value));return token
    collector=Tokens();raw=page.get_filtered_contents(collector);regions=[];offset=start=0
    for typ,value in collector.items:
        offset+=len(value)
        if typ==pikepdf.TokenType.inline_image:raise ValueError('Inline image token surgery needs a separate profile')
        if typ==pikepdf.TokenType.word:
            regions.append((start,offset,value.decode('ascii')));start=offset
    parsed=pikepdf.parse_content_stream(page)
    if len(regions)!=len(parsed)or any(op!=str(instruction.operator)for (_,_,op),instruction in zip(regions,parsed)):
        raise ValueError('Raw token/operator region mapping is not exact')
    pieces=[];position=0
    for index,instruction in sorted(replacements.items()):
        a,z,operator=regions[index]
        if operator not in ['Tj','TJ']:raise ValueError('Only prose Tj/TJ regions may be changed')
        prefix=re.match(rb'\s*',raw[a:z])[0]
        instructions=instruction if isinstance(instruction,list)else[instruction]
        pieces.extend([raw[position:a],prefix,pikepdf.unparse_content_stream(instructions).rstrip(b'\r\n')]);position=z
    pieces.append(raw[position:]);return b''.join(pieces)


def suppress_prose(source,page_number,selected_glyphs,protected_form_glyphs=None):
    """Hide chosen codes while preserving exact source text-show advances.

    Decoded glyphs must match the source trace exactly, including mixed
    WinAnsi/CID resources sharing one font family. Every removed glyph is
    painted with Tr=3 and empty ActualText. Original encoded source bytes,
    original character/word spacing and kerning advances remain renderer-native.
    """
    native=fitz.open(source);page=native[page_number-1]
    # MuPDF rawdict truncates some PostScript names (e.g. BoldItal), whereas
    # texttrace and BaseFont retain the complete name. Accept only a unique
    # source-trace prefix alias; never conflate different source font faces.
    trace_names={family_name(t['font'])for t in page.get_texttrace()}
    canonical=[]
    for item in selected_glyphs:
        ch=dict(item);name=family_name(ch['font'])
        if name not in trace_names:
            matches=[full for full in trace_names if full.startswith(name)]
            if len(matches)!=1:raise ValueError('Ambiguous source font alias: '+name)
            name=matches[0]
        ch['font']=name;canonical.append(ch)
    selected_glyphs=canonical
    # ffi can contain two logical f records at the same origin. A set would
    # silently lose one selection. Count logical Unicode records exactly.
    selected=Counter(glyph_key(c)for c in selected_glyphs if not c['c'].isspace())
    queues=defaultdict(list)
    traces=page.get_texttrace();ti=0
    while ti<len(traces):
        trace=traces[ti];mode=trace['type'];ti+=1
        # Tr=2 yields two MuPDF traces (fill, then stroke) for a single
        # source text-show. Pair only exact adjacent outline identities, and
        # later demand that the PDF text-rendering state really is Tr=2.
        if mode==0 and ti<len(traces):
            following=traces[ti]
            if following['type']==1 and following['font']==trace['font']and following['size']==trace['size']and following['chars']==trace['chars']and following['seqno']==trace['seqno']+1:
                mode=2;ti+=1
        for cp,gid,origin,bbox in trace['chars']:
            queues[family_name(trace['font'])].append({'c':chr(cp),'font':trace['font'],'size':trace['size'],'origin':origin,'bbox':bbox,'render_mode':mode,'trace_gid':gid})
    counters=Counter();removed=[];consumed=Counter()
    with pikepdf.Pdf.open(source) as pdf:
        out=pikepdf.Pdf.new();out.pages.append(pdf.pages[page_number-1]);p=out.pages[0]
        selected_families={family_name(c['font'])for c in selected_glyphs}
        def resource_fonts(resources):
            info={}
            for name,font in resources.get('/Font',{}).items():
                family=family_name(bytes(font.get('/BaseFont')).decode('latin1'))
                if family not in trace_names:
                    aliases=[value for value in trace_names if family.startswith(value)]
                    if not aliases:
                        folded=lambda value:re.sub('[^a-z0-9]','',value.lower())
                        aliases=[value for value in trace_names if folded(family)==folded(value)]
                    if len(aliases)==1:family=aliases[0]
                if family not in selected_families and protected_form_glyphs is None:continue
                enc=str(font.get('/Encoding'));code_bytes=source_code_bytes(font)
                descendant=font.get('/DescendantFonts',[font])[0]
                descriptor=descendant.get('/FontDescriptor',{})
                # Some original Word math subsets omit ToUnicode entries for
                # painted superscript CIDs. Their explicit Identity CID-to-GID
                # map and embedded TTF can still identify a read-only glyph
                # against MuPDF's gid/FFFD trace, without inventing Unicode.
                identity_native=(enc=='/Identity-H'and str(descendant.get('/CIDToGIDMap'))=='/Identity'and '/FontFile2'in descriptor)
                ws,default=widths(font);info[str(name)]=(family,cmap(font),ws,default,code_bytes,identity_native)
            return info
        replacements={}
        def walk(container,resources,state=('',0,0,1,0),writable=True,ancestors=()):
            active,tc,tw,tf,tr=state;graphics=[];instructions=[];fontinfo=resource_fonts(resources)
            if len(ancestors)>20:raise ValueError('Excessive Form nesting')
            for operator_index,instruction in enumerate(pikepdf.parse_content_stream(container)):
                operands=list(instruction.operands);operator=str(instruction.operator);changed_here=False
                if operator=='q':graphics.append((active,tc,tw,tf,tr))
                if operator=='Q':active,tc,tw,tf,tr=graphics.pop()
                if operator=='Tf':active=str(operands[0]);tf=float(operands[1])
                if operator=='Tc':tc=float(operands[0])
                if operator=='Tw':tw=float(operands[0])
                if operator=='Tr':tr=int(operands[0])
                if operator=='"':tw=float(operands[0]);tc=float(operands[1])
                if operator=='Do':
                    child=resources.get('/XObject',{}).get(operands[0])
                    if child is not None and str(child.get('/Subtype'))=='/Form':
                        if child.objgen in ancestors:raise ValueError('Recursive Form XObject')
                        # Form mathematics can share a prose font family. It
                        # participates in the native trace order, but its
                        # streams/resources must remain completely untouched.
                        walk(child,child.get('/Resources',resources),(active,tc,tw,tf,tr),False,ancestors+(child.objgen,))
                if operator in ['TJ','Tj',"'",'"'] and active in fontinfo:
                    family,encoding,ws,default,code_bytes,identity_native=fontinfo[active]
                    items=list(operands[0])if operator=='TJ'else[operands[-1]];segments=[]
                    def append_code(value,hidden):
                        if not segments or segments[-1][0]!=hidden:segments.append((hidden,[]))
                        dest=segments[-1][1]
                        if dest and isinstance(dest[-1],pikepdf.String):dest[-1]=pikepdf.String(bytes(dest[-1])+value)
                        else:dest.append(pikepdf.String(value))
                    for item in items:
                        if not isinstance(item,pikepdf.String):
                            if not segments:segments.append((False,[]))
                            segments[-1][1].append(item);continue
                        raw=bytes(item)
                        if len(raw)%code_bytes:raise ValueError('Incomplete encoded glyph')
                        for pos in range(0,len(raw),code_bytes):
                            code=int.from_bytes(raw[pos:pos+code_bytes],'big');decoded=encoding.get(code)
                            if not decoded:
                                qi=counters[family];unknown=queues[family][qi:qi+1]
                                if not(identity_native and len(unknown)==1 and unknown[0]['trace_gid']==code and unknown[0]['c']=='\ufffd'):
                                    raise ValueError(f'Missing Unicode destination {family} {code}')
                                ch=unknown[0]
                                # rawdict can spell the same unknown glyph as
                                # chr(CID), so erasure rejection uses geometry,
                                # independently of its unreliable Unicode.
                                if any(family_name(c['font'])==family and abs(c['size']-ch['size'])<.0001 and abs(c['origin'][0]-ch['origin'][0])<.0001 and abs(c['origin'][1]-ch['origin'][1])<.0001 for c in selected_glyphs):
                                    raise ValueError('Selected prose has an unmapped native Identity CID')
                                decoded='\ufffd'
                            qi=counters[family];cluster=queues[family][qi:qi+len(decoded)]
                            if len(cluster)!=len(decoded):raise ValueError('More encoded CIDs than traced glyphs')
                            counters[family]+=len(decoded);ch=cluster[0]
                            if any(tr!=part['render_mode']for part in cluster):raise ValueError(f'PDF/trace rendering-mode mismatch {family}: Tr={tr}, trace={ch["render_mode"]}')
                            traced=''.join(part['c']for part in cluster)
                            if decoded!=traced:raise ValueError(f'CID/trace mismatch {family} {code} {decoded!r} {traced!r}')
                            cluster_keys=Counter(glyph_key(part)for part in cluster)
                            requested=any(selected[key]>consumed[key]for key in cluster_keys)
                            complete=all(selected[key]-consumed[key]>=count for key,count in cluster_keys.items())
                            if requested and not complete:
                                raise ValueError('Selected prose contains only part of a Unicode glyph cluster')
                            if len(cluster)>1:
                                # One CID can map to a Unicode string. MuPDF
                                # emits the real painted glyph followed by
                                # zero-width gid=-1 extraction continuations.
                                # Only this exact, read-only profile is safe.
                                if ch['trace_gid']<0 or any(part['trace_gid']!=-1 or part['origin']!=ch['origin']or part['size']!=ch['size']or abs(part['bbox'][2]-part['bbox'][0])>1e-6 for part in cluster[1:]):
                                    raise ValueError('Unsupported multi-Unicode CID trace cluster')
                            if not writable and protected_form_glyphs is not None:
                                protected_form_glyphs.extend({k:v for k,v in part.items()if k not in ['render_mode','trace_gid']}for part in cluster)
                            if not writable and any(c['c']==part['c']and c['font']==part['font']and abs(c['origin'][0]-part['origin'][0])<.0001 and abs(c['origin'][1]-part['origin'][1])<.0001 for c in selected_glyphs for part in cluster):
                                raise ValueError('Selected prose inside a preserved native Form XObject: '+repr(ch))
                            if requested:
                                if not writable:raise ValueError('Selected prose inside a preserved native Form XObject')
                                # Quote shows combine line movement (and, for
                                # double quote, spacing changes) with text.
                                # Match their native trace and retain the
                                # original operator bytes; never rewrite them.
                                if operator in ["'",'"']:raise ValueError('Selected prose inside a read-only quote text-show operator')
                                changed_here=True
                                width=ws.get(code,default)
                                if width is None:raise ValueError('Selected glyph has no explicit width')
                                if tf==0:raise ValueError('Zero text font size cannot preserve advances')
                                append_code(raw[pos:pos+code_bytes],True)
                                removed.extend(glyph_key(part)for part in cluster)
                                consumed.update(cluster_keys)
                            else:append_code(raw[pos:pos+code_bytes],False)
                    if changed_here:
                        def inst(values,name):return pikepdf.ContentStreamInstruction(values,pikepdf.Operator(name))
                        changed_instructions=[]
                        for hidden,values in segments:
                            if hidden:
                                changed_instructions.extend([
                                    inst([pikepdf.Name('/Span'),pikepdf.Dictionary(ActualText=pikepdf.String(''))],'BDC'),
                                    inst([3],'Tr'),inst([pikepdf.Array(values)],'TJ'),inst([tr],'Tr'),inst([],'EMC')])
                            else:changed_instructions.append(inst([pikepdf.Array(values)],'TJ'))
                result=pikepdf.ContentStreamInstruction(operands,pikepdf.Operator(operator));instructions.append(result)
                if changed_here:replacements[operator_index]=changed_instructions
            if graphics:raise ValueError('Unbalanced source graphics stack')
            return instructions
        instructions=walk(p,p.Resources)
        if Counter(removed)!=selected:
            raise ValueError('Selected prose not removed exactly: '+str(selected-Counter(removed)))
        for family,count in counters.items():
            if count!=len(queues[family]):raise ValueError('Unconsumed source glyph trace: '+family)
        p.Contents=out.make_stream(replace_show_regions(p,replacements))
        # QPDF's default stream compression rewrites tiny originally raw
        # image/alpha streams even when every drawing operator is untouched.
        # Preserve existing raw and Flate payloads in their original state.
        stream=BytesIO();out.save(stream,compress_streams=False);native.close();return stream.getvalue(),len(removed)


def native_form_glyphs(source,page_number):
    """Return read-only native Form text geometry, independent of prose slots.

    Decode every source text show against its MuPDF trace, including nested
    Form calls. No Form stream/resource is ever edited. Unknown encodings or
    mismatches fail closed rather than guessing which text is mathematical.
    """
    glyphs=[];suppress_prose(source,page_number,[],protected_form_glyphs=glyphs)
    return glyphs
