from pathlib import Path
from collections import Counter
import argparse,json,re
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('pages',nargs='+',type=int);args=ap.parse_args();doc=f.open(g.SOURCE);journal=[]
for n in args.pages:
    page=doc[n-1];blocks=page.get_text('rawdict')['blocks'];lines=[]
    for bi,b in enumerate(blocks):
        for li,l in enumerate(b.get('lines',[])):
            cs=[dict(c,font=s['font'],size=s['size'],flags=s['flags'])for s in l['spans']for c in s['chars']];cs=[c for c in cs if c['c'].strip()]
            if not cs:continue
            baseline=Counter(c['origin'][1]for c in cs).most_common(1)[0][0];r=[min(c['bbox'][0]for c in cs),min(c['bbox'][1]for c in cs),max(c['bbox'][2]for c in cs),max(c['bbox'][3]for c in cs)];text=''.join(c['c']for s in l['spans']for c in s['chars'])
            lines.append(dict(source_line=[bi,li],source_text=text,source_baseline=baseline,source_point_sizes=sorted({c['size']for c in cs}),source_nonspace_rect=r,source_center_x=(r[0]+r[2])/2,italic_prose=any(c['flags']&2 for c in cs if c['c'].isalpha()),source_fonts=sorted({c['font']for c in cs})))
    lines.sort(key=lambda v:(v['source_baseline'],v['source_nonspace_rect'][0]));selected={}
    for i,line in enumerate(lines):
        if not re.match(r'\s*(?:Fig(?:ure)?\.?\s*\d|Scheme\s*\d|Table\s*\d)',line['source_text']):continue
        selected[tuple(line['source_line'])]=line;last=line
        for next in lines[i+1:]:
            if last['source_text'].rstrip().endswith('.')or not next['italic_prose']:break
            dy=next['source_baseline']-last['source_baseline']
            if not .1<dy<=max(last['source_point_sizes'])*1.6 or abs(next['source_center_x']-line['source_center_x'])>.5:break
            selected[tuple(next['source_line'])]=next;last=next
    if not selected:continue
    p=B/f'page{n:02}.overrides.json';q=json.loads(p.read_text('utf8'));scope=q['__layout_scope__'];existing={tuple(v)for v in scope.get('centered_source_lines',[])}
    scope['centered_source_lines']=[list(v)for v in sorted(existing|set(selected))]
    scope['source_caption_alignment_review']=list(selected.values())
    scope['source_caption_alignment_basis']='Each reviewed original Fig./Scheme/Table caption retains its own measured full nonspace source-glyph run center, including native variables and subscripts. Wrapped rows use their own original source centers. Page41 Fig1 follows the left NMR plot center and Table2 follows the separate right table; no page-center replacement is used.'
    p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');journal+=list(dict(v,page=n)for v in selected.values());print(json.dumps(dict(page=n,caption_rows=[dict(source_line=v['source_line'],center=v['source_center_x'],baseline=v['source_baseline'])for v in selected.values()])),flush=True)
(B/('source-caption-centering-'+','.join(map(str,args.pages))+'.json')).write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,rows=journal),ensure_ascii=False,indent=2)+'\n','utf8')
