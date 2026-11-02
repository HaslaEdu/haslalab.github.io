"""Natural fixed-size Korean lines with Batang Hangul and native PDF mathematics.

Only eligible regular serif Hangul glyphs are replaced. Every ASCII, Latin,
mathematical, bold, sans and italic glyph retains its original encoded bytes,
font program, point size, painting style and baseline; it may move horizontally.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import hashlib,json,re
from collections import Counter
import pymupdf as fitz
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from izho_natural_spacing import baseline_lines,boundary_gap,records,visible,inject_atomic_tokens
from pdf_native_inline_reposition import reposition_inline

BATANG=Path('C:/Windows/Fonts/batang.ttc')

def _plain(text):return ''.join(c for c in text if not c.isspace())
def _hangul(c):return len(c)==1 and 0xac00<=ord(c)<=0xd7a3
def _key(r):return(r['c'],r['font'],round(r['size'],6),round(r['origin'][0],4),round(r['origin'][1],4))
def _glyph(r):return{k:r[k]for k in('c','font','size','origin')}

def normalize_placements(page,placements):
    """Accept IZhO point/width and CPhO origin/text placement journals."""
    rows=visible(records(page));out=[]
    for original in placements or[]:
        p=dict(original);p['point']=p.get('point',p.get('origin'))
        p['text']=p.get('korean',p.get('text',''))
        if p.get('width')is None:p['width']=p.get('advance')
        if p.get('width')is None and p.get('point')and p['text'].strip():
            x,y=p['point'];expected=_plain(p['text'])
            candidates=sorted([r for r in rows if abs(r['origin'][1]-y)<.02 and r['origin'][0]>=x-.03],key=lambda r:r['origin'][0])
            if candidates and candidates[0]['origin'][0]-x<max(1,p.get('size',12)*.6)and ''.join(r['c']for r in candidates[:len(expected)])==expected:
                p['width']=max(r['bbox'][2]for r in candidates[:len(expected)])-x
        out.append(p)
    return out

def _italic(row,p):
    if p is None:return False
    parts=p.get('parts',[])
    for i,part in enumerate(parts):
        point=part.get('point');end=parts[i+1].get('point',[float('inf')])[0]if i+1<len(parts)else p['point'][0]+p['width']+.1
        if point and point[0]-.03<=row['origin'][0]<end-.01:
            return bool(part.get('oblique_angle',0)or re.search('Ital|Oblique',part.get('source_font','')))
    return bool(p.get('italic')or p.get('target_oblique_angle')or re.search('Ital|Oblique',p.get('source_font','')))

def _replace(row,p):
    return _hangul(row['c'])and 'NotoSerif'in row['font']and 'Regular'in row['font']and not _italic(row,p)

def _style(row,p):
    mode=int(row.get('paint',0));size=row['size']
    line_width=(p or{}).get('border_width',row.get('linewidth'))
    color=(p or{}).get('color',row.get('color',(0,0,0)))
    if isinstance(color,int):color=tuple(((color>>n)&255)/255 for n in(16,8,0))
    if color is None:color=(0,0,0)
    if len(color)==1:color=tuple(color)*3
    stroke=row.get('stroke_color')or color
    if len(stroke)==1:stroke=tuple(stroke)*3
    if mode not in(0,2):raise ValueError('New Batang requires reviewed fill or fill/stroke painting')
    if mode==2 and(not line_width or line_width<=0):raise ValueError('Tr2 Batang requires actual positive PDF stroke width')
    return dict(render_mode=mode,color=list(color),stroke_color=list(stroke),line_width=line_width if mode==2 else 0,
                fill_opacity=row.get('opacity',1),stroke_opacity=row.get('stroke_opacity',1)or 1,size=size,overlay=(p or{}).get('overlay',True))

def _units(item,placements,metric):
    p=placements[item['placement']]if 'placement'in item else None
    rows=sorted(visible(item['glyphs']),key=lambda r:(r['origin'][0],r['origin'][1]))
    if item['kind']=='native':
        return[dict(kind='native',glyphs=item['glyphs'],width=item['x1']-item['x0'],old_x=item['x0'],shift_kwargs=item.get('shift_kwargs',{}))]
    text=(p or{}).get('text',item['text'])
    if _plain(text)!=''.join(r['c']for r in rows):
        text=item['text']
    if _plain(text)!=''.join(r['c']for r in rows):
        raise ValueError(('Authored prose text differs from visible glyph sequence',text,''.join(r['c']for r in rows)))
    # Edge spaces are represented once by boundary_gap. Keeping authored
    # trailing/leading blanks here would produce a doubled word space.
    text=text.strip()
    units=[];ri=0
    for c in text:
        if c.isspace():
            if not units or units[-1]['kind']!='space':units.append(dict(kind='space',width=item['size']/4))
            continue
        row=rows[ri];ri+=1;replace=_replace(row,p)
        signature=(replace,row['font'],row['size'],row.get('paint',0),tuple(row['origin'][1:]),str(row.get('color')),row.get('linewidth'))
        if units and units[-1]['kind']!='space'and units[-1]['signature']==signature:
            unit=units[-1];unit['glyphs'].append(row);unit['text']+=c
            if replace:unit['width']=metric.text_length(unit['text'],fontsize=row['size'])
            else:unit['width']=max(r['bbox'][2]for r in unit['glyphs'])-unit['old_x']
        else:
            units.append(dict(kind='batang'if replace else'native',signature=signature,text=c,glyphs=[row],
                              old_x=row['origin'][0],width=metric.text_length(c,fontsize=row['size'])if replace else row['bbox'][2]-row['origin'][0],
                              style=_style(row,p)if replace else None))
    return units

def compose_page(source,page_number,*,allowed_line_rects,prose_placements=None,excluded_figure_rects=None,
                 centered_lines=None,right_aligned_lines=None,font_path=BATANG,native_atomic_tokens=None,
                 native_move_options=None,native_control_output=None,prose_trace_predicate=None,baseline_tolerance_pt=.12,
                 font_resource_name='KO_Natural_Batang',stationary_native_glyphs=None,include_image_only_native_math=False):
    """Return single-page PDF bytes and review report; no files are overwritten.

    Rectangles are separate reviewed lines/columns. Header/folio columns must
    be separate rectangles. Centers/right edges use source content geometry.
    ``native_atomic_tokens`` is reserved for the shared Form/clip token helper.
    """
    doc=fitz.open(source);page=doc[page_number-1];placements=normalize_placements(page,prose_placements)
    font=TTFont(font_path,fontNumber=0 if str(font_path).lower().endswith('.ttc')else-1,recalcTimestamp=False)
    font.recalcTimestamp=False
    initial=BytesIO();font.save(initial);metric=fitz.Font(fontbuffer=initial.getvalue())
    from pdf_original_text_ops import glyph_key
    if any(_hangul(g['c'])for g in stationary_native_glyphs or[]):raise ValueError('A stationary native-math journal must not exclude Korean prose')
    locked={glyph_key(g)for g in stationary_native_glyphs or[]}
    if locked-{glyph_key(g)for g in records(page)}:raise ValueError('A stationary native glyph is absent from the exact input PDF')
    shifts=[];erase=[];insertions=[];journals=[];claimed=set()
    for rect in allowed_line_rects:
        lines=baseline_lines(page,allowed_line_rects=[rect],excluded_figure_rects=excluded_figure_rects,prose_placements=placements,prose_trace_predicate=prose_trace_predicate,baseline_tolerance_pt=baseline_tolerance_pt,stationary_native_glyphs=stationary_native_glyphs)
        if native_atomic_tokens is not False:
            from izho_native_atomic_tokens import atomic_tokens
            atom_options={'include_image_only':True}if include_image_only_native_math else{}
            atoms=atomic_tokens(source,page_number,rect,[dict(baseline=line['baseline'],size=max(t['size']for t in line['tokens']))for line in lines],excluded_figure_rects,**atom_options)
            atoms=[a for a in atoms if not any(glyph_key(g)in locked for g in a['glyphs'])]
            if isinstance(native_atomic_tokens,list):
                from pdf_original_text_ops import glyph_key
                explicit=[]
                for item in native_atomic_tokens:
                    if not(rect[0]-1<=item['x0']and item['x1']<=rect[2]+1 and rect[1]<=item['y']<=rect[3]):continue
                    box=fitz.Rect(item.get('bbox',[item['x0'],item['y']-item['size'],item['x1'],item['y']+item['size']/3]))
                    if any(box.intersects(fitz.Rect(r))for r in excluded_figure_rects or[]):continue
                    if any(glyph_key(g)in locked for g in item['glyphs']):raise ValueError('An explicitly moving atom includes stationary native mathematics')
                    explicit.append(item)
                keys={glyph_key(r)for item in explicit for r in item['glyphs']}
                atoms=[a for a in atoms if not any(glyph_key(r)in keys for r in a['glyphs'])]+explicit
            lines=inject_atomic_tokens(lines,atoms)
        for line in lines:
            tokens=line['tokens'];cursor=tokens[0]['x0'];local=[];gaps=[]
            for i,item in enumerate(tokens):
                keys={_key(r)for r in visible(item['glyphs'])}
                if keys&claimed:raise ValueError(('Overlapping reviewed rectangles claim a visible glyph twice',rect,line['baseline'],item['text'],list(keys&claimed)[:8]))
                claimed.update(keys)
                if i:
                    gap=boundary_gap(tokens[i-1],item);cursor+=gap
                    gaps.append(dict(left=tokens[i-1]['text'],right=item['text'],old_gap=item['x0']-tokens[i-1]['x1'],new_gap=gap))
                for unit in _units(item,placements,metric):
                    if unit['kind']!='space':local.append(dict(unit,x=cursor))
                    cursor+=unit['width']
            start=tokens[0]['x0'];adjust=0
            centers=[v['center']for v in centered_lines or[]if abs(v['baseline']-line['baseline'])<.02 and ('rect'not in v or v['rect']==rect)]
            rights=[v['right']for v in right_aligned_lines or[]if abs(v['baseline']-line['baseline'])<.02 and ('rect'not in v or v['rect']==rect)]
            if len(centers)+len(rights)>1:raise ValueError('Ambiguous line alignment')
            if centers:adjust=centers[0]-(start+cursor)/2
            if rights:adjust=rights[0]-cursor
            if cursor+adjust>rect[2]+.1 or start+adjust<rect[0]-.1:raise ValueError(('Natural fixed-size line overflows reviewed rectangle',line['baseline'],start+adjust,cursor+adjust,rect))
            for unit in local:
                x=unit['x']+adjust
                if unit['kind']=='batang':
                    erase.extend(_glyph(r)for r in unit['glyphs'])
                    insertions.append(dict(text=unit['text'],point=[x,unit['glyphs'][0]['origin'][1]],style=unit['style']))
                else:
                    dx=x-unit['old_x']
                    # An original float32 coordinate and the same recomputed
                    # center can differ by one ULP. Keep that native text at
                    # its original position instead of issuing a fake motion.
                    if abs(dx)>1e-4:shifts.append(dict(glyphs=[_glyph(r)for r in unit['glyphs']if r['c'].strip()],dx=dx,**unit.get('shift_kwargs',{})))
            journals.append(dict(baseline=line['baseline'],rect=rect,old_right=max(t['x1']for t in tokens),new_right=cursor+adjust,gaps=gaps,center=centers[0]if centers else None))
    raw,move_qa=reposition_inline(source,page_number,erased_glyphs=erase,shifts=shifts,**(native_move_options or{}))
    if native_control_output is not None:
        control_path=Path(native_control_output)
        if control_path.resolve()==Path(source).resolve():raise ValueError('Native control must not overwrite its source')
        control_path.parent.mkdir(parents=True,exist_ok=True);control_path.write_bytes(raw)
    options=subset.Options();options.retain_gids=True;options.name_IDs=['*'];worker=subset.Subsetter(options=options)
    worker.populate(text=''.join(s['text']for s in insertions));worker.subset(font);buffer=BytesIO();font.save(buffer)
    subset_bytes=buffer.getvalue();cmap=font.getBestCmap()or{};glyphset=font.getGlyphSet();checked={}
    for c in set(''.join(s['text']for s in insertions)):
        if c.isspace():continue
        name=cmap.get(ord(c))
        if not name:raise ValueError(('Missing Batang Hangul mapping',c))
        pen=BoundsPen(glyphset);glyphset[name].draw(pen)
        if pen.bounds is None:raise ValueError(('Empty Batang Hangul outline',c,name))
        checked[c]=font.getGlyphID(name)
    out=fitz.open(stream=raw,filetype='pdf');p=out[0]
    if insertions:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',font_resource_name):raise ValueError('A new Batang font resource needs an ASCII identifier')
        if font_resource_name in{f[4]for f in p.get_fonts()}:raise ValueError('Batang font resource already exists; use a unique font_resource_name for a second composition')
        p.insert_font(fontname=font_resource_name,fontbuffer=subset_bytes)
    for entry in insertions:
        style=entry['style'];size=style['size'];mode=style['render_mode']
        x,y=entry['point']
        if any(c.isspace()and c!=' 'for c in entry['text']):raise ValueError('A fixed-baseline Batang run supports ordinary word spaces only')
        for fragment in re.split(r'( +)',entry['text']):
            if not fragment:continue
            if fragment.isspace():x+=len(fragment)*size/4;continue
            p.insert_text((x,y),fragment,fontname=font_resource_name,fontsize=size,
                color=style['stroke_color']if mode==2 else style['color'],fill=style['color'],render_mode=mode,
                border_width=style['line_width']/size if mode==2 else 1,miter_limit=10,
                fill_opacity=style['fill_opacity'],stroke_opacity=style['stroke_opacity'],overlay=style.get('overlay',True))
            x+=metric.text_length(fragment,fontsize=size)
    result=out.tobytes(garbage=0,deflate=False);out.close()
    control=fitz.open(stream=raw,filetype='pdf');final=fitz.open(stream=result,filetype='pdf')
    def identity(r):
        return(r['c'],r['gid'],r['font'],r['size'],tuple(r['origin']),r['paint'],str(r.get('color')),r.get('linewidth'),str(r.get('stroke_color')))
    before=Counter(identity(r)for r in visible(records(control[0])))
    after=Counter(identity(r)for r in visible(records(final[0])))
    if before-after:raise ValueError('Adding Batang changed retained native text/font/size/painting/geometry')
    new_rows=after-before
    expected_new=sum(len(_plain(s['text']))for s in insertions)
    if sum(new_rows.values())!=expected_new:raise ValueError(('New Batang glyph count mismatch',sum(new_rows.values()),expected_new))
    new_faces={row[2]for row in new_rows}
    if new_faces-{'Batang'}:raise ValueError(('Wrong new Hangul font',new_faces))
    if any(not _hangul(row[0])for row in new_rows):raise ValueError('Font replacement changed a non-Hangul character')
    if any(row[1]!=checked[row[0]]for row in new_rows):raise ValueError('Final Batang glyph ID differs from checked embedded outline')
    control.close();final.close();doc.close()
    report=dict(source=str(source),source_page=page_number,source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        output_sha256=hashlib.sha256(result).hexdigest(),font='Windows Batang TTC face0; subset only'if insertions else'Source fonts retained; no Hangul font resource added',font_sha256=hashlib.sha256(Path(font_path).read_bytes()).hexdigest(),
        font_resource_name=font_resource_name if insertions else None,
        replaced_hangul_glyphs=len(erase),new_batang_runs=len(insertions),new_batang_placements=insertions,
        native_shifts=shifts,erased_hangul_glyphs=erase,
        stationary_native_glyphs=stationary_native_glyphs or[],
        stationary_native_glyph_keys_matched=len(locked),
        native_move_qa=move_qa,lines=journals,no_font_scaling=True,original_native_ascii_latin_math_programs_retained=True,
        native_control_sha256=hashlib.sha256(raw).hexdigest(),native_control_output=str(native_control_output)if native_control_output is not None else None,
        retained_native_glyphs_after_new_text_insertion=sum(before.values()),retained_native_style_or_geometry_mismatches_after_insertion=0,
        new_batang_hangul_glyphs_checked=expected_new,new_non_hangul_font_replacements=0,
        new_batang_unique_actual_outlines_checked=len(checked),empty_new_batang_outlines=0,
        word_spacing='One quarter of the original prose point size; no justification tracking',visual_review_required=True)
    return result,report
