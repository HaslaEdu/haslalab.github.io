from pathlib import Path
import json,hashlib
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;journal=[]
for n in range(1,61):
    p=B/f'page{n:02}.overrides.json';q=json.loads(p.read_text('utf8'));plan=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'));changed=False
    for original in plan['slots']+q.get('__extra_slots__',[]):
        s=dict(original,**q.get('__slot_edits__',{}).get(original['id'],{}));text=q.get(s['id'],s.get('text',''))
        if s.get('skip')or not text:continue
        attrs={}
        if s['source'].startswith('-')and text.startswith('-'):attrs['join_left']=True
        if s['source'].rstrip().endswith('-')and text.rstrip().endswith('-'):attrs['join_right']=True
        if attrs:
            q.setdefault('__slot_edits__',{}).setdefault(s['id'],{}).update(attrs);changed=True;journal.append(dict(page=n,id=s['id'],source=s['source'],unchanged_korean=text,flags=attrs))
    if n==60:
        sc=q['__layout_scope__'];sc['native_only_stationary_rects']=sc.get('native_only_stationary_rects',[])+[[70,92,396.1,144.]]
        lines=[[3,0],[3,13],[3,18]];sc['fixed_grid_inline_source_lines']=[list(v)for v in sorted({tuple(v)for v in sc.get('fixed_grid_inline_source_lines',[])+lines})];sc['fixed_prose_baselines']=sorted(set(sc.get('fixed_prose_baselines',[])+[102.8599853515625,128.17999267578125]))
        for id in['p60:b3:l0:s1-1:c0-9','p60:b3:l13:s1-1:c0-9','p60:b3:l18:s1-1:c0-9']:q.setdefault('__slot_edits__',{}).setdefault(id,{})['source_word_right_aligned_label']=True
        sc['source_two_column_choice_review']='Original two-column reagent answer layout, source checkbox origins70.824/318.650pt. Every original checkbox/chemical formula/charge/subscript stays at its exact source position, font and point size. Only the three original diluted words are translated within their own source-line group and aligned at their original source-word right edges. No cross-column native atom merging.';changed=True
    if changed:p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
(B/'scientific-name-hyphen-join-review.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,rows=journal,korean_text_bytes_unchanged=True,meaning='Explicitly retain original nomenclature hyphen joins: L-lysine, myo-inositol, alpha-amino, cyclohexane-1,2,…-hexol, and related source-bound names.'),ensure_ascii=False,indent=2)+'\n','utf8');print(len(journal),flush=True)
