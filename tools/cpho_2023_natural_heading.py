"""Centre complete translated headings, retaining original point size/styles."""
from pathlib import Path
import json,hashlib,os
from io import BytesIO
import pymupdf as fitz
import cpho_2023_original_style as b
from pdf_original_style_audit import glyphs
from pdf_original_text_ops import suppress_prose

OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2023/natural-layout')

def apply(input_pdf,language,target):
    source=fitz.open(b.SOURCE);data=json.loads((b.OUT/'slots.json').read_text('utf8'));slots={s['id']:s for s in data['pages'][0]['slots']}
    with fitz.open(input_pdf)as old:
        heading=[g for g in b.characters(old[0])if abs(g['origin'][1]-slots['1-0-0']['origin'][1])<.02]
    raw,_=suppress_prose(input_pdf,1,heading);doc=fitz.open(stream=raw,filetype='pdf');page=doc[0]
    title=slots['1-0-0'];number=slots['1-0-1'];size=title['size'];baseline=title['origin'][1]
    # 40 is prose numbering. Its source font program/size/rendering style are
    # retained while the complete heading is centred as a single unit.
    number_xref=next(f[0]for f in source[0].get_fonts()if f[4]=='F5');number_buffer=source.extract_font(number_xref)[3]
    number_face=fitz.Font(fontbuffer=number_buffer)
    prose_path=(b.ROOT/'tools/ko/fonts/NotoSansCJKkr-Regular.otf')if language=='ko'else __import__('cpho_official_hans_fonts').font_face('simhei.ttf')
    runs=[('제',False),('40',True),('회 전국 중학생 물리경시대회 결선 이론시험 참고해설',False)]if language=='ko'else[('40',True),('th CPhO Final Theory Reference Solutions',False)]
    from pdf_original_style_fonts import subset_font
    prose_path=subset_font(prose_path,''.join(text for text,native in runs if not native),OUT/'heading-fonts')
    prose_face=fitz.Font(fontfile=str(prose_path))
    width=sum((number_face if native else prose_face).text_length(text,fontsize=size)for text,native in runs)
    x=(page.rect.width-width)/2;start=x;placements=[]
    page.insert_font(fontname='HeadingOriginalNumber',fontbuffer=number_buffer)
    page.insert_font(fontname='HeadingTranslatedProse',fontfile=str(prose_path))
    for text,native in runs:
        style=number if native else title;face=number_face if native else prose_face
        page.insert_text((x,baseline),text,fontname='HeadingOriginalNumber'if native else'HeadingTranslatedProse',fontsize=size,render_mode=style['render_mode'],border_width=style['border_width']/size,miter_limit=10,color=(0,0,0))
        advance=face.text_length(text,fontsize=size);placements.append(dict(text=text,x=x,advance=advance,size=size,source_size=size,native_number_face=native));x+=advance
    centre_error=abs((start+x)/2-page.rect.width/2)
    assert centre_error<1e-7
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True);doc.save(target,garbage=0,deflate=False);doc.close();source.close()
    target.with_suffix('.heading.json').write_text(json.dumps(dict(source=b.SOURCE.name,language=language,complete_heading_centred=True,centre_error_pt=centre_error,source_size=size,baseline=baseline,placements=placements,sha256=hashlib.sha256(target.read_bytes()).hexdigest()),ensure_ascii=False,indent=2)+'\n','utf8')
    return target

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--language',choices=['ko','en'],required=True);p.add_argument('--input',type=Path,required=True);a=p.parse_args();target=OUT/f'CPhO_2023_p1_{a.language.upper()}_heading_proof.pdf';print(apply(a.input,a.language,target))
