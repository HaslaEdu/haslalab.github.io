"""Preserve KPhC official answer reprints and extract native 2020/21 answers.

No legacy answer data is added to the site's automatic OMR grading catalog.
The originals came from the 2022 public archive described in the source audit.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'tmp/kphc_answers_research'
ARCHIVE=WORK/'privatenote-archive-0.zip'
INPUTS=WORK/'privatenote-archive-0/물올 기출'
OUTPUT=ROOT/'pdfx/kphe'
SOURCE_PAGE='https://blog.privatenote.co.kr/8'
OFFICIAL_PAGE='https://kphc.kps.or.kr/bbs/index.asp?bbs_code=withexam_middle&page=1&number=6519&mode=view'
ARCHIVE_SHA='d5aa2c44564d5d5ceab50e644a44acb96c9317fe84a0e93500990fe2bb02c7c4'
KEYS_PATH=ROOT/'tools/kphc_official_keys.json'
PAPER_NAMES={
    2015:{'T1':'2015P_1.pdf','T2':'2015P_2.pdf'},
    2016:{'T':'2016P.pdf'},2017:{'T':'2017P.pdf'},2018:{'T':'2018P.pdf'},2019:{'T':'2019P.pdf'},
    2020:{'T':'2020PA.pdf'},2021:{'T':'2021PA.pdf'},
    2022:{'T1':'2022P-1.pdf','T2':'2022P-2.pdf'}}


def sha(data): return hashlib.sha256(data).hexdigest()


def get_inputs():
    WORK.mkdir(parents=True,exist_ok=True)
    if not ARCHIVE.exists():
        from bs4 import BeautifulSoup
        raw=urllib.request.urlopen(urllib.request.Request(SOURCE_PAGE,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
        soup=BeautifulSoup(raw,'html.parser')
        link=next(a['href'] for a in soup.find_all('a',href=True) if '.zip' in a.get_text().lower())
        data=urllib.request.urlopen(urllib.request.Request(link,headers={'User-Agent':'Mozilla/5.0','Referer':SOURCE_PAGE}),timeout=60).read()
        if sha(data)!=ARCHIVE_SHA: raise ValueError('The public source archive changed; review before publishing')
        ARCHIVE.write_bytes(data)
    assert sha(ARCHIVE.read_bytes())==ARCHIVE_SHA
    directory=INPUTS.parent.resolve()
    with zipfile.ZipFile(ARCHIVE) as archive:
        for member in archive.infolist():
            if member.is_dir(): continue
            target=(directory/member.filename).resolve()
            assert target.is_relative_to(directory)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.read(member))


def parse_choices(value):
    value=re.sub(r'[\x00-\x1f]',' ',value).strip()
    if value=='*':
        return {'answer_type':'full_credit','accepted_responses':None,'official_display':'*',
            'scoring_override':{'type':'full_credit_for_every_examinee','reason':'한국물리학회 교육위원회 심의에 따른 1교시 2번 전원 득점 처리'}}
    translated=value.translate(str.maketrans('①②③④⑤','12345'))
    choices=[int(x) for x in re.findall(r'[1-5]',translated)]
    if '또는' in value:
        return {'answer_type':'alternative_single_choice','accepted_responses':[[n] for n in choices],
            'official_display':value,'note':'각 선택지 하나씩을 별도로 인정하며, 두 선택지 동시 선택을 요구하는 문제가 아님.'}
    return {'answer_type':'exact_choice_set','accepted_responses':[choices],
        'official_display':value,'multiple_select':len(choices)>1}


def table_answers(year):
    import pymupdf as fitz
    path=INPUTS/f'{year}A.pdf'
    document=fitz.open(path)
    tables=document[0].find_tables().tables
    assert len(tables)==1
    table=tables[0]
    rows=table.extract()[1:]
    parts={part:[] for part in PAPER_NAMES[year]}
    period=1
    for index,row in enumerate(rows):
        if year==2015:
            number=int(row[0])
            for column,part in [(1,'T1'),(2,'T2')]:
                parts[part].append({'number':number,**parse_choices(row[column]),'source_page':1,
                    'source_rect':[round(float(x),3) for x in table.rows[index+1].cells[column]]})
        elif year==2022:
            if row[0]:period=int(row[0])
            parts[f'T{period}'].append({'number':int(row[1]),**parse_choices(row[2]),'source_page':1,
                'source_rect':[round(float(x),3) for x in table.rows[index+1].cells[2]]})
        else:
            number=int(re.search(r'\d+',row[0]).group())
            parts['T'].append({'number':number,**parse_choices(row[1]),'source_page':1,
                'source_rect':[round(float(x),3) for x in table.rows[index+1].cells[1]]})
    for part,answers in parts.items():
        expected=20 if year==2015 else 15 if year==2022 else 30
        assert [r['number'] for r in answers]==list(range(1,expected+1))
    return document,parts


def inline_answers(year,old_parts):
    import numpy as np
    import pymupdf as fitz
    from PIL import Image
    document=fitz.open(INPUTS/f'{year}PA.pdf')
    prior={r['number']:r for r in old_parts.get('T',{}).get('answers',[])}
    answers=[]
    for index,page in enumerate(document):
        blocks=[]
        for block in page.get_text('dict')['blocks']:
            if 'lines' not in block:continue
            text='\n'.join(''.join(span['text'] for span in line['spans']) for line in block['lines'])
            if re.search(r'\(?답\)',text):blocks.append((block,text))
        blocks.sort(key=lambda item:item[0]['bbox'][0])
        if not blocks:continue
        assert len(blocks)==2
        for column,(block,text) in enumerate(blocks):
            number=(index-1)*2+column+1
            box=fitz.Rect(block['bbox'])
            marker_line=next(line for line in block['lines'] if re.search(r'\(?답\)',''.join(span['text'] for span in line['spans'])))
            marker_top=marker_line['bbox'][1]
            selected=[block]
            for other in page.get_text('dict')['blocks']:
                if other.get('type')==0 and tuple(other['bbox'])==tuple(block['bbox']):continue
                other_box=fitz.Rect(other['bbox'])
                if (other_box.x0>page.rect.width/2)!=bool(column):continue
                other_text='\n'.join(''.join(span['text'] for span in line['spans']) for line in other.get('lines',[]))
                if re.fullmatch(r'page\s*\d+',other_text.strip(),re.I):continue
                center=(other_box.y0+other_box.y1)/2
                # The published page has one question per column. Text below
                # its answer marker is the answer's continuation, including
                # the two complete statements in 2020 Q16.
                below=other_box.y0>=marker_top-1
                math=other.get('type')==0 and not re.search('[가-힣]',other_text) and box.y0-10<=center<=box.y1+10 and other_box.x0<=box.x1+20
                # 2020 Q25 is a graphical answer whose image straddles 답).
                image=other.get('type')==1 and other_box.y0<box.y1 and other_box.y1>box.y0
                response_heading=year==2021 and number==26 and '소비전력' in other_text.replace(' ','') and box.y0-30<=other_box.y0<marker_top
                if below or math or image or response_heading:selected.append(other)
            candidate=fitz.Rect(box)
            for other in selected:candidate|=fitz.Rect(other['bbox'])
            candidate+=(-2,-2,2,2)
            pix=page.get_pixmap(matrix=fitz.Matrix(3,3),clip=candidate,colorspace=fitz.csRGB,alpha=False)
            rgb=np.frombuffer(pix.samples,dtype='uint8').reshape(pix.height,pix.width,3)
            yy,xx=np.where(np.min(rgb,axis=2)<245)
            assert len(xx)
            clip=fitz.Rect((pix.x+xx.min())/3-2,(pix.y+yy.min())/3-2,
                (pix.x+xx.max()+1)/3+2,(pix.y+yy.max()+1)/3+2)
            old=prior.get(number,{})
            if old.get('source_rect_override'):clip=fitz.Rect(old['source_rect_override'])
            record={'number':number,'answer_type':'published_expression_or_statement_set',
                'raw_pdf_text':'\n'.join('\n'.join(''.join(span['text'] for span in line['spans']) for line in other.get('lines',[])) for other in sorted(selected,key=lambda b:(b['bbox'][1],b['bbox'][0]))),
                'source_page':index+1,'source_rect':[round(float(x),3) for x in clip],
                'source_coordinate_system':'native PDF points, top-left origin',
                'source_content':'Original KPS-published answer glyphs and equation objects following 답).'}
            for key in ('answer_type','answer_text','answer_latex','statement_set','statement_texts','response_fields','source_rect_override','visual_verified'):
                if key in old:record[key]=old[key]
            preview=page.get_pixmap(matrix=fitz.Matrix(3,3),clip=clip,colorspace=fitz.csRGB,alpha=False)
            preview.save(WORK/f'{year}-answer-{number:02d}.png')
            answers.append(record)
    assert [r['number'] for r in answers]==list(range(1,31))
    return document,{'T':answers}


def excerpt_pdf(year,document,answers,target):
    import pymupdf as fitz
    from kphe_fonts import font_path
    result=fitz.open()
    fontfile=str(font_path('Gulim'))
    for start in (0,15):
        page=result.new_page(width=595.276,height=841.89)
        page.insert_font(fontname='KPhCHeading',fontfile=fontfile)
        page.insert_text((42,46),f'{year}년 한국중학생물리대회 정답',fontname='KPhCHeading',fontsize=16)
        page.insert_text((42,66),f'{start+1}–{start+15}',fontname='KPhCHeading',fontsize=10,color=(.25,.25,.25))
        top=88
        for answer in answers[start:start+15]:
            clip=fitz.Rect(answer['source_rect'])
            height=max(36,clip.height+8)
            assert top+height<805,(year,start,answer['number'],top,height,answer['source_rect'])
            page.insert_text((45,top+20),f'{answer["number"]}.',fontname='KPhCHeading',fontsize=11)
            target_rect=fitz.Rect(94,top+(height-clip.height)/2,94+clip.width,top+(height+clip.height)/2)
            page.show_pdf_page(target_rect,document,answer['source_page']-1,clip=clip,keep_proportion=True)
            answer['excerpt_pdf_page']=len(result)
            answer['excerpt_pdf_rect']=[round(float(x),3) for x in target_rect]
            page.draw_line((42,top+height),(553,top+height),color=(.87,.87,.87),width=.35)
            top+=height
    original_sha=sha((INPUTS/f'{year}PA.pdf').read_bytes())
    result.set_metadata({'title':f'{year}년 한국중학생물리대회 공식 원문 정답 발췌',
        'author':'한국물리학회 (원문 답); HaslaLab (답 영역 발췌)',
        'subject':f'Original answer glyph excerpts from {year}PA.pdf; SHA256={original_sha}; source pages 2-16; archive={ARCHIVE_SHA}; {SOURCE_PAGE}',
        'creator':'HaslaLab kphc_answers_build.py; native PDF answer clips; original answer text not retyped',
        'keywords':'KPhC, 공식 원문 답 발췌, indirect public preservation, source SHA256, native glyphs'})
    result.subset_fonts()
    result.save(target,garbage=4,deflate=True)
    return len(result)


def preview_sheets(year,answers):
    from PIL import Image,ImageDraw,ImageFont
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for start in (0,10,20):
        sheet=Image.new('RGB',(1200,5*185),'white');draw=ImageDraw.Draw(sheet)
        for offset,answer in enumerate(answers[start:start+10]):
            col,row=offset%2,offset//2
            draw.text((col*600+8,row*185+5),f'{year} Q{answer["number"]} | original p{answer["source_page"]}',fill='black',font=font)
            image=Image.open(WORK/f'{year}-answer-{answer["number"]:02d}.png')
            image.thumbnail((575,145))
            sheet.paste(image,(col*600+8,row*185+35))
        sheet.save(WORK/f'{year}-answers-contact-{start//10+1}.png')


def main():
    import pymupdf as fitz
    get_inputs();OUTPUT.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'tools/theory/kphc.json').read_text(encoding='utf8'))
    old=json.loads(KEYS_PATH.read_text(encoding='utf8')) if KEYS_PATH.exists() else {}
    audit_path=ROOT/'tools/kphc_answer_sources.json'
    previous_audit=json.loads(audit_path.read_text(encoding='utf8')) if audit_path.exists() else {}
    data={'version':1,'competition':'Korean Middle-School Physics Competition','prefix':'KPhC',
        'scope':'2015 second competition and 2016-2022 published official answers',
        'not_for_automatic_grading':True,'grader_integration':'This file is evidence/answer data only; do not insert keys into the KPhC source manifest or infer a legacy OMR mode.',
        'source_page':SOURCE_PAGE,'official_origin_page':OFFICIAL_PAGE,'archive_sha256':ARCHIVE_SHA,'years':{}}
    mappings={'kphe':{}};files=[];paper_matches=[]
    for entry in manifest['years']:
        year=int(entry['y']);old_parts=old.get('years',{}).get(str(year),{}).get('parts',{})
        for paper in [f for f in entry['files'] if f['kind']=='paper']:
            source=INPUTS/PAPER_NAMES[year][paper['part']]
            assert sha(source.read_bytes())==paper['sha256']
            paper_matches.append({'year':year,'part':paper['part'],'archive_member':source.name,'sha256':paper['sha256'],'matches_existing_independent_olimpicos_copy':True})
        if year in (2020,2021):
            document,answers=inline_answers(year,old_parts)
            target=OUTPUT/f'KPhC_{year}_TK.pdf'
            pages=excerpt_pdf(year,document,answers['T'],target)
            preview_sheets(year,answers['T'])
            source_name=f'{year}PA.pdf';source_kind='official_answer_excerpts'
            source_sha=sha((INPUTS/source_name).read_bytes())
            output_info={part:{'file':target.name,'sha256':sha(target.read_bytes()),'bytes':target.stat().st_size,'pages':pages} for part in answers}
        else:
            document,answers=table_answers(year)
            source_name=f'{year}A.pdf';source_kind='preserved_official_answer'
            source=INPUTS/source_name;source_sha=sha(source.read_bytes())
            output_info={}
            for part in answers:
                target=OUTPUT/f'KPhC_{year}_{part}K.pdf'
                shutil.copyfile(source,target)
                assert target.read_bytes()==source.read_bytes()
                output_info[part]={'file':target.name,'sha256':source_sha,'bytes':source.stat().st_size,'pages':len(document)}
        parts={}
        mappings['kphe'][str(year)]={'f':{}}
        for part,rows in answers.items():
            output=output_info[part]
            parts[part]={'source_pdf':source_name,'source_sha256':source_sha,'source_type':source_kind,
                'pdf':output['file'],'answer_count':len(rows),'answers':rows}
            local=f'pdfx/kphe/{output["file"]}'
            mappings['kphe'][str(year)]['f'][part]={'key':local}
            files.append({'year':year,'part':part,'kind':'key','lang':'KO',**output,'local':local,
                'url':SOURCE_PAGE,'source_page':SOURCE_PAGE,'official_origin_page':OFFICIAL_PAGE,
                'source_type':source_kind,'archive_member':f'물올 기출/{source_name}',
                'archive_sha256':ARCHIVE_SHA,'source_sha256':source_sha,
                'source_answer_pages':list(range(2,17)) if year in(2020,2021) else [1],
                'official_direct_download':False,
                'source_note':'2022-09-13 학회 파일 공개 재수록 ZIP. 문제 원문 10개가 독립 보존본과 바이트 일치함.'})
        data['years'][str(year)]={'session':'second' if year==2015 else 'annual','parts':parts}
    KEYS_PATH.write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    (ROOT/'tools/kphc_key_print_overlay.json').write_text(json.dumps(mappings,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    audit={'checked_on':'2026-10-30','classification':'indirectly_preserved_official_material',
        'source_page':SOURCE_PAGE,'source_publication_date':'2022-09-13','official_origin_page':OFFICIAL_PAGE,
        'archive_file':'물올 기출.zip','archive_sha256':ARCHIVE_SHA,'archive_bytes':ARCHIVE.stat().st_size,
        'provenance_evidence':['The contemporaneous public archive explicitly states that it contains files from the KPS official website and links the original official board post.',
            'All ten question/answer-booklet PDFs match the independently hosted olimpicos question PDFs byte-for-byte.',
            'The 2020/2021 source headers explicitly identify 한국물리학회 as the writer and contain 답) / (답) after all 30 questions.',
            'The 2015 key preserves the KPS Education Committee full-credit decision; the 2019 revised key preserves the alternative-answer amendment.'],
        'paper_byte_matches':paper_matches,'files':files,
        'special_cases':{'2015_T1_Q2':'Full credit for every examinee, rather than an unknown/missing answer.',
            '2019_T_Q7':'Revised 2019-08-22 key accepts option 3 OR option 4 separately; not a required two-option selection.',
            '2020_2021':'Published source expresses answers as formulas or statement sets and embeds them directly after each question. No choice-number OMR mapping is inferred.'},
        'excluded_candidate':{'url':'https://orbi.kr/download/united/17504799/0','sha256':'28127e3bc9788d8d4a70e4594fd845df0ecec88bcb22e3256aea6ea4b65172f8','reason':'2018 user-created selected-question compilation with different numbering, not the complete official year answer tables.'}}
    for field in ('direct_archive_checks','independent_answer_corroboration','worked_solutions','visual_review','validation',
            'raw_source_documents','archive_download_url_at_verification','archive_download_note'):
        if field in previous_audit:audit[field]=previous_audit[field]
    audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    if '--sync-catalog' in sys.argv:
        for year in manifest['years']:
            year['files']=[row for row in year['files'] if row['kind']!='key']
            year['files'].extend({key:value for key,value in row.items() if key!='year'} for row in files if row['year']==int(year['y']))
            assert 'keys' not in year
        (ROOT/'tools/theory/kphc.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    print('Prepared',len(files),'download entries;',sum(len(part['answers']) for year in data['years'].values() for part in year['parts'].values()),'answers; independent paper hashes',len(paper_matches))


if __name__=='__main__': main()
