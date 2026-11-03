from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;p=B/'page51.overrides.json';q=json.loads(p.read_text('utf8'));ed=q.setdefault('__slot_edits__',{});sc=q['__layout_scope__'];doc=f.open(g.SOURCE);line=doc[50].get_text('rawdict')['blocks'][4]['lines'][0]
ed.setdefault('p51:b4:l0:s0-0:c0-4',{})['text']='착물'
ed.setdefault('p51:b4:l0:s4-4',{})['text']='는 금속의 배위권에 전자를 …개 갖는다.'
sc['native_only_stationary_rects']=sc.get('native_only_stationary_rects',[])+[[92,132,122,149]]
sc['fixed_prose_baselines']=sorted(set(sc.get('fixed_prose_baselines',[])+[line['spans'][0]['origin'][1]]))
sc['source_first_answer_formula_review']='The first original Cu(I)N4 atom has a metric ascender box crossing the top answer-frame border in the source, while its actual ink is below the border. Keep that exact source formula stationary. Translate the original short article as 착물 in its original prefix field, then 는… in the original following prose field; this gives natural 착물 Cu(I)N4는… without changing the original formula x/y/font/GID/size or weakening vector-overlap checks. All other answer rows retain ordinary natural reflow.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
