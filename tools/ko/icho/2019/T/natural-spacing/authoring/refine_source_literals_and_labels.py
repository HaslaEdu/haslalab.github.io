from pathlib import Path
import json,copy
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;doc=f.open(g.SOURCE)
def load(n):return json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'))
def save(n,q):(B/f'page{n:02}.overrides.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def active_fragment(slot,start,end,text,id):
    s=copy.deepcopy(slot);s['id']=id;s['source']=slot['source'][start:end];offset=slot.get('char_start',0);s['char_start']=offset+start;s['char_end']=offset+end;s['text']=text;s.pop('skip',None);s.pop('skip_reason',None);return s
q=load(2);edits=q.setdefault('__slot_edits__',{});edits['p2:b13:l1:s0-0']=dict(text='Stop 명령이 주어지면 즉시 시험을 중단해야 한다. 명령 후')
id='p2:b13:l2:s0-0';plan=json.loads((g.PLANS/'page02.ko.json').read_text('utf8'));slot=next(s for s in plan['slots']if s['id']==id);index=slot['source'].index('½')
edits[id]=dict(skip=True,skip_reason='Original fraction½ remains at its source font and exact point size; only the adjacent source-bound prose fragments are translated.')
extras=[active_fragment(slot,0,index,'계속 필기한 시간이',id+':before-native-half'),active_fragment(slot,index+1,len(slot['source']),'분 이상이면 이론 시험이 무효 처리된다.',id+':after-native-half')]
q['__extra_slots__']=[s for s in q.get('__extra_slots__',[])if s['id']not in{v['id']for v in extras}]+extras
q['__layout_scope__']['centered_source_lines']=[[19,0]]
line=doc[1].get_text('rawdict')['blocks'][19]['lines'][0];chars=[dict(c,font=s['font'],size=s['size'])for s in line['spans']for c in s['chars']if c['c'].strip()];rect=[min(c['bbox'][0]for c in chars),min(c['bbox'][1]for c in chars),max(c['bbox'][2]for c in chars),max(c['bbox'][3]for c in chars)]
spec=dict(source_line=[19,0],source_text=''.join(c['c']for c in chars),source_full_nonspace_run_rect=rect,source_center_x=(rect[0]+rect[2])/2,original_baselines=sorted({c['origin'][1]for c in chars}),original_point_sizes=sorted({c['size']for c in chars}),basis='Center this original message itself, independently of the cover center and page center; source baseline/point size unchanged.')
q['__layout_scope__']['reviewed_source_centered_message']=[spec];save(2,q)
(B/'source-page02-message-centering.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,pages={'2':[spec]}),ensure_ascii=False,indent=2)+'\n','utf8')
q=load(4);q.setdefault('__slot_edits__',{})['p4:b15:l3:s0-0']=dict(text='단');save(4,q)
q=load(6);plan=json.loads((g.PLANS/'page06.ko.json').read_text('utf8'));id='p6:b14:l0:s0-0:c4-20';slot=next(s for s in plan['slots']if s['id']==id);assert slot['source']==' equatorial, ax '
q.setdefault('__slot_edits__',{})[id]=dict(skip=True,skip_reason='Keep native ax abbreviation in its original font/GID; translate only the equatorial prose before it.')
extra=active_fragment(slot,0,13,'적도 방향,',id+':equatorial-prose')
q['__extra_slots__']=[s for s in q.get('__extra_slots__',[])if s['id']!=extra['id']]+[extra]
table=json.loads((B/'source-profile/page06.json').read_text('utf8'))['tables'][1]
q['__layout_scope__']['prose_column_rects']=[[table['bbox'][0],675,table['bbox'][2],685]]
q['__layout_scope__']['legend_scope_review']='The original eq/ax glossary below the table uses the source table outer width; native eq/ax/= symbols remain original, Korean directions keep the source12pt size and original baseline.'
save(6,q)
q=load(32);extras=q.setdefault('__extra_slots__',[]);blocks=doc[31].get_text('rawdict')['blocks']
for bi in[2,4]:
    line=blocks[bi]['lines'][0];matches=[(si,s)for si,s in enumerate(line['spans'])if'i.e.'in''.join(c['c']for c in s['chars'])];assert len(matches)==1
    si,span=matches[0];text=''.join(c['c']for c in span['chars']);start=text.index('i.e.');id=f'p32:b{bi}:l0:s{si}-{si}:explanatory-ie'
    extra=dict(id=id,page=32,at=[bi,0,si,si],source='i.e.',char_start=start,char_end=start+4,rect=list(span['bbox']),point=list(span['chars'][start]['origin']),font=span['font'],font_role='serif',size=span['size'],dir=list(line['dir']),text='즉')
    extras[:]=[s for s in extras if s['id']!=id];extras.append(extra)
save(32,q)
print(json.dumps(dict(page2_message_center_x=spec['source_center_x'],native_half_fraction_retained=True,source_at_condition='단',native_eq_ax_retained=True,explanatory_ie_translated=[8,32]),ensure_ascii=False),flush=True)
