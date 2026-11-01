"""Subset actual source-equivalent font faces; never fit or scale translated text."""
from pathlib import Path
from io import BytesIO
import hashlib,re
from fontTools.ttLib import TTFont
from fontTools import subset
import pymupdf as fitz
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new_font(path,text,font_index=0):
    path=Path(path);cache=BASE/'font-cache';cache.mkdir(exist_ok=True)
    key=hashlib.sha256(path.read_bytes()+str(font_index).encode()+text.encode('utf8')+b'retain-gids-source-role-v1').hexdigest()[:18]
    target=cache/(path.stem+f'-face{font_index}-'+key+'.ttf')
    if not target.exists():
        f=TTFont(path,fontNumber=font_index,recalcTimestamp=False)
        missing=[c for c in set(text)if ord(c)not in f.getBestCmap()]
        if missing:raise ValueError(('Unsupported source-equivalent font character',str(path),font_index,missing))
        options=subset.Options();options.retain_gids=True;options.name_IDs=['*'];options.name_languages=['*'];options.name_legacy=True
        worker=subset.Subsetter(options=options);worker.populate(text=text);worker.subset(f);f.save(target);f.close()
    raw=target.read_bytes()
    with TTFont(BytesIO(raw),recalcTimestamp=False)as f:
        cmap=f.getBestCmap();invalid=[c for c in set(text)if not c.isspace()and(ord(c)not in cmap or f['hmtx'][cmap[ord(c)]][0]<=0)]
        if invalid:raise ValueError(('Actual positive source-face advances required',invalid))
        name=f['name'].getDebugName(6)
    return raw,fitz.Font(fontbuffer=raw),dict(source_path=str(path),source_face_index=font_index,source_sha256=sha(path),actual_postscript_name=name,subset=str(target),subset_sha256=sha(target),actual_nonspace_font_advances_positive=True)
def width(metric,text,size):
    return sum(size/4 if c==' 'else metric.text_length(c,fontsize=size)for c in text)
def write_words(page,x,y,text,metric,size,alias,render_mode=0,line_width=0):
    start=x
    for match in re.finditer(r' +|[^ ]+',text):
        word=match.group()
        if word.isspace():x+=len(word)*size/4;continue
        page.insert_text((x,y),word,fontname=alias,fontsize=size,color=(0,0,0),fill=(0,0,0),render_mode=render_mode,border_width=(line_width or 0)/size)
        x+=metric.text_length(word,fontsize=size)
    return x-start
