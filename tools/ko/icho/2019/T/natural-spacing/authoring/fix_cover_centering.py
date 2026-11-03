from pathlib import Path
import json,hashlib
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;p=B/'page01.overrides.json';q=json.loads(p.read_text('utf8'));scope=q['__layout_scope__']
scope['centered_source_lines']=[[2,0],[3,0],[5,1]]
scope.pop('source_caption_centering',None)
doc=f.open(g.SOURCE);blocks=doc[0].get_text('rawdict')['blocks'];rows=[]
for bi,li in scope['centered_source_lines']:
    line=blocks[bi]['lines'][li];chars=[dict(c,font=s['font'],size=s['size'])for s in line['spans']for c in s['chars']];nonspace=[c for c in chars if c['c'].strip()];rect=[min(c['bbox'][0]for c in nonspace),min(c['bbox'][1]for c in nonspace),max(c['bbox'][2]for c in nonspace),max(c['bbox'][3]for c in nonspace)]
    rows.append(dict(source_line=[bi,li],source_text=''.join(c['c']for c in chars),source_raw_line_rect=list(line['bbox']),source_full_nonspace_run_rect=rect,source_center_x=(rect[0]+rect[2])/2,original_baselines=sorted({c['origin'][1]for c in chars}),original_point_sizes=sorted({c['size']for c in chars}),basis='Original cover title and slogan use centered full source runs. Measure all nonspace glyphs, excluding the source trailing spaces. Only horizontal alignment of the translated counterparts follows this measured source center; exact source baselines, point sizes and font-style roles are retained.'))
scope['reviewed_source_cover_centering']=rows
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
(B/'source-cover-centering.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,pages={1:rows}),ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(rows,ensure_ascii=False),flush=True)
