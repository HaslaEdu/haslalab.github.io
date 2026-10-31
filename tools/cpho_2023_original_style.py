"""Original-layout CPhO 2023 prose replacement, with native mathematics locked."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,hashlib,json,re,os
import pymupdf as fitz
import cpho_cjk_translate as cjk
from pdf_original_text_ops import suppress_prose,native_form_glyphs
from pdf_original_style_fonts import FONTS,source_font_role,subset_font
from pdf_original_style_audit import audit
from pdf_original_graphics_ink import audit as graphics_audit
import cpho_2023_original_labels as figure_language
from cpho_2023_original_labels_qa import form_programs
from pdf_original_style_audit import glyphs,key,close_origin

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tmp/source-audit/CPhO_2023_T_ZH.pdf'
OUT=ROOT/'tmp/original-style-repair/2023'
PROOF_DIR=Path(os.environ.get('HASLA_CPHO2023_PROOF_DIR',str(OUT)))
FONT_CACHE=Path(os.environ.get('HASLA_CPHO2023_FONT_CACHE',str(OUT/'fonts')))
_PROSE_SYMBOL_FONT=None

def proof_path(number,lang):
    return PROOF_DIR/f'CPhO_2023_p{number}_{lang.upper()}_proof.pdf'

def available_width(slot,lang):
    return slot['right']-slot['origin'][0]+(slot.get('en_left_extension',0)if lang=='en'else 0)

def prose_symbol_font():
    """Use a complete same-face font; the source subset has a blank OR glyph."""
    global _PROSE_SYMBOL_FONT
    if _PROSE_SYMBOL_FONT is None:
        from fontTools.ttLib import TTFont
        from fontTools.pens.boundsPen import BoundsPen
        installed=Path('C:/Windows/Fonts/simsun.ttc')
        path=FONT_CACHE/'SimSun-complete-face0.ttf';path.parent.mkdir(parents=True,exist_ok=True)
        marker=path.with_suffix('.source-sha256')
        signature=hashlib.sha256(installed.read_bytes()).hexdigest()
        if not path.exists()or not marker.exists()or marker.read_text('ascii')!=signature:
            face=TTFont(installed,fontNumber=0,recalcTimestamp=False)
            assert face['name'].getDebugName(6)=='SimSun'and face['OS/2'].usWeightClass==400
            glyphset=face.getGlyphSet();mapping=face.getBestCmap()
            for char in '∝∨':
                name=mapping.get(ord(char));pen=BoundsPen(glyphset)
                if name:glyphset[name].draw(pen)
                if pen.bounds is None or face['hmtx'][name][0]<=0:raise ValueError('Same-face connective lacks actual ink')
            face.save(path);face.close();marker.write_text(signature,'ascii')
        _PROSE_SYMBOL_FONT=path
    return _PROSE_SYMBOL_FONT

def characters(page):
    result=[]
    for bi,block in enumerate(page.get_text('rawdict')['blocks']):
        if block['type']:continue
        for li,line in enumerate(block['lines']):
            for span in line['spans']:
                for char in span['chars']:
                    result.append(dict(char,font=span['font'],size=span['size'],flags=span['flags'],color=span['color'],block=bi,line=li,index=len(result)))
    return result

def horizontal_rules(page):
    """Keep original fraction bars, answer rules and straight figure rules clear."""
    rules=[]
    for drawing in page.get_drawings():
        pad=max(.25,float(drawing.get('width')or 0)/2+.25)
        for item in drawing['items']:
            if item[0]=='l'and drawing.get('color')is not None:
                a,b=item[1:3]
                if abs(a.y-b.y)<.1 and abs(a.x-b.x)>2:
                    rules.append([min(a.x,b.x)-pad,min(a.y,b.y)-pad,max(a.x,b.x)+pad,max(a.y,b.y)+pad])
            if item[0]=='re'and drawing.get('fill')is not None:
                rect=fitz.Rect(item[1])
                if rect.height<=1.5 and rect.width>2:rules.append(list(rect+(-.25,-.25,.25,.25)))
    return rules

def extract(pages):
    original=fitz.open(SOURCE);old=json.loads((ROOT/'tmp/cpho-build/2023-reviewed/translation.json').read_text(encoding='utf8'))
    data={'source':str(SOURCE.relative_to(ROOT)).replace('\\','/'),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'pages':[]}
    for number in pages:
        page=original[number-1];chars=characters(page);protected=native_form_glyphs(SOURCE,number)
        protected_indices={c['index']for c in chars if any(abs(c['origin'][0]-g['origin'][0])<.03 and abs(c['origin'][1]-g['origin'][1])<.03 for g in protected)}
        rows=cjk.prose_rows([c for c in chars if c['index']not in protected_indices]);slots=[]
        math_rects=[fitz.Rect(m['source_rect'])for e in old['entries']if e['page']==number-1 for m in e['math']if m.get('source_rect')]
        image_rects=[fitz.Rect(im['bbox'])for im in page.get_image_info()]
        if number==5:image_rects.append(fitz.Rect(428,72,508,193))
        for ri,row in enumerate(rows):
            owned=list(row['chars']);heading=any(c['size']>13 for c in owned)
            if heading:
                owned=[c for c in chars if c['index']not in protected_indices and abs(c['origin'][1]-row['baseline'])<.03 and c['size']>13]
            groups=[]
            owned_ids={c['index']for c in owned}
            inline_native=[c for c in chars if c['index']not in owned_ids and not c['c'].isspace()and abs(c['origin'][1]-row['baseline'])<row['size']*.45]if number>=15 else[]
            for char in sorted(owned,key=lambda c:c['origin'][0]):
                same_style=groups and (char['font'],char['size'],char['flags'],char['color'])==(groups[-1][-1]['font'],groups[-1][-1]['size'],groups[-1][-1]['flags'],groups[-1][-1]['color'])
                crosses_native=groups and any(groups[-1][-1]['origin'][0]+.1<c['origin'][0]<char['origin'][0]-.1 for c in inline_native)
                if groups and same_style and not crosses_native and char['origin'][0]-groups[-1][-1]['bbox'][2]<3:groups[-1].append(char)
                else:groups.append([char])
            owned_ids={c['index']for c in owned}
            for si,group in enumerate(groups):
                while group and group[0]['c'].isspace():group=group[1:]
                while group and group[-1]['c'].isspace():group=group[:-1]
                if not group:continue
                # Keep the original black lenticular bracket, a formatting
                # glyph preceding the translated alternative derivation.
                if ((number==2 and ri==21)or(number==3 and ri==4))and si==0 and group[0]['c']=='【':group=group[1:]
                bracket_right=None
                if group[0]['c']=='【'and group[-1]['c']=='】':
                    bracket_right=group[-1]['bbox'][0]-.25
                    group=group[1:-1]
                first=group[0];rect=fitz.Rect(first['bbox'])
                for char in group[1:]:rect|=fitz.Rect(char['bbox'])
                size=first['size'];baseline=first['origin'][1];right=505.6
                if bracket_right is not None:right=bracket_right
                elif heading:right=rect.x1
                else:
                    obstacles=[]
                    for char in chars:
                        if char['index']in owned_ids or char['c'].isspace():continue
                        if abs(char['origin'][1]-baseline)<=size*.45 and char['bbox'][0]>=rect.x1-size*.12:obstacles.append(char['bbox'][0]-.6)
                    for box in math_rects+image_rects:
                        if box.y0<baseline+size*.15 and box.y1>baseline-size*.8 and box.x0>=rect.x1-size*.12:obstacles.append(box.x0-.6)
                    later=[g[0]['bbox'][0]-.6 for g in groups[si+1:]if g[0]['bbox'][0]>rect.x1]
                    right=min([right,*obstacles,*later])
                    right=max(rect.x1,right)
                role=source_font_role(first['font'],first['flags'])
                slots.append(dict(id=f'{number}-{ri}-{si}',source=''.join(c['c']for c in group),source_font=first['font'],size=size,flags=first['flags'],color=first['color'],role=role,
                    origin=list(first['origin']),rect=list(rect),right=right,align='center'if heading else 'left',
                    allowed_rect=[rect.x0-.15,baseline-size*1.1,max(rect.x1,right)+.15,baseline+size*.3],glyphs=group,ko='',en=''))
        # Caption numbers are prose, not physical notation. Translate a complete
        # caption in its original centred box rather than pinning its digits.
        if number==1:
            caption_bands=[(9,340,490),(13,80,320),(13,320,510)]
            caption_slots=[]
            for ci,(rowno,left,right)in enumerate(caption_bands):
                previous=[s for s in slots if s['id'].split('-')[1]==str(rowno)and left<=s['origin'][0]<right]
                baseline=previous[0]['origin'][1]
                group=sorted([c for c in chars if not c['c'].isspace()and abs(c['origin'][1]-baseline)<.1 and left<=c['origin'][0]<right],key=lambda c:c['origin'][0])
                rect=fitz.Rect(group[0]['bbox'])
                for c in group[1:]:rect|=fitz.Rect(c['bbox'])
                slot={**previous[0],'id':f'{number}-caption-{ci}','source':''.join(c['c']for c in group),'glyphs':group,'origin':[rect.x0,baseline],'rect':list(rect),'right':rect.x1,'align':'center',
                    'allowed_rect':[rect.x0-.15,baseline-11.616,rect.x1+.15,baseline+3.168]}
                caption_slots.append(slot)
                slots=[s for s in slots if s not in previous]
            slots+=caption_slots
        if number==3:
            # The source expands this one prose line with 3.7pt tracking.
            # It contains no interleaved mathematics; keep one fixed baseline
            # and the complete original line box for the translation.
            parts=[s for s in slots if s['id'].startswith('3-12-')]
            if len(parts)>1:
                merged={**parts[0],'source':''.join(s['source']for s in parts),'glyphs':[g for s in parts for g in s['glyphs']]}
                merged['rect'][2]=parts[-1]['rect'][2];merged['right']=parts[-1]['right'];merged['allowed_rect'][2]=parts[-1]['allowed_rect'][2]
                slots=[s for s in slots if s not in parts]+[merged]
        if number==11:
            # Question numbers and their score are prose, not formulae. Keep
            # the complete fixed-size prefix before the first native alpha.
            parts=[s for s in slots if s['id']in ['11-0-0','11-0-1']]
            group=sorted([c for c in chars if abs(c['origin'][1]-82.58)<.1 and parts[0]['origin'][0]<=c['origin'][0]<parts[-1]['right']],key=lambda c:c['origin'][0])
            merged={**parts[0],'id':'11-header','source':''.join(c['c']for c in group),'glyphs':group,'right':parts[-1]['right']}
            merged['rect'][2]=parts[-1]['rect'][2];merged['allowed_rect'][2]=parts[-1]['allowed_rect'][2]
            slots=[s for s in slots if s not in parts]+[merged]
        if number==14:
            old=next(s for s in slots if s['id']=='14-10-0');cut=next(i for i,c in enumerate(old['glyphs'])if c['c']=='】');pieces=[]
            for sid,group,right in [('14-method-4',old['glyphs'][1:cut],old['glyphs'][cut]['bbox'][0]-.25),('14-method-4-gloss',old['glyphs'][cut+1:],old['right'])]:
                rect=fitz.Rect(group[0]['bbox'])
                for c in group[1:]:rect|=fitz.Rect(c['bbox'])
                pieces.append({**old,'id':sid,'source':''.join(c['c']for c in group),'glyphs':group,'origin':list(group[0]['origin']),'rect':list(rect),'right':right,'allowed_rect':[rect.x0-.15,old['allowed_rect'][1],right+.15,old['allowed_rect'][3]]})
            slots=[s for s in slots if s is not old]+pieces
        if number in[17,26]:
            for sid in(['17-6-2','17-12-2']if number==17 else['26-4-2']):
                old=next(s for s in slots if s['id']==sid)
                left=next(i for i,c in enumerate(old['glyphs'])if c['c']=='【')
                right=next(i for i,c in enumerate(old['glyphs'])if c['c']=='】')
                pieces=[]
                for suffix,group,bound in [('unit',old['glyphs'][:left],old['glyphs'][left]['bbox'][0]-.25),('method',old['glyphs'][left+1:right],old['glyphs'][right]['bbox'][0]-.25)]:
                    rect=fitz.Rect(group[0]['bbox'])
                    for c in group[1:]:rect|=fitz.Rect(c['bbox'])
                    pieces.append({**old,'id':sid+'-'+suffix,'source':''.join(c['c']for c in group),'glyphs':group,'origin':list(group[0]['origin']),'rect':list(rect),'right':bound,'allowed_rect':[rect.x0-.15,old['allowed_rect'][1],bound+.15,old['allowed_rect'][3]]})
                slots=[s for s in slots if s is not old]+pieces
        if number==24:
            old=next(s for s in slots if s['id']=='24-9-1')
            left=next(i for i,c in enumerate(old['glyphs'])if c['c']=='【')
            right=next(i for i,c in enumerate(old['glyphs'])if c['c']=='】')
            pieces=[]
            for suffix,group,bound in [('prefix',old['glyphs'][:left],old['glyphs'][left]['bbox'][0]-.25),('method',old['glyphs'][left+1:right],old['glyphs'][right]['bbox'][0]-.25)]:
                rect=fitz.Rect(group[0]['bbox'])
                for c in group[1:]:rect|=fitz.Rect(c['bbox'])
                pieces.append({**old,'id':'24-9-1-'+suffix,'source':''.join(c['c']for c in group),'glyphs':group,'origin':list(group[0]['origin']),'rect':list(rect),'right':bound,'allowed_rect':[rect.x0-.15,old['allowed_rect'][1],bound+.15,old['allowed_rect'][3]]})
            slots=[s for s in slots if s is not old]+pieces
        if number in[29,30]:
            targets=['29-0-0','29-2-0','29-10-0','29-0-2']if number==29 else['30-1-0','30-3-0','30-1-1','30-1-2']
            for sid in targets:
                old=next(s for s in slots if s['id']==sid);group=old['glyphs'];right=old['right']
                if sid in['29-0-2','30-3-0']:
                    if group[-1]['c']!='】':raise ValueError('Expected native closing note bracket')
                    right=min(right,group[-1]['bbox'][0]-.25);group=group[:-1]
                else:
                    expected='（'if sid=='30-1-1'else'）'if sid=='30-1-2'else'【'
                    if group[0]['c']!=expected:raise ValueError('Expected native note punctuation')
                    group=group[1:]
                rect=fitz.Rect(group[0]['bbox'])
                for c in group[1:]:rect|=fitz.Rect(c['bbox'])
                replacement={**old,'source':''.join(c['c']for c in group),'glyphs':group,'origin':list(group[0]['origin']),'rect':list(rect),'right':right,'allowed_rect':[rect.x0-.15,old['allowed_rect'][1],right+.15,old['allowed_rect'][3]]}
                slots=[replacement if s is old else s for s in slots]
        used={c['index']for s in slots for c in s['glyphs']}
        for ci,char in enumerate(c for c in chars if c['index']not in used and c['index']not in protected_indices and c['size']>=9 and cjk.HAN.search(c['c'])):
            size=char['size'];rect=fitz.Rect(char['bbox']);x,y=char['origin']
            slots.append(dict(id=f'{number}-label-{ci}',source=char['c'],source_font=char['font'],size=size,flags=char['flags'],color=char['color'],role=source_font_role(char['font'],char['flags']),origin=[x,y],rect=list(rect),right=rect.x1,align='left',allowed_rect=[rect.x0-.15,y-size*1.1,rect.x1+.15,y+size*.3],glyphs=[char],ko='',en=''))
        if number==5:
            # Korean places the shared request verb after the final variable.
            # Replace the source sentence-ending prose period in its original
            # baseline, using the existing blank at the end of that line.
            ch=next(c for c in chars if c['c']=='。'and abs(c['origin'][0]-120.5)<.05 and abs(c['origin'][1]-435.19)<.05)
            rect=fitz.Rect(ch['bbox']);size=ch['size'];x,y=ch['origin']
            slots.append(dict(id='5-19-tail',source=ch['c'],source_font=ch['font'],size=size,flags=ch['flags'],color=ch['color'],role=source_font_role(ch['font'],ch['flags']),origin=[x,y],rect=list(rect),right=505.6,align='left',allowed_rect=[x-.15,y-size*1.1,505.75,y+size*.3],glyphs=[ch],ko='',en=''))
        traces=page.get_texttrace()
        for slot in slots:
            matching=[sp for sp in traces for ch in sp['chars']if ch[0]==ord(slot['glyphs'][0]['c'])and abs(ch[2][0]-slot['glyphs'][0]['origin'][0])<.02 and abs(ch[2][1]-slot['glyphs'][0]['origin'][1])<.02]
            modes={sp['type']for sp in matching};slot['render_mode']=2 if modes=={0,1}else 0
            slot['border_width']=next(sp['linewidth']for sp in matching if sp['linewidth']is not None)if slot['render_mode']==2 else 1
        for slot in slots:
            if any(abs(c['origin'][0]-g['origin'][0])<.03 and abs(c['origin'][1]-g['origin'][1])<.03 for c in slot['glyphs']for g in protected):raise ValueError('Prose overlaps original mathematical Form: '+slot['id'])
            if len(slot['source'].strip())==1 and slot['source'].strip()in'（）':slot['cell_center']=True
            # A translated Korean phrase needs a normal word boundary inside
            # these very short original cells. Adjust only the blank advance;
            # glyph outlines, point size and source baselines stay unchanged.
            if slot['id']=='1-23-1':slot['word_space']=1.5
            if slot['id']=='1-23-2':slot['word_space']=2.0
            if slot['id']=='4-0-5':slot['word_space']=2.3
            if slot['id']=='5-18-1':slot['word_space']=1.0
            if slot['id']=='6-13-1':slot['word_space']=1.0
            if slot['id']=='7-9-1':slot['word_space']=1.0
            if slot['id']=='8-6-0':slot['word_space']=1.0
            if slot['id']=='9-0-1':slot['word_space']=.5
            if slot['id']=='11-27-2':slot['word_space']=.5
            if slot['id']=='11-4-2':slot['word_space']=2.25
            if slot['id']=='11-8-2':slot['word_space']=1.4
            if slot['id']=='11-9-2':slot['word_space']=2.2
            if slot['id']=='14-11-2':slot['word_space']=2.0
            if slot['id']=='14-12-1':slot['word_space']=1.0
            if slot['id']=='15-2-3':slot['word_space']=2.0
            if slot['id']=='15-1-1':slot['word_space']=2.2
            if slot['id']=='23-0-2':
                # The final Korean glyph's unpainted side bearing ends after
                # the cell; its actual ink stays within the original prose box.
                slot['right']+=.5;slot['advance_end_blank_allowance_pt']=.5
            if slot['id']=='23-6-0':slot['word_space']=.2
            if slot['id']=='27-5-2':slot['word_space']=1.0
            if number==11 and slot['id']in ['11-3-0','11-3-1','11-3-2']:
                slot['origin'][0]-=10;slot['allowed_rect'][0]-=10;slot['align']='right'
            if slot['id']=='2-8-0':slot['align']='right'
            if slot['id']=='2-12-0':
                slot['origin'][0]-=15;slot['allowed_rect'][0]-=15;slot['align']='right'
        deferred=[g for g in protected if cjk.HAN.search(g['c'])and g['size']>=9]
        data['pages'].append(dict(number=number,page_rect=list(page.rect),slots=slots,protected_glyph_origins=[g['origin']for g in protected],native_rule_rects=horizontal_rules(page),deferred_figure_labels=deferred))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'slots.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUT/'source-slots.tsv').write_text('\n'.join('\t'.join([s['id'],s['source'],f'{s["source_font"]} {s["size"]:.3f}pt',f'width={s["right"]-s["origin"][0]:.3f}',f'y={s["origin"][1]:.3f}'])for p in data['pages']for s in p['slots'])+'\n',encoding='utf8')
    print('extracted',sum(len(p['slots'])for p in data['pages']),'prose slots')
    return data

def text_runs(slot,text,lang):
    latin=prose_symbol_font()if lang=='en'and'SimSun'in slot['source_font']else Path('C:/Windows/Fonts')/(('times'if slot['role'].startswith('serif')else'arial')+('bd'if'Bold'in slot['source_font']or slot['flags']&16 else'')+'.ttf')
    if lang=='en'and'SimHei'in slot['source_font']:
        # Complete same-family/same-version SimHei, recovered read-only from
        # the signed official Microsoft font CAB; original resources stay put.
        from cpho_official_hans_fonts import font_face
        latin=font_face('simhei.ttf')
    runs=[]
    for char in text:
        path=prose_symbol_font()if char in '∨∝'else latin if lang=='en'or(char.isascii()and not char.isspace())else FONTS[slot['role']]
        split_spaces=bool(slot.get('word_space')or lang=='en'and'SimSun'in slot['source_font'])
        if split_spaces and char==' ':runs.append((path,char))
        elif runs and runs[-1][0]==path and not(split_spaces and runs[-1][1]==' '):runs[-1]=(path,runs[-1][1]+char)
        else:runs.append((path,char))
    return runs

def run_advance(slot,font,run,lang=None):
    if lang=='en'and'en_word_space'in slot and run==' ':return slot['en_word_space']
    if slot.get('word_space')and run==' ':return slot['word_space']
    if run==' 'and lang=='en'and'SimSun'in slot['source_font']:return slot['size']*.25
    return font.text_length(run,fontsize=slot['size'])

def build(data,translations,lang,resume=False):
    dependencies=[Path(__file__),*(ROOT/'tools'/name for name in ['pdf_original_text_ops.py','pdf_original_style_audit.py','pdf_original_style_fonts.py','pdf_original_graphics_ink.py','pdf_original_image_ink.py','cpho_2023_original_labels.py']),figure_language.AUTHOR/'label-plan.json']
    engine_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in dependencies}
    for page_data in data['pages']:
        number=page_data['number'];slots=page_data['slots'];fonts=defaultdict(str)
        target=proof_path(number,lang);target.parent.mkdir(parents=True,exist_ok=True)
        inputs=dict(source_sha256=data['source_sha256'],engine=engine_hashes,page={k:([dict((a,b)for a,b in s.items()if not a.startswith('_'))for s in v]if k=='slots'else v)for k,v in page_data.items()},translation={s['id']:translations[s['id']][lang]for s in slots})
        fingerprint=hashlib.sha256(json.dumps(inputs,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        if resume and target.exists()and target.with_suffix('.qa.json').exists():
            prior=json.loads(target.with_suffix('.qa.json').read_text('utf8'))
            if prior.get('passed')and prior.get('input_sha256')==fingerprint and prior['proof_sha256']==hashlib.sha256(target.read_bytes()).hexdigest():
                print(target.name,'reviewed current inputs; retained',flush=True);continue
        for slot in slots:
            if slot['id']not in translations:raise ValueError('Missing '+slot['id'])
            text=translations[slot['id']][lang]
            if slot['source']in['（','）']and text!=slot['source']:
                raise ValueError('Keep original standalone formatting punctuation: '+slot['id'])
            slot['_pass']=text==slot['source']
            if slot['_pass']:continue
            for path,run in text_runs(slot,text,lang):fonts[path]+=run
        subsetted={path:subset_font(path,text,FONT_CACHE)for path,text in fonts.items()}
        selected=[c for s in slots if not s['_pass']for c in s['glyphs']if not c['c'].isspace()]
        raw,count=suppress_prose(SOURCE,number,selected);doc=fitz.open(stream=raw,filetype='pdf');page=doc[0];placements=[]
        for slot in slots:
            if slot['_pass']:continue
            text=translations[slot['id']][lang];runs=text_runs(slot,text,lang)
            width=sum(run_advance(slot,fitz.Font(fontfile=str(subsetted[path])),run,lang)for path,run in runs)
            available=available_width(slot,lang)
            if width>available+.02:raise ValueError(f'{slot["id"]}/{lang}: {width:.2f}pt exceeds {available:.2f}pt: {text}')
            point=slot['origin'].copy()
            if lang=='en':point[0]-=slot.get('en_left_extension',0)
            align=slot.get('en_align',slot['align'])if lang=='en'else slot['align']
            if align=='center':point[0]+=(available-width)/2
            elif align=='right':point[0]+=available-width
            if slot.get('cell_center')or text.strip()in[',','(',')']:
                point[0]+=(min(available,slot['rect'][2]-slot['origin'][0])-width)/2
            start=point.copy()
            for path,run in runs:
                name='Translation'+str(list(subsetted).index(path))
                page.insert_text(point,run,fontname=name,fontfile=str(subsetted[path]),fontsize=slot['size'],color=tuple(((slot['color']>>shift)&255)/255 for shift in [16,8,0]),render_mode=slot['render_mode'],border_width=slot['border_width']/slot['size'],miter_limit=10)
                point[0]+=run_advance(slot,fitz.Font(fontfile=str(subsetted[path])),run,lang)
            placements.append(dict(id=slot['id'],text=text,size=slot['size'],source_size=slot['size'],origin=start,source_origin=slot['origin'],fonts=[str(path)for path,run in runs],source_font=slot['source_font'],render_mode=slot['render_mode'],border_width=slot['border_width']))
        before_labels=Counter(key(g)for g in glyphs(page))
        labels=figure_language.apply(page,number,lang)
        label_spec=figure_language.audit_spec(number)
        mutable=label_spec['mutable_form_prose_origins']
        added_label_glyphs=[]
        for g in glyphs(page):
            token=key(g)
            if before_labels[token]:before_labels[token]-=1
            else:added_label_glyphs.append(g)
        new_label_regions=[]
        for label in labels:
            font=fitz.Font(fontfile=str(ROOT/label['font_path']))
            for run in label['placed_runs']:
                x,y=run['origin'];advance=font.text_length(run['text'],fontsize=label['size'])
                def in_run(g):
                    gx,gy=g['origin']
                    return (abs(gy-y)<.03 and x-.03<=gx<=x+advance+.03)if run.get('rotate',0)==0 else(abs(gx-x)<.03 and y-advance-.03<=gy<=y+.03)
                candidates=[g for g in added_label_glyphs if in_run(g)and not g['c'].isspace()]
                if candidates:
                    rect=figure_language.native_prose_ink(page,candidates)
                    new_label_regions.append([rect[0]-.125,rect[1]-.125,rect[2]+.125,rect[3]+.125])
        doc.save(target,garbage=0,deflate=False);doc.close()
        body_regions=[([s['allowed_rect'][0]-s.get('en_left_extension',0),*s['allowed_rect'][1:]]if lang=='en'else s['allowed_rect'])for s in slots]
        spec=dict(source_page=number,proof_page=1,allowed_rects=body_regions+label_spec['source_language_regions']+new_label_regions,erased_glyph_origins=[c['origin']for c in selected]+mutable,protected_glyph_origins=[p for p in page_data.get('protected_glyph_origins',[])if not any(close_origin(p,q)for q in mutable)],protected_rects=page_data.get('native_rule_rects',[]))
        report=audit(SOURCE,target,spec)
        graphics=graphics_audit(SOURCE,target,number,language_regions=[s['allowed_rect']for s in slots if s['id']=='2-8-0']+label_spec['source_language_regions'])
        if graphics['original_graphics_ink_changed_pixels']or not graphics['original_image_and_smask_programs_and_positions_identical']:
            raise ValueError('Original graphics audit failed: '+str(graphics))
        report['graphics_audit']=graphics
        report['audit_spec']=spec
        report['figure_language']=labels
        with fitz.open(SOURCE)as original,fitz.open(target)as proof:
            form_origins=[g['origin']for g in native_form_glyphs(SOURCE,number)]
            source_forms=Counter(key(g)for g in glyphs(original[number-1])if any(close_origin(g['origin'],p)for p in form_origins))
            proof_forms=Counter(key(g)for g in glyphs(proof[0]))
            report['original_form_glyph_metadata_changed']=list((source_forms-proof_forms).elements())
            def fonts(d,p):return Counter((f[3],hashlib.sha256(d.extract_font(f[0])[3]).hexdigest())for f in p.get_fonts(full=True)if not f[4].startswith(('Translation','FigureLanguage')))
            report['original_font_programs_identical']=fonts(original,original[number-1])==fonts(proof,proof[0])
        report['original_form_raw_and_decoded_programs_identical']=form_programs(SOURCE,number)==form_programs(target,1)
        if report['original_form_glyph_metadata_changed']or not report['original_font_programs_identical']or not report['original_form_raw_and_decoded_programs_identical']:raise ValueError('Original font/Form program or metadata changed')
        report.update(removed_prose_glyphs=count,placements=placements,autoshrink=False,reflow=False,math_images=False,figure_replacement=False,input_sha256=fingerprint,engine_sha256=engine_hashes)
        report['passed']=not(report['native_glyphs_changed']or report['changed_pixels_outside_prose']or report['changed_pixels_in_native_glyph_neighborhood'])
        target.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        if report['native_glyphs_changed']or report['changed_pixels_outside_prose']or report['changed_pixels_in_native_glyph_neighborhood']:raise ValueError('Original-native audit failed: '+str(target))
        print(target.name,report['native_glyphs_checked'],'native glyphs unchanged',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--extract',action='store_true');parser.add_argument('--pages',nargs='+',type=int,default=[1]);parser.add_argument('--build',action='store_true');args=parser.parse_args()
    data=extract(args.pages)if args.extract else json.loads((OUT/'slots.json').read_text(encoding='utf8'))
    if args.build:
        rows={key:{'ko':ko,'en':en}for key,ko,en in (row.split('\t')for row in (ROOT/'tools/ko/cpho/2023/original-style.tsv').read_text(encoding='utf8').splitlines()if row.strip())}
        for lang in ['ko','en']:build(data,rows,lang)
