"""Restore actual original numeric prose faces in early CPhO headings.

Only header/title/footer prose digits are reinserted. Each actual source digit
must have the same real cmap/GID/outline/advance; source math is not selected.
Original inter-digit spacing, size, baseline offset and paint are retained.
"""
from pathlib import Path
from io import BytesIO
import hashlib,json,re
from collections import defaultdict
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.boundsPen import BoundsPen
import pikepdf,pymupdf as fitz
from pdf_native_inline_reposition import _traces,reposition_inline
from pdf_original_text_ops import family_name,glyph_key
from pdf_original_style_fonts import subset_font


def _colour(value):
    return tuple(value)*3 if len(value)==1 else tuple(value)


def source_font(doc,page,glyph,folder):
    candidates=[]
    for record in page.get_fonts(full=True):
        if record[6]!=0 or family_name(record[3])!=glyph['font']:continue
        raw=doc.extract_font(record[0])[3]
        with TTFont(BytesIO(raw),recalcTimestamp=False)as font:
            cmap=font.getBestCmap();name=cmap.get(ord(glyph['c']))
            if name is None or font.getGlyphID(name)!=glyph['trace_gid']:continue
            gs=font.getGlyphSet();p=BoundsPen(gs);gs[name].draw(p)
            if p.bounds is None or font['hmtx'][name][0]<=0:continue
            pen=DecomposingRecordingPen(gs);gs[name].draw(pen)
            signature=(font['head'].unitsPerEm,font['hmtx'][name],repr(pen.value))
            candidates.append((raw,signature,record,font['name'].getDebugName(5)))
    if not candidates:raise ValueError('No actual source numeric cmap/GID witness')
    if len({str(r[1])for r in candidates})!=1:raise ValueError('Ambiguous actual source numeric font program')
    raw,signature,record,version=candidates[0];digest=hashlib.sha256(raw).hexdigest()
    folder.mkdir(parents=True,exist_ok=True);path=folder/(glyph['font']+'-'+digest[:16]+'.ttf')
    if not path.exists():path.write_bytes(raw)
    metric=fitz.Font(fontbuffer=raw)
    if abs(metric.glyph_advance(ord(glyph['c']))*glyph['size']-(glyph['bbox'][2]-glyph['origin'][0]))>.001:
        raise ValueError('Source heading digit has unsupported horizontal scaling')
    return path,dict(source_alias=record[4],source_program_sha256=digest,source_version=version,
        original_gid=glyph['trace_gid'],actual_cmap_gid=glyph['trace_gid'],
        original_advance=signature[1],original_outline_nonempty=True)


def page(source_original,baseline,number,slots,placements,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with fitz.open(source_original)as src,fitz.open(baseline)as current:
        original=_traces(src[number-1]);rows=[g for g in _traces(current[number-1])if g['c'].strip()and g['trace_gid']>=0]
        erase=[];insertions=[];reports=[]
        source_slots={s['id']:s for s in slots}
        for p in placements:
            s=source_slots.get(p['id'])
            if not s or s.get('original_paragraph_role')not in('header','title','footer'):continue
            chars=[c for c in s['source_characters']if c['c'].isascii()and c['c'].isdigit()]
            if not chars:continue
            digits=''.join(c['c']for c in chars)
            if ''.join(c for c in p['text']if c.isascii()and c.isdigit())!=digits:
                raise ValueError('Numeric heading/footer content differs from original')
            x,y=p['point'];visible=sorted([g for g in rows if abs(g['origin'][1]-y)<.03 and x-.03<=g['origin'][0]<x+p['width']+.15],key=lambda g:g['origin'][0])
            if ''.join(g['c']for g in visible)!=''.join(p['text'].split()):raise ValueError('Numeric heading prose association changed')
            target=[g for g in visible if g['c'].isascii()and g['c'].isdigit()]
            original_digits=[]
            for c in chars:
                found=[g for g in original if g['c']==c['c']and g['font']==family_name(c['font'])
                    and abs(g['size']-c['size'])<.001 and max(abs(a-b)for a,b in zip(g['origin'],c['origin']))<.001]
                if len(found)!=1:raise ValueError('Source numeric trace must be unique')
                original_digits.append(found[0])
            # Run boundaries are taken from the source prose, so e.g. the two
            # footer values are separate while the digits in30 retain spacing.
            spans=list(re.finditer('[0-9]+',s['source']));cursor=0
            for span in spans:
                length=len(span[0]);old_run=original_digits[cursor:cursor+length];new_run=target[cursor:cursor+length];cursor+=length
                left=new_run[0]['origin'][0];source_left=old_run[0]['origin'][0]
                for old,new in zip(old_run,new_run):
                    if old['direction']!=(1.,0.)and tuple(old['direction'])!=(1.,0.):raise ValueError('Only horizontal prose number restoration is supported')
                    if old.get('opacity',1)!=1:raise ValueError('Unexpected transparent original prose number')
                    if old['render_mode']not in(0,2):raise ValueError('Unsupported original prose digit paint')
                    donor,witness=source_font(src,src[number-1],old,folder/'source-fonts')
                    font=subset_font(donor,old['c'],folder/'font-subsets')
                    point=[left+old['origin'][0]-source_left,new['origin'][1]+old['origin'][1]-s['origin'][1]]
                    erase.append({k:new[k]for k in('c','font','size','origin')})
                    insertions.append(dict(text=old['c'],point=point,font=str(font),size=old['size'],
                        paint=old['render_mode'],linewidth=old.get('linewidth')or 0,
                        fill=_colour(old['color']),stroke=_colour(old.get('stroke_color')or old['color']),
                        miter=s.get('miter_limit',10)))
                    reports.append(dict(slot=p['id'],digit=old['c'],original_font=old['font'],old_translation_font=new['font'],
                        original_size=old['size'],translation_point=point,source_origin=old['origin'],
                        original_render_mode=old['render_mode'],original_linewidth=old.get('linewidth'),**witness))
            if cursor!=len(target):raise ValueError('Source numeric runs do not cover translated numeric prose')
    raw,qa=reposition_inline(baseline,number,erased_glyphs=erase)
    doc=fitz.open(stream=raw,filetype='pdf');p=doc[0]
    for i,item in enumerate(insertions):
        p.insert_text(item['point'],item['text'],fontfile=item['font'],fontname='OriginalNumericProse'+str(i),
            fontsize=item['size'],color=item['stroke'],fill=item['fill'],render_mode=item['paint'],
            border_width=item['linewidth']/item['size']if item['paint']==2 else .05,miter_limit=item['miter'])
    out=folder/f'page{number:02}.pdf';doc.save(out,garbage=0,deflate=False);doc.close()
    with fitz.open(out)as proof:
        final=_traces(proof[0])
        for r in reports:
            found=[g for g in final if g['c']==r['digit']and g['font']==r['original_font']and g['trace_gid']==r['original_gid']
                and abs(g['size']-r['original_size'])<.0001 and max(abs(a-b)for a,b in zip(g['origin'],r['translation_point']))<.001]
            if len(found)!=1:raise ValueError('Actual source heading digit font/GID/size/position was not restored')
    report=dict(source=str(source_original),baseline=str(baseline),source_page=number,output=str(out),
        output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),numeric_prose_only=True,
        builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        immutable_baseline_sha256=hashlib.sha256(Path(baseline).read_bytes()).hexdigest(),
        original_source_sha256=hashlib.sha256(Path(source_original).read_bytes()).hexdigest(),
        source_original_font_programs_not_modified=True,physics_or_equation_digits_retyped=False,
        digits=reports,erasure_qa=qa,passed=True)
    out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    return out,report
