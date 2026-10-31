"""Move native PDF glyphs horizontally without replacing their font or outlines.

``reposition_inline(source, page_number, erased_glyphs=[],
                    shifts=[{'glyphs': [...], 'dx': 12.0}])``
returns ``(single_page_pdf_bytes, qa)``. Origins and dx use MuPDF's displayed
page coordinates (points, positive right). Input glyphs are c/font/size/origin
dictionaries from the *input* PDF, not a different edition. Text remains native:
the original encoded CID bytes are bracketed by cancelling TJ adjustments.
No page rasterization, font rewriting, new mathematical text or white masks.

Forms are moved only as complete invocation groups. A nested invocation gets
a private ancestor copy; every original Form stream/resource remains unchanged.
Complete original q/clip/text/Q groups move atomically, including the original
clip and native vectors. Other top-level groups intersecting vector drawings
fail closed unless their exact pure native path is explicitly reviewed through
``vector_paths`` from ``inspect_inline_groups``. Rotated baselines fail closed
when a page-horizontal move cannot be represented by TJ alone.
"""
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
import hashlib
import math
import re

import pikepdf
import pymupdf as fitz

from pdf_original_text_ops import (
    cmap, family_name, glyph_key, source_code_bytes, widths,
)


IDENTITY = (1., 0., 0., 1., 0., 0.)
PATH_CONSTRUCTION={'m','l','c','v','y','h','re'}
PATH_PAINT={'S','s','f','F','f*','B','B*','b','b*','n'}


def _multiply(a, b):
    """PDF row-vector affine composition: apply a, then b."""
    x,y,z,w,e,f=a; A,B,C,D,E,F=b
    return (x*A+y*C, x*B+y*D, z*A+w*C, z*B+w*D,
            e*A+f*C+E, e*B+f*D+F)


def _inverse_vector(matrix, dx, dy=0.):
    a,b,c,d,_,_=matrix; det=a*d-b*c
    if abs(det)<1e-14:raise ValueError('Singular native transformation')
    return ((d*dx-c*dy)/det, (-b*dx+a*dy)/det)


def _point(matrix,x,y):
    a,b,c,d,e,f=matrix;return a*x+c*y+e,b*x+d*y+f


def _traces(page):
    """Collapse only the exact fill/stroke pair emitted by source Tr=2."""
    values=page.get_texttrace(); result=[]; i=0
    while i<len(values):
        t=values[i];mode=t['type'];stroke=None;i+=1
        if mode==0 and i<len(values):
            n=values[i]
            if n['type']==1 and n['font']==t['font'] and n['size']==t['size'] and n['chars']==t['chars'] and n['seqno']==t['seqno']+1:
                mode=2;stroke=n;i+=1
        for cp,gid,origin,bbox in t['chars']:
            result.append(dict(c=chr(cp),font=family_name(t['font']),size=t['size'],
                               origin=origin,bbox=bbox,render_mode=mode,trace_gid=gid,
                               color=t.get('color'),opacity=t.get('opacity'),
                               linewidth=(stroke or t).get('linewidth'),direction=t.get('dir'),
                               stroke_color=stroke.get('color') if stroke else None,
                               stroke_opacity=stroke.get('opacity') if stroke else None,
                               wmode=t.get('wmode'),colorspace=t.get('colorspace')))
    return result


def _canonical(items, trace_names):
    result=[]
    for item in items:
        ch=dict(item);name=family_name(ch['font'])
        if name not in trace_names:
            aliases=[v for v in trace_names if v.startswith(name)]
            if not aliases:
                folded=lambda v:re.sub('[^a-z0-9]','',v.lower())
                aliases=[v for v in trace_names if folded(v)==folded(name)]
            if len(aliases)!=1:raise ValueError('Ambiguous native font alias: '+name)
            name=aliases[0]
        ch['font']=name;result.append(ch)
    return result


def _raw_regions(container):
    class Collector(pikepdf.TokenFilter):
        def __init__(self):super().__init__();self.items=[]
        def handle_token(self,t):self.items.append((t.type_,t.raw_value));return t
    if isinstance(container,pikepdf.Page):
        c=Collector();raw=container.get_filtered_contents(c)
    else:
        # A temporary analysis page lets QPDF tokenize a Form without ever
        # serializing its high-precision cm/Tm tokens.
        owner=pikepdf.Pdf.new();p=owner.add_blank_page()
        p.Contents=owner.make_stream(container.read_bytes())
        c=Collector();raw=p.get_filtered_contents(c)
    regions=[];offset=start=0
    for typ,value in c.items:
        offset+=len(value)
        if typ==pikepdf.TokenType.inline_image:
            raise ValueError('Inline-image content needs a separate surgery profile')
        if typ==pikepdf.TokenType.word:
            regions.append((start,offset,value.decode('ascii')));start=offset
    parsed=pikepdf.parse_content_stream(container)
    if len(regions)!=len(parsed) or any(v[2]!=str(i.operator) for v,i in zip(regions,parsed)):
        raise ValueError('Raw-token/operator mapping is not exact')
    return raw,regions


def _replace(container, replacements):
    raw,regions=_raw_regions(container);pieces=[];position=0
    for index,value in sorted(replacements.items()):
        a,z,operator=regions[index]
        if value and operator not in {'Tj','TJ','Do','q'}|PATH_CONSTRUCTION|PATH_PAINT:
            raise ValueError('Only native shows, Form invocations or reviewed pure paths may change')
        prefix=re.match(rb'\s*',raw[a:z])[0]
        pieces.extend([raw[position:a],prefix,value.rstrip(b'\r\n')]);position=z
    pieces.append(raw[position:]);return b''.join(pieces)


def _serialize(operands,operator):
    if operator=='TJ':
        values=[]
        for value in operands[0]:
            if isinstance(value,pikepdf.String):values.append(b'<'+bytes(value).hex().encode('ascii')+b'>')
            elif isinstance(value,float):values.append(_number(value).encode('ascii'))
            else:values.append(str(value).encode('ascii'))
        return b'['+b' '.join(values)+b'] TJ'
    item=pikepdf.ContentStreamInstruction(operands,pikepdf.Operator(operator))
    return pikepdf.unparse_content_stream([item]).rstrip(b'\r\n')


def _number(value):
    if not math.isfinite(value):raise ValueError('Nonfinite transformation')
    return ('%.12f'%value).rstrip('0').rstrip('.') or '0'


def _font_programs(page):
    programs=set();seen=set()
    def walk(resources):
        for font in resources.get('/Font',{}).values():
            for face in font.get('/DescendantFonts',[font]):
                desc=face.get('/FontDescriptor',{})
                for key in ['/FontFile','/FontFile2','/FontFile3']:
                    if key in desc:programs.add(hashlib.sha256(desc[key].read_bytes()).hexdigest())
        for obj in resources.get('/XObject',{}).values():
            if str(obj.get('/Subtype'))=='/Form' and obj.objgen not in seen:
                seen.add(obj.objgen);walk(obj.get('/Resources',resources))
    walk(page.Resources);return programs


def _verify_glyphs(source_page, result, erase, offsets, tolerance=.0001, occurrence_offsets=None):
    proof=fitz.open(stream=result,filetype='pdf');a=_traces(source_page);b=_traces(proof[0])
    buckets=defaultdict(list)
    def identity(c):
        # GID, actual font, size, paint mode, and glyph order are preserved.
        return (c['c'],c['font'],c['trace_gid'],round(c['size'],5),c['render_mode'],
                str(c['color']),c['opacity'],c['linewidth'],c['direction'],
                c['wmode'],c['colorspace'],str(c['stroke_color']),c['stroke_opacity'])
    for c in b:buckets[identity(c)].append(c)
    failures=[];space_rounding=[];max_dx=max_dy=0.;visible_dx=visible_dy=0.;expected=0
    for source_index,c in enumerate(a):
        key=glyph_key(c)
        if key in erase:continue
        expected+=1;dx=(occurrence_offsets or {}).get(source_index,offsets.get(key,0.));x,y=c['origin'];x+=dx
        candidates=buckets[identity(c)]
        if not candidates:
            failures.append(dict(reason='missing native glyph',glyph=c));continue
        k=min(range(len(candidates)),key=lambda j:abs(candidates[j]['origin'][0]-x)+abs(candidates[j]['origin'][1]-y))
        actual=candidates.pop(k);ex=abs(actual['origin'][0]-x);ey=abs(actual['origin'][1]-y)
        max_dx=max(max_dx,ex);max_dy=max(max_dy,ey)
        allowed=tolerance
        if c['c']==' ':
            # MuPDF accumulates text advances in float32. Empty original
            # ASCII-space origins can differ by two ULPs after cancelling TJ
            # sums even though every visible outline stays exact. Report
            # these independently; never relax the visible-glyph tolerance.
            ulp=max(2.**(math.frexp(abs(value))[1]-24) if value else 2.**-149 for value in (x,y))
            allowed=max(allowed,ulp*3)
            if ex>tolerance or ey>tolerance:
                space_rounding.append(dict(source_origin=c['origin'],actual_origin=actual['origin'],
                                           x_error_pt=ex,y_error_pt=ey,allowed_float32_ulp_pt=allowed))
        else:visible_dx=max(visible_dx,ex);visible_dy=max(visible_dy,ey)
        if ex>allowed or ey>allowed:
            failures.append(dict(reason='native position differs from requested dx',source=c,actual=actual,dx=dx))
    extra=sum(len(v) for v in buckets.values());proof.close()
    return dict(expected_native_glyphs=expected,unexpected_glyphs=extra,
                native_glyph_mismatches=failures,position_tolerance_pt=tolerance,
                max_position_error_x_pt=max_dx,max_position_error_y_pt=max_dy,
                max_visible_position_error_x_pt=visible_dx,max_visible_position_error_y_pt=visible_dy,
                nonpainting_ascii_space_rounding=space_rounding)


def reposition_inline(source, page_number, erased_glyphs=None, shifts=None,
                      *, validate=True, reject_vector_overlap=True,
                      allow_white_background_panels=False,
                      reviewed_white_panel_rects=None,
                      reviewed_stationary_vector_paths=None,
                      text_shift_mode='tj',
                      position_tolerance_pt=.001,
                      _inspect_only=False,_inspect_text_shows=False):
    """Apply native per-glyph dx and optional simultaneous prose suppression.

    ``source`` is a filename/Path or PDF bytes. ``page_number`` is one-based.
    A shift must list the exact source glyphs (including full multi-CID formula
    groups). Do not supply display equations. The caller owns line packing;
    this function changes no unselected advance, y coordinate, font or style.

    A complete Form group can contain native bitmap/vector fractions. Selecting
    only part of a Form is rejected. To move a nested group without modifying
    a shared program, only its ancestor invocation resources are privately
    cloned; original streams are retained under /NativeInlineOriginal.
    An optional shift ``vector_paths=[entry]`` moves reviewed pure top-level
    path+paint operators with that shift; use entries from ``inspect_inline_groups``.
    Clip paths cannot be moved separately: their complete original q group
    must be selected, or the new glyph must remain inside its unchanged clip.
    ``reject_vector_overlap=False`` is only for separately proved text-only
    groups (for example a nonintersecting distant decorative frame).
    ``allow_white_background_panels=True`` ignores only opaque, unstroked,
    white rectangular background fills wider than half the page. Those
    background paths stay byte-for-byte at their original positions.
    ``reviewed_white_panel_rects`` whitelists smaller exact background rects;
    every entry must match an opaque, unstroked, white rectangle in the input.
    ``reviewed_stationary_vector_paths`` permits separately audited, exact
    nonmathematical pure paths (e.g. a header underline) to remain stationary
    despite a metric-box intersection. Actual ink/graphics QA is still required.
    Exact coincident original duplicate paints move together as one selection;
    the API never drops one copy or changes their original paint styles.
    ``text_shift_mode='ctm'`` uses cancelling graphics-state translations
    around original CID runs instead of TJ displacement. Text matrices are
    not q/Q stack members, so original glyph advances continue unchanged.
    This avoids float32 accumulation from repeated TJ displacement pairs.
    The reported x/y measurement tolerance is 0.001 point; CID/GID/font/size/
    paint identities and original asset programs remain exact requirements.
    """
    raw_source=bytes(source) if isinstance(source,(bytes,bytearray)) else Path(source).read_bytes()
    if text_shift_mode not in ['tj','ctm']:raise ValueError('Unknown native text-shift mode')
    if not 0<float(position_tolerance_pt)<=.001:raise ValueError('Position tolerance must be positive and at most 0.001pt')
    native=fitz.open(stream=raw_source,filetype='pdf')
    if not 1<=page_number<=len(native):raise ValueError('Page outside input PDF')
    page=native[page_number-1];trace=_traces(page);names={c['font'] for c in trace}
    erased=_canonical(erased_glyphs or [],names)
    erase={glyph_key(c) for c in erased if not c['c'].isspace()}
    offsets={};groups=[]
    for shift in shifts or []:
        dx=float(shift['dx'])
        if not math.isfinite(dx):raise ValueError('Nonfinite dx')
        glyphs=_canonical(shift['glyphs'],names)
        keys={glyph_key(c) for c in glyphs}
        if not keys and shift.get('form_path')is None and shift.get('image_path')is None:
            raise ValueError('Empty native shift group needs an exact original Form/image path')
        if keys&erase:raise ValueError('A glyph cannot be erased and shifted')
        if keys&offsets.keys():raise ValueError('Native shift groups overlap')
        for key in keys:offsets[key]=dx
        groups.append(dict(keys=keys,glyphs=glyphs,dx=dx,form_path=shift.get('form_path'),
                           image_path=shift.get('image_path'),vector_refs=shift.get('vector_paths',[])))
    requested=set(offsets)|erase
    requested_offsets=dict(offsets)
    trace_indices={id(c):i for i,c in enumerate(trace)}
    occurrences=Counter(glyph_key(c) for c in trace)
    for key in requested:
        if occurrences[key]<1:raise ValueError('Requested glyph is missing: '+repr(key))
    width_cache={}
    def advance_widths(font):
        key=font.objgen if font.objgen!=(0,0) else id(font)
        if key not in width_cache:width_cache[key]=widths(font)
        return width_cache[key]
    queues=defaultdict(list)
    for c in trace:queues[c['font']].append(c)
    selected_families={key[1] for key in requested};counters=Counter();records=[];nodes=[];images=[]
    page_matrix=tuple(page.transformation_matrix)
    source_pdf=pikepdf.Pdf.open(BytesIO(raw_source));out=pikepdf.Pdf.new()
    out.pages.append(source_pdf.pages[page_number-1]);p=out.pages[0]

    suffix_alias_font_ids=set()
    def resource_fonts(resources):
        info={}
        for name,font in resources.get('/Font',{}).items():
            family=family_name(bytes(font.get('/BaseFont')).decode('latin1'))
            if family not in names:
                folded=lambda v:re.sub('[^a-z0-9]','',v.lower())
                face_names=[family]
                for face in font.get('/DescendantFonts',[font]):
                    for value in [face.get('/BaseFont'),face.get('/FontDescriptor',{}).get('/FontName')]:
                        if value is not None:face_names.append(family_name(bytes(value).decode('latin1')))
                aliases={v for f in face_names for v in names
                         if f==v or f.startswith(v) or folded(f)==folded(v)}
                if not aliases:
                    # Old Word Symbol subsets can expose only their literal
                    # suffix (e.g. Symbol+FPEF -> FPEF) to MuPDF. Accept this
                    # only for embedded Identity CID-to-GID fonts, and verify
                    # every original encoded CID against its actual trace GID
                    # below. The font resource/program itself is never changed.
                    face=font.get('/DescendantFonts',[font])[0]
                    suffix={v for f in face_names for v in names if len(v)>=4 and f.endswith('+'+v)}
                    if len(suffix)==1 and str(font.get('/Encoding'))=='/Identity-H' and str(face.get('/CIDToGIDMap'))=='/Identity' and '/FontFile2'in face.get('/FontDescriptor',{}):
                        aliases=suffix;suffix_alias_font_ids.add(font.objgen)
                if len(aliases)==1:family=aliases.pop()
            # All resources in a selected family participate in trace order,
            # including read-only nested Forms sharing that family.
            # Decode every trace family so a Form completeness check cannot
            # accidentally omit a second face (e.g. a fraction denominator).
            if family not in names:continue
            enc=str(font.get('/Encoding'));cb=source_code_bytes(font)
            descfont=font.get('/DescendantFonts',[font])[0];descriptor=descfont.get('/FontDescriptor',{})
            identity=(enc=='/Identity-H' and str(descfont.get('/CIDToGIDMap'))=='/Identity' and '/FontFile2' in descriptor)
            info[str(name)]=(family,cmap(font),cb,identity,font)
        return info

    def walk(container, resources, state=None, parent=None, invocation=None, ancestors=()):
        # Text matrices are not graphics-state stack members. Track their
        # linear parts separately; Td/T*/TL affect only origins, which are
        # independently read from exact source trace association.
        st=dict(active='',tc=0.,tw=0.,tf=1.,tr=0,th=1.,ts=0.,ctm=IDENTITY,clips=()) if state is None else dict(state)
        tm=IDENTITY;stack=[];active_q=[];fonts=resource_fonts(resources)
        node=dict(container=container,resources=resources,parent=parent,invocation=invocation,
                  records=[],children=[],replacements={},keys=set(),trace_indices=set(),image_paths=set(),direct_images=[],shift=0.,vector_paths=[],clip_groups=[],entry_ctm=st['ctm'])
        node['path']=[] if parent is None else parent['path']+[invocation['index']]
        if parent is not None:
            node['original_raw_sha256']=hashlib.sha256(container.read_raw_bytes()).hexdigest()
            node['original_decoded_sha256']=hashlib.sha256(container.read_bytes()).hexdigest()
        nodes.append(node)
        pending_path=None
        for index,instruction in enumerate(pikepdf.parse_content_stream(container)):
            operands=list(instruction.operands);op=str(instruction.operator)
            if op in PATH_CONSTRUCTION:
                if pending_path is None:
                    pending_path=dict(indices=[],ops=[],points=[],ctm=st['ctm'],safe=True)
                pending_path['indices'].append(index)
                pending_path['ops'].append(op)
                vals=list(map(float,operands))
                if op=='re':
                    x,y,w,h=vals;points=[(x,y),(x+w,y),(x,y+h),(x+w,y+h)]
                elif op=='h':points=[]
                else:points=list(zip(vals[::2],vals[1::2]))
                pending_path['points'].extend(points)
            elif op in ['W','W*']:
                if pending_path is None:raise ValueError('Clip without a current source path')
                constructions=pending_path['ops']
                transform=_multiply(pending_path['ctm'],page_matrix)
                rect=None
                if constructions==['re'] and abs(transform[1])<1e-9 and abs(transform[2])<1e-9:
                    points=[_point(transform,*v) for v in pending_path['points']]
                    rect=[min(v[0] for v in points),min(v[1] for v in points),
                          max(v[0] for v in points),max(v[1] for v in points)]
                pending_path['clip']=dict(rect=rect,operator_index=index)
                pending_path['safe']=False
                if active_q:
                    active_q[-1]['has_clip']=True
                    active_q[-1]['own_clips'].append(pending_path['clip'])
            elif op in PATH_PAINT:
                if pending_path is not None:
                    pending_path['indices'].append(index)
                    if op!='n' and pending_path['safe'] and pending_path['points']:
                        transform=_multiply(pending_path['ctm'],page_matrix)
                        points=[_point(transform,*v) for v in pending_path['points']]
                        pending_path['rect']=[min(v[0] for v in points),min(v[1] for v in points),
                                              max(v[0] for v in points),max(v[1] for v in points)]
                        pending_path['paint_operator']=op
                        node['vector_paths'].append(pending_path)
                    if 'clip' in pending_path:st['clips']=st['clips']+(pending_path['clip'],)
                pending_path=None
            elif pending_path is not None:
                # Even a colour/width operator interleaved with construction
                # is outside the narrow, reviewed pure-path profile.
                pending_path['safe']=False
            if op=='q':
                stack.append(dict(st));active_q.append(dict(start=index,keys=set(),trace_indices=set(),image_paths=set(),has_clip=False,
                                                            own_clips=[],ctm=st['ctm'],parent_clips=st['clips']))
            elif op=='Q':
                if not stack:raise ValueError('Unbalanced source Q')
                st=stack.pop()
                qgroup=active_q.pop();qgroup['end']=index
                if qgroup['has_clip'] and (qgroup['keys']or qgroup['image_paths']):node['clip_groups'].append(qgroup)
            elif op=='cm':st['ctm']=_multiply(tuple(map(float,operands)),st['ctm'])
            elif op=='BT':tm=IDENTITY
            elif op=='Tm':tm=tuple(map(float,operands))
            elif op=='Tf':st['active']=str(operands[0]);st['tf']=float(operands[1])
            elif op=='Tc':st['tc']=float(operands[0])
            elif op=='Tw':st['tw']=float(operands[0])
            elif op=='Tz':st['th']=float(operands[0])/100.
            elif op=='Ts':st['ts']=float(operands[0])
            elif op=='Tr':st['tr']=int(operands[0])
            elif op=='"':st['tw']=float(operands[0]);st['tc']=float(operands[1])
            elif op=='Do':
                child=resources.get('/XObject',{}).get(operands[0])
                if child is not None and str(child.get('/Subtype'))=='/Form':
                    if child.objgen in ancestors or len(ancestors)>20:raise ValueError('Recursive/deep native Form')
                    childstate=dict(st)
                    childstate['ctm']=_multiply(tuple(map(float,child.get('/Matrix',IDENTITY))),st['ctm'])
                    call=dict(index=index,name=operands[0],ctm=st['ctm'],clips=st['clips'])
                    n=walk(child,child.get('/Resources',resources),childstate,node,call,ancestors+(child.objgen,))
                    node['children'].append(n);node['keys'].update(n['keys'])
                    node['trace_indices'].update(n['trace_indices'])
                    node['image_paths'].update(n['image_paths'])
                    for qgroup in active_q:
                        qgroup['keys'].update(n['keys']);qgroup['trace_indices'].update(n['trace_indices'])
                        qgroup['image_paths'].update(n['image_paths'])
                elif child is not None and str(child.get('/Subtype'))=='/Image':
                    path=tuple(node['path']+[index]);transform=_multiply(st['ctm'],page_matrix)
                    corners=[_point(transform,x,y)for x,y in[(0,0),(1,0),(0,1),(1,1)]]
                    image=dict(path=path,node=node,index=index,name=operands[0],ctm=st['ctm'],clips=st['clips'],
                        container=child,bbox=[min(v[0]for v in corners),min(v[1]for v in corners),max(v[0]for v in corners),max(v[1]for v in corners)],
                        raw_sha256=hashlib.sha256(child.read_raw_bytes()).hexdigest(),shift=0.)
                    images.append(image);node['direct_images'].append(image);node['image_paths'].add(path)
                    for qgroup in active_q:qgroup['image_paths'].add(path)
            if op not in ['Tj','TJ',"'",'"'] or st['active'] not in fonts:continue
            family,encoding,cb,identity,font=fonts[st['active']]
            items=list(operands[0]) if op=='TJ' else [operands[-1]]
            record=dict(node=node,index=index,op=op,items=items,parts=[],state=dict(st),tm=tm,font=font,cb=cb)
            for item in items:
                if not isinstance(item,pikepdf.String):record['parts'].append(item);continue
                raw=bytes(item)
                if len(raw)%cb:raise ValueError('Incomplete source CID')
                for pos in range(0,len(raw),cb):
                    data=raw[pos:pos+cb];code=int.from_bytes(data,'big');decoded=encoding.get(code)
                    qi=counters[family]
                    if not decoded:
                        unknown=queues[family][qi:qi+1]
                        if not(identity and len(unknown)==1 and unknown[0]['trace_gid']==code and unknown[0]['c']=='\ufffd'):
                            raise ValueError(f'Missing ToUnicode {family} CID {code}')
                        decoded='\ufffd'
                    cluster=queues[family][qi:qi+len(decoded)];counters[family]+=len(decoded)
                    if len(cluster)!=len(decoded) or ''.join(c['c'] for c in cluster)!=decoded:
                        raise ValueError(f'CID/trace association failed: {family} CID {code}')
                    if font.objgen in suffix_alias_font_ids and (cluster[0]['trace_gid']!=code or any(c['trace_gid']!=-1 for c in cluster[1:])):
                        raise ValueError('A shortened native font alias lacks exact original CID/GID identity')
                    if any(c['render_mode']!=st['tr'] for c in cluster):raise ValueError('Source Tr/trace mismatch')
                    keys={glyph_key(c) for c in cluster}
                    if len(cluster)>1 and keys&requested:
                        first=cluster[0]
                        if first['trace_gid']<0 or any(c['trace_gid']!=-1 or c['origin']!=first['origin']
                            or c['size']!=first['size'] or abs(c['bbox'][2]-c['bbox'][0])>1e-6 for c in cluster[1:]):
                            raise ValueError('Unsupported painted multi-Unicode CID cluster')
                        wholly_erased=keys<=erase
                        wholly_shifted=keys<=offsets.keys() and len({offsets[k] for k in keys})==1
                        if not(wholly_erased or wholly_shifted):
                            raise ValueError('Multi-Unicode CID requires every continuation at one atomic dx')
                    part=dict(raw=data,code=code,cluster=cluster,keys=keys)
                    record['parts'].append(part);node['keys'].update(keys)
                    members={trace_indices[id(c)] for c in cluster}
                    node['trace_indices'].update(members)
                    for qgroup in active_q:
                        qgroup['keys'].update(keys);qgroup['trace_indices'].update(members)
            records.append(record);node['records'].append(record)
        if stack:raise ValueError('Unbalanced source q')
        node['exit_ctm']=st['ctm']
        return node

    root=walk(p,p.Resources)
    for family,queue in queues.items():
        if counters[family]!=len(queue):raise ValueError('Unconsumed native trace '+family)

    def native_form_bbox(node):
        box=list(map(float,node['container'].get('/BBox',[])))
        if len(box)!=4:raise ValueError('Native Form has no explicit BBox')
        x0,y0,x1,y1=box;transform=_multiply(node['entry_ctm'],page_matrix)
        points=[_point(transform,x,y) for x,y in[(x0,y0),(x1,y0),(x0,y1),(x1,y1)]]
        return[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
    if _inspect_only:
        by_key={glyph_key(c):c for c in trace}
        inventory=dict(page_number=page_number,forms=[dict(
            path=n['path'],source_objgen=list(n['container'].objgen),
            native_page_bbox=native_form_bbox(n),
            entry_ctm=n['entry_ctm'],page_matrix=page_matrix,
            invocation_ctm=n['invocation']['ctm'],
            image_paths=[list(v)for v in sorted(n['image_paths'])],
            painted_image_rects=[i['bbox']for i in images if i['path']in n['image_paths']],
            own_vector_paths=[dict(operator_indices=v['indices'],rect=v['rect'],paint_operator=v['paint_operator']) for v in n['vector_paths']],
            glyphs=[by_key[k] for k in sorted(n['keys'])],
            original_raw_sha256=n['original_raw_sha256']) for n in nodes[1:]],
            vector_paths=[dict(operator_indices=v['indices'],rect=v['rect'],
                               paint_operator=v['paint_operator']) for v in root['vector_paths']],
            clip_groups=[dict(operator_indices=[v['start'],v['end']],
                              image_paths=[list(v)for v in sorted(v['image_paths'])],
                              glyphs=[by_key[k] for k in sorted(v['keys'])],
                              clip_rects=[c['rect'] for c in v['own_clips']],
                              ancestor_clip_rects=[c['rect'] for c in v['parent_clips']],
                              known_rectangular_clips=all(c['rect'] is not None for c in v['own_clips']))
                         for v in root['clip_groups']])
        inventory['images']=[dict(path=list(i['path']),bbox=i['bbox'],entry_ctm=i['ctm'],page_matrix=page_matrix,
            ancestor_clip_rects=[c['rect']for c in i['clips']],source_objgen=list(i['container'].objgen),
            original_raw_sha256=i['raw_sha256'])for i in images]
        inventory['final_ctm']=root['exit_ctm']
        if _inspect_text_shows:
            inventory['top_level_text_shows']=[dict(operator_index=r['index'],operator=r['op'],
                state=r['state'],text_matrix=r['tm'],parts=[dict(raw_hex=p['raw'].hex(),code=p['code'],
                glyphs=p['cluster']) for p in r['parts'] if isinstance(p,dict)]) for r in root['records']]
        native.close();out.close();source_pdf.close();return inventory

    # Old translation PDFs often wrap one native inline formula in a tight
    # q/re/W/n/.../Q clip. A TJ-only move would retain that old clip and could
    # make the native glyph disappear. Move the complete original q group,
    # including its clip and any fraction lines, whenever it is selected whole.
    nonspace=lambda keys:{k for k in keys if not k[0].isspace()}
    stationary_paths=[];stationary_indices=set()
    for reference in reviewed_stationary_vector_paths or []:
        indices=reference['operator_indices'] if isinstance(reference,dict) else reference
        values=[v for v in root['vector_paths'] if v['indices']==list(indices)]
        if len(values)!=1:raise ValueError('Stationary reviewed path is not one exact pure top-level path')
        stationary_paths.append(values[0]);stationary_indices.update(indices)
    for group in groups:
        if group['form_path']is not None and group['image_path']is not None:raise ValueError('Select one native Form or image invocation per atom')
        selected_images=set()
        if group['form_path']is not None:
            matches=[n for n in nodes[1:]if n['path']==list(group['form_path'])]
            if len(matches)!=1:raise ValueError('Requested native Form path is missing or ambiguous')
            selected_images.update(matches[0]['image_paths'])
        if group['image_path']is not None:
            selected_images.add(tuple(group['image_path']))
            matches=[i for i in images if i['path']==tuple(group['image_path'])]
            if len(matches)!=1:raise ValueError('Requested native image path is missing or ambiguous')
            if matches[0]['node']is not root:raise ValueError('A nested mathematical image must move through its complete original Form')
            group['image_node']=matches[0]
        group['selected_images']=selected_images
    atomic_clips=[];atomic_clip_keys=set();atomic_clip_images=set();claimed_clip_ranges=[]
    for group in groups:
        candidates=[v for v in root['clip_groups'] if
            ((nonspace(v['keys']) and nonspace(v['keys'])<=nonspace(group['keys'])) or
             (not nonspace(v['keys']) and v['image_paths'] and v['image_paths']<=group['selected_images']))
            and (not group['selected_images']or v['image_paths']<=group['selected_images'])]
        candidates=[v for v in candidates if not any(v['start']<=i<=v['end'] for i in stationary_indices)]
        # Use an outer complete group if it contains complete nested clips;
        # no other invocation may then claim the same original range.
        candidates.sort(key=lambda v:(v['start'],-v['end']))
        for v in candidates:
            if any(a<=v['start'] and v['end']<=z for a,z in claimed_clip_ranges):continue
            if any(not(v['end']<a or v['start']>z) for a,z in claimed_clip_ranges):
                raise ValueError('Overlapping atomic native clip groups')
            if v['keys']&erase:raise ValueError('An atomically moved clip group also contains erased prose')
            claimed_clip_ranges.append((v['start'],v['end']));atomic_clip_keys.update(v['keys'])
            atomic_clip_images.update(v['image_paths'])
            for key in v['keys']:offsets[key]=group['dx']
            atomic_clips.append(dict(group=v,dx=group['dx']))

    # Include all native Form glyphs, not merely the selected families, when
    # testing completeness. The read-only core uses the identical association.
    # A selected group must exactly cover its invocation's visible trace.
    claimed_forms=[]
    for group in groups:
        remaining=group['keys']-atomic_clip_keys
        if group['form_path'] is not None:
            # A pure bitmap/math-path Form legitimately has no glyphs. Its
            # exact invocation is still one complete native mathematical atom.
            exact=[n for n in nodes[1:]if n['path']==list(group['form_path'])]
            if exact and (exact[0]['keys']or exact[0]['image_paths']) and exact[0]['keys']<=atomic_clip_keys and exact[0]['image_paths']<=atomic_clip_images:
                continue
            candidates=[n for n in exact if nonspace(n['keys'])==nonspace(remaining)]
        else:
            contained=[n for n in nodes[1:] if n['keys']&remaining]
            if not contained:continue
            candidates=[n for n in contained if nonspace(n['keys'])==nonspace(remaining)]
        if not candidates:raise ValueError('Partial native Form selection would strand vector/image mathematics')
        if len(candidates)!=1:
            raise ValueError('Ambiguous nested native Form group: supply form_path from inspect_inline_groups')
        target=candidates[0]
        if any(target['path'][:len(path)]==path or path[:len(target['path'])]==target['path']for path in claimed_forms):
            raise ValueError('Overlapping original Form invocations cannot be shifted twice')
        claimed_forms.append(target['path'])
        target['shift']=group['dx']
        for key in target['keys']:offsets[key]=group['dx']
        group['form_node']=target
    for group in groups:
        image=group.get('image_node')
        if image is None or image['path']in atomic_clip_images:continue
        if image['shift']:raise ValueError('Overlapping original image shift groups')
        moved=fitz.Rect(image['bbox'])+(group['dx'],0,group['dx'],0)
        for clip in image['clips']:
            if clip['rect']is None or not fitz.Rect(clip['rect']).contains(moved):
                raise ValueError('Native image shift would leave its unchanged source clip; select the complete original clip/Form')
        image['shift']=group['dx']
    for n in nodes[1:]:
        if n['keys']&erase:raise ValueError('Prose erasure inside native Form is unsupported')

    form_keys=set(atomic_clip_keys)
    for n in nodes[1:]:
        if n['shift']:form_keys.update(n['keys'])
    top_groups=[g for g in groups if 'form_node' not in g and g['keys']-atomic_clip_keys]
    selected_paths=[];path_indices=set()
    raw_content,raw_regions=_raw_regions(p)
    for item in atomic_clips:
        v=item['group'];a=raw_regions[v['start']][0];z=raw_regions[v['end']][1]
        for ch in trace:
            if glyph_key(ch) not in v['keys']:continue
            r=fitz.Rect(ch['bbox']);dx=item['dx'];moved=fitz.Rect(r.x0+dx,r.y0,r.x1+dx,r.y1)
            for clip in v['parent_clips']:
                if clip['rect'] is None:
                    raise ValueError('Moved atomic clip group has an unknown unchanged ancestor clip')
                if fitz.Rect(clip['rect']).contains(moved):continue
                # Word repeats a row clip inside an identical ancestor clip.
                # Original ascender/descender metric boxes may already exceed
                # the row vertically. The group's own unchanged clip program
                # moves together with its glyphs: its visible source portion,
                # rather than invisible metric overshoot, must fit the ancestor.
                visible=fitz.Rect(r)
                for own in v['own_clips']:
                    if own['rect'] is None:raise ValueError('Atomic native clip has unknown visible physical bounds')
                    visible &= fitz.Rect(own['rect'])
                if not v['own_clips'] or (not visible.is_empty and not fitz.Rect(clip['rect']).contains(visible+(dx,0,dx,0))):
                    raise ValueError('Moved atomic clip group would leave an unchanged ancestor clip')
        for image in images:
            if image['path']not in v['image_paths']:continue
            physical=fitz.Rect(image['bbox']);ancestor=image['node']
            while ancestor is not root:
                physical &= fitz.Rect(native_form_bbox(ancestor));ancestor=ancestor['parent']
            for own in v['own_clips']:
                if own['rect']is None:raise ValueError('Atomic image requires known own-clip physical bounds')
                physical &= fitz.Rect(own['rect'])
            if not physical.is_empty:
                for clip in v['parent_clips']:
                    if clip['rect']is None or not fitz.Rect(clip['rect']).contains(physical+(item['dx'],0,item['dx'],0)):
                        raise ValueError('Moved atomic native image would leave an unchanged ancestor clip')
        fragment=raw_content[a:z]
        tx,ty=_inverse_vector(_multiply(v['ctm'],page_matrix),item['dx'])
        prefix=('q 1 0 0 1 '+_number(tx)+' '+_number(ty)+' cm ').encode('ascii')
        root['replacements'][v['start']]=prefix+fragment+b' Q'
        for index in range(v['start']+1,v['end']+1):root['replacements'][index]=b''
        item['fragment']=fragment
    # All still-moved text must fit every unchanged rectangular ancestor
    # clip in both old and new locations. Unknown clip shapes fail closed.
    for rec in records:
        for part in rec['parts']:
            if not isinstance(part,dict):continue
            for ch in part['cluster']:
                key=glyph_key(ch)
                if key not in offsets or key in form_keys:continue
                r=fitz.Rect(ch['bbox']);dx=offsets[key]
                moved=fitz.Rect(r.x0+dx,r.y0,r.x1+dx,r.y1)
                for clip in rec['state']['clips']:
                    if clip['rect'] is None or not fitz.Rect(clip['rect']).contains(moved):
                        raise ValueError('Native shift would leave an unchanged clip; select its complete clip group')
    for group in groups:
        node=group.get('form_node')
        if node is None:continue
        if not nonspace(node['keys']):
            moved=fitz.Rect(native_form_bbox(node))+(group['dx'],0,group['dx'],0)
            for clip in node['invocation']['clips']:
                if clip['rect']is None or not fitz.Rect(clip['rect']).contains(moved):
                    raise ValueError('Pure native mathematical Form would leave an unchanged source clip')
        for ch in trace:
            if glyph_key(ch) not in node['keys']:continue
            r=fitz.Rect(ch['bbox']);dx=group['dx'];moved=fitz.Rect(r.x0+dx,r.y0,r.x1+dx,r.y1)
            for clip in node['invocation']['clips']:
                if clip['rect'] is None or not fitz.Rect(clip['rect']).contains(moved):
                    raise ValueError('Moved Form would leave an unchanged ancestor clip')
    for group in groups:
        if group['vector_refs'] and 'form_node' in group:
            raise ValueError('A complete Form already moves its vector paths')
        group['selected_paths']=[]
        for reference in group['vector_refs']:
            indices=reference['operator_indices'] if isinstance(reference,dict) else reference
            candidates=[v for v in root['vector_paths'] if v['indices']==list(indices)]
            if len(candidates)!=1:raise ValueError('Reviewed native path is not one exact, pure top-level path+paint group')
            vector=candidates[0]
            owners=[item for item in atomic_clips if any(
                item['group']['start']<=index<=item['group']['end'] for index in indices)]
            if owners:
                raise ValueError('A complete atomic native clip already owns this reviewed vector path; '
                    'omit the duplicated vector_paths entry: '+repr(dict(
                        operator_indices=list(indices),atomic_clip_ranges=[
                            [item['group']['start'],item['group']['end'],item['dx']] for item in owners])))
            if path_indices.intersection(indices):raise ValueError('Reviewed native vector groups overlap')
            if stationary_indices.intersection(indices):raise ValueError('A native path cannot be both stationary and moved')
            path_indices.update(indices)
            a=raw_regions[indices[0]][0];z=raw_regions[indices[-1]][1];fragment=raw_content[a:z]
            if isinstance(reference,dict) and reference.get('source_sha256') not in [None,hashlib.sha256(fragment).hexdigest()]:
                raise ValueError('Reviewed native vector source bytes changed')
            tx,ty=_inverse_vector(_multiply(vector['ctm'],page_matrix),group['dx'])
            prefix=('q 1 0 0 1 '+_number(tx)+' '+_number(ty)+' cm ').encode('ascii')
            root['replacements'][indices[0]]=prefix+fragment+b' Q'
            for index in indices[1:]:root['replacements'][index]=b''
            item=dict(vector=vector,dx=group['dx'],fragment=fragment)
            selected_paths.append(item);group['selected_paths'].append(item)
    if reject_vector_overlap:
        drawings=page.get_drawings()
        stationary_drawings=[]
        for path in stationary_paths:
            matching=[d for d in drawings if all(abs(a-b)<.001 for a,b in zip(d['rect'],path['rect']))]
            if not matching:raise ValueError('Stationary path bounds do not exactly match a source rendered drawing')
            stationary_drawings.extend(matching)
        ignored_backgrounds=[]
        reviewed_backgrounds=[list(map(float,r)) for r in reviewed_white_panel_rects or []]
        found_reviewed=set()
        if allow_white_background_panels or reviewed_backgrounds:
            for drawing in drawings:
                fill=drawing.get('fill')
                matches=[i for i,rect in enumerate(reviewed_backgrounds)
                         if all(abs(a-b)<.001 for a,b in zip(drawing['rect'],rect))]
                if (drawing['type']=='f' and fill is not None and len(fill)==3
                    and all(abs(float(v)-1)<1e-9 for v in fill)
                    and abs(float(drawing.get('fill_opacity',1))-1)<1e-9
                    and drawing.get('color') is None
                    and ((allow_white_background_panels and drawing['rect'].width>=page.rect.width*.5) or matches)
                    and drawing['items'] and all(item[0]=='re' for item in drawing['items'])):
                    ignored_backgrounds.append(drawing);found_reviewed.update(matches)
        if found_reviewed!=set(range(len(reviewed_backgrounds))):
            raise ValueError('Reviewed background entry is not an exact opaque white unstroked rectangle')
        for group in top_groups:
            box=fitz.Rect()
            for c in group['glyphs']:
                candidates=[t for t in trace if glyph_key(t)==glyph_key(c)]
                box|=fitz.Rect(candidates[0]['bbox'])
            for drawing in drawings:
                if any(drawing is v for v in ignored_backgrounds+stationary_drawings):continue
                r=fitz.Rect(drawing['rect']);pad=max(float(drawing.get('width') or 0)/2,.1)
                r=fitz.Rect(r.x0-pad,r.y0-pad,r.x1+pad,r.y1+pad)
                if box.intersects(r):
                    reviewed=False
                    for item in group['selected_paths']:
                        authorized=fitz.Rect(item['vector']['rect']);authorized+=(-pad-.001,-pad-.001,pad+.001,pad+.001)
                        if authorized.contains(r):reviewed=True;break
                    if not reviewed:
                        raise ValueError('Top-level glyph group intersects native vector drawing; move a complete Form/reviewed vector group instead: '+repr(dict(
                            glyphs=''.join(c['c']for c in group['glyphs']),glyph_rect=list(box),vector_rect=list(drawing['rect']),dx=group['dx'])))

    changed_glyphs=removed=0
    for rec in records:
        node=rec['node'];parts=rec['parts'];st=rec['state'];new=[];kept=bytearray();changed=False
        if text_shift_mode=='ctm':
            if not any(any(k in erase or (k in offsets and k not in form_keys and offsets[k]) for k in part['keys'])
                       for part in parts if isinstance(part,dict)):continue
            if node is not root:raise ValueError('Non-atomic native Form edit')
            if rec['op'] in ["'",'"']:raise ValueError('Selected quote show needs an explicit line-state profile')
            chunks=[];run=[];run_dx=0.
            def flush_ctm():
                if not run:return
                show=_serialize([pikepdf.Array(run)],'TJ')
                if run_dx:
                    tx,ty=_inverse_vector(_multiply(st['ctm'],page_matrix),run_dx)
                    show=('q 1 0 0 1 '+_number(tx)+' '+_number(ty)+' cm ').encode('ascii')+show+b' Q'
                chunks.append(show);run.clear()
            for part in parts:
                if not isinstance(part,dict):run.append(part);continue
                ch=part['cluster'][0];key=glyph_key(ch)
                if key in erase:
                    ws,default=advance_widths(rec['font']);width=ws.get(part['code'],default)
                    if width is None or st['tf']==0:raise ValueError('Selected prose has no explicit source advance')
                    spacing=st['tc']+(st['tw'] if rec['cb']==1 and part['code']==32 else 0)
                    run.append(-(width+spacing*1000/st['tf']));removed+=1
                    continue
                value=0. if key in form_keys else offsets.get(key,0.)
                if value!=run_dx:flush_ctm();run_dx=value
                run.append(pikepdf.String(part['raw']))
                if value:changed_glyphs+=1
            flush_ctm();node['replacements'][rec['index']]=b'\n'.join(chunks)
            continue
        current_dx=0.
        def flush():
            if kept:new.append(pikepdf.String(bytes(kept)));kept.clear()
        def set_dx(value):
            nonlocal current_dx,changed
            if value==current_dx:return
            if rec['op'] in ["'",'"']:raise ValueError('Selected quote show needs an explicit line-state profile')
            transform=_multiply(_multiply(rec['tm'],st['ctm']),page_matrix)
            ax,ay=transform[:2]
            if abs(ay)>1e-8 or abs(ax)<1e-12 or st['tf']==0 or st['th']==0:
                raise ValueError('TJ cannot express a pure page-horizontal move on this transformed baseline')
            flush();new.append(-1000*(value-current_dx)/(st['tf']*st['th']*ax))
            current_dx=value;changed=True
        for part in parts:
            if not isinstance(part,dict):flush();new.append(part);continue
            ch=part['cluster'][0];key=glyph_key(ch)
            if key in erase:
                if node is not root:raise ValueError('Non-atomic native Form edit')
                if rec['op'] in ["'",'"']:raise ValueError('Selected quote show needs an explicit line-state profile')
                flush();changed=True
                ws,default=advance_widths(rec['font']);width=ws.get(part['code'],default)
                if width is None or st['tf']==0:raise ValueError('Selected prose has no explicit source advance')
                spacing=st['tc']+(st['tw'] if rec['cb']==1 and part['code']==32 else 0)
                new.append(-(width+spacing*1000/st['tf']));removed+=1
            else:
                # A TJ number advances -(number/1000)*Tf*Tz along the
                # Tm*CTM baseline. Its paired opposite restores the source
                # advance exactly for every following source CID.
                value=0. if key in form_keys else offsets.get(key,0.)
                if value and node is not root:raise ValueError('Non-atomic native Form edit')
                set_dx(value);kept.extend(part['raw'])
                if value:changed_glyphs+=1
        set_dx(0.)
        flush()
        if changed:node['replacements'][rec['index']]=_serialize([pikepdf.Array(new)],'TJ')

    clone_count=0
    def build(node):
        nonlocal clone_count
        resources=node['resources'];replacement_resources=None
        for image in node['direct_images']:
            if not image['shift']:continue
            tx,ty=_inverse_vector(_multiply(image['ctm'],page_matrix),image['shift'])
            raw,regions=_raw_regions(node['container']);a,z,_=regions[image['index']]
            node['replacements'][image['index']]=('q 1 0 0 1 '+_number(tx)+' '+_number(ty)+' cm ').encode('ascii')+raw[a:z]+b' Q'
        for child in node['children']:
            changed_child=build(child)
            if changed_child is None and not child['shift']:continue
            call=child['invocation'];name=call['name']
            if changed_child is not None:
                if replacement_resources is None:
                    replacement_resources=pikepdf.Dictionary(resources)
                    replacement_resources.XObject=pikepdf.Dictionary(resources.get('/XObject',{}))
                alias=pikepdf.Name('/NativeInlineMove'+str(clone_count));clone_count+=1
                replacement_resources.XObject[alias]=changed_child;name=alias
            invocation=_serialize([name],'Do')
            if child['shift']:
                transform=_multiply(call['ctm'],page_matrix)
                tx,ty=_inverse_vector(transform,child['shift'])
                invocation=('q 1 0 0 1 '+_number(tx)+' '+_number(ty)+' cm ').encode('ascii')+invocation+b' Q'
            node['replacements'][call['index']]=invocation
        if not node['replacements']:return None
        data=_replace(node['container'],node['replacements'])
        if node is root:
            p.Contents=out.make_stream(data)
            if replacement_resources is not None:p.Resources=replacement_resources
            return None
        original=node['container'];clone=out.make_stream(data)
        for key,value in original.items():
            if str(key) not in ['/Length','/Filter','/DecodeParms']:clone[key]=value
        if replacement_resources is not None:clone.Resources=replacement_resources
        clone['/NativeInlineOriginal']=original
        return clone

    before_programs=_font_programs(p);build(root)
    stream=BytesIO();out.save(stream,compress_streams=False);result=stream.getvalue()
    qa=dict(api='native-inline-reposition-v1',page_number=page_number,
            text_shift_mode=text_shift_mode,
            erased_glyphs=removed,shifted_top_level_glyphs=changed_glyphs,
            shifted_form_instances=sum(bool(n['shift']) for n in nodes[1:]),
            shifted_direct_image_instances=sum(bool(i['shift'])for i in images),
            shifted_atomic_clip_groups=len(atomic_clips),
            shifted_reviewed_vector_paths=len(selected_paths),
            unchanged_white_background_panels_ignored=len(ignored_backgrounds) if reject_vector_overlap else 0,
            reviewed_stationary_vector_paths_unchanged=[v['indices'] for v in stationary_paths],
            private_form_ancestor_copies=clone_count,
            font_programs_unchanged=before_programs==_font_programs(p),
            original_form_streams_unchanged=all(
                hashlib.sha256(n['container'].read_raw_bytes()).hexdigest()==n['original_raw_sha256']
                and hashlib.sha256(n['container'].read_bytes()).hexdigest()==n['original_decoded_sha256']
                for n in nodes[1:]),
            original_image_streams_unchanged=all(hashlib.sha256(i['container'].read_raw_bytes()).hexdigest()==i['raw_sha256']for i in images),
            native_vector_path_bytes_preserved=all(item['fragment'] in p.Contents.read_bytes() for item in selected_paths),
            native_atomic_clip_bytes_preserved=all(item['fragment'] in p.Contents.read_bytes() for item in atomic_clips),
            output_sha256=hashlib.sha256(result).hexdigest())
    if validate:
        # Two original encoded ASCII-space occurrences may share the exact
        # same family/size/origin while belonging to different q/clip groups.
        # Group expansion must not claim that an untouched outside occurrence
        # moved. Keep source CID/trace occurrence membership authoritative.
        occurrence_offsets={i:requested_offsets.get(glyph_key(c),0.) for i,c in enumerate(trace)}
        for item in atomic_clips:
            for i in item['group']['trace_indices']:occurrence_offsets[i]=item['dx']
        for node in nodes[1:]:
            if node['shift']:
                for i in node['trace_indices']:occurrence_offsets[i]=node['shift']
        qa['atomic_nonpainting_space_occurrence_shifts']=[dict(source_trace_index=i,source_origin=c['origin'],dx=occurrence_offsets[i])
            for i,c in enumerate(trace) if c['c']==' ' and occurrence_offsets[i]!=requested_offsets.get(glyph_key(c),0.)]
        qa.update(_verify_glyphs(page,result,erase,offsets,tolerance=float(position_tolerance_pt),occurrence_offsets=occurrence_offsets))
        qa['passed']=not qa['native_glyph_mismatches'] and not qa['unexpected_glyphs'] and qa['font_programs_unchanged'] and qa['original_form_streams_unchanged'] and qa['original_image_streams_unchanged'] and qa['native_vector_path_bytes_preserved'] and qa['native_atomic_clip_bytes_preserved']
        if not qa['passed']:raise ValueError('Native inline move failed its glyph invariant: '+repr(qa))
    else:qa['passed']=None
    native.close();out.close();source_pdf.close()
    return result,qa


# Descriptive alias for callers already using suppress_prose terminology.
move_native_inline = reposition_inline


def inspect_inline_groups(source, page_number, *,include_text_shows=False):
    """Return complete, exact invocation glyph groups usable in ``shifts``.

    Every Form entry has a stable operator-index ``path`` and source ``glyphs``.
    Parent/child entries overlap: choose either a whole parent or selected
    disjoint children, never both. ``clip_groups`` lists atomic q/clip/text/Q
    glyphs. ``vector_paths`` lists the operator indices and bounds of pure
    native paths; only explicitly reviewed entries may be added to a shift.
    This does not modify the input PDF.
    """
    return reposition_inline(source,page_number,_inspect_only=True,_inspect_text_shows=include_text_shows)
