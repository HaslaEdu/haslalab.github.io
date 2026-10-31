"""Independent original-glyph/graphic and actual-ink QA for CPhO2013 pages."""
from pathlib import Path
from collections import Counter
from io import BytesIO
import argparse,hashlib,json,re
import pikepdf
import pymupdf as fitz
import cpho_2013_original_build as b
import cpho_2013_original_graphics as prose_guard
import pdf_original_style_audit as preservation
import pdf_original_graphics_ink as graphics
from pdf_original_text_ops import cmap,widths,source_code_bytes
from cpho_2022_original_qa import extra_glyphs,exact
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from pdf_white_raster_original_style import fill_rectangles
from pdf_hangul_visibility import audit as hangul_audit

def selected(page):
    return [g for s in page['slots']if not s.get('retain_native')for g in s['source_characters']
            if not g['c'].isspace()and g['index']not in s.get('retained_source_indices',[])]

def translation_ink_rects(doc,page,additional):
    """Resolve actual outlines from native-prose and raster-prose subsets.

    Both may use the same font family with distinct retained-GID subsets.
    A missing outline in one subset must not hide ink in the other subset.
    """
    fonts=[];rects=[]
    for record in page.get_fonts(full=True):
        if 'Translation'not in record[4]:continue
        font=TTFont(BytesIO(doc.extract_font(record[0])[3]));names={re.sub('[^a-z0-9]','',n.toUnicode().lower())for n in font['name'].names}
        names.add(re.sub('[^a-z0-9]','',record[3].lower()));fonts.append((names,font))
    for glyph in additional:
        if glyph['c'].isspace():continue
        name=re.sub('[^a-z0-9]','',glyph['font'].lower());bounds=set()
        for names,font in fonts:
            if name not in names or glyph['gid']>=len(font.getGlyphOrder()):continue
            glyphset=font.getGlyphSet();pen=BoundsPen(glyphset);glyphset[font.getGlyphOrder()[glyph['gid']]].draw(pen)
            if pen.bounds is not None:bounds.add(tuple(v/font['head'].unitsPerEm for v in pen.bounds))
        if not bounds:raise ValueError('Additional nonspace glyph has no original replacement outline: '+repr(glyph))
        if len(bounds)!=1:raise ValueError('Replacement subsets disagree about glyph outline')
        x0,y0,x1,y1=next(iter(bounds));dx,dy=glyph['direction'];x,y=glyph['origin'];size=glyph['size']
        pts=[(x+(gx*dx+gy*dy)*size,y+(gx*dy-gy*dx)*size)for gx in(x0,x1)for gy in(y0,y1)]
        rects.append([min(x for x,y in pts)-.25,min(y for x,y in pts)-.25,max(x for x,y in pts)+.25,max(y for x,y in pts)+.25])
    for names,font in fonts:font.close()
    return rects

def original_font_programs(doc,page):
    programs={};visited=set()
    with pikepdf.open(doc.name)as pdf:
        def walk(resources):
            for alias,font in resources.get('/Font',{}).items():
                if 'Translation'in str(alias):continue
                descriptor=font.get('/FontDescriptor')
                if descriptor is None and '/DescendantFonts'in font:descriptor=font['/DescendantFonts'][0].get('/FontDescriptor')
                raw=[]
                if descriptor is not None:
                    for name in ['/FontFile','/FontFile2','/FontFile3']:
                        if name in descriptor:raw.append(hashlib.sha256(descriptor[name].read_bytes()).hexdigest())
                name='|'.join([bytes(font.get('/BaseFont')).decode('latin1'),str(font.get('/Subtype')),str(font.get('/Encoding'))])
                programs.setdefault(name,set()).add(tuple(raw))
            for child in resources.get('/XObject',{}).values():
                if str(child.get('/Subtype'))!='/Form'or child.objgen in visited:continue
                visited.add(child.objgen)
                if '/Resources'in child:walk(child['/Resources'])
        walk(pdf.pages[page.number].Resources)
    return{name:sorted(values)for name,values in programs.items()}

def new_ascii_widths(path,page_index=0):
    checked=0;bad=[]
    with pikepdf.open(path)as pdf:
        page=pdf.pages[page_index]
        for instruction in pikepdf.parse_content_stream(page):
            op=str(instruction.operator);args=instruction.operands
            if op=='Tf':active=args[0]
            if op not in ['Tj','TJ']or'Translation'not in str(active):continue
            font=page.Resources.Font[active];code_bytes=source_code_bytes(font);mapping=cmap(font);values,default=widths(font)
            strings=[args[0]]if op=='Tj'else[x for x in args[0]if isinstance(x,pikepdf.String)]
            for value in strings:
                raw=bytes(value)
                if len(raw)%code_bytes:raise ValueError('Incomplete new text encoding')
                for pos in range(0,len(raw),code_bytes):
                    code=int.from_bytes(raw[pos:pos+code_bytes],'big');char=mapping.get(code);width=values.get(code,default)
                    if char is None:raise ValueError('New translation character has no explicit source mapping')
                    if len(char)==1 and ord(char)<128:
                        checked+=1
                        if width is None or width<=0:bad.append(dict(font=str(active),code=code,text=char,width=width))
    return dict(ascii_codes_checked=checked,nonpositive_or_missing_widths=bad)

def audit(number,lang):
    path=b.BASE/lang/f'page{number:02}.pdf';page=b.data()['pages'][number-1]
    built=json.loads(path.with_suffix('.build.json').read_text('utf8'))
    if built['source_sha256']!=b.source.SOURCE_SHA:raise ValueError('Wrong original source')
    if built.get('authoring_sha256')!=b.authoring_hashes(number,lang):raise ValueError('Proof predates the current manual text or authoring tools')
    picked=selected(page);erased=[g['origin']for g in picked]
    raster=b.raster.plans(number,lang)
    expected=built['placements'][:]
    raster_qa=built.get('raster_overlay')
    if raster_qa is not None:
        if raster_qa['proof_sha256']!=hashlib.sha256(path.read_bytes()).hexdigest():raise ValueError('Raster proof changed after its audit')
        expected.extend(dict(origin=p['point'],size=p['size'],render_mode=0,line_width=0)for p in raster_qa['placements'])
    with fitz.open(b.source.SOURCE)as src,fitz.open(path)as out:
        a=src[number-1];current=out[0];added=extra_glyphs(a,current)
        ink=translation_ink_rects(out,current,added)
        allowed=[[r[0]-.25,r[1]-.25,r[2]+.25,r[3]+.25]for g in picked for r in[g['bbox']]]+ink
        if raster:
            erase_rects,_=fill_rectangles(raster,a.rect)
            allowed.extend(list(r+(-.25,-.25,.25,.25))for r in erase_rects)
        keep=[g for g in preservation.glyphs(a)if not g['c'].isspace()and not any(preservation.close_origin(g['origin'],o)for o in erased)]
        counts=Counter(exact(g)for g in preservation.glyphs(current));missing=[]
        for g in keep:
            if counts[exact(g)]:counts[exact(g)]-=1
            else:missing.append(g)
        # This independently protects every native mathematical font run and
        # the explicitly retained original inline formula parentheses.
        math=[g for g in preservation.glyphs(a)if re.search('Italic|Symbol|Math|Extra',g['font'])]
        math.extend(g for s in page['slots']for g in s['source_characters']if g['index']in s.get('retained_source_indices',[]))
        spec=dict(source_page=number,proof_page=1,erased_glyph_origins=erased,allowed_rects=allowed,
            protected_glyph_origins=[g['origin']for g in math]+[g['origin']for g in page['native_form_glyphs']])
        old_fonts=original_font_programs(src,a);new_fonts=original_font_programs(out,current)
        style=[]
        for g in added:
            if g['c'].isspace():continue
            candidates=[p for p in expected if abs(g['size']-p['size'])<.0001 and abs(g['origin'][1]-p['origin'][1])<.0001 and(g['render_type']in [0,1]if p['render_mode']==2 else g['render_type']==p['render_mode'])]
            if not candidates:style.append(g)
        stroke_failures=[]
        for trace in current.get_texttrace():
            if trace['type']!=1 or not re.search('Noto|Times|Arial',trace['font']):continue
            for cp,gid,origin,box in trace['chars']:
                if chr(cp).isspace():continue
                candidates=[p for p in built['placements']if p['render_mode']==2 and abs(p['size']-trace['size'])<.0001 and abs(p['origin'][1]-origin[1])<.0001]
                if candidates and all(abs(trace['linewidth']-p['line_width'])>1e-6 for p in candidates):
                    stroke_failures.append(dict(text=chr(cp),font=trace['font'],origin=origin,width=trace['linewidth']))
    result=preservation.audit(b.source.SOURCE,path,spec)
    graphic=graphics.audit(b.source.SOURCE,path,number)
    profile=None
    profiles=json.loads((b.AUTHOR/'graphics-profiles.json').read_text('utf8'))
    active=[p for p in profiles if p['source_page']==number]
    if len(active)>1:raise ValueError('Ambiguous document-specific graphics profile')
    if active:
        if active[0]['id']!='2013-p1-selected-wei-prose-only-guard-pixel'or number!=1 or active[0]['source_sha256']!=b.source.SOURCE_SHA:raise ValueError('Unknown explicit graphics profile')
        profile=prose_guard.audit(b.source.SOURCE,path.with_suffix('.control.pdf'),path,picked)
    graphics_pass=(graphic['original_graphics_ink_changed_pixels']==0)
    if raster:
        # A translated bitmap necessarily changes language pixels. The shared
        # scan audit checks actual native ink and its guard outside the explicit
        # old-language/new-blank-background classification, including curves
        # and equations inside explicitly protected portions of those regions.
        graphics_pass=raster_qa is not None and(raster_qa['passed']or raster_qa.get('document_specific_old_prose_guard_witness',{}).get('passed',False))
    if profile is not None:graphics_pass=profile['passed']
    result.update(source_page=number,language=lang,pdf=str(path.relative_to(b.ROOT)).replace('\\','/'),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bit_exact_native_nonspace_glyphs_checked=len(keep),
        bit_exact_native_nonspace_glyphs_changed=missing,original_font_programs_identical=old_fonts==new_fonts,
        original_font_program_sha256=old_fonts,original_graphics=graphic,translation_style_violations=style,
        translation_stroke_width_violations=stroke_failures,new_ascii_widths=new_ascii_widths(path),
        source_selection_sha256=hashlib.sha256(json.dumps(erased).encode()).hexdigest(),authoring_sha256=built['authoring_sha256'])
    if raster_qa is not None:result['reviewed_raster_language_audit']=raster_qa
    if profile is not None:result['reviewed_original_prose_guard_profile']=profile
    if lang=='ko':result['hangul_visibility']=hangul_audit(path)
    with pikepdf.open(b.source.SOURCE)as src,pikepdf.open(path)as dst:
        result['original_page_group_unchanged']=str(src.pages[number-1].obj.get('/Group'))==str(dst.pages[0].obj.get('/Group'))
    result['passed']=not(any(result.get(k)for k in ['native_glyphs_changed','protected_glyphs_selected_for_erasure','changed_pixels_outside_prose',
        'changed_pixels_in_native_glyph_neighborhood','bit_exact_native_nonspace_glyphs_changed','translation_style_violations','translation_stroke_width_violations'])
        or not result['original_font_programs_identical']or not result['original_page_group_unchanged']
        or not graphics_pass or not graphic['original_image_and_smask_programs_and_positions_identical']
        or result['new_ascii_widths']['nonpositive_or_missing_widths']or result.get('hangul_visibility',{}).get('flagged_components',0))
    result['preservation_passed']=result['passed']
    result['translation_scope_complete']=built['raster_language_status']!='pending'
    result['passed']&=result['translation_scope_complete']
    path.with_suffix('.qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    summary={k:result[k]for k in ['source_page','language','passed','native_glyphs_checked','bit_exact_native_nonspace_glyphs_checked',
        'changed_pixels_outside_prose','changed_pixels_in_native_glyph_neighborhood','original_font_programs_identical','original_page_group_unchanged']}
    summary.update(changed_native=len(result['native_glyphs_changed']),exact_native_changed=len(missing),graphic_pixels=graphic['original_graphics_ink_changed_pixels'])
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pages',nargs='+',required=True,type=int);p.add_argument('--lang',choices=['ko','en']);a=p.parse_args();failed=False
    for number in a.pages:
        for lang in [a.lang]if a.lang else['ko','en']:failed|=not audit(number,lang)['passed']
    raise SystemExit(failed)
