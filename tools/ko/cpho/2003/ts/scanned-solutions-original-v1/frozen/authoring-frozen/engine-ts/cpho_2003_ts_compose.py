"""Private2003 scanned solutions: reviewed prose slots and original math replay.

Source and output roots are separate. No source files/resources are modified.
This module never infers an erase ROI from OCR or translated text.
"""
from pathlib import Path
from io import BytesIO
import argparse,hashlib,json,re,sys,math
import pikepdf
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools import subset
from pdf_native_inline_reposition import reposition_inline
from pdf_original_raster_math import replay,nums,program_sha
from haslalab_runtime_paths import map_repository_path

ROOT=map_repository_path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
BASE=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native/TS')
SOURCE=BASE.parent/'inputs/CPhO_2003_Chinese_original.pdf'
SOURCE_SHA='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def new_font(path,text):
    path=Path(path);cache=BASE/'font-cache';cache.mkdir(exist_ok=True)
    key=hashlib.sha256(path.read_bytes()+text.encode('utf8')+b'retain-gids-scan-ts-v1').hexdigest()[:18]
    target=cache/(path.stem+'-'+key+'.ttf')
    if not target.exists():
        f=TTFont(path,fontNumber=0,recalcTimestamp=False)
        missing=[c for c in set(text)if ord(c)not in f.getBestCmap()]
        if missing:raise ValueError((str(path),'Unsupported translation characters',missing))
        options=subset.Options();options.retain_gids=True;options.name_IDs=['*'];options.name_languages=['*'];options.name_legacy=True
        worker=subset.Subsetter(options=options);worker.populate(text=text);worker.subset(f);f.save(target);f.close()
    from cpho2003_native_runtime import isolated_new_english_subset
    if 'SimSun'in path.name or 'simhei'in path.name.lower():target=isolated_new_english_subset(target,'serif'if 'SimSun'in path.name else'sans')
    raw=target.read_bytes()
    with TTFont(BytesIO(raw),recalcTimestamp=False)as checked:
        cmap=checked.getBestCmap();invalid=[c for c in set(text)if not c.isspace()and(ord(c)not in cmap or checked['hmtx'][cmap[ord(c)]][0]<=0)]
        if invalid:raise ValueError(('New prose requires actual positive font advances',invalid))
    return raw,fitz.Font(fontbuffer=raw),dict(source_path=str(path),source_sha256=sha(path),subset=str(target),subset_sha256=sha(target),actual_nonspace_font_advances_positive=True,checked_characters=len({c for c in text if not c.isspace()}))

def font_path(lang,face='SimSun'):
    if lang=='ko':
        return Path('C:/Windows/Fonts/batang.ttc')if face=='SimSun'else ROOT/'tools/ko/fonts/NotoSansCJKkr-Regular.otf'
    if face=='SimSun':return Path('D:/CodexBuilds/Hasla-original-style-20261031/english-face-repair/font-faces/SimSun-5.24.ttf')
    if face=='SimHei':return Path('D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simhei.ttf')
    raise ValueError(('Unknown original Chinese prose face',face))


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

def write_row_token(page,row,token,metric,alias,language=None):
    text=token['text'];x=token['x'];y=row['baseline'];size=row['size']
    if 'printed_regular_stroke'in row:
        regular=row['printed_regular_stroke'];bold=row['printed_bold_stroke']
        if language and language in row.get('printed_stroke_by_language',{}):
            regular=row['printed_stroke_by_language'][language]['regular'];bold=row['printed_stroke_by_language'][language]['bold']
        if row.get('role')=='mixed-bold'and token.get('index')==0 and ':'in text:
            end=text.index(':')+1
            x+=write_words(page,x,y,text[:end],metric,size,alias,2,bold)
            write_words(page,x,y,text[end:],metric,size,alias,2,regular)
        else:
            write_words(page,x,y,text,metric,size,alias,2,bold if row.get('role')=='serif-bold'else regular)
        return
    if row.get('role')=='mixed-bold':
        if token.get('index')==0 and ':'in text:
            end=text.index(':')+1;prefix=text[:end]
            x+=write_words(page,x,y,prefix,metric,size,alias,2,row.get('bold_prefix_line_width',.1))
            write_words(page,x,y,text[end:],metric,size,alias)
        else:write_words(page,x,y,text,metric,size,alias)
    else:
        mode=row.get('render_mode',2 if row.get('role')=='serif-bold'else 0)
        stroke=row.get('line_width',.15 if mode==2 else 0)
        write_words(page,x,y,text,metric,size,alias,mode,stroke)

def digits(slot):
    groups=[]
    for char in slot['source_characters']:
        if not(char['c'].isascii()and char['c'].isdigit()):continue
        if groups and char['origin'][0]-groups[-1][-1]['bbox'][2]<.5:
            groups[-1].append(char)
        else:groups.append([char])
    return groups

def header_control(number,lang,out):
    if number==10:
        from cpho2003_hybrid_native_prose import control
        return control(number,lang,out)
    """Keep every original Arabic digit CID/font/paint; only x may change."""
    inventory=json.loads((BASE/'inputs/native-slots.json').read_text('utf8'))
    plan=json.loads((BASE/'authoring'/f'page{number:02d}.json').read_text('utf8'))
    slots={s['id']:s for s in inventory['pages'][number-1]['slots']}
    erased=[];shifts=[];placements=[];fonts={};text_items=[]
    for header in plan['native_headers']:
        slot=slots[header['source_slot']];text=header['translations'][lang]
        groups=digits(slot);matches=list(re.finditer(r'\d+',text))if groups else []
        # A Chinese ordinal such as 一、 is prose; its translated1. is new prose.
        if groups and(len(matches)!=len(groups)or[m.group()for m in matches]!=[''.join(g['c']for g in group)for group in groups]):
            raise ValueError(('Original Arabic numbers mismatch',number,slot['id'],text,groups))
        erased.extend(c for c in slot['source_characters']if not(c['c'].isascii()and c['c'].isdigit())and not c.get('synthetic'))
        face=next((c['font']for c in slot['source_characters']if re.search('[\u3400-\u9fff]',c['c'])),slot['source_font']);role=face
        if role not in fonts:fonts[role]=new_font(font_path(lang,face),''.join(h['translations'][lang]for h in plan['native_headers']if h['source_prose_face']==face))
        raw,metric,font_qa=fonts[role];size=slot['size'];parts=[];end=0
        for match,group in zip(matches,groups):
            parts.append(dict(text=text[end:match.start()],width=width(metric,text[end:match.start()],size)))
            parts.append(dict(glyphs=group,width=group[-1]['bbox'][2]-group[0]['origin'][0]))
            end=match.end()
        parts.append(dict(text=text[end:],width=width(metric,text[end:],size)))
        total=sum(p['width']for p in parts)
        if slot.get('align')=='center':x=slot['original_horizontal_center']-total/2
        elif slot.get('align')=='right':x=slot['right']-total
        else:x=slot['origin'][0]
        if x<slot['allowed_rect'][0]-.01 or x+total>slot['allowed_rect'][2]+.01:
            raise ValueError(('Unchanged-size heading overflow',slot['id'],lang,text,x,total,slot['allowed_rect']))
        left=x
        for part in parts:
            if 'glyphs'in part:
                shifts.append(dict(glyphs=part['glyphs'],dx=x-part['glyphs'][0]['origin'][0]))
            elif part['text']:
                text_items.append(dict(x=x,y=slot['source_characters'][0]['origin'][1],text=part['text'],face=face,size=size,render_mode=slot['render_mode'],line_width=slot['line_width']))
            x+=part['width']
        placements.append(dict(source_slot=slot['id'],text=text,left=left,right=x,baseline=slot['source_characters'][0]['origin'][1],size=size,source_font=face,original_numbers=[''.join(c['c']for c in g)for g in groups],alignment=slot.get('align'),font=font_qa))
    raw,qa=reposition_inline(SOURCE,number,erased_glyphs=erased,shifts=shifts,allow_white_background_panels=True)
    doc=fitz.open(stream=raw,filetype='pdf');page=doc[0]
    for face,(raw_font,metric,_)in fonts.items():page.insert_font(fontname='TSHeader'+face,fontbuffer=raw_font)
    for item in text_items:
        write_words(page,item['x'],item['y'],item['text'],fonts[item['face']][1],item['size'],'TSHeader'+item['face'],item['render_mode'],item['line_width'])
    doc.save(out,garbage=0,deflate=False);doc.close();restore_actual_source_group(out,number)
    return dict(native_digit_motion=qa,placements=placements,erased_original_prose=erased,native_shifts=shifts)

def add_erase_rects(base,target,rects):
    with pikepdf.open(base)as doc:
        page=doc.pages[0];height=float(page.MediaBox[3]-page.MediaBox[1]);ops=[b'q 1 g\n']
        for x0,y0,x1,y1 in rects:
            if not(x1>x0 and y1>y0):raise ValueError('Empty reviewed erase ROI')
            ops.append((nums([x0,height-y1,x1-x0,y1-y0])+' re f\n').encode())
        ops.append(b'Q\n');old=list(page.Contents)if isinstance(page.Contents,pikepdf.Array)else[page.Contents]
        page.Contents=pikepdf.Array([*old,doc.make_stream(b''.join(ops))]);doc.save(target,compress_streams=False)

def row_layout(row,lang,metric):
    size=row['size'];x=row.get('left_by_language',{}).get(lang,row['left']);tokens=[];maths={a['id']:a for a in row.get('atoms',[])}
    for part in re.split(r'(\[\[[^\]]+\]\])',row[lang]):
        if not part:continue
        if part.startswith('[['):
            name=part[2:-2];atom=maths[name]
            before=row.get('math_before_gaps_by_language',{}).get(lang,{}).get(name,0)
            if not isinstance(before,(int,float))or not 0<=before<=size/4:raise ValueError(('Invalid reviewed original-math leading gap',row['id'],name,before))
            x+=before
            if name in row.get('original_image_right_edge_pixel_grid_atom_ids',[]):
                whole_width=atom['rect'][2]-atom['rect'][0]
                x=math.ceil((x+whole_width-1e-8)*2)/2-whole_width
            elif row.get('whole_original_image_expression_pixel_grid')and row.get('align')!='center':x=math.ceil((x-1e-8)*2)/2
            if name not in row['source_atom_ids']:raise ValueError(('Unregistered source math atom',name))
            tokens.append(dict(kind='math',id=name,x=x,width=atom['rect'][2]-atom['rect'][0],atom=atom,index=len(tokens)));x+=tokens[-1]['width']
            gap=row.get('math_after_gaps_by_language',{}).get(lang,{}).get(name,0)
            if not isinstance(gap,(int,float))or not 0<=gap<=size/4:raise ValueError(('Invalid reviewed mathematical punctuation gap',row['id'],name,gap))
            x+=gap
        else:
            tokens.append(dict(kind='prose',text=part,x=x,width=width(metric,part,size),index=len(tokens)));x+=tokens[-1]['width']
    if row.get('align')=='center':
        center=row['source_caption_horizontal_center']
        left=tokens[0]['x']if tokens else row['left'];dx=center-(left+x)/2
        for token in tokens:token['x']+=dx
        x+=dx
        if tokens and tokens[0]['x']<row.get('min_left',0)-.001:raise ValueError(('Fixed-size source-centered prose overflow',row['id'],lang))
    if row.get('align')=='right':
        dx=row['right']-x
        for token in tokens:token['x']+=dx
        x=row['right']
        if tokens and tokens[0]['x']<row.get('min_left',0)-.001:raise ValueError(('Fixed-size right-aligned prose overflow',row['id'],lang,tokens[0]['x']))
    if x>row['right']+.001:raise ValueError(('Unchanged-size translated row overflow',row['id'],lang,x,row['right']))
    if sorted(re.findall(r'\[\[([^\]]+)\]\]',row[lang]))!=sorted(row['source_atom_ids']):raise ValueError(('Original math atom count mismatch',row['id'],lang))
    return tokens,x

def restore_actual_source_group(path,number):
    temporary=Path(path).with_suffix('.actual-group.pdf')
    with pikepdf.open(SOURCE)as source,pikepdf.open(path)as out:
        value=source.pages[number-1].obj.get('/Group')
        if value is not None:out.pages[0].obj.Group=out.copy_foreign(source.make_indirect(value))
        elif '/Group'in out.pages[0].obj:del out.pages[0].obj['/Group']
        for alias,font in out.pages[0].Resources.get('/Font',{}).items():
            if not str(alias).startswith(('/TSHeader','/TSScanBody')):continue
            face=font.get('/DescendantFonts',[font])[0];descriptor=face.get('/FontDescriptor')
            if descriptor is None:raise ValueError('New font descriptor missing')
            field=next(k for k in ['/FontFile2','/FontFile3']if k in descriptor)
            with TTFont(BytesIO(descriptor[field].read_bytes()))as actual:name=actual['name'].getDebugName(6)
            font.BaseFont=pikepdf.Name('/'+name);face.BaseFont=pikepdf.Name('/'+name);descriptor.FontName=pikepdf.Name('/'+name)
        out.save(temporary,compress_streams=False)
    temporary.replace(path)

def isolate_native_raster_instances(path,expected):
    """Give every reviewed paint its own unchanged original image object.

    MuPDF may reuse an incorrectly clipped decoded image when a single image
    object is drawn through many differently clipped horizontal translations.
    Distinct original-byte copies avoid that cache interaction. No source
    bitmap, interpolation flag, colour/mask dictionary, matrix, or clipping
    program changes. Independent per-atom renders remain mandatory.
    """
    path=Path(path);temporary=path.with_suffix('.isolated-native.pdf');copies=[]
    with pikepdf.open(path)as doc:
        page=doc.pages[0]
        for content in page.Contents:
            raw=content.read_bytes()
            if b'/OriginalRasterMath'not in raw:continue
            def replace(match):
                original=page.Resources.XObject[match[1].decode('ascii')]
                clone=doc.make_stream(original.read_bytes())
                for key,value in original.items():
                    if str(key)not in ['/Length','/Filter','/DecodeParms','/Resources']:clone[key]=value
                resources=pikepdf.Dictionary(original.Resources);images=pikepdf.Dictionary();checked=[]
                for alias,image in original.Resources.XObject.items():
                    if str(image.get('/Subtype'))!='/Image':raise ValueError('Native raster instance is not image-only')
                    copy=doc.make_stream(image.read_raw_bytes())
                    for key,value in image.items():
                        if str(key)!='/Length':copy[key]=value
                    if program_sha(copy)!=program_sha(image):raise ValueError('Native encoded image program differs')
                    images[alias]=copy;checked.append(program_sha(image))
                resources.XObject=images;clone.Resources=resources
                # This is a newly introduced wrapper, not an original source
                # group. An isolated image paint prevents renderer cache reuse
                # from dropping portions under subsequent translated text.
                clone.Group=pikepdf.Dictionary(S=pikepdf.Name.Transparency,I=True,K=False,CS=pikepdf.Name.DeviceRGB)
                if clone.read_bytes()!=original.read_bytes():raise ValueError('Native original clipping/matrix program differs')
                name='/IndependentNativeImageInstance'+str(len(copies)+1);page.Resources.XObject[name]=clone
                copies.append(dict(original_alias=match[1].decode('ascii'),isolated_alias=name,unchanged_image_programs=checked,unchanged_form_content_sha256=hashlib.sha256(original.read_bytes()).hexdigest()))
                return(name+' Do').encode('ascii')
            content.write(re.sub(rb'(/OriginalRasterMath\d+) Do',replace,raw))
        if len(copies)!=expected:raise ValueError(('Native image paint count differs',len(copies),expected))
        doc.save(temporary,compress_streams=False)
    temporary.replace(path)
    return dict(instance_count=len(copies),unchanged_original_image_programs_and_clipping_matrices=True,new_wrapper_transparency_isolation=True,original_source_page_group_unchanged=True,copies=copies)

def build(number,lang):
    if sha(SOURCE)!=SOURCE_SHA:raise ValueError('Source SHA mismatch')
    plan=json.loads((BASE/'authoring'/f'page{number:02d}-layout.json').read_text('utf8'))
    if not plan.get('manual_rois_reviewed'):raise ValueError('Source language/math ROIs require manual approval')
    out=BASE/'proofs'/lang;out.mkdir(parents=True,exist_ok=True)
    stem=out/f'page{number:02d}';header=stem.with_suffix('.headers.pdf')
    header_qa=header_control(number,lang,header)
    erase=[]
    for row in plan['rows']:
        if not row.get('reviewed'):raise ValueError(('Unreviewed row',row['id']))
        erase.extend(row['erase_rects'])
        erase.extend(atom['rect']for atom in row['atoms'])
    control=stem.with_suffix('.control.pdf');add_erase_rects(header,control,erase)
    role_text={}
    for row in plan['rows']:
        face=row.get('source_prose_face','SimSun')
        if face not in ['SimSun','SimHei']:raise ValueError(('Unreviewed original scanned source face',face))
        role_text[face]=role_text.get(face,'')+re.sub(r'\[\[[^\]]+\]\]','',row[lang])
    body_fonts={face:new_font(font_path(lang,face),text)for face,text in role_text.items()}
    atoms=[];placements=[];authored=[]
    for row in plan['rows']:
        face=row.get('source_prose_face','SimSun');raw_font,metric,font_qa=body_fonts[face]
        alias='TSScanBody'if face=='SimSun'else'TSScanBody'+face
        tokens,end=row_layout(row,lang,metric)
        for token in tokens:
            if token['kind']=='prose':authored.append((row,token))
            else:
                atom=token['atom'];pieces=atom.get('paint_pieces',[atom['rect']]);dx=token['x']-atom['rect'][0]
                for piece_index,piece in enumerate(pieces):
                    atoms.append(dict(id=f"{row['id']}-{atom['id']}"+(f'-piece{piece_index+1}'if len(pieces)>1 else''),rect=piece,image_path=atom['image_path'],dx=dx,reviewed=True,reason=atom['reason']+(' Complete expression pieces share one identical horizontal translation; no relative piece motion.'if len(pieces)>1 else''),logical_expression_id=f"{row['id']}-{atom['id']}"))
        placements.append(dict(id=row['id'],text=row[lang],size=row['size'],baseline=row['baseline'],left=tokens[0]['x']if tokens else row['left'],right=end,word_space=row['size']/4,tokens=tokens,source_erase_rects=row['erase_rects'],source_prose_face=face,font_alias=alias,font=font_qa))
    background=[]
    for record in plan.get('source_background_restore_atoms',[]):
        if record.get('reviewed')is not True or record.get('source_sha256')!=SOURCE_SHA or record.get('dx')!=0:raise ValueError('Source background restoration requires pinned original evidence and zero displacement')
        background.append(dict(record));atoms.append(dict(record))
    # Original image-region paints include opaque white scan padding. Paint
    # them before new prose, then independently require no physical math ink
    # / new prose collision and no missing new-prose ink in the final PDF.
    raster=stem.with_suffix('.pre-prose.pdf');raw,replay_qa=replay(SOURCE,number,control,atoms);raster.write_bytes(raw)
    doc=fitz.open(raster);page=doc[0]
    for face,(raw_font,metric,font_qa)in body_fonts.items():
        page.insert_font(fontname='TSScanBody'if face=='SimSun'else'TSScanBody'+face,fontbuffer=raw_font)
    for row,token in authored:
        face=row.get('source_prose_face','SimSun');raw_font,metric,font_qa=body_fonts[face]
        write_row_token(page,row,token,metric,'TSScanBody'if face=='SimSun'else'TSScanBody'+face,lang)
    target=stem.with_suffix('.pdf');assert not target.exists(),target;doc.save(target,garbage=0,deflate=False);doc.close();restore_actual_source_group(target,number)
    isolated=isolate_native_raster_instances(target,len(atoms))
    replay_qa.update(stage='original-math replay before new prose',final_output_sha256=sha(target),new_prose_painted_after_original_bitmap_padding=True)
    report=dict(source=str(SOURCE),source_sha256=SOURCE_SHA,source_page=number,language=lang,output=str(target),output_sha256=sha(target),publication_ready=False,scope_complete=False,
        header=header_qa,body_fonts={face:parts[2]for face,parts in body_fonts.items()},body_placements=placements,inline_math_replay=replay_qa,isolated_native_image_paints=isolated,source_background_restore_atoms=background,layout_sha256=sha(BASE/'authoring'/f'page{number:02d}-layout.json'),
        page_scope='Complete reviewed page translation; final visual/source-nonlanguage/new-prose collision audits remain required.')
    target.with_suffix('.composition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print(lang,number,sha(target),target,flush=True)
    return target

if __name__=='__main__':
    from pdf_memory_gate import page_worker
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('page',type=int);p.add_argument('language',choices=['ko','en']);args=p.parse_args()
    with page_worker():build(args.page,args.language)
