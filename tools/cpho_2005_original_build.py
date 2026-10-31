"""Fixed-baseline KO/EN translation of the pinned CPhO2005 Chinese source.

Each source native prose slot and bitmap language ROI requires manual text.
Equations, images, original font programs and original drawing tokens remain
native. The final assembly uses qpdf page append, preserving each PageGroup.
"""
from pathlib import Path
from collections import defaultdict
import argparse,hashlib,json,os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
import pikepdf
import pymupdf as fitz
import cpho_2005_original_extract as source
import cpho_2005_original_fonts as original_fonts
from pdf_original_text_ops import suppress_prose
from pdf_original_style_fonts import subset_font

ROOT=source.ROOT;AUTHOR=source.AUTHOR;BASE=original_fonts.CACHE.parent/'native';FONTS=ROOT/'tools/ko/fonts'

def data():
    value=json.loads((AUTHOR/'native-slots.json').read_text('utf8'))
    if value['source_sha256']!=source.SOURCE_SHA:raise ValueError('Source inventory differs')
    return value

def translations(pages):
    result={}
    for number in pages:
        for line in (AUTHOR/f'page{number:02}.tsv').read_text('utf8').splitlines():
            if not line.strip():continue
            key,ko,en=line.split('\t')
            if key in result:raise ValueError('Duplicate manual translation: '+key)
            result[key]=dict(ko=ko,en=en)
    return result

def font_path(slot,lang):
    return original_fonts.select(slot,lang)

def authoring_hashes(number,lang):
    page=data()['pages'][number-1]
    paths=[Path(__file__),Path(source.__file__),Path(original_fonts.__file__),AUTHOR/'native-slots.json',AUTHOR/f'page{number:02}.tsv',
        ROOT/'tools/pdf_original_text_ops.py',ROOT/'tools/pdf_original_style_fonts.py']
    paths.extend(sorted({font_path(slot,lang)for slot in page['slots']if not slot.get('retain_native')}))
    return {str(p.relative_to(ROOT)).replace('\\','/')if p.is_relative_to(ROOT)else str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}

def translated_text(slot,value):
    if slot.get('retain_native'):return ''
    if slot.get('native_prefix'):
        prefixes=(')', '）')if slot['native_prefix']in')）'else(slot['native_prefix'],)
        if not value.startswith(prefixes):raise ValueError('Retained original punctuation requires its translation marker: '+slot['id'])
        value=value[1:]
    return value

def fitting(pages,lang):
    inventory=data();text=translations(pages);metrics={};report=[]
    for page in inventory['pages']:
        if page['source_page']not in pages:continue
        required={s['id']for s in page['slots']}
        if not required.issubset(text):raise ValueError('Missing manual prose: '+str(sorted(required-set(text))))
        for slot in page['slots']:
            value=translated_text(slot,text[slot['id']][lang])
            path=font_path(slot,lang);key=str(path)
            if key not in metrics:metrics[key]=fitz.Font(fontfile=key)
            font=metrics[key];width=font.text_length(value,fontsize=slot['size']);available=slot['right']-slot['origin'][0]
            origin=list(slot['origin'])
            if slot.get('align')=='center':origin[0]=slot['original_horizontal_center']-width/2
            elif slot.get('align')=='right':origin[0]=slot['right']-width
            report.append(dict(id=slot['id'],page=page['source_page'],source=slot['source'],text=value,
                width=width,available=available,overflow=max(0,width-available),size=slot['size'],origin=origin,font=str(path)))
    return report

def preflight(pages):
    BASE.mkdir(parents=True,exist_ok=True);report=[]
    for lang in ['ko','en']:
        rows=fitting(pages,lang)
        for row in rows:row['language']=lang
        report.extend(rows)
    (AUTHOR/'fixed-slot-fit-draft.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    bad=[r for r in report if r['overflow']>.02]
    print(json.dumps(bad,ensure_ascii=False,indent=2),flush=True)
    return bad

def compose_page(number,lang):
    inventory=data();page=inventory['pages'][number-1];texts=translations([number]);fit=fitting([number],lang)
    if any(r['overflow']>.02 for r in fit):raise ValueError('Fixed-size prose overflow')
    if number>=4:raise ValueError('Scanned solution language ROIs must be reviewed before composition')
    selected=[g for s in page['slots']if not s.get('retain_native')for g in s['source_characters']if not g['c'].isspace()and g['index']not in s.get('retained_source_indices',[])]
    raw,removed=suppress_prose(source.SOURCE,number,selected)
    folder=BASE/lang;folder.mkdir(parents=True,exist_ok=True)
    control=folder/f'page{number:02}.control.pdf';control.write_bytes(raw)
    doc=fitz.open(stream=raw,filetype='pdf');target=doc[0];groups=defaultdict(str)
    for slot in page['slots']:
        if not slot.get('retain_native'):groups[str(font_path(slot,lang))]+=translated_text(slot,texts[slot['id']][lang])
    fonts={path:subset_font(Path(path),value,original_fonts.CACHE/'subsets')for path,value in groups.items()}
    placements=[];fits={row['id']:row for row in fit}
    for slot in page['slots']:
        if slot.get('retain_native'):continue
        value=translated_text(slot,texts[slot['id']][lang])
        if not value:continue
        path=fonts[str(font_path(slot,lang))];name='Translation'+slot['family']+('Bold'if slot['bold']else'Regular')
        color=tuple(((slot['color']>>n)&255)/255 for n in [16,8,0]);mode=slot['render_mode'];width=slot['line_width']or 0
        origin=fits[slot['id']]['origin']
        target.insert_text(fitz.Point(*origin),value,fontsize=slot['size'],fontname=name,fontfile=str(path),
            color=color,fill=color,render_mode=mode,border_width=width/slot['size']if mode in [1,2]else.05,
            miter_limit=slot['miter_limit'])
        placements.append(dict(id=slot['id'],text=value,size=slot['size'],origin=origin,render_mode=mode,line_width=width))
    output=folder/f'page{number:02}.pdf';doc.save(output,garbage=0,deflate=False);doc.close()
    output.with_suffix('.build.json').write_text(json.dumps(dict(source_sha256=source.SOURCE_SHA,source_page=number,
        removed_native_prose_glyphs=removed,translation=lang,autoshrink=False,reflow=False,added_notes=False,placements=placements,
        raster_language_status='not-required',authoring_sha256=authoring_hashes(number,lang)),ensure_ascii=False,indent=2),'utf8')
    print(output,flush=True)
    return output

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['preflight','page']);p.add_argument('--pages',nargs='+',type=int,required=True);p.add_argument('--lang',choices=['ko','en']);args=p.parse_args()
    if args.command=='preflight':preflight(args.pages)
    else:
        for number in args.pages:
            for lang in [args.lang]if args.lang else['ko','en']:compose_page(number,lang)

if __name__=='__main__':main()
