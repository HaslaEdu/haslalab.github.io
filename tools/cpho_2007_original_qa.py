"""Audit the native-layout 2007 editions against their original PDF."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re
from io import BytesIO
import pymupdf as fitz
from PIL import Image,ImageDraw
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import cpho_2007_original_build as b
import pdf_original_style_audit as preservation
from cpho_original_latin_fonts import BUILD_ROOT as EN_REPAIR_ROOT
import pdf_hangul_visibility as visibility


def sha(value):return hashlib.sha256(value).hexdigest()


def exact_glyph_key(g):
    return(g['c'],g['font'],g['gid'],g['size'],tuple(g['origin']),tuple(g['color']),g['render_type'])


def image_keys(page):
    return Counter((tuple(item['bbox']),item['width'],item['height'],item['bpc'],item['colorspace'],item['digest'].hex())
                   for item in page.get_image_info(hashes=True))


def font_keys(doc,page):
    result={}
    for record in page.get_fonts(full=True):
        name=record[3]
        if name.startswith('Translation'):continue
        data=doc.extract_font(record[0])[3]
        result[name]=sha(data)
    return result


def translated_ink_rects(doc,page,original_page):
    """Actual outlines, including Times f/j overhang and descenders."""
    old={t['font']for t in original_page.get_texttrace()};fonts=[];rects=[]
    for record in page.get_fonts(full=True):
        if not record[4].startswith('Translation'):continue
        font=TTFont(BytesIO(doc.extract_font(record[0])[3]))
        names={re.sub('[^a-z0-9]','',entry.toUnicode().lower())for entry in font['name'].names}
        names.add(re.sub('[^a-z0-9]','',record[3].lower()));fonts.append((names,font))
    for trace in page.get_texttrace():
        if trace['font']in old:continue
        key=re.sub('[^a-z0-9]','',trace['font'].lower())
        font=next(font for names,font in fonts if key in names);glyphs=font.getGlyphSet()
        factor=trace['size']/font['head'].unitsPerEm
        for cp,gid,origin,box in trace['chars']:
            pen=BoundsPen(glyphs);glyphs[font.getGlyphOrder()[gid]].draw(pen)
            if pen.bounds is None:continue
            x0,y0,x1,y1=pen.bounds;x,y=origin
            # One raster pixel covers outline antialiasing at audit scale.
            rects.append([x+x0*factor-.25,y-y1*factor-.25,x+x1*factor+.25,y-y0*factor+.25])
    return rects


def translation_style_checks(original,proof,plan,fit_rows):
    """Compare actual added glyph metadata with the original prose slots."""
    before=Counter(exact_glyph_key(g)for g in preservation.glyphs(original));added=[]
    for glyph in preservation.glyphs(proof):
        token=exact_glyph_key(glyph)
        if before[token]:before[token]-=1
        elif not glyph['c'].isspace():added.append(glyph)
    expected=[];fit={r['id']:r for r in fit_rows}
    for slot in plan['slots']:
        if slot.get('retain_native'):continue
        # A Chinese figure-reference group can contain both original black
        # and magenta words; translation preserves that same source palette.
        colours={slot['color'],*[c['color']for c in slot['source_characters']]}
        placed=fit[slot['id']]
        if not placed['text']:continue
        expected.append(dict(id=slot['id'],size=slot['size'],baseline=slot['origin'][1],left=placed['origin'][0],right=placed['origin'][0]+placed['width'],
                             render_mode=slot.get('render_mode',0),colours=colours))
    failures=[];max_size=0;max_baseline=0
    for glyph in added:
        frames=[e for e in expected if e['left']-.08<=glyph['origin'][0]<=e['right']+.08 and abs(e['baseline']-glyph['origin'][1])<.0001 and abs(e['size']-glyph['size'])<.0001]
        closest=min(frames or expected,key=lambda e:abs(e['baseline']-glyph['origin'][1])+10*abs(e['size']-glyph['size']))
        dy=abs(closest['baseline']-glyph['origin'][1]);ds=abs(closest['size']-glyph['size'])
        max_size=max(max_size,ds);max_baseline=max(max_baseline,dy)
        modes={0,1}if closest['render_mode']==2 else{closest['render_mode']}
        colours=[tuple(((colour>>n)&255)/255 for n in [16,8,0])for colour in closest['colours']]
        colour_ok=any(all(abs(a-b)<.0001 for a,b in zip(glyph['color'],rgb))for rgb in colours)
        if not frames or ds>.0001 or dy>.0001 or glyph['render_type']not in modes or not colour_ok:
            failures.append(dict(glyph=glyph,source_slot=closest['id'],baseline_delta_pt=dy,size_delta_pt=ds,
                                 source_render_mode=closest['render_mode'],source_colour_palette=colours))
    return dict(translation_style_violations=failures,translation_size_max_delta_pt=max_size,
                translation_baseline_max_delta_pt=max_baseline,translation_style_added_nonspace_glyphs_checked=len(added),
                translation_style_method='Actual extra glyph traces versus original fixedslot size, baseline, render mode and original prose colour palette; tolerance0.0001pt')


def add_style_metadata(path,pages):
    """Read-only supplementation of an already hash-matched pixel audit."""
    path=path.resolve();folder=EN_REPAIR_ROOT/'2007'/'qa'/path.stem
    report=json.loads((folder/'audit.json').read_text(encoding='utf8'))
    assert report['sha256']==sha(path.read_bytes())and report['source_sha256']==b.SOURCE_SHA
    data=json.loads((b.BASE/'slots.json').read_text(encoding='utf8'))
    fit=json.loads(path.with_suffix('.build.json').read_text(encoding='utf8'))['fit_report']
    with fitz.open(b.SOURCE)as source,fitz.open(path)as proof:
        for pi,number in enumerate(pages):
            row=report['pages'][pi];assert row['source_page']==number
            row.update(translation_style_checks(source[number-1],proof[pi],data['pages'][number-1],[r for r in fit if r['page']==number]))
            row['passed']&=not row['translation_style_violations'];report['passed']&=row['passed']
    (folder/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report


def audit(path,pages,scale=4):
    data=json.loads((b.BASE/'slots.json').read_text(encoding='utf8'))
    source=fitz.open(b.SOURCE);proof=fitz.open(path);assert len(proof)==len(pages)
    folder=EN_REPAIR_ROOT/'2007'/'qa'/path.stem;folder.mkdir(parents=True,exist_ok=True)
    fit=json.loads(path.with_suffix('.build.json').read_text(encoding='utf8'))['fit_report']
    report={'pdf':str(path.resolve()),'sha256':sha(path.read_bytes()),'source_sha256':b.SOURCE_SHA,
            'source_pages':pages,'pages':[],'passed':True}
    previews=[]
    for pi,number in enumerate(pages):
        page=data['pages'][number-1];erased=[c['origin']for c in b.selected_glyphs(page)]
        spec={'source_page':number,'proof_page':pi+1,
              'allowed_rects':[s['allowed_rect']for s in page['slots']if not s.get('retain_native')],
              'erased_glyph_origins':erased}
        # Include new prose's real font metric boxes: Times has overhanging
        # f/j and a slightly deeper descender than the source CJK cells.
        # This never weakens the independently protected native ink mask.
        spec['allowed_rects'] +=translated_ink_rects(proof,proof[pi],source[number-1])
        (folder/f'page{number:02}-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
        row=preservation.audit(b.SOURCE,path,spec,scale)
        # Root audit rounds only for comparison; this second check requires
        # bit-identical original nonspace glyph size and origins.
        kept=[g for g in preservation.glyphs(source[number-1])if not g['c'].isspace()
              and not any(preservation.close_origin(g['origin'],p)for p in erased)]
        current=Counter(exact_glyph_key(g)for g in preservation.glyphs(proof[pi]))
        missing=[]
        for g in kept:
            key=exact_glyph_key(g)
            if current[key]:current[key]-=1
            else:missing.append(g)
        row['bit_exact_native_nonspace_glyphs_checked']=len(kept)
        row['bit_exact_native_nonspace_glyphs_changed']=missing
        row['original_images_identical']=image_keys(source[number-1])==image_keys(proof[pi])
        old_fonts=font_keys(source,source[number-1]);new_fonts=font_keys(proof,proof[pi])
        row['original_font_programs_identical']=all(new_fonts.get(k)==v for k,v in old_fonts.items())
        row['original_font_program_sha256']=old_fonts
        row['remaining_han']=re.findall('[\u3400-\u9fff]',proof[pi].get_text())
        # The damaged native source character is intentionally retained on p18.
        row['unexpected_nul']=sum(g['c']=='\x00'and not any(preservation.close_origin(g['origin'],p['origin'])
                   for p in kept if p['c']=='\x00')for g in preservation.glyphs(proof[pi]))
        row.update(translation_style_checks(source[number-1],proof[pi],page,[r for r in fit if r['page']==number]))
        row['passed']=not(row['native_glyphs_changed']or missing or row['protected_glyphs_selected_for_erasure']
             or row['changed_pixels_outside_prose']or row['changed_pixels_in_native_glyph_neighborhood']
             or not row['original_images_identical']or not row['original_font_programs_identical']
             or row['remaining_han']or row['unexpected_nul']or row['translation_style_violations'])
        report['passed']&=row['passed'];report['pages'].append(row)
        pix=proof[pi].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False)
        image=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        image.save(folder/f'page{number:02}-mupdf.png');image.thumbnail((595,842));previews.append((number,image.copy()))
        print(path.name,'source p',number,'outside',row['changed_pixels_outside_prose'],
              'native ink',row['changed_pixels_in_native_glyph_neighborhood'],'exact glyphs',len(missing),flush=True)
    cols=2;rows=(len(previews)+1)//2;contact=Image.new('RGB',(cols*620,rows*875),'#ddd');draw=ImageDraw.Draw(contact)
    for index,(number,image)in enumerate(previews):
        x=(index%cols)*620;y=(index//cols)*875;draw.text((x+12,y+5),f'Source page {number}',fill='black');contact.paste(image,(x+12,y+25))
    contact.save(folder/'contact-mupdf.png')
    if '_KO' in path.stem:
        visible=visibility.audit(path,scale=scale);report['hangul_visibility']=visible
        report['passed']&=not visible['flagged_components']
    (folder/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('--pages',nargs='+',type=int,required=True)
    p.add_argument('--scale',type=int,default=4);args=p.parse_args();result=audit(args.pdf,args.pages,args.scale)
    print('PASSED',result['passed']);raise SystemExit(not result['passed'])
