from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;p=B/'page08.overrides.json';q=json.loads(p.read_text('utf8'));scope=q['__layout_scope__'];edits=q.setdefault('__slot_edits__',{})
edits.update({
 'p8:b16:l0:s1-1:c7-22':dict(text='전자는 양 끝 결합에'),
 'p8:b16:l1:s0-0':dict(text='국소화되어 분리된 두 무한 퍼텐셜 우물에서'),
 'p8:b16:l2:s0-0':dict(text='운동한다. 각 우물의 길이:'),
 'p8:b17:l0:s1-1:c7-22':dict(text='전자는 분자 전체에'),
 'p8:b17:l1:s0-0':dict(text='비편재화되어 한 무한 퍼텐셜 우물에서'),
 'p8:b17:l2:s0-0:c0-43':dict(text='운동한다. 우물의 길이:')
})
doc=f.open(g.SOURCE);blocks=doc[7].get_text('rawdict')['blocks'];source_lines=[[b,l]for b in[16,17]for l in range(3)]
scope['fixed_grid_inline_source_lines']=source_lines
scope['fixed_prose_baselines']=sorted({blocks[b]['lines'][l]['spans'][0]['origin'][1]for b,l in source_lines})
leftmax=max(blocks[16]['lines'][l]['bbox'][2]for l in range(3));rightmin=min(blocks[17]['lines'][l]['bbox'][0]for l in range(3));boundary=(leftmax+rightmin)/2
rightmax=max(blocks[17]['lines'][l]['bbox'][2]for l in range(3))
scope['fixed_inline_group_column_bounds']=[dict(source_line=[b,l],right=boundary if b==16 else rightmax,source_rect=list(blocks[b]['lines'][l]['bbox']))for b,l in source_lines]
scope['model_caption_column_review']='The source has two independent three-line model captions beneath separate wells. Every caption row retains its original source x anchor/baseline/point size, with natural spacing only within that row. Korean clauses are assigned across the same three source rows; the source intercolumn gutter is an explicit strict right boundary.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
(B/'source-page08-caption-columns.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,source_left_column_right=leftmax,source_right_column_left=rightmin,intercolumn_boundary=boundary,right_column_right=rightmax,rows=scope['fixed_inline_group_column_bounds']),indent=2)+'\n','utf8')
print('Page8 original two-column captions bounded at',boundary,rightmax,flush=True)
