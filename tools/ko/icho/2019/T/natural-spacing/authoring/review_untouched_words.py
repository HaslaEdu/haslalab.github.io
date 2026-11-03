from pathlib import Path
from collections import defaultdict
import hashlib,json,re,sys
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;doc=f.open(g.SOURCE);results=[]
short='--short-functions'in sys.argv
pattern=r'(?<![A-Za-z0-9])(?:a|an|of|to|in|at|as|by|or|is|be|if|on|no|so|vs)(?![A-Za-z0-9])'if short else r"[A-Za-z][A-Za-z.'’–-]{2,}"
for n,page in enumerate(doc,1):
    plan=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'));over=json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'));blocks=page.get_text('rawdict')['blocks'];selected=defaultdict(set)
    for orig in plan['slots']+over.get('__extra_slots__',[]):
        s=dict(orig,**over.get('__slot_edits__',{}).get(orig['id'],{}))
        if s.get('skip'):continue
        bi,li,a,z=s['at'];offset=sum(len(t['chars'])for t in blocks[bi]['lines'][li]['spans'][:a]);raw=[c for t in blocks[bi]['lines'][li]['spans'][a:z+1]for c in t['chars']];start=s.get('char_start',0);end=s.get('char_end',len(raw))
        assert ''.join(c['c']for c in raw[start:end])==s['source']
        selected[(bi,li)].update(range(offset+start,offset+end))
    for bi,block in enumerate(blocks):
        for li,line in enumerate(block.get('lines',[])):
            text=''.join(c['c']for s in line['spans']for c in s['chars'])
            for m in re.finditer(pattern,text):
                if not(set(range(m.start(),m.end()))&selected[(bi,li)]):results.append(dict(page=n,source_line=[bi,li],untouched_word=m.group(),source_line_text=text,source_baseline=line['spans'][0]['origin'][1]))
(B/('untouched-source-short-function-words-review.json'if short else'untouched-source-words-review.json')).write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,rows=results),ensure_ascii=False,indent=2)+'\n','utf8')
for r in results:print(json.dumps(r,ensure_ascii=False),flush=True)
