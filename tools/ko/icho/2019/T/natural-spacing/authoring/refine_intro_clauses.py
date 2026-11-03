from pathlib import Path
import json,copy
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent
def load(n):return json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'))
def save(n,q):(B/f'page{n:02}.overrides.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
q=load(6);plan=json.loads((g.PLANS/'page06.ko.json').read_text('utf8'));by={v['id']:v for v in plan['slots']};edits=q.setdefault('__slot_edits__',{});extras=q.setdefault('__extra_slots__',[])
def split(original,start,end,text,name):
    s=copy.deepcopy(by[original]);s['id']=original+':'+name;s['source']=s['source'][start:end];base=s.get('char_start',0);s['char_start']=base+start;s['char_end']=base+end;s['text']=text;s.pop('skip',None);s.pop('skip_reason',None)
    extras[:]=[v for v in extras if v['id']!=s['id']];extras.append(s)
for id in['p6:b8:l2:s0-0:c0-21','p6:b8:l3:s0-0:c0-30']:
    edits[id]=dict(skip=True,skip_reason='Native ax/eq scientific labels retain original glyphs; only source-bound surrounding prose subranges are translated below.')
split('p6:b8:l2:s0-0:c0-21',5,21,'(사이클로헥세인):','compound-prose')
split('p6:b8:l3:s0-0:c0-30',5,9,'또는','or-prose')
split('p6:b8:l3:s0-0:c0-30',14,30,'(같은 고리):','same-cyclohexane-prose')
for s in plan['slots']:
    if s['source']=='-':edits[s['id']]=dict(skip=True,skip_reason='Original numerical range/minus glyph retains its exact source font and point size.')
q['source_chemical_label_review']='Native ax-ax/ax-eq/eq-eq symbols remain original. The second cyclohexane row explicitly refers to the same ring defined in the immediately preceding row; no compound, geometry or coupling value changes.'
save(6,q)
q=load(8);edits=q.setdefault('__slot_edits__',{})
edits['p8:b10:l0:s0-0']=dict(text='이 계는 전자가 자유로운 1차원 상자(')
edits['p8:b10:l0:s2-2']=dict(text='무한 우물)로 모형화할 수 있다.')
doc=f.open(g.SOURCE);raw=doc[7].get_text('rawdict');span=raw['blocks'][10]['lines'][0]['spans'][1];chars=span['chars'];source=''.join(c['c']for c in chars)
assert source.strip()=='i.e.'
extra=dict(id='p8:b10:l0:s1-1:explanatory-ie',page=8,at=[10,0,1,1],source=source,rect=list(span['bbox']),point=list(chars[0]['origin']),font=span['font'],font_role='serif',size=span['size'],dir=list(raw['blocks'][10]['lines'][0]['dir']),text='즉')
q['__extra_slots__']=[s for s in q.get('__extra_slots__',[])if s['id']!=extra['id']]+[extra]
save(8,q)
q=load(10);fixed=q['__layout_scope__']['fixed_native_rects'];r=[160,86,410,130]
if r not in fixed:fixed.append(r)
q['__layout_scope__']['reviewed_display_formula_note']='The independent electron-density display, including the original lower summation limit i=1, remains at its exact source geometry; the following paragraph is a separate source line.'
save(10,q)
print('Source-bound 2019 introduction clauses and independent display scope updated.',flush=True)
