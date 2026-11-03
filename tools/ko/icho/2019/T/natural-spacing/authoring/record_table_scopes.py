from pathlib import Path
import json
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;journal=[]
for n in range(1,61):
    profile=json.loads((B/'source-profile'/f'page{n:02}.json').read_text('utf8'));assert profile['source_sha256']==g.SOURCE_SHA
    tables=[t for i,t in enumerate(profile['tables'])if not(n==6 and i==0)]
    if not tables:continue
    p=B/f'page{n:02}.overrides.json';q=json.loads(p.read_text('utf8'));scope=q['__layout_scope__']
    scope['fixed_table_rects']=[t['bbox']for t in tables]
    cells=[]
    for t in tables:
        for cell in t['cells']:
            if cell not in cells:cells.append(cell)
    scope['fixed_table_cells']=cells
    scope['original_table_scope_review']='Original source table grids/cell boundaries remain unchanged. Native symbols in cells without prose stay stationary; only the reviewed full inline group inside its own prose-bearing cell may use natural advances. The first page6 detected structure is a spectral plot rather than a table and is excluded.'
    p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');journal.append(dict(page=n,table_rects=scope['fixed_table_rects'],table_cells=cells))
(B/'source-table-scopes.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,pages=journal),ensure_ascii=False,indent=2)+'\n','utf8')
p=B/'page02.overrides.json';q=json.loads(p.read_text('utf8'));q['__layout_scope__']['reviewed_native_vector_attachments']=[json.loads((B/'page02-native-highlight-profile.json').read_text('utf8'))];p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
p=B/'page03.overrides.json';q=json.loads(p.read_text('utf8'));scope=q['__layout_scope__'];r=[400,185,525,430]
if r not in scope['fixed_native_rects']:scope['fixed_native_rects'].append(r)
scope['prose_column_rects']=[[70,185,395,430]]
scope['source_toc_column_review']='The original separate weight column at402.43pt and page-reference column at494.5pt remain fixed, including all original GIDs/fonts/point sizes; translated titles use only the original left title column.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('Original source table/cell scopes:',len(journal),'pages; original TOC columns and page2 highlight bound.',flush=True)
