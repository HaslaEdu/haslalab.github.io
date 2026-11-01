"""Inventory the pinned CPhO2013 Chinese source without changing its design.

Native prose is selected explicitly in the exported inventory for manual review.
OCR on the original solution bitmaps is a draft transcription/position aid only;
equations are never OCR-transcribed into a translated PDF.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re
import pymupdf as fitz
import cpho_cjk_translate as cjk
from cpho_original_style import source_characters
from pdf_original_text_ops import native_form_glyphs

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'
SOURCE_SHA='612d676f525ddc35ad3b417a8f25141d3467f48309d52dfdbcab7bd222201d68'
AUTHOR=ROOT/'tools/ko/cpho/2013/original'
BASE=ROOT/'tmp/original-style-repair/2013'

def source():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Pinned Chinese source differs')
    doc=fitz.open(SOURCE)
    if len(doc)!=14 or '考试答案'not in doc[3].get_text()or '八、'not in doc[2].get_text():raise ValueError('Source T3/TS11 boundary differs')
    return doc

def extract():
    doc=source();AUTHOR.mkdir(parents=True,exist_ok=True);BASE.mkdir(parents=True,exist_ok=True)
    pages=[];summary=[];readable=[]
    for pi,page in enumerate(doc):
        chars=source_characters(page);forms=native_form_glyphs(SOURCE,pi+1)
        paths=[fitz.Rect(drawing['rect'])for drawing in page.get_drawings()]
        protected={(g['font'],round(g['origin'][0],5),round(g['origin'][1],5))for g in forms}
        rows=cjk.prose_rows(chars);slots=[];traces=page.get_texttrace()
        for ri,row in enumerate(rows):
            # Original paragraph alignment belongs to the complete prose
            # heading/footer, including its ordinary page/edition numerals.
            # Those numerals are not mathematical variables. Preserve their
            # values while translating and retaining the source alignment.
            whole_kind=('title'if row['size']>14 and '全国' in row['plain']else
                        'header'if '届决赛试题及答案'in row['plain']else
                        'footer'if re.sub(r'\s+','',row['plain'])=='第页共页'else None)
            owned=[g for g in row['chars']if not g['c'].isspace()and(g['font'],round(g['origin'][0],5),round(g['origin'][1],5))not in protected]
            if whole_kind:
                owned=[c for c in chars if abs(c['origin'][1]-row['baseline'])<.3 and not c['c'].isspace()]
            if not owned:continue
            indices={g['index']for g in owned}
            locked=[c for c in chars if c['index']not in indices and not c['c'].isspace()
                    and c['bbox'][1]<row['baseline']+row['size']*.2 and c['bbox'][3]>row['baseline']-row['size']]
            groups=[]
            for c in sorted(owned,key=lambda c:c['origin'][0]):
                blocked=groups and any(groups[-1][-1]['origin'][0]+.1<g['origin'][0]<c['origin'][0]-.1 for g in locked)
                if groups and not blocked and c['origin'][0]-groups[-1][-1]['bbox'][2]<3:groups[-1].append(c)
                else:groups.append([c])
            if whole_kind:groups=[sorted(owned,key=lambda c:c['origin'][0])]
            for si,group in enumerate(groups):
                first=group[0];rect=fitz.Rect(first['bbox'])
                for c in group[1:]:rect|=fitz.Rect(c['bbox'])
                right=min([539.65,*[c['bbox'][0]-.3 for c in locked if c['origin'][0]>group[-1]['origin'][0]+.1]])
                for box in paths:
                    if box.x0>group[-1]['origin'][0]+.1 and box.y0<rect.y1 and box.y1>rect.y0:
                        right=min(right,box.x0-.6)
                # Native diagrams are immutable obstacles. Tiny math sprites
                # and the huge scanned solution bodies remain separate.
                for image in page.get_image_info():
                    box=fitz.Rect(image['bbox'])
                    if box.x0>rect.x0 and box.y0<rect.y1 and box.y1>rect.y0:right=min(right,box.x0-.6)
                matching=[t for t in traces if t['font']==first['font']and any(abs(o[0]-first['origin'][0])<.02 and abs(o[1]-first['origin'][1])<.02 for cp,gid,o,b in t['chars'])]
                modes={t['type']for t in matching};mode=2 if modes=={0,1}else next(iter(modes),0)
                text=''.join(c['c']for c in group)
                slot=dict(id=f'{pi+1}-{ri}-{si}',page=pi,row=ri,source=text,source_font=first['font'],size=first['size'],
                    flags=first['flags'],family='sans'if re.search('SimHei|YaHei|DengXian',first['font'])else'serif',
                    bold=bool(first['flags']&16)and mode!=2,italic=bool(first['flags']&2),color=first['color'],
                    origin=list(first['origin']),source_rect=list(rect),right=right,source_characters=group,
                    render_mode=mode,line_width=next((t['linewidth']for t in matching if t['type']==1),None),miter_limit=10,
                    allowed_rect=[rect.x0,row['baseline']-first['size']*1.05,max(rect.x1,right),row['baseline']+first['size']*.25])
                if text and all(c in '，．。；：！？、（）【】(),.;:!?[]'for c in text):slot['retain_native']=True
                if whole_kind:
                    slot['original_paragraph_role']=whole_kind
                    slot['original_horizontal_center']=(rect.x0+rect.x1)/2
                    left,right=(300,rect.x1)if whole_kind=='header'else(54,539.65)if whole_kind=='title'else(200,395)
                    slot['align']='right'if whole_kind=='header'else'center'
                    slot['origin'][0]=left;slot['right']=right
                    slot['allowed_rect'][0]=left;slot['allowed_rect'][2]=right
                slots.append(slot)
            full=[c for c in chars if abs(c['origin'][1]-row['baseline'])<2]
            readable.append(f'ROW {pi+1}-{ri}: '+''.join(c['c']for c in sorted(full,key=lambda c:c['origin'][0])))
            for slot in slots:
                if slot['row']==ri:readable.append(f'{slot["id"]}\t{slot["source"]}\t{slot["right"]-slot["origin"][0]:.2f}\t{slot["size"]:.3f}')
        # An isolated retained opening parenthesis belongs to a source inline
        # formula. Its closing glyph may share a prose run with the following
        # conjunction; keep that original closing font/GID/position as well.
        pending=0
        from cpho_2022_original_build import glyph_ink_box
        font_cache={}
        for slot in slots:
            if slot.get('retain_native'):
                pending=max(0,pending+sum(slot['source'].count(c)for c in '（(')-sum(slot['source'].count(c)for c in '）)'))
            elif pending and slot['source'].startswith(('）',')')):
                char=slot['source_characters'][0];ink=glyph_ink_box(doc,page,char,font_cache)
                slot['retained_source_indices']=[char['index']];slot['native_prefix']=char['c']
                slot['origin'][0]=max(slot['origin'][0],ink.x1+.6);pending-=1
        images=[dict(index=i,xref=im['xref'],bbox=list(im['bbox']),transform=list(im['transform']),width=im['width'],height=im['height'])for i,im in enumerate(page.get_image_info(xrefs=True))]
        pages.append(dict(source_page=pi+1,kind='T'if pi<3 else'TS',page_rect=list(page.rect),slots=slots,native_form_glyphs=forms,images=images))
        summary.append(dict(page=pi+1,kind=pages[-1]['kind'],native_prose_slots=len(slots),native_form_glyphs=len(forms),source_images=len(images)))
    result=dict(source=str(SOURCE.relative_to(ROOT)).replace('\\','/'),source_sha256=SOURCE_SHA,
        source_url='https://cpho.pku.edu.cn/info/1053/1139.htm',source_pages=dict(T=[1,2,3],TS=list(range(4,15))),
        native_prose_requires_manual_review=True,bitmap_language_requires_manual_review=True,pages=pages)
    (AUTHOR/'native-slots.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    (AUTHOR/'native-slots.txt').write_text('\n'.join(readable)+'\n','utf8')
    (AUTHOR/'source-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return result

def ocr(pages):
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
    doc=source();engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1)
    for number in pages:
        output=AUTHOR/f'ocr-page{number:02}-draft.json'
        if output.exists():continue
        page=doc[number-1];pix=page.get_pixmap(matrix=fitz.Matrix(2,2));pixels=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        found,timing=engine(pixels)
        result=dict(source_sha256=SOURCE_SHA,page=number,scale=2,requires_manual_review=True,
            equations_must_remain_original_pixels=True,lines=[dict(polygon=poly,text=text,confidence=float(score))for poly,text,score in found or[]])
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
        print(json.dumps(dict(page=number,draft_ocr_lines=len(result['lines'])),ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['extract','ocr']);parser.add_argument('--pages',nargs='+',type=int)
    args=parser.parse_args()
    if args.command=='extract':extract()
    else:ocr(args.pages or list(range(4,15)))
