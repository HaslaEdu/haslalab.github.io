"""Native-position translation experiment: edit prose, retain native equations.

The experimental 2007 solution-page profile intentionally has no paragraph
merging, HTML reflow, font shrinking, equation images, or diagram replacement.
Prose CIDs are removed from TJ arrays and replaced by their exact text advance.
"""
from pathlib import Path
from collections import Counter, defaultdict
from io import BytesIO
import argparse, hashlib, json, re
import numpy as np
import pikepdf
import pymupdf as fitz
from PIL import Image
from fontTools import subset
from fontTools.ttLib import TTFont
import cpho_cjk_translate as cjk

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tmp/source-audit/CPhO_2007_T_ZH.pdf'
OUT=ROOT/'tmp/original-style-repair/2007-s-p5'
FONTS=ROOT/'tools/ko/fonts'


def source_characters(page):
    result=[]
    for bi,block in enumerate(page.get_text('rawdict')['blocks']):
        if block['type']:continue
        for li,line in enumerate(block['lines']):
            for span in line['spans']:
                for char in span['chars']:
                    result.append({**char,'font':span['font'],'size':span['size'],
                        'flags':span['flags'],'color':span['color'],'block':bi,'line':li,'index':len(result)})
    return result


def glyph_key(c):
    return (c['c'],c['font'],round(c['size'],6),round(c['origin'][0],5),round(c['origin'][1],5))


def extract_slots(source=SOURCE,page_number=5):
    """Extract original line/run geometry, keeping every mathematical gap."""
    doc=fitz.open(source);page=doc[page_number-1];chars=source_characters(page)
    rows=cjk.prose_rows(chars);slots=[]
    for ri,row in enumerate(rows):
        owned=list(row['chars'])
        # The original Hei subsection numeral and its punctuation are prose.
        if ri in [0,1]:
            owned=[c for c in chars if c['font']=='ºÚÌå+FPEF' and abs(c['origin'][1]-row['baseline'])<.03]
        groups=[]
        for ch in sorted(owned,key=lambda c:c['origin'][0]):
            if groups and ch['origin'][0]-groups[-1][-1]['bbox'][2]<3:groups[-1].append(ch)
            else:groups.append([ch])
        if ri in [0,1]:groups=[owned]
        for si,group in enumerate(groups):
            first=group[0];r=fitz.Rect(first['bbox'])
            for c in group[1:]:r|=fitz.Rect(c['bbox'])
            # A source prose slot may use its original empty line to the
            # next locked mathematical glyph, never crossing that glyph.
            other=[c for c in chars if c['index']not in {g['index']for g in owned}
                and not c['c'].isspace() and c['bbox'][1]<row['baseline']+first['size']*.2
                and c['bbox'][3]>row['baseline']-first['size']
                and c['origin'][0]>=r.x1-first['size']*.15]
            column_right=293.55 if 3<=ri<=9 else 506
            if ri==0:column_right=436.56
            right=min([column_right,*[c['bbox'][0]-.65 for c in other]])
            family='sans' if first['font']=='ºÚÌå+FPEF' else 'serif'
            slots.append({'id':f'{ri}-{si}','row':ri,'source':''.join(c['c']for c in group),
                'source_font':first['font'],'size':first['size'],'flags':first['flags'],'family':family,
                'bold':bool(first['flags']&16),'italic':bool(first['flags']&2),'color':first['color'],
                'origin':list(first['origin']),'source_rect':list(r),'right':right,
                'allowed_rect':[r.x0,row['baseline']-first['size']*1.05,max(r.x1,right),row['baseline']+first['size']*.25],
                'source_characters':group,'ko':'','en':''})
            if ri==0:slots[-1]['align']='center'
    data={'source':str(source.resolve()),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'source_page':page_number,'page_rect':list(page.rect),'slots':slots}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'slots.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    doc.close();return data


def erase_prose_operators(source,page_number,slots):
    from pdf_original_text_ops import suppress_prose
    selected=[c for slot in slots for c in slot['source_characters'] if not c['c'].isspace()]
    return suppress_prose(source,page_number,selected)


def font_file(slot,lang):
    if slot['italic']:raise ValueError('An exact italic prose font must be supplied; no synthetic italic is applied')
    family='NotoSerifCJKkr'if slot['family']=='serif'else'NotoSansCJKkr'
    weight='Bold'if slot['bold']else'Regular'
    return FONTS/(family+'-'+weight+'.otf')


def subset_translation_fonts(data,translations,lang):
    """Subset only new translation fonts; original PDF font programs stay intact."""
    files=defaultdict(str)
    for slot in data['slots']:files[font_file(slot,lang)]+=translations[slot['id']][lang]
    result={}
    for path,text in files.items():
        target=OUT/('subset-'+lang+'-'+path.name)
        key={'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'characters':''.join(sorted(set(text))),'retain_gids':True}
        metadata=target.with_suffix('.json')
        if target.is_file()and metadata.is_file()and json.loads(metadata.read_text(encoding='utf8'))==key:
            result[path]=target;continue
        font=TTFont(path);options=subset.Options();options.name_IDs=['*'];options.name_languages=['*'];options.retain_gids=True
        sub=subset.Subsetter(options=options);sub.populate(text=text);sub.subset(font);font.save(target);font.close()
        metadata.write_text(json.dumps(key,ensure_ascii=False,indent=2),encoding='utf8')
        result[path]=target
    return result


def compose(data,translations,lang):
    raw,count=erase_prose_operators(Path(data['source']),data['source_page'],data['slots'])
    doc=fitz.open(stream=raw,filetype='pdf');page=doc[0];fits=[];font_files=subset_translation_fonts(data,translations,lang)
    for slot in data['slots']:
        text=translations[slot['id']][lang];original_font=font_file(slot,lang);file=font_files[original_font];font=fitz.Font(fontfile=str(file))
        width=font.text_length(text,fontsize=slot['size']);available=slot['right']-slot['origin'][0]
        point=list(slot['origin'])
        if slot.get('align')=='center':point[0]+=(available-width)/2
        fits.append({'id':slot['id'],'width':width,'available':available,'overflow':max(0,width-available),'font':original_font.name,'size':slot['size'],'origin':point,'source_baseline':slot['origin'][1],'text':text})
        if width>available+.01:continue
        if text:
            name='Translation'+slot['family']+('Bold'if slot['bold']else'Regular')
            page.insert_text(fitz.Point(point),text,fontsize=slot['size'],fontname=name,fontfile=str(file),
                color=tuple(((slot['color']>>n)&255)/255 for n in [16,8,0]))
    if any(row['overflow']>.01 for row in fits):
        (OUT/f'overflow-{lang}.json').write_text(json.dumps(fits,ensure_ascii=False,indent=2),encoding='utf8')
        doc.close();raise ValueError('Translation does not fit its original prose slots; see overflow report')
    stale=OUT/f'overflow-{lang}.json'
    if stale.is_file():stale.unlink()
    path=OUT/f'CPhO_2007_TS_source_p5_{lang.upper()}.pdf'
    doc.save(path,garbage=4,deflate=True);doc.close()
    return path,fits,count


def verify(data,path,lang,fits,count):
    original=fitz.open(data['source']);a=original[data['source_page']-1];out=fitz.open(path);b=out[0]
    selected={glyph_key(c)for slot in data['slots']for c in slot['source_characters']if not c['c'].isspace()}
    def exact(c):return (c['c'],c['font'],c['size'],tuple(c['origin']))
    expected=Counter(exact(c)for c in source_characters(a)if not c['c'].isspace()and glyph_key(c)not in selected)
    actual=Counter(exact(c)for c in source_characters(b)if not c['c'].isspace())
    missing=expected-actual
    font_programs=[]
    for xref,ext,kind,name,*_ in a.get_fonts(full=True):
        original_program=original.extract_font(xref)[3]
        match=[x for x in b.get_fonts(full=True)if x[3]==name]
        same=bool(match)and any(out.extract_font(x[0])[3]==original_program for x in match)
        font_programs.append({'source_font':name,'sha256':hashlib.sha256(original_program).hexdigest(),'identical':same})
    bad=[c for c in source_characters(b)if c['c']in ['\x00','\ufffd']]
    source_images=a.get_image_info(hashes=True);target_images=b.get_image_info(hashes=True)
    image_matches=[{'bbox':list(im['bbox']),'digest':im['digest'].hex(),
         'identical':any(im['bbox']==t['bbox']and im['digest']==t['digest']for t in target_images)}for im in source_images]
    scale=4;pa=a.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False);pb=b.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
    aa=np.frombuffer(pa.samples,np.uint8).reshape(pa.height,pa.width,pa.n);bb=np.frombuffer(pb.samples,np.uint8).reshape(pb.height,pb.width,pb.n)
    mask=np.zeros((pa.height,pa.width),bool)
    for slot in data['slots']:
        r=fitz.Rect(slot['allowed_rect'])
        x0,y0,x1,y1=int(r.x0*scale)-1,int(r.y0*scale)-1,int(r.x1*scale)+2,int(r.y1*scale)+2
        mask[max(0,y0):min(pa.height,y1),max(0,x0):min(pa.width,x1)]=True
    changed=np.any(aa!=bb,axis=2);outside=changed&~mask
    pa.save(OUT/'source-p5.png');pb.save(path.with_suffix('.png'))
    overlay=bb.copy();overlay[outside]=[255,0,0];Image.fromarray(overlay).save(OUT/f'outside-diff-{lang}.png')
    report={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_page':data['source_page'],
        'source_prose_glyphs_removed':count,'native_glyphs_locked':sum(expected.values()),'native_glyphs_missing_or_changed':list(missing.items()),
        'native_metadata_comparison':'bit-exact original font name, numeric size, and origin coordinates; no rounding/tolerance',
        'comparison_scale':scale,'pixels_changed_outside_prose_slots':int(outside.sum()),'fit_report':fits,
        'original_font_programs':font_programs,'missing_or_replacement_text_glyphs':bad,
        'original_images':image_matches,
        'rules':{'font_size_fixed':True,'baseline_fixed':True,'autoshrink':False,'math_images':False,'figure_replacement':False,'paragraph_merging':False}}
    qa=OUT/f'qa-{lang}.json'
    if qa.is_file():
        previous=json.loads(qa.read_text(encoding='utf8'))
        if previous.get('sha256')==report['sha256']:
            for key in ['poppler','pages_visually_reviewed']:
                if key in previous:report[key]=previous[key]
    qa.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    original.close();out.close();return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['extract','build']);args=parser.parse_args()
    if args.command=='extract':
        data=extract_slots()
        for slot in data['slots']:print(slot['id'],repr(slot['source']),round(slot['right']-slot['origin'][0],2),flush=True)
        return
    data=json.loads((OUT/'slots.json').read_text(encoding='utf8'));translations={}
    for line in (ROOT/'tools/ko/cpho/2007/original-style-p5.tsv').read_text(encoding='utf8').splitlines():
        if line.strip():key,ko,en=line.split('\t',2);translations[key]={'ko':ko,'en':en}
    for lang in ['ko','en']:
        path,fits,count=compose(data,translations,lang);report=verify(data,path,lang,fits,count)
        print(lang,'outside pixels',report['pixels_changed_outside_prose_slots'],'native missing',len(report['native_glyphs_missing_or_changed']),flush=True)


if __name__=='__main__':main()
