"""Original-coordinate IZhO Korean proof; never reflow or rasterize equations.

The source page's selected prose glyphs are suppressed with exact PDF text
advances. Korean is written in reviewed slots at the original font size and
baseline. All other source text, diagrams and vector paths remain native.
"""
from __future__ import annotations
import argparse
from collections import Counter
from io import BytesIO
import json
import math
from pathlib import Path
import re
import hashlib
import pymupdf as fitz
import numpy as np
from PIL import Image, ImageDraw
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from pdf_original_text_ops import suppress_prose, glyph_key

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'tools/ko/fonts'
FONT_FILES = {
    'serif': FONTS/'NotoSerifCJKkr-Regular.otf',
    'serif_bold': FONTS/'NotoSerifCJKkr-Bold.otf',
    'sans_bold': FONTS/'NotoSansCJKkr-Bold.otf',
}


def raw_runs(page):
    """Use nonempty spans, matching the reviewed source inventory."""
    result = {}
    trace_names = {item['font'] for item in page.get_texttrace()}
    for bi, block in enumerate(page.get_text('rawdict')['blocks']):
        if block['type'] != 0:
            continue
        for li, line in enumerate(block['lines']):
            si = 0
            for span in line['spans']:
                text = ''.join(c['c'] for c in span['chars'])
                if not text.strip():
                    continue
                name=span['font']
                if name not in trace_names:
                    candidates=[value for value in trace_names if value.startswith(name)]
                    if len(candidates)!=1:
                        raise ValueError(('Ambiguous source font alias',name,candidates))
                    name=candidates[0]
                result[(bi, li, si)] = dict(span, text=text, font=name)
                si += 1
    return result


def chars_of(span):
    return [dict(c, font=span['font'], size=span['size']) for c in span['chars']]


def match_range(span, word):
    start = span['text'].index(word)
    return start, start + len(word)


def subset_buffer(path, text):
    font = TTFont(path)
    options = subset.Options()
    options.name_IDs = ['*']
    options.name_legacy = True
    options.name_languages = ['*']
    options.retain_gids = True
    worker = subset.Subsetter(options=options)
    worker.populate(text=text)
    worker.subset(font)
    stream = BytesIO()
    font.save(stream)
    return stream.getvalue()


def font_role(span):
    if 'Arial' in span['font']:
        return 'sans_bold'
    if 'Bold' in span['font']:
        return 'serif_bold'
    return 'serif'


def slot_geometry(spec, span):
    chars = span['chars']
    start, end = 0, len(chars)
    if spec.get('before'):
        end = match_range(span, spec['before'])[0]
    if spec.get('after'):
        start = match_range(span, spec['after'])[1]
    if start >= end:
        raise ValueError(('Empty source slot', spec))
    rect = fitz.Rect(chars[start]['bbox'])
    for char in chars[start+1:end]:
        rect |= fitz.Rect(char['bbox'])
    if spec.get('extend_to') is not None:
        rect.x1 = spec['extend_to']
    return rect, (chars[start]['origin'][0], span['origin'][1])


def native_trace(page):
    return Counter(glyph_key(dict(c=chr(cp), font=trace['font'], size=trace['size'], origin=origin))
                   for trace in page.get_texttrace()
                   for cp, gid, origin, bbox in trace['chars'] if not chr(cp).isspace())


def trace_records(page):
    return [dict(c=chr(cp),font=trace['font'],size=trace['size'],gid=gid,origin=origin)
            for trace in page.get_texttrace()
            for cp,gid,origin,bbox in trace['chars']if not chr(cp).isspace()]


def float32_ulp(value):
    value=np.float32(abs(value))
    return float(np.nextafter(value,np.float32(np.inf))-value)


def compare_native_records(expected,actual):
    """Keep font/GID/size exact; allow only insignificant float32 origins.

    Replacing a run of CID advances with an equivalent TJ number changes the
    multiplication order in MuPDF. At x=553pt its one float32 ULP is 0.000061pt.
    No kerning is changed to imitate an interpreter's internal rounding.
    """
    groups={}
    for record in actual:
        key=tuple(record[k]for k in('c','font','size','gid'))
        groups.setdefault(key,[]).append(record)
    missing=[];differences=[]
    for record in expected:
        key=tuple(record[k]for k in('c','font','size','gid'))
        candidates=groups.get(key,[])
        if not candidates:missing.append(record);continue
        nearest=min(candidates,key=lambda r:max(abs(a-b)for a,b in zip(r['origin'],record['origin'])))
        delta=[abs(a-b)for a,b in zip(nearest['origin'],record['origin'])]
        limits=[max(.0001,float32_ulp(value))for value in record['origin']]
        if any(a>b for a,b in zip(delta,limits)):missing.append(record);continue
        candidates.remove(nearest)
        if any(delta):
            differences.append(dict(c=record['c'],font=record['font'],size=record['size'],gid=record['gid'],
                                    source_origin=record['origin'],output_origin=nearest['origin'],
                                    max_delta_pt=max(delta),max_delta_float32_ulps=max(d/float32_ulp(v)if d else 0 for d,v in zip(delta,record['origin']))))
    return dict(missing=missing,extra=sum(len(rows)for rows in groups.values()),differences=differences,
                max_delta_pt=max([row['max_delta_pt']for row in differences]or[0]),
                max_delta_float32_ulps=max([row['max_delta_float32_ulps']for row in differences]or[0]))


def rgb(page, scale):
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)


def check_plan(plan_path):
    """Report every width problem before doing PDF work or font subsetting."""
    plan_path=plan_path if plan_path.is_absolute()else ROOT/plan_path
    data=json.loads(plan_path.read_text('utf8'))
    doc=fitz.open(ROOT/data['source'])
    page=doc[data['page']]
    fitz.TOOLS.set_small_glyph_heights(True)
    runs=raw_runs(page)
    names={item['font']for item in page.get_texttrace()}
    latin={}
    for item in sorted(page.get_fonts(),key=lambda item:item[5]!='WinAnsiEncoding'):
        plain=item[3].split('+')[-1]
        matches=[value for value in names if plain.startswith(value)]
        name=matches[0]if len(matches)==1 else plain
        if name not in latin and item[1]in {'ttf','otf'}:
            latin[name]=fitz.Font(fontbuffer=doc.extract_font(item[0])[3])
    metrics={name:fitz.Font(fontfile=str(path))for name,path in FONT_FILES.items()}
    errors=[]
    for spec in data.get('slots',[]):
        span=runs[tuple(spec['at'])]
        rect,point=slot_geometry(spec,span)
        metric=metrics[font_role(span)]
        native=latin.get(span['font'])
        width=sum((native if text.isdigit()and native and all(native.has_glyph(ord(c))for c in text)else metric).text_length(text,fontsize=span['size'])for text in re.split(r'([0-9]+)',spec['text'])if text)
        if width>rect.width+.05:
            errors.append({'slot':spec['at'],'text':spec['text'],'width':width,'available':rect.width})
    for spec in data.get('rich_slots',[]):
        span=runs[tuple(spec['at'])]
        rect,point=slot_geometry(spec,span)
        if spec.get('through'):rect|=fitz.Rect(runs[tuple(spec['through'])]['bbox'])
        if spec.get('extend_to')is not None:rect.x1=spec['extend_to']
        width=0
        for part in spec['parts']:
            style=runs[tuple(part.get('style_from',spec['at']))]
            metric=latin[style['font']]if part.get('native')else metrics[font_role(style)]
            width+=metric.text_length(part['text'],fontsize=style['size'])
        if width>rect.width+.05:
            errors.append({'slot':spec['at'],'text':''.join(v['text']for v in spec['parts']),'width':width,'available':rect.width})
    print(json.dumps(errors,ensure_ascii=False,indent=2))
    return errors


def build(plan_path, target):
    plan_path = plan_path if plan_path.is_absolute() else ROOT/plan_path
    target = target if target.is_absolute() else ROOT/target
    data = json.loads(plan_path.read_text('utf8'))
    source_path = ROOT / data['source']
    source_sha=hashlib.sha256(source_path.read_bytes()).hexdigest()
    if data.get('source_sha256') and data['source_sha256']!=source_sha:
        raise ValueError('Reviewed original PDF hash changed')
    source = fitz.open(source_path)
    pi = data['page']
    page = source[pi]
    fitz.TOOLS.set_small_glyph_heights(True)
    runs = raw_runs(page)
    trace_names = {item['font'] for item in page.get_texttrace()}
    def source_font_name(name):
        plain=name.split('+')[-1]
        matches=[value for value in trace_names if plain.startswith(value)]
        return matches[0] if len(matches)==1 else plain
    # MuPDF's small-height char boxes describe text advances. TrueType ink can
    # overhang them (notably f/r and italic punctuation). Use the embedded
    # source outlines, never a rectangle inferred from the translated pixels.
    outline_faces={}
    for item in sorted(page.get_fonts(),key=lambda item:item[5]!='WinAnsiEncoding'):
        name=source_font_name(item[3])
        if name not in outline_faces and item[1] in {'ttf','otf'}:
            face=TTFont(BytesIO(source.extract_font(item[0])[3]))
            cmap=face.getBestCmap()or{}
            if not cmap:
                for table in face['cmap'].tables:cmap.update(table.cmap)
            outline_faces[name]=(face,face.getGlyphSet(),cmap,face['head'].unitsPerEm)
    outline_cache={}
    def actual_char_rect(char):
        name=char['font'];cp=ord(char['c']);key=(name,cp)
        if key not in outline_cache:
            bounds=None
            if name in outline_faces:
                face,glyphs,cmap,upm=outline_faces[name]
                glyph_name=cmap.get(cp)
                if glyph_name:
                    pen=BoundsPen(glyphs);glyphs[glyph_name].draw(pen)
                    if pen.bounds:bounds=tuple(value/upm for value in pen.bounds)
            outline_cache[key]=bounds
        bounds=outline_cache[key]
        if bounds is None:return fitz.Rect(char['bbox'])
        x,y=char['origin'];size=char['size'];x0,y0,x1,y1=bounds
        return fitz.Rect(x+x0*size,y-y1*size,x+x1*size,y-y0*size)
    kept = set()
    for b, l, s, text in data.get('keep_prose_substrings',[]):
        run = runs[(b,l,s)]
        a,z = match_range(run, text)
        kept.update(glyph_key(c) for c in chars_of(run)[a:z])

    selected = []
    prose_frames = []
    forced = {tuple(key) for key in data.get('force_prose_runs',[])}
    for key, run in runs.items():
        if key not in forced and (run['font'].startswith('CambriaMath') or not re.search('[A-Za-z]{2,}', run['text'])):
            continue
        for char in chars_of(run):
            if glyph_key(char) not in kept:
                selected.append(char)
                prose_frames.append(list((fitz.Rect(char['bbox'])|actual_char_rect(char))+(-.15,-.15,.15,.15)))

    all_ko = (''.join(s['text'] for s in data.get('slots',[])) +
              ''.join(v[2]+v[4] for v in data.get('centered',[])) +
              ''.join(part['text'] for rich in data.get('rich_slots',[]) for part in rich['parts']))
    font_buffers = {role: subset_buffer(path, all_ko) for role,path in FONT_FILES.items()}
    metrics = {role: fitz.Font(fontbuffer=buffer) for role,buffer in font_buffers.items()}

    # Text-show suppression changes no source glyph positions or vector objects.
    native_bytes, removed = suppress_prose(source_path, pi+1, selected)
    control = fitz.open(stream=native_bytes,filetype='pdf')
    output = fitz.open(stream=native_bytes, filetype='pdf')
    out = output[0]
    for role, buffer in font_buffers.items():
        out.insert_font(fontname='KO_'+role, fontbuffer=buffer)
    latin_fonts = {}
    for font in sorted(page.get_fonts(),key=lambda item:item[5]!='WinAnsiEncoding'):
        name = source_font_name(font[3])
        if name not in latin_fonts and font[1] in {'ttf','otf'}:
            latin_fonts[name] = (font[4],fitz.Font(fontbuffer=source.extract_font(font[0])[3]))
    source_angles = {source_font_name(font[3]): float(TTFont(BytesIO(source.extract_font(font[0])[3]))['post'].italicAngle)
                     for font in page.get_fonts() if 'Ital' in font[3]}

    placements = []
    def put(spec, span):
        rect, point = slot_geometry(spec,span)
        role = font_role(span)
        size = span['size']
        text = spec['text']
        pieces=[]
        native_face=latin_fonts.get(span['font'])
        for fragment in re.split(r'([0-9]+)',text):
            if not fragment:
                continue
            if fragment.isdigit() and native_face and all(native_face[1].has_glyph(ord(c))for c in fragment):
                alias,metric=native_face
                pieces.append((fragment,alias,metric,True))
            else:
                pieces.append((fragment,'KO_'+role,metrics[role],False))
        advance = sum(metric.text_length(fragment,fontsize=size)for fragment,alias,metric,native in pieces)
        if advance > rect.width + .05:
            raise ValueError(f"Korean slot overflow {spec['at']}: {advance:.3f} > {rect.width:.3f}: {text}")
        x,y = point
        if spec.get('align') == 'center':
            x = (rect.x0+rect.x1-advance)/2
        italic = spec.get('italic',bool(span['flags']&2))
        angle = abs(source_angles.get(span['font'],-15)) if italic else 0
        morph = (fitz.Point(x,y),fitz.Matrix(1,0,math.tan(math.radians(angle)),1,0,0)) if italic else None
        cursor=x
        for fragment,alias,metric,native in pieces:
            part_morph=(fitz.Point(cursor,y),fitz.Matrix(1,0,math.tan(math.radians(angle)),1,0,0))if italic and not native else None
            out.insert_text((cursor,y),fragment,fontname=alias,fontsize=size,morph=part_morph,overlay=True)
            cursor+=metric.text_length(fragment,fontsize=size)
        # Full em frame accommodates Hangul ascenders while retaining the source
        # horizontal slot, source font size and exact baseline.
        # Italic descenders protrude left of the advance box. Include that
        # source-font ink overhang, independently of any output pixel audit.
        overhang = math.tan(math.radians(angle))*size*.3 if italic else 0
        frame = [rect.x0-.2-overhang,y-size-1,rect.x1+.2,y+size*.3]
        prose_frames.append(frame)
        placements.append(dict(source_slot=spec['at'],source_text=span['text'],korean=text,
                               point=[x,y],source_baseline=span['origin'][1],size=size,
                               source_size=span['size'],source_font=span['font'],font=role,
                               italic=italic,source_italic_angle=-angle if italic else 0,
                               target_oblique_angle=angle,frame=frame,advance=advance))

    for spec in data.get('slots',[]):
        put(spec,runs[tuple(spec['at'])])
    for b,l,ko1,latin1,ko2,latin2 in data.get('centered',[]):
        span = runs[(b,l,0)]
        size = span['size']
        rect = fitz.Rect(span['bbox'])
        alias,metric = latin_fonts['TimesNewRomanPS-BoldMT']
        parts=[(ko1,'KO_serif_bold',metrics['serif_bold']),
               (latin1,alias,metric),(ko2,'KO_serif_bold',metrics['serif_bold']),
               (latin2,alias,metric)]
        width=sum(font.text_length(text,fontsize=size) for text,name,font in parts)
        if width>rect.width+.05:
            raise ValueError(('Centered heading overflow',b,l,width,rect.width))
        x=(rect.x0+rect.x1-width)/2
        y=span['origin'][1]
        for text,name,font in parts:
            out.insert_text((x,y),text,fontname=name,fontsize=size,overlay=True)
            x+=font.text_length(text,fontsize=size)
        prose_frames.append([rect.x0-.2,y-size-1,rect.x1+.2,y+size*.3])
        placements.append(dict(source_slot=[b,l,0],source_text=span['text'],korean=ko1+latin1+ko2+latin2,
                               point=[(rect.x0+rect.x1-width)/2,y],source_baseline=y,
                               size=size,source_size=size,source_font=span['font'],
                               font='serif_bold + native TimesNewRomanPS-BoldMT',align='center',advance=width))

    for spec in data.get('rich_slots',[]):
        anchor = runs[tuple(spec['at'])]
        rect,point = slot_geometry(spec,anchor)
        if spec.get('through'):
            rect |= fitz.Rect(runs[tuple(spec['through'])]['bbox'])
        if spec.get('extend_to') is not None:
            rect.x1 = spec['extend_to']
        prepared=[]
        for part in spec['parts']:
            style=runs[tuple(part.get('style_from',spec['at']))]
            size=style['size']
            if abs(size-anchor['size'])>.001:
                raise ValueError('Mixed-size line needs an explicit reviewed baseline plan')
            italic=part.get('italic',bool(style['flags']&2))
            angle=abs(source_angles.get(style['font'],-15)) if italic else 0
            if part.get('native'):
                alias,metric=latin_fonts[style['font']]
                angle=0  # The embedded original face already has its italic outlines.
            else:
                role=font_role(style)
                alias,metric='KO_'+role,metrics[role]
            advance=metric.text_length(part['text'],fontsize=size)
            prepared.append((part,style,alias,size,angle,advance))
        width=sum(item[-1]for item in prepared)
        if width>rect.width+.05:
            raise ValueError(f"Rich source slot overflow {spec['at']}: {width:.3f} > {rect.width:.3f}")
        x,y=point
        if spec.get('align')=='center':x=(rect.x0+rect.x1-width)/2
        start_x=x
        for part,style,alias,size,angle,advance in prepared:
            morph=(fitz.Point(x,y),fitz.Matrix(1,0,math.tan(math.radians(angle)),1,0,0))if angle else None
            out.insert_text((x,y),part['text'],fontname=alias,fontsize=size,morph=morph,overlay=True)
            x+=advance
        size=anchor['size']
        overhang=max([math.tan(math.radians(item[4]))*size*.3 for item in prepared]or[0])
        frame=[rect.x0-.2-overhang,y-size-1,rect.x1+.2,y+size*.3]
        prose_frames.append(frame)
        placements.append(dict(source_slot=spec['at'],source_text=anchor['text'],
                               korean=''.join(part['text']for part in spec['parts']),
                               point=[start_x,y],source_baseline=anchor['origin'][1],size=size,
                               source_size=size,source_font=anchor['font'],font='reviewed mixed styles',
                               parts=[dict(text=v[0]['text'],font=v[2],size=v[3],oblique_angle=v[4],source_style=v[1]['font'])for v in prepared],
                               align=spec.get('align','left'),advance=width,frame=frame))

    target.parent.mkdir(parents=True,exist_ok=True)
    output.save(target,garbage=4,deflate=True)
    output.close()
    output=fitz.open(target)
    final=output[0]
    scale=4
    before=rgb(page,scale)
    after=rgb(final,scale)
    allowed=Image.new('1',(before.shape[1],before.shape[0]))
    draw=ImageDraw.Draw(allowed)
    for r in prose_frames:
        draw.rectangle(tuple(v*scale for v in r),fill=1)
    changed=np.any(before!=after,axis=2)
    outside=changed&~np.asarray(allowed,dtype=bool)
    selected_counter=Counter(glyph_key(c)for c in selected if not c['c'].isspace())
    expected=native_trace(page)-selected_counter
    actual=native_trace(final)
    missing_native=expected-actual
    original_math=(Counter(glyph_key(c)for r in runs.values() if r['font'].startswith('CambriaMath') for c in chars_of(r) if not c['c'].isspace())-selected_counter)
    missing_math=original_math-actual
    remove_counts=selected_counter.copy();expected_records=[]
    for record in trace_records(page):
        key=glyph_key(record)
        if remove_counts[key]:remove_counts[key]-=1
        else:expected_records.append(record)
    native_geometry=compare_native_records(expected_records,trace_records(final))
    math_geometry=compare_native_records([r for r in expected_records if r['font'].startswith('CambriaMath')],trace_records(final))
    # Compare visible formula pixels inside the original small glyph bounds.
    math_mask=Image.new('1',allowed.size)
    math_draw=ImageDraw.Draw(math_mask)
    math_ink_mask=Image.new('1',allowed.size)
    math_ink_draw=ImageDraw.Draw(math_ink_mask)
    for run in runs.values():
        if not run['font'].startswith('CambriaMath'):
            continue
        for c in run['chars']:
            if c['c'].strip() and glyph_key(dict(c,font=run['font'],size=run['size']))not in selected_counter:
                math_draw.rectangle(tuple(v*scale for v in c['bbox']),fill=1)
                char=dict(c,font=run['font'],size=run['size'])
                math_ink_draw.rectangle(tuple(v*scale for v in actual_char_rect(char)),fill=1)
    mathematical_delta=changed&np.asarray(math_mask,dtype=bool)
    native_mask=Image.new('1',allowed.size)
    native_draw=ImageDraw.Draw(native_mask)
    for trace in page.get_texttrace():
        for cp,gid,origin,bbox in trace['chars']:
            key=glyph_key(dict(c=chr(cp),font=trace['font'],size=trace['size'],origin=origin))
            if key in expected:
                char=dict(c=chr(cp),font=trace['font'],size=trace['size'],origin=origin,bbox=bbox)
                native_draw.rectangle(tuple(v*scale for v in actual_char_rect(char)),fill=1)
    original_ink=np.min(before,axis=2)<250
    # A native comma's rectangle can contain an adjacent English r's overhang.
    # The suppression-only control identifies actual native ink separately from
    # removed prose, without excluding any native glyph. Independently require
    # its exact glyph geometry and embedded font programs to match the source,
    # then protect every native-ink pixel from both suppression and Korean.
    control_pixels=rgb(control[0],scale)
    control_ink=np.min(control_pixels,axis=2)<250
    native_region=np.asarray(native_mask,dtype=bool)
    math_region=np.asarray(math_ink_mask,dtype=bool)
    source_control_delta=np.any(before!=control_pixels,axis=2)
    control_final_delta=np.any(control_pixels!=after,axis=2)
    native_ink_delta=changed&native_region&original_ink&control_ink
    mathematical_ink_delta=changed&math_region&original_ink&control_ink
    suppression_native_ink_delta=source_control_delta&native_region&control_ink
    intrusion=control_final_delta&native_region&control_ink
    def font_programs(pg,doc):
        return {(item[3],hashlib.sha256(doc.extract_font(item[0])[3]).hexdigest())for item in pg.get_fonts(full=True)}
    control_geometry=compare_native_records(expected_records,trace_records(control[0]))
    control_geometry_unchanged=not control_geometry['missing']and not control_geometry['extra']
    control_fonts_unchanged=font_programs(page,source)==font_programs(control[0],control)
    final_fonts_unchanged=font_programs(page,source)<=font_programs(final,output)
    target.with_suffix('.control.pdf').write_bytes(native_bytes)
    source_images=Counter((info['digest'].hex(),tuple(round(v,5)for v in info['bbox']))
                          for info in page.get_image_info(hashes=True))
    output_images=Counter((info['digest'].hex(),tuple(round(v,5)for v in info['bbox']))
                          for info in final.get_image_info(hashes=True))
    figure_mask=Image.new('1',allowed.size)
    figure_draw=ImageDraw.Draw(figure_mask)
    for info in page.get_image_info(hashes=True):
        figure_draw.rectangle(tuple(v*scale for v in info['bbox']),fill=1)
    figure_delta=changed&np.asarray(figure_mask,dtype=bool)
    # An image's fractional outer bbox can round into a neighbouring prose
    # descender row. Protect the actual native image ink in the prose-free
    # control, and verify the original image data and placement independently.
    figure_region=np.asarray(figure_mask,dtype=bool)
    figure_ink_delta=figure_delta&original_ink&control_ink
    control_figure_delta=source_control_delta&figure_region&control_ink
    figure_intrusion=control_final_delta&figure_region&control_ink
    report=dict(source=data['source'],source_page=pi+1,output=str(target.relative_to(ROOT)),
                output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                source_sha256=source_sha,
                authoring_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in [plan_path,Path(__file__).resolve(),ROOT/'tools/pdf_original_text_ops.py',*FONT_FILES.values()]},
                removed_prose_glyphs=removed,slots=len(placements),autoshrink=False,
                reflow=False,equation_images=0,render_scale=scale,
                source_embedded_glyph_outline_bounds=True,
                outside_prose_changed_pixels=int(outside.sum()),
                native_glyphs_expected=sum(expected.values()),
                missing_or_moved_native_glyphs=len(native_geometry['missing']),
                strict_native_origin_mismatches_at_5_decimals=sum(missing_native.values()),
                native_font_gid_size_unchanged=not native_geometry['missing'],
                native_origin_tolerance_pt=.0001,
                max_native_origin_delta_pt=native_geometry['max_delta_pt'],
                max_native_origin_delta_float32_ulps=native_geometry['max_delta_float32_ulps'],
                native_origin_rounding_differences=native_geometry['differences'],
                mathematical_glyphs=sum(original_math.values()),
                missing_or_moved_math_glyphs=len(math_geometry['missing']),
                changed_pixels_inside_math_bounds=int(mathematical_delta.sum()),
                original_math_ink_changed_pixels=int(mathematical_ink_delta.sum()),
                original_native_ink_changed_pixels=int(native_ink_delta.sum()),
                source_to_suppression_control_native_ink_changed_pixels=int(suppression_native_ink_delta.sum()),
                korean_intrusion_on_native_ink_pixels=int(intrusion.sum()),
                suppression_control_native_geometry_unchanged=control_geometry_unchanged,
                suppression_control_source_font_programs_unchanged=control_fonts_unchanged,
                original_source_font_programs_preserved_in_final=final_fonts_unchanged,
                changed_pixels_inside_figure_bounds=int(figure_delta.sum()),
                original_figure_ink_changed_pixels=int(figure_ink_delta.sum()),
                source_to_suppression_control_figure_ink_changed_pixels=int(control_figure_delta.sum()),
                korean_intrusion_on_figure_ink_pixels=int(figure_intrusion.sum()),
                native_images_unchanged=source_images==output_images,
                native_vector_drawings_unchanged=[{k:v for k,v in path.items()if k!='seqno'}for path in page.get_drawings()]==[{k:v for k,v in path.items()if k!='seqno'}for path in final.get_drawings()],
                placements=placements,prose_frames=prose_frames)
    target.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    for name,pg in [('source',page),('proof',final)]:
        pg.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(target.parent/f'{target.stem}-{name}.png')
    diff=np.full_like(before,255)
    diff[changed]=[255,0,0]
    Image.fromarray(diff).save(target.parent/f'{target.stem}-difference.png')
    print(json.dumps({k:v for k,v in report.items() if k not in {'placements','prose_frames','native_origin_rounding_differences'}},ensure_ascii=False,indent=2))
    if report['outside_prose_changed_pixels'] or report['missing_or_moved_native_glyphs'] or report['missing_or_moved_math_glyphs'] or report['original_math_ink_changed_pixels'] or report['original_native_ink_changed_pixels'] or report['original_figure_ink_changed_pixels'] or report['source_to_suppression_control_native_ink_changed_pixels'] or report['korean_intrusion_on_native_ink_pixels'] or report['source_to_suppression_control_figure_ink_changed_pixels'] or report['korean_intrusion_on_figure_ink_pixels'] or not control_geometry_unchanged or not control_fonts_unchanged or not final_fonts_unchanged or not report['native_vector_drawings_unchanged'] or not report['native_images_unchanged']:
        raise ValueError('Original-layout proof audit failed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'tmp/original-style-repair/izho-2026-t-page2-slots.json')
    parser.add_argument('--out',type=Path,default=ROOT/'tmp/original-style-repair/IZhO_2026_T_p2_KO_proof.pdf')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.check:raise SystemExit(bool(check_plan(args.plan)))
    build(args.plan,args.out)
