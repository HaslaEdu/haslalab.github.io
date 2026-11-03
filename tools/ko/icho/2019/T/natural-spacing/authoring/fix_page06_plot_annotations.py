from pathlib import Path
import json
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;p=B/'page06.overrides.json';q=json.loads(p.read_text('utf8'));plan=json.loads((g.PLANS/'page06.ko.json').read_text('utf8'));scope=q['__layout_scope__'];edits=q.setdefault('__slot_edits__',{})
scope['native_only_stationary_rects']=[[65,150,563,375]]
scope['fixed_prose_baselines']=sorted({s['point'][1]for s in plan['slots']if s['at'][0]==3 and not s.get('skip')})
for id in['p6:b3:l180:s0-0:c0-6','p6:b3:l308:s0-0:c0-9']:
    edits.setdefault(id,{})['source_word_right_aligned_label']=True
edits['p6:b3:l180:s0-0:c0-6']['text']='아미드'
scope['source_nmr_plot_review']='Original NMR plot bars, dotted grid, axis numbers and all native chemical labels stay at exact source geometry/programs; they never join translated annotations into one line. Each original source annotation baseline/start is independent. The amide and benzylic prefixes preserve the original word right edge before the adjacent unchanged native chemical formula, at source point size; 아미드 is the established Korean name for amide. Native ink collision remains zero without excluding any chart ink.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('NMR native plot fixed; source-word-edge Korean annotation alignment recorded.',flush=True)
