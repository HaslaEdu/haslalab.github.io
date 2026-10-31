"""Independent original-glyph/graphic and actual-ink QA for CPhO2005 pages."""
from pathlib import Path
from collections import Counter
from io import BytesIO
import argparse,hashlib,json,re
from fontTools.ttLib import TTFont
import pikepdf
import pymupdf as fitz
import cpho_2005_original_build as b
import pdf_original_style_audit as preservation
import pdf_original_graphics_ink as graphics
from pdf_original_text_ops import cmap,widths,source_code_bytes
from cpho_2022_original_qa import extra_glyphs,translation_ink_rects,original_font_programs,exact
from pdf_hangul_visibility import audit as hangul_audit
from izho_new_prose_outline_qa import trace_font_resources,outline_results

def selected(page):
    return [g for s in page['slots']if not s.get('retain_native')for g in s['source_characters']
            if not g['c'].isspace()and g['index']not in s.get('retained_source_indices',[])]

def new_ascii_widths(path):
    checked=0;bad=[]
    with pikepdf.open(path)as pdf:
        page=pdf.pages[0]
        for instruction in pikepdf.parse_content_stream(page):
            op=str(instruction.operator);args=instruction.operands
            if op=='Tf':active=args[0]
            if op not in ['Tj','TJ']or not str(active).startswith('/Translation'):continue
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


def new_outline_ink(path):
    """Check actual final GIDs; positive cmap/Widths alone cannot prove ink."""
    with pikepdf.open(path)as pdf,fitz.open(path)as doc:
        aliases=[]
        # MuPDF reports the embedded Times PostScript name while its PDF
        # BaseFont can be the installed Windows full name. Normalise only
        # this read-only analysis copy using the actual program's name table;
        # neither the delivered PDF nor any font program is rewritten.
        for alias,font in pdf.pages[0].Resources.Font.items():
            if not str(alias).startswith('/Translation'):continue
            descriptor=font.get('/DescendantFonts',[font])[0]['/FontDescriptor']
            field=next(k for k in ['/FontFile2','/FontFile3']if k in descriptor)
            with TTFont(BytesIO(descriptor[field].read_bytes()))as program:
                name=program['name'].getDebugName(6)
            if name not in{t['font']for t in doc[0].get_texttrace()}:raise ValueError('New actual font PostScript name is not a rendered trace face')
            if str(font['/BaseFont'])!='/'+name:
                aliases.append(dict(alias=str(alias),pdf_basefont=str(font['/BaseFont']),actual_program_postscript_name=name))
                font['/BaseFont']=pikepdf.Name('/'+name)
        mapped,programs=trace_font_resources(pdf,doc[0]);cache={};checked=[]
        added=[g for g in mapped if g['font_alias'].startswith('/Translation')and not g['c'].isspace()and g['gid']>=0]
        for digest in sorted({g['font_program_sha256']for g in added}):
            if digest is None:raise ValueError('New translation face must have an actual embedded font program')
            checked.extend(outline_results(dict(programs[digest],sha=digest),[g for g in added if g['font_program_sha256']==digest],cache))
    return dict(new_nonspace_gids_checked=len(checked),new_ascii_gids_checked=sum(ord(g['c'])<128 for g in checked),
        analysis_font_name_aliases=aliases,delivered_pdf_modified=False,
        empty_outline_count=sum(g['outline_empty']for g in checked),empty_outlines=[g for g in checked if g['outline_empty']])

def audit(number,lang):
    path=b.BASE/lang/f'page{number:02}.pdf';page=b.data()['pages'][number-1]
    built=json.loads(path.with_suffix('.build.json').read_text('utf8'))
    if built['source_sha256']!=b.source.SOURCE_SHA:raise ValueError('Wrong original source')
    if built.get('authoring_sha256')!=b.authoring_hashes(number,lang):raise ValueError('Proof predates the current manual text or authoring tools')
    picked=selected(page);erased=[g['origin']for g in picked]
    with fitz.open(b.source.SOURCE)as src,fitz.open(path)as out:
        a=src[number-1];current=out[0];added=extra_glyphs(a,current)
        ink=translation_ink_rects(out,current,added)
        allowed=[[r[0]-.25,r[1]-.25,r[2]+.25,r[3]+.25]for g in picked for r in[g['bbox']]]+ink
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
            candidates=[p for p in built['placements']if abs(g['size']-p['size'])<.0001 and abs(g['origin'][1]-p['origin'][1])<.0001 and(g['render_type']in [0,1]if p['render_mode']==2 else g['render_type']==p['render_mode'])]
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
    graphics_pass=(graphic['original_graphics_ink_changed_pixels']==0)
    result.update(source_page=number,language=lang,pdf=str(path.relative_to(b.ROOT)if path.is_relative_to(b.ROOT)else path).replace('\\','/'),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bit_exact_native_nonspace_glyphs_checked=len(keep),
        bit_exact_native_nonspace_glyphs_changed=missing,original_font_programs_identical=old_fonts==new_fonts,
        original_font_program_sha256=old_fonts,original_graphics=graphic,translation_style_violations=style,
        translation_stroke_width_violations=stroke_failures,new_ascii_widths=new_ascii_widths(path),new_outline_ink=new_outline_ink(path),
        source_selection_sha256=hashlib.sha256(json.dumps(erased).encode()).hexdigest(),authoring_sha256=built['authoring_sha256'])
    if lang=='ko':result['hangul_visibility']=hangul_audit(path)
    with pikepdf.open(b.source.SOURCE)as src,pikepdf.open(path)as dst:
        result['original_page_group_unchanged']=str(src.pages[number-1].obj.get('/Group'))==str(dst.pages[0].obj.get('/Group'))
    result['passed']=not(any(result.get(k)for k in ['native_glyphs_changed','protected_glyphs_selected_for_erasure','changed_pixels_outside_prose',
        'changed_pixels_in_native_glyph_neighborhood','bit_exact_native_nonspace_glyphs_changed','translation_style_violations','translation_stroke_width_violations'])
        or not result['original_font_programs_identical']or not result['original_page_group_unchanged']
        or not graphics_pass or not graphic['original_image_and_smask_programs_and_positions_identical']
        or result['new_ascii_widths']['nonpositive_or_missing_widths']or result['new_outline_ink']['empty_outline_count']
        or result.get('hangul_visibility',{}).get('flagged_components',0))
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
