from pathlib import Path
import json
import author_outlined_vector_labels as a
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;R=B/'graphic-language-audit-01-56-20261103';data=json.loads((R/'graphic-language-audit-report.json').read_text('utf8'));profiles={n:json.loads((R/f'page{n:02}-source-vector-profile.json').read_text('utf8'))for n in[27,28,54]}
old=a.form
def form(n):
    if n not in profiles:return old(n)
    forms=profiles[n]['forms'];assert len(forms)==1;return forms[0]
a.form=form
def add(n,id,eng,ko,starts,**kw):a.add(n,id,eng,ko,starts,**kw)
add(27,'p27-initial','initial','초기',[1]);add(27,'p27-solution','solution','용액',[118])
add(27,'p27-phase','phase','상',[433]);add(27,'p27-separation','separation','분리',[577])
for k,starts in enumerate([[1383,1460,1558],[1725,1802,1900]]):
    add(27,f'p27-near-endpoint-{k}-1','until near','종말점',starts[:2]);add(27,f'p27-near-endpoint-{k}-2','endpoint','직전까지',starts[2:])
for k,starts in enumerate([[2144,2235],[2386,2477]]):
    add(27,f'p27-add-starch-{k}-1','add','녹말',starts[:1]);add(27,f'p27-add-starch-{k}-2','starch','첨가',starts[1:])
for k,starts in enumerate([[2752,2933,3010],[3079,3260,3337]]):
    add(27,f'p27-titrate-end-{k}-1','titration','종말점까지',starts[:1]);add(27,f'p27-titrate-end-{k}-2','until end','적정',starts[1:])
for v in data['ordinary_uncovered_vector_labels']:
    if v['page']!=28:continue
    starts=[p['operator_indices'][0]for p in v['source_paths']];word=v['source_text'];ko=v['suggested_Korean']
    if word=='Dark Blue':add(28,v['id']+'-1','Dark','짙은',starts[:1]);add(28,v['id']+'-2','Blue','청색',starts[1:])
    elif word=='Yello- / wish':
        add(28,v['id']+'-1','Yello-','누런',starts[:1]);add(28,v['id']+'-2','wish','기운',starts[1:])
    else:add(28,v['id'],word,'누런색'if word=='Yellowish'else ko,starts,left_anchor=word in['colourless','dark','purple'])
add(54,'p54-acetone','Acetone','아세톤',[1438],left_anchor=True)
for n,labels in a.rows.items():
    p=B/f'page{n:02}.overrides.json';q=json.loads(p.read_text('utf8'));q['__outlined_vector_labels__']=labels;p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(n,len(labels),flush=True)
(B/'additional-outlined-vector-label-authoring-review.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,pages=a.rows,source_inventory_sha256=a.hashlib.sha256((R/'graphic-language-audit-report.json').read_bytes()).hexdigest(),review='Read source27/28/54 diagrams. Preserve original two-line label rows, centres, original scientific aq/org, CLess/Dk, beaker letters, stages, solvent slash/H2O. Font/point/baseline inferred from outlined English per original row; exact source font metadata is unavailable.'),ensure_ascii=False,indent=2)+'\n','utf8')
