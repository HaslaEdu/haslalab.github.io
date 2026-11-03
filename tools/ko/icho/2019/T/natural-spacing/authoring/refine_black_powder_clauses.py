from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent
def apply(n,edits):
    p=B/f'page{n:02}.overrides.json';q=json.loads(p.read_text('utf8'));dest=q.setdefault('__slot_edits__',{})
    for id,text in edits.items():dest.setdefault(id,{})['text']=text
    return p,q
p,q=apply(24,{
 'p24:b8:l0:s2-2:c0-34':'세기에 프랑스 사업가 ',
 'p24:b8:l0:s2-2:c35-87':'. 쿠르투아는 화약용 질산염 ',
 'p24:b8:l1:s7-7':') 생산을 전문으로 하였다. 아시아에서 수입하던 ',
 'p24:b8:l1:s9-9':'를 이후 질산염 ',
 'p24:b8:l2:s7-7':')에 해조류에서 얻은 화합물 ',
 'p24:b8:l2:s9-9':'를 교환 반응시켜 제조하였다.'
});p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
p,q=apply(25,{
 'p25:b2:l0:s0-0':'',
 'p25:b2:l0:s2-2:c0-2':'를 얻기 위해 ',
 'p25:b2:l0:s2-2:c9-28':'의 고체 화합물 ',
 'p25:b2:l0:s4-4:c0-39':'를 ',
 'p25:b2:l0:s4-4:c46-50':'의 ',
 'p25:b2:l1:s0-0:c0-36':'과량이다. 그 결과 ',
 'p25:b2:l1:s0-0:c43-65':'의 흰색 침전 ',
 'p25:b2:l1:s2-2':'가 생성되어 ',
 'p25:b2:l2:s0-0':'거름으로 제거하고 거른 액을 증발시켜 고체 혼합물 ',
 'p25:b2:l2:s2-2':'를 질량이 일정할 때까지 가열했다.',
 'p25:b2:l3:s0-0:c0-38':'시료에는 아질산염 ',
 'p25:b3:l0:s1-1':'만 있었다. 기체 생성물은 분자 산소뿐이었고 부피는 ',
 'p25:b3:l1:s0-0:c7-11':'이며, 온도 ',
 'p25:b3:l1:s0-0:c15-19':', 압력 ',
 'p25:b3:l1:s0-0:c24-72':'이다(분자 산소는 이상 기체로 볼 수 있다).',
 'p25:b4:l0:s3-3':'다음 혼합물의 조성(w%)을: ',
 'p25:b4:l0:s5-5':'. 포함된 화합물은 ',
 'p25:b4:l1:s2-2':'뿐이며 불순물은 없다. 또한 ',
 'p25:b4:l1:s4-4':'는 순수한 무수물로 사용했다.'
})
doc=f.open(g.SOURCE);raw=doc[24].get_text('rawdict');span=raw['blocks'][2]['lines'][0]['spans'][6];source=''.join(c['c']for c in span['chars']);assert source=='.'
extra=dict(id='p25:b2:l0:s6-6:solution-predicate',page=25,at=[2,0,6,6],source=source,rect=list(span['bbox']),point=list(span['chars'][0]['origin']),font=span['font'],font_role='serif',size=span['size'],dir=list(raw['blocks'][2]['lines'][0]['dir']),text='가 든 용액에 첨가했다.')
q['__extra_slots__']=[s for s in q.get('__extra_slots__',[])if s['id']!=extra['id']]+[extra]
q['clause_review']='All source chemical symbols and numerical/unit values retain their original order and glyphs. Korean predicates are placed after the same native subject/object as needed. The original prose period after the first B supplies the Korean solution-containing-B predicate; the following second B still starts the original excess clause.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('Source chemical order preserved; black-powder introduction clauses shortened over original rows.',flush=True)
