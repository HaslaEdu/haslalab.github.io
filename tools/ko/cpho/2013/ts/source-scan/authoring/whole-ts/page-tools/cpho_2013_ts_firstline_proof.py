"""Unpublished first-line proof for the scanned2013 solutions; not a READY edition."""
from pathlib import Path
from io import BytesIO
import json,hashlib
import pikepdf
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools import subset
from pdf_original_raster_math import replay,nums
from pdf_memory_gate import page_worker

SOURCE=Path('tmp/original-style-sources/CPhO_2013_Chinese_original.pdf')
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/first-line')
TEXT={
 'ko':['매번 공이 튄 직후의 수직 속력은 직전의','배이다. 첫 충돌 때의 수직 속력은'],
 'en':['After each bounce the vertical speed is','times its impact speed. At the first impact,'],
}

def font_bytes(path,text):
    f=TTFont(path,fontNumber=0,recalcTimestamp=False);options=subset.Options();options.retain_gids=True;options.name_IDs=['*']
    worker=subset.Subsetter(options=options);worker.populate(text=text);worker.subset(f);out=BytesIO();f.save(out);return out.getvalue()

def advance(metric,text,size):return sum(size/4 if c==' 'else metric.text_length(c,fontsize=size)for c in text)

def write_words(page,point,text,metric,size):
    x,y=point
    for word in text.split(' '):
        page.insert_text((x,y),word,fontname='TranslatedScanBody',fontsize=size,color=(0,0,0))
        x+=metric.text_length(word,fontsize=size)+size/4

def build(lang):
    BASE.mkdir(parents=True,exist_ok=True);size=9.91;y=145.25557675899174;left=76.2;right=522.75
    original=[332,136,339,149];font=Path('C:/Windows/Fonts')/('batang.ttc'if lang=='ko'else'simsun.ttc')
    first,last=TEXT[lang];raw_font=font_bytes(font,first+last);metric=fitz.Font(fontbuffer=raw_font)
    math_x=left+advance(metric,first,size)+size/4;after_x=math_x+7+(0 if lang=='ko'else size/4)
    end=after_x+advance(metric,last,size)
    if end>right:raise ValueError(('Unchanged-size first-line translation exceeds original column',lang,end,right))
    base=BASE/f'page04-{lang}.base.pdf'
    with pikepdf.open(SOURCE)as source,pikepdf.Pdf.new()as out:
        out.pages.append(source.pages[3]);page=out.pages[0];old=page.Contents if isinstance(page.Contents,pikepdf.Array)else[page.Contents]
        page.Contents=pikepdf.Array([*old,out.make_stream(b'q 1 g 75.2 692.54 391.8 13.5 re f Q\n')]);out.save(base,compress_streams=False)
    doc=fitz.open(base);page=doc[0];page.insert_font(fontname='TranslatedScanBody',fontbuffer=raw_font)
    write_words(page,[left,y],first,metric,size);write_words(page,[after_x,y],last,metric,size)
    # A pikepdf final assembly preserves original encoded image streams/Group.
    language=BASE/f'page04-{lang}.language.pdf';doc.save(language,garbage=0,deflate=False);doc.close()
    atom=dict(id='p4-first-line-lambda',image_path=[369],rect=original,dx=math_x-original[0],reviewed=True,
        reason='Manually reviewed entire original inline lambda; original bitmap scale/q/clip/cm/Do preserved. The Chinese language line and old lambda ROI are explicitly erased by the document plan.')
    raw,qa=replay(SOURCE,4,language,[atom]);target=BASE/f'page04-{lang}.proof.pdf';target.write_bytes(raw)
    qa.update(scope_complete=False,publication_ready=False,translation=TEXT[lang],size=size,baseline=y,column=[left,right],new_right=end,
        font=str(font),font_sha256=hashlib.sha256(font.read_bytes()).hexdigest(),font_measurement='Existing manually isolated 球 source glyph compared with source native SimSun outline: bitmap-font-measurements.json record0; estimate9.91pt, baseline145.25557675899174. No fit-based shrinking.',word_space=size/4)
    target.with_suffix('.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),'utf8')
    with fitz.open(target)as final:
        final[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(70,132,525,153)).save(BASE/f'first-line-{lang}.png')
    print(lang,target,end,qa['output_sha256'],flush=True)

if __name__=='__main__':
    import sys
    with page_worker():build(sys.argv[1])
