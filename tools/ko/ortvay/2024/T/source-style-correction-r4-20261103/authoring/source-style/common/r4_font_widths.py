"""Correct only new Batang CID /W serialization; never alter font programs."""
from pathlib import Path
from io import BytesIO
from decimal import Decimal
import hashlib,json,re,struct
import pymupdf as fitz
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def digest(data):return hashlib.sha256(data).hexdigest()
def ref(value):
    match=re.fullmatch(r'(\d+)\s+0\s+R',value.strip())
    if not match:raise ValueError('Expected one explicit indirect font reference')
    return int(match.group(1))
def decimals(items,default=1000):
    items=list(items);mapping={};i=0
    while i<len(items):
        first=int(items[i]);value=items[i+1];i+=2
        if isinstance(value,pikepdf.Array):
            for j,w in enumerate(value):mapping[first+j]=Decimal(str(w))
        else:
            end=int(value);width=Decimal(str(items[i]));i+=1
            for cid in range(first,end+1):mapping[cid]=width
    return mapping,Decimal(str(default))
def decimal_text(value):
    value=Decimal(value)
    if not value.is_finite():raise ValueError('Nonfinite font advance')
    return format(value,'f')
def compact_W(mapping):
    keys=sorted(mapping);pieces=[];i=0
    while i<len(keys):
        first=keys[i];last=first;width=mapping[first];i+=1
        while i<len(keys) and keys[i]==last+1 and mapping[keys[i]]==width:
            last=keys[i];i+=1
        pieces.append(f'{first} {last} {decimal_text(width)}' if last>first else f'{first} [{decimal_text(width)}]')
    return '['+' '.join(pieces)+']'

def to_unicode(data):
    """Parse actual generated bfchar/bfrange mappings, including range arrays."""
    result={}
    for section in re.findall(rb'beginbfchar(.*?)endbfchar',data,re.S):
        for a,b in re.findall(rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>',section):
            result[int(a,16)]=bytes.fromhex(b.decode()).decode('utf-16-be')
    for section in re.findall(rb'beginbfrange(.*?)endbfrange',data,re.S):
        tokens=re.findall(rb'<[0-9a-fA-F]+>|\[|\]',section);i=0
        while i<len(tokens):
            start=int(tokens[i][1:-1],16);end=int(tokens[i+1][1:-1],16);value=tokens[i+2];i+=3
            if value==b'[':
                for cid in range(start,end+1):
                    token=tokens[i];i+=1
                    result[cid]=bytes.fromhex(token[1:-1].decode()).decode('utf-16-be')
                if tokens[i]!=b']':raise ValueError('Malformed ToUnicode range array')
                i+=1
            else:
                raw=bytes.fromhex(value[1:-1].decode());base=int.from_bytes(raw,'big')
                for cid in range(start,end+1):result[cid]=(base+cid-start).to_bytes(len(raw),'big').decode('utf-16-be')
    if not result:raise ValueError('Empty generated ToUnicode mapping')
    return result

def capture_original_font_lineage(page):
    doc=page.parent;roots=sorted({v[0] for v in page.get_fonts(full=True)});todo=list(roots);objects={}
    while todo:
        xref=todo.pop()
        if xref in objects:continue
        raw=doc.xref_object(xref,compressed=False).encode('utf8')
        objects[xref]=dict(object_sha256=digest(raw),raw_stream_sha256=digest(doc.xref_stream_raw(xref)) if doc.xref_is_stream(xref) else None)
        todo += [int(v) for v in re.findall(rb'(?<!\d)(\d+)\s+0\s+R',raw) if int(v) not in objects]
        if len(objects)>10000:raise ValueError('Unexpected original font graph size')
    return dict(original_font_root_xrefs=roots,original_font_graph=objects,xref_limit_before_KO_insertion=doc.xref_length(),
                original_aliases=sorted({v[4] for v in page.get_fonts(full=True)}))

def assert_original_font_lineage(page,snapshot):
    doc=page.parent
    for key,row in snapshot['original_font_graph'].items():
        xref=int(key)
        assert digest(doc.xref_object(xref,compressed=False).encode('utf8'))==row['object_sha256'],'Original font object changed'
        if row['raw_stream_sha256'] is not None:assert digest(doc.xref_stream_raw(xref))==row['raw_stream_sha256'],'Original font stream changed'

def used_for_role(layout,role):
    return sorted({ch for p in layout['placements'] if p['font_role']==role for ch in p.get('draw_text',p['text'])}|{' '})

def desired_widths(layout,role,program,to_unicode_map,cid_to_gid,approved):
    path=Path(layout['new_font_paths'][role])
    assert path.resolve()==Path(approved['path']).resolve() and sha(path)==approved['sha256']
    assert layout['new_font_file_sha256'][role]==approved['sha256']
    master=TTFont(path,fontNumber=approved['face_index'],recalcTimestamp=False)
    subset=TTFont(BytesIO(program),recalcTimestamp=False)
    units=master['head'].unitsPerEm
    assert units==approved['units_per_em']==subset['head'].unitsPerEm
    assert master['post'].italicAngle==subset['post'].italicAngle==0
    mc,sc=master.getBestCmap(),subset.getBestCmap();morder=master.getGlyphOrder();sorder=subset.getGlyphOrder()
    mg,sg=master.getGlyphSet(),subset.getGlyphSet();widths={};used=[]
    for ch in used_for_role(layout,role):
        cp=ord(ch)
        if cp not in mc or cp not in sc:raise ValueError('Missing master/subset glyph for actual paint')
        gid=master.getGlyphID(mc[cp]);assert gid==subset.getGlyphID(sc[cp]) and gid>0
        candidates=[cid for cid,text in to_unicode_map.items() if text==ch and cid_to_gid(cid)==gid]
        if len(candidates)!=1:raise ValueError(f'Ambiguous actual CID-to-GID/Unicode mapping: {cp}/{gid}/{candidates}')
        cid=candidates[0];advance,lsb=master['hmtx'].metrics[morder[gid]]
        assert subset['hmtx'].metrics[sorder[gid]]==(advance,lsb)
        a,b=DecomposingRecordingPen(mg),DecomposingRecordingPen(sg)
        mg[morder[gid]].draw(a);sg[sorder[gid]].draw(b)
        assert a.value==b.value,'Used subset outline differs from the full master'
        value=Decimal(advance)*Decimal(1000)/Decimal(units)
        assert Decimal(str(struct.unpack('f',struct.pack('f',float(value)))[0]))==value,'Master width is not exactly representable in the in-memory PDF real'
        widths[cid]=value
        used.append(dict(character=ch,unicode=cp,cid=cid,gid=gid,master_hmtx_advance=advance,master_lsb=lsb,
                         master_units_per_em=units,exact_W=decimal_text(value),outline_and_hmtx_match_full_master=True))
    master.close();subset.close()
    return widths,used

def apply_in_memory(page,layout,approved,snapshot,doc_role):
    """Run after new font registration, before any new prose is painted."""
    doc=page.parent;reports=[]
    for item in page.get_fonts(full=True):
        fontxref,_,_,base,alias=item[:5]
        if not alias.startswith('KO_Natural_') or not base.split('+')[-1].startswith('Batang'):continue
        if alias.startswith('KO_Natural_Raster'):raise ValueError('This correction does not authorize Batang raster-label resources')
        role=alias[len('KO_Natural_'):].replace('_','-')
        if role not in layout['new_font_paths']:raise ValueError('Unknown new Batang role')
        assert alias not in snapshot['original_aliases'] and fontxref>=snapshot['xref_limit_before_KO_insertion']
        assert doc.xref_get_key(fontxref,'Encoding')==('name','/Identity-H')
        kind,array=doc.xref_get_key(fontxref,'DescendantFonts');assert kind=='array'
        ids=re.findall(r'(\d+)\s+0\s+R',array);assert len(ids)==1;desc=int(ids[0])
        assert desc>=snapshot['xref_limit_before_KO_insertion'] and doc.xref_get_key(desc,'Subtype')==('name','/CIDFontType2')
        unicode_xref=ref(doc.xref_get_key(fontxref,'ToUnicode')[1]);umap=to_unicode(doc.xref_stream(unicode_xref))
        mapkind,mapvalue=doc.xref_get_key(desc,'CIDToGIDMap')
        if (mapkind,mapvalue)==('name','/Identity'):
            cid_to_gid=lambda cid:cid;mapping=dict(kind='Identity',dictionary_value=mapvalue)
        elif (mapkind,mapvalue)==('null','null'):
            assert doc.xref_get_key(desc,'Subtype')==('name','/CIDFontType2')
            cid_to_gid=lambda cid:cid;mapping=dict(kind='default-Identity',dictionary_entry_absent=True,
                specification='ISO 32000-1 CIDFont dictionary CIDToGIDMap default Identity',
                specification_url='https://developer.adobe.com/document-services/docs/assets/35e4369068f86065372c18787171a17e/PDF_ISO_32000-1.pdf')
        elif mapkind=='xref':
            xref=ref(mapvalue);data=doc.xref_stream(xref);assert len(data)%2==0
            cid_to_gid=lambda cid:int.from_bytes(data[cid*2:cid*2+2],'big') if cid*2+2<=len(data) else -1
            mapping=dict(kind='explicit-stream',stream_xref=xref,decoded_sha256=digest(data),bytes=len(data))
        else:raise ValueError('Unbound CID-to-GID mapping')
        program=doc.extract_font(fontxref)[3]
        desired,used=desired_widths(layout,role,program,umap,cid_to_gid,approved)
        wk,wraw=doc.xref_get_key(desc,'W');original_W_entry=dict(kind=wk,value=wraw)
        if wk=='xref':wraw=doc.xref_object(ref(wraw),compressed=False);wk='array' if wraw.lstrip().startswith('[') else wk
        assert wk=='array'
        dk,draw=doc.xref_get_key(desc,'DW');default=Decimal(draw) if dk not in ('null','none') else Decimal(1000)
        old,_=decimals(pikepdf.Object.parse(wraw.encode('ascii')),default);new=dict(old)
        for row in used:row['old_W']=decimal_text(old.get(row['cid'],default))
        new.update(desired);serialized=compact_W(new)
        doc.xref_set_key(desc,'W',serialized)
        assert doc.extract_font(fontxref)[3]==program
        assert_original_font_lineage(page,snapshot)
        reports.append(dict(applied=True,doc_role=doc_role,alias=alias,font_xref=fontxref,descendant_xref=desc,
            proven_new_resource=True,original_font_resources_unchanged=True,font_program_binary_sha256=digest(program),
            master=approved,cid_to_gid=mapping,original_W_dictionary_entry=original_W_entry,old_W_serialization=wraw,old_DW=decimal_text(default),
            exact_W_input_serialization=serialized,used_glyphs=used,old_defined_widths=len(old),
            only_used_CID_advances_changed=True,unlisted_W_entries_semantically_unchanged=True,
            in_memory_width_values_exactly_float32_representable=True,
            final_exact_decimal_serialization_checked_separately=True))
    if not reports:raise ValueError('No newly inserted approved Batang resource was corrected')
    return reports

def _canonical(obj,ignore_W=False,seen=None):
    seen=set() if seen is None else set(seen)
    if isinstance(obj,(pikepdf.Dictionary,pikepdf.Array,pikepdf.Stream)) and obj.is_indirect:
        if obj.objgen in seen:return {'cycle':True}
        seen.add(obj.objgen)
    if isinstance(obj,pikepdf.Stream):
        return dict(dictionary={str(k):_canonical(v,False,seen) for k,v in sorted(obj.items(),key=lambda kv:str(kv[0])) if str(k)!='/Length'},
                    decoded_sha256=digest(obj.read_bytes()),encoded_sha256=digest(obj.read_raw_bytes()))
    if isinstance(obj,pikepdf.Dictionary):
        return {str(k):_canonical(v,ignore_W,seen) for k,v in sorted(obj.items(),key=lambda kv:str(kv[0])) if not(ignore_W and str(k)=='/W')}
    if isinstance(obj,pikepdf.Array):return [_canonical(v,ignore_W,seen) for v in obj]
    if isinstance(obj,Decimal):return decimal_text(obj)
    if isinstance(obj,(bool,int,float)) or obj is None:return obj
    return str(obj)

def finalize_exact_serialization(target,layout,approved,reports):
    """Persist exact Decimal /W after MuPDF save; preserve every other object."""
    target=Path(target);before=target.read_bytes();patched=target.with_name(target.stem+'.before-exact-W-finalization.pdf')
    assert not patched.exists();patched.write_bytes(before)
    allowed={r['alias']:r for r in reports if r['doc_role']=='target'};assert allowed
    with pikepdf.Pdf.open(BytesIO(before)) as pdf:
        fonts=pdf.pages[0].Resources.Font
        graph_before={str(name):_canonical(font,str(name).lstrip('/') in allowed) for name,font in fonts.items()}
        for name,font in fonts.items():
            alias=str(name).lstrip('/')
            if alias not in allowed:continue
            row=allowed[alias];desc=font.DescendantFonts[0]
            mapping=row['cid_to_gid']
            if mapping['kind']=='Identity':assert str(desc.CIDToGIDMap)==mapping['dictionary_value']
            elif mapping['kind']=='default-Identity':assert '/CIDToGIDMap' not in desc and str(desc.Subtype)=='/CIDFontType2'
            else:assert digest(desc.CIDToGIDMap.read_bytes())==mapping['decoded_sha256']
            current,default=decimals(desc.W,desc.get('/DW',1000))
            for used in row['used_glyphs']:current[used['cid']]=Decimal(used['exact_W'])
            desc.W=pikepdf.Object.parse(compact_W(current).encode('ascii'))
        assert {str(name):_canonical(font,str(name).lstrip('/') in allowed) for name,font in fonts.items()}==graph_before
        output=BytesIO();pdf.save(output,compress_streams=False,object_stream_mode=pikepdf.ObjectStreamMode.disable)
    after=output.getvalue()
    with pikepdf.Pdf.open(BytesIO(after)) as check:
        fonts=check.pages[0].Resources.Font
        assert {str(name):_canonical(font,str(name).lstrip('/') in allowed) for name,font in fonts.items()}==graph_before
        for alias,row in allowed.items():
            values,default=decimals(fonts['/'+alias].DescendantFonts[0].W,fonts['/'+alias].DescendantFonts[0].get('/DW',1000))
            for used in row['used_glyphs']:assert values.get(used['cid'],default)==Decimal(used['exact_W'])
    target.write_bytes(after)
    return dict(passed=True,pre_finalization_pdf_path=str(patched),pre_finalization_sha256=digest(before),
                final_pdf_sha256=digest(after),all_font_program_binaries_and_non_W_font_graphs_identical=True,
                all_used_W_values_equal_exact_master_hmtx_decimal=True,
                source_and_unrelated_new_font_resources_unchanged=True,
                only_new_approved_Batang_W_corrected=True)
