"""Concise faithful Korean on original physical source rows, pages52–56."""
from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent
edits={
52:{'p52:b11:l0:s3-3':' 입체 화학적 세부 사항 없이 이노시톨의 구조식을.'},
55:{'p55:b7:l0:s2-2':'다음 생성물','p55:b7:l0:s4-4':'는 전자 밀도가 가장 높은 이중 결합의 반응으로 생성된다.',
    'p55:b7:l1:s0-0:c34-78':'-사이클로헥사다이엔은 다음 물질의 부분 구조이다:',
    'p55:b7:l1:s3-3':'둘러싸라:','p55:b7:l2:s0-0':'가장 높은 이중 결합을.',
    'p55:b7:l2:s2-2':' 브로민의 모든 전자적','p55:b7:l3:s0-0':'효과를.',
    'p55:b15:l0:s3-3':' 다음 화합물의 입체 이성질체 중','p55:b15:l0:s5-5':'이 합성으로 얻을 수 있는 총수를. 출발 물질은',
    'p55:b15:l1:s0-0':'거울상 순수 화합물이다:'},
56:{'p56:b3:l0:s3-3':' 다음 반응 조건','p56:b3:l0:s5-5':'으로 다음 생성물을 얻는 경우를:',
    'p56:b5:l0:s2-2':'다음 물질에 브로민이 없으면:','p56:b5:l0:s4-4':', 다음 물질 외에도:',
    'p56:b5:l1:s0-0':'얻어진다. 합성 반응들의 입체 선택성은 변하지 않으며,',
    'p56:b5:l2:s0-0':'후속 단계의 당량 수는 다음 물질의 합성 때와 같다고 가정하라:',
    'p56:b7:l0:s2-2':'다음 물질','p56:b7:l0:s4-4':'를 다음 물질로부터 합성할 때:',
    'p56:b7:l0:s6-6':' 보호기 또는 지향기의 제거 단계들을.'}}
journal=[]
for n,changes in edits.items():
    path=B/f'page{n:02}.overrides.json';old=path.read_bytes();q=json.loads(old);plan=json.loads((B.parent/'2019'/f'page{n:02}.ko.json').read_text('utf8'));slots={s['id']:s for s in plan['slots']+q.get('__extra_slots__',[])}
    for id,text in changes.items():
        source=slots[id]['source'];before=q.get(id,q.get('__slot_edits__',{}).get(id,{}).get('text',slots[id].get('text')))
        q.setdefault('__slot_edits__',{}).setdefault(id,{})['text']=text
        journal.append(dict(page=n,id=id,source=source,before=before,after=text))
    path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
(B/'final-body-clauses-52-56-review.json').write_text(json.dumps(dict(edits=journal,note='Original pages52/55/56 read. Same scientific predicates, numbers/formulas/stereochemical conditions and original underlined command roles; only Korean text edited at existing source rows.'),ensure_ascii=False,indent=2)+'\n','utf8')
