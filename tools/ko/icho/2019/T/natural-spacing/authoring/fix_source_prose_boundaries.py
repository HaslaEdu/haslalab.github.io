from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent
def load(n):return json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'))
def save(n,q):(B/f'page{n:02}.overrides.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
q=load(8);edits=q.setdefault('__slot_edits__',{})
edits.setdefault('p8:b8:l0:s0-0:c0-9',{})['join_right']=True
edits.setdefault('p8:b8:l0:s0-0:c12-45',{})['join_left']=True
edits.setdefault('p8:b14:l0:s4-4',{})['text']='적어도 가장 낮은 세 에너지 준위'
edits.setdefault('p8:b14:l0:s8-8',{})['text']='을 각각의'
save(8,q)
q=load(14);q.setdefault('__slot_edits__',{}).setdefault('p14:b6:l3:s3-3:c0-26',{})['text']='수치를 소수점 아래';save(14,q)
doc=f.open(g.SOURCE)
for n,bi,li,si,start,end,expected,id in[
 (31,4,2,3,0,2,', ','p31:b4:l2:s3-3:source-prose-comma'),
 (41,6,2,7,0,3,' a ','p41:b6:l2:s7-7:english-indefinite-article')]:
    q=load(n);raw=doc[n-1].get_text('rawdict');span=raw['blocks'][bi]['lines'][li]['spans'][si];chars=span['chars'];source=''.join(c['c']for c in chars[start:end]);assert source==expected
    extra=dict(id=id,page=n,at=[bi,li,si,si],source=source,char_start=start,char_end=end,rect=list(span['bbox']),point=list(chars[start]['origin']),font=span['font'],font_role='serif',size=span['size'],dir=list(raw['blocks'][bi]['lines'][li]['dir']),text='')
    q['__extra_slots__']=[v for v in q.get('__extra_slots__',[])if v['id']!=id]+[extra];save(n,q)
print('Chemical-name hyphens joined; original prose comma/article removed in exact source-bound fragments.',flush=True)
