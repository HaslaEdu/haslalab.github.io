"""Bind seven reviewed source-only prose underlines to their Korean clauses."""
from pathlib import Path
import json,sys
import pymupdf as f
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'engine'))
import latex_native_motion as motion
import natural_plan_compose_icho2019 as c
import icho2019_write_guard as g
doc=f.open(g.SOURCE)
rows=[
 (21,[248.2100067,201.8599854,521.6199951,202.3399658],200.65997314453125,[('p21:b4:l2:s2-2:c0-32','분자 산소의 화학량론적 계수는'),('p21:b4:l2:s2-2:c33-63','로 하라.')],[(387.9985046386719,'1')]),
 (35,[401.3500061,267.0199585,427.75,268.0999756],265.82000732421875,[('p35:b6:l0:s16-16','근거를 제시하라')],[]),
 (43,[70.8239975,507.6699829,406.8739929,508.1499939],506.469970703125,[('p43:b6:l2:s0-0','몰 질량의 로그값은 용리 부피의 선형 함수이며, 그 변수는')],[]),
 (52,[196.9400024,174.0200195,252.2839966,174.5],172.82000732421875,[('p52:b8:l0:s0-0:c0-85:unit-prose-1:unit-prose-1','구조')],['3D']),
 (52,[284.4500122,174.0200195,372.6740112,174.5],172.82000732421875,[('p52:b8:l0:s0-0:c0-85:unit-prose-1:unit-prose-1','투시식')],[]),
 (56,[239.0899963,616.1499634,270.4100037,617.2299805],614.949951171875,[('p56:b7:l0:s5-5:c1-9','골라라')],[]),
 (56,[372.1900024,616.1499634,470.4940186,616.6300049],614.949951171875,[('p56:b7:l0:s6-6','보호기 또는 지향기')],[])]
for n,rect,y,targets,refs in rows:
    p=B/f'page{n:02}.overrides.json';q=json.loads(p.read_text('utf8'));plan=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'))
    slots=[dict(s,**q.get('__slot_edits__',{}).get(s['id'],{}))for s in plan['slots']+q.get('__extra_slots__',[])]
    def slot(id):
        out=[s for s in slots if s['id']==id];assert len(out)==1,id;return out[0]
    inv=motion.inspect_inline_groups(g.SOURCE,n);paths=[v for v in inv['vector_paths']if max(abs(a-b)for a,b in zip(rect,v['rect']))<.001];assert len(paths)==1,(n,paths)
    path=paths[0];native=[]
    for ref in refs:
        if ref=='3D':
            native=[v for v in c._glyphs(doc[n-1])if v['c']in'3D'and abs(v['origin'][1]-y)<.001 and rect[0]-.01<=v['origin'][0]<rect[2]];assert ''.join(v['c']for v in native)=='3D',native
        else:
            out=[v for v in c._glyphs(doc[n-1])if v['c']==ref[1]and abs(v['origin'][0]-ref[0])<.001 and abs(v['origin'][1]-y)<.001];assert len(out)==1;native+=out
    sourcefragments=[]
    for id,text in targets:
        s=slot(id);assert text in q.get(id,s.get('text','')),(id,s)
        sourcefragments.append(dict(slot_id=id,source_text=s['source']))
    if n==52:
        sourcefragments=[dict(slot_id='p52:b8:l0:s0-0:c0-85',source_text='3D structure'if refs else'perspective formula')]
    spec=dict(id=f'p{n}-missing-prose-underline-{path["operator_indices"][0]}',target_fragments=[dict(slot_id=id,target_text=text)for id,text in targets],source_fragments=sourcefragments,source_text=' | '.join(v['source_text']for v in sourcefragments),source_rect=path['rect'],source_baseline=y,operator_indices=path['operator_indices'],paint_operator=path['paint_operator'],native_source_glyphs=native,review='Original English prose underline, exact original source hash/path/English GIDs and source baseline verified. Only horizontal placement follows the source-bound Korean emphasized phrase; original y, thickness, black fill and native mathematical glyphs remain unchanged.')
    if n==43:
        spec['fit_source_prose_underline_to_translated_phrase']=True
        spec['review']+=' Explicit prose-only horizontal contraction to translated phrase width prevents intersection with the unchanged original V_e subscript; original construction bytes and the original/target width and transform matrix are retained in QA.'
    specs=q.setdefault('__prose_vector_decorations__',[]);specs[:]=[v for v in specs if v['id']!=spec['id']];specs.append(spec)
    p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(n,spec['id'],flush=True)
