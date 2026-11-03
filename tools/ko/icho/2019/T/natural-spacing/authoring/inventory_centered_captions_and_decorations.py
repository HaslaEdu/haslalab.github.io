"""Read original caption centers and all thin black prose-decoration paths."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,re
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;doc=f.open(g.SOURCE);captions=[];decorations=[]
for n,page in enumerate(doc,1):
    plan=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'));over=json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'));blocks=page.get_text('rawdict')['blocks'];chosen=defaultdict(set);source_slots=defaultdict(list)
    for original in plan['slots']+over.get('__extra_slots__',[]):
        s=dict(original,**over.get('__slot_edits__',{}).get(original['id'],{}))
        if s.get('skip'):continue
        bi,li,a,z=s['at'];offset=sum(len(t['chars'])for t in blocks[bi]['lines'][li]['spans'][:a]);raw=[c for t in blocks[bi]['lines'][li]['spans'][a:z+1]for c in t['chars']];start=s.get('char_start',0);end=s.get('char_end',len(raw));assert ''.join(c['c']for c in raw[start:end])==s['source']
        chosen[(bi,li)].update(range(offset+start,offset+end));source_slots[(bi,li)].append(s)
    all_chars=[]
    for bi,block in enumerate(blocks):
        caption_block=any(re.match(r'\s*(?:Fig(?:ure)?\.?\s*\d|Scheme\s*\d)', ''.join(c['c']for s in l['spans']for c in s['chars']))for l in block.get('lines',[]))
        for li,line in enumerate(block.get('lines',[])):
            cs=[dict(c,size=s['size'],font=s['font'],selected=i in chosen[(bi,li)],source_line=[bi,li])for i,(c,s)in enumerate((c,s)for s in line['spans']for c in s['chars'])]
            all_chars+=cs;nonspace=[c for c in cs if c['c'].strip()]
            if not nonspace:continue
            rect=[min(c['bbox'][0]for c in nonspace),min(c['bbox'][1]for c in nonspace),max(c['bbox'][2]for c in nonspace),max(c['bbox'][3]for c in nonspace)];center=(rect[0]+rect[2])/2
            if caption_block and source_slots[(bi,li)]:
                slots=[dict(id=s['id'],source=s['source'],text=over.get(s['id'],s.get('text')))for s in source_slots[(bi,li)]]
                captions.append(dict(page=n,source_line=[bi,li],source_text=''.join(c['c']for c in cs),source_nonspace_rect=rect,source_center_x=center,page_center_x=page.rect.width/2,source_baselines=sorted({c['origin'][1]for c in nonspace}),source_sizes=sorted({c['size']for c in nonspace}),near_original_page_center=abs(center-page.rect.width/2)<=1.5,slots=slots))
    refs=[r['source_rect']for r in over.get('__prose_vector_decorations__',[])]+[r['vector_path']['rect']for r in over.get('__layout_scope__',{}).get('reviewed_native_vector_attachments',[])if r.get('kind')=='original-prose-underline-containing-native-numeral']
    for draw in page.get_drawings():
        r=draw['rect']
        if draw['fill']!=(0.,0.,0.)or not .15<r.height<1.8 or not 3<r.width<520:continue
        members=[c for c in all_chars if c['c'].strip()and r.x0-.5<=c['origin'][0]<=r.x1+.5 and .2<r.y0-c['origin'][1]<c['size']*.6]
        selected=[c for c in members if c['selected']and c['c'].isascii()and c['c'].isalpha()]
        if len(selected)<2:continue
        baseline=min(selected,key=lambda c:abs(r.y0-c['origin'][1]-1.2))['origin'][1];members=[c for c in members if abs(c['origin'][1]-baseline)<.1]
        matched=any(max(abs(a-b)for a,b in zip(r,v))<.001 for v in refs)
        decorations.append(dict(page=n,source_rect=list(r),source_baseline=baseline,source_text_under_path=''.join(c['c']for c in sorted(members,key=lambda c:c['origin'][0])),source_lines=sorted({tuple(c['source_line'])for c in members}),already_source_bound=matched,prose_slot_ids=sorted({s['id']for c in selected for s in source_slots[tuple(c['source_line'])]})))
out=dict(source_sha256=g.SOURCE_SHA,caption_candidates=captions,thin_black_source_prose_paths=decorations,unmatched_prose_paths=[v for v in decorations if not v['already_source_bound']],inventory_only_no_auto_authorization=True)
(B/'source-caption-and-decoration-full-inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(dict(captions=captions,prose_paths=len(decorations),unmatched=out['unmatched_prose_paths']),ensure_ascii=False),flush=True)
