from pathlib import Path
import json,hashlib
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;doc=f.open(g.SOURCE);rows=[]
for n,page in enumerate(doc,1):
    q=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'));b=page.get_text('rawdict')['blocks'];drawings=page.get_drawings()
    edits=json.loads((B/f'page{n:02}.overrides.json').read_text('utf8')).get('__slot_edits__',{})
    for original in q['slots']:
        slot=dict(original,**edits.get(original['id'],{}))
        if slot.get('skip'):continue
        bi,li,a,z=slot['at'];cs=[dict(c,size=s['size'])for s in b[bi]['lines'][li]['spans'][a:z+1]for c in s['chars']][slot.get('char_start',0):slot.get('char_end')]
        cs=[c for c in cs if c['c'].strip()]
        if not cs:continue
        left=min(c['bbox'][0]for c in cs);right=max(c['bbox'][2]for c in cs);baseline=cs[0]['origin'][1];size=cs[0]['size']
        paths=[d for d in drawings if abs(d['rect'].height)<size*.15 and .3<d['rect'].y0-baseline<size*.6 and abs(d['rect'].x0-left)<2 and abs(d['rect'].x1-right)<2]
        for d in paths:rows.append(dict(page=n,slot_id=slot['id'],source=slot['source'],target=slot['text'],source_baseline=baseline,source_rect=list(d['rect']),drawing_type=d['type']))
(B/'source-prose-underline-candidates.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,rows=rows),ensure_ascii=False,indent=2)+'\n','utf8')
for r in rows:print(json.dumps(r,ensure_ascii=False),flush=True)
