"""Explicit bilingual running-header/section/footer translations for2013TS.

Only the source's native prose labels are written; its scanned solution text
is reviewed independently. The original erroneous total-page fields stay native.
"""
import json,re
import cpho_2013_original_extract as b

def prepare():
    data=json.loads((b.AUTHOR/'native-slots.json').read_text('utf8'))
    ordinal={v:f'{i}.'for i,v in enumerate(['一、','二、','三、','四、','五、','六、','七、','八、'],1)}
    for page in data['pages']:
        path=b.AUTHOR/f'page{page["source_page"]:02}.tsv'
        existing={}
        if path.exists():
            for line in path.read_text('utf8').splitlines():
                key,ko,en=line.split('\t');existing[key]=(ko,en)
        values=[]
        for slot in page['slots']:
            text=slot['source'];y=slot['origin'][1]
            role=slot.get('original_paragraph_role')
            if role=='header':ko,en='제30회 결선 문제 및 해설','30th Final Problems and Answers'
            elif role=='title':
                ko='제30회 전국 중등학생 물리 경시대회 결선 시험 '+('문제'if page['kind']=='T'else'해설')
                en='30th National Secondary-School Physics Olympiad Final '+('Exam'if page['kind']=='T'else'Answers')
            elif role=='footer':
                match=re.fullmatch(r'第(\d+)页共(\d+)页',re.sub(r'\s+','',text))
                if not match:raise ValueError('Unexpected original page field: '+text)
                ko=f'{match[1]}쪽 / 총 {match[2]}쪽';en=f'Page {match[1]} of {match[2]}'
            elif page['kind']=='T'and slot['id']in existing:ko,en=existing[slot['id']]
            elif text=='第':ko,en=('','p.')if y>750 else('제','')
            elif text=='页':ko,en='쪽',''
            elif text=='共':ko,en='총','of'
            elif text=='届决赛试题及答案':ko,en='회 결선 문제 및 해설','th Final: Q & A'
            elif text=='届全国中学生物理竞赛决赛考试答案':ko,en='회 전국 중등 물리경시 결선 시험 해설','th National School Physics Olympiad Final Answers'
            elif text in ordinal:ko=en=ordinal[text]
            else:raise ValueError('Unreviewed native TS header: '+repr(text))
            values.append('\t'.join([slot['id'],ko,en]))
        path.write_text('\n'.join(values)+'\n','utf8')
    print('Explicit native header translations prepared; bitmap solution body is still pending.')

if __name__=='__main__':prepare()
