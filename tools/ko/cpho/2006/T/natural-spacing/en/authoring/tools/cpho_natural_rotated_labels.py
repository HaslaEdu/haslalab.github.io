"""Same-size Batang prose labels retaining their original measured rotation."""
from io import BytesIO
from pathlib import Path
import json
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools import subset
from pdf_native_inline_reposition import reposition_inline,_traces
from cpho_natural_spacing import baseline


def apply(raw,year,language,number):
    if language!='ko':return raw,None
    data=json.loads(baseline(year,language).with_suffix('.build.json').read_text('utf8'))
    labels=[v for v in data.get('raster_label_translation',[])if v['page']==number and v.get('effective_alignment')=='rotated']
    if not labels:return raw,None
    with fitz.open(stream=raw,filetype='pdf')as doc:rows=_traces(doc[0])
    erase=[]
    for label in labels:
        box=fitz.Rect(label['source_ink_rect'])+(-10,-10,10,10)
        selected=[g for g in rows if g['c']in label['text']and 'NotoSerif'in g['font']and abs(g['size']-label['size'])<.001 and box.contains(fitz.Point(g['origin']))]
        if ''.join(g['c']for g in selected)!=label['text']:raise ValueError('A rotated label cannot be associated with its exact old Korean CIDs')
        erase.extend({k:g[k]for k in('c','font','size','origin')}for g in selected)
    control,qa=reposition_inline(raw,1,erased_glyphs=erase)
    font=TTFont('C:/Windows/Fonts/batang.ttc',fontNumber=0,recalcTimestamp=False)
    options=subset.Options();options.retain_gids=True;options.name_IDs=['*'];sub=subset.Subsetter(options=options)
    sub.populate(text=''.join(v['text']for v in labels));sub.subset(font);buffer=BytesIO();font.save(buffer)
    out=fitz.open(stream=control,filetype='pdf');page=out[0]
    page.insert_font(fontname='KO_Natural_BatangRotated',fontbuffer=buffer.getvalue());placements=[]
    for label in labels:
        run=label['runs'][0];point=fitz.Point(run['origin'])
        page.insert_text(point,run['text'],fontname='KO_Natural_BatangRotated',fontsize=label['size'],color=(0,0,0),morph=(point,fitz.Matrix(run['angle'])))
        placements.append(dict(text=run['text'],point=run['origin'],size=label['size'],angle=run['angle']))
    result=out.tobytes(garbage=0,deflate=False);out.close()
    return result,dict(erased_hangul_glyphs=erase,new_batang_placements=placements,native_move_qa=qa,
        original_point_size_origin_and_rotation_preserved=True,no_font_scaling=True,source_raster_font_inference=data['raster_label_translation'][-1].get('inferred_font_family'))
