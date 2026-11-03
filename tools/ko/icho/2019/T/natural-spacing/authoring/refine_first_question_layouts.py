from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent
def load(n):return json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'))
def save(n,q):(B/f'page{n:02}.overrides.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
q=load(4);scope=q['__layout_scope__'];scope['fixed_native_rects']=[r for r in scope['fixed_native_rects']if r!=[300,150,550,780]]
for r in[[300,150,550,520],[334,521,550,549],[300,550,550,780]]:
    if r not in scope['fixed_native_rects']:scope['fixed_native_rects'].append(r)
scope['source_formula_column_review']='Separate source formula rows, including the conditions after the source word at, remain fixed. The translated conditional word 단 occupies only its own original prose position outside those formula fields.'
save(4,q)
q=load(8);q.setdefault('__slot_edits__',{})['p8:b11:l0:s2-2']=dict(text='인 무한 우물 속 전자의 에너지:');save(8,q)
q=load(10);scope=q['__layout_scope__'];scope['fixed_native_rects']=[([160,86,410,127]if r==[160,86,410,130]else r)for r in scope['fixed_native_rects']]
scope['reviewed_display_formula_note']='The exact source display through the lower summation limit i=1 is protected. Its field ends before the following original paragraph baseline; no added three-point whitespace band intrudes into that separate paragraph.'
save(10,q)
q=load(12);q.setdefault('__slot_edits__',{})['p12:b7:l0:s3-3:c38-80']=dict(text=')을 짧은 순으로 나열하라.');save(12,q)
q=load(14);r=[66,528,220,585]
if r not in q['__layout_scope__']['fixed_native_rects']:q['__layout_scope__']['fixed_native_rects'].append(r)
q['__layout_scope__']['source_choice_formula_review']='Three original voltage-comparison checkbox formulae remain at exact source positions; they are independent answer options, not parts of the nearby prose label where.'
save(14,q)
q=load(15);plan=json.loads((g.PLANS/'page15.ko.json').read_text('utf8'));profile=json.loads((B/'source-profile/page15.json').read_text('utf8'));doc=f.open(g.SOURCE);blocks=doc[14].get_text('rawdict')['blocks'];over=q.get('__slot_edits__',{});specs=[]
for original in plan['slots']:
    s=dict(original,**over.get(original['id'],{}))
    if s.get('skip'):continue
    b,l,a,z=s['at'];chars=[c for span in blocks[b]['lines'][l]['spans'][a:z+1]for c in span['chars']][s.get('char_start',0):s.get('char_end')];chars=[c for c in chars if c['c'].strip()]
    if not chars:continue
    rect=f.Rect(min(c['bbox'][0]for c in chars),min(c['bbox'][1]for c in chars),max(c['bbox'][2]for c in chars),max(c['bbox'][3]for c in chars))
    for image in profile['images']:
        if rect.intersects(f.Rect(image['bbox'])):specs.append(dict(slot_id=s['id'],source_baseline=chars[0]['origin'][1],source_image_rect=image['bbox'],source_image_xref=image['xref'],review='Original source prose annotation shares the source chart raster canvas. Only this exact source-bound counterpart is allowed within that same canvas; original source glyph ink overlap is independently verified by the compositor, and all encoded image bytes/placements/native ink remain protected.'))
q['__layout_scope__']['allowed_raster_caption_slots']=specs;save(15,q)
q=load(16);q.setdefault('__slot_edits__',{})['p16:b6:l0:s0-0']=dict(text='누적 광자 플럭스(그보다 파장이 짧은 광자가 전체 광자 플럭스에서 차지하는 비율).');save(16,q)
print('Source-bound layout refinements applied; explicit source-chart prose labels:',len(specs),flush=True)
