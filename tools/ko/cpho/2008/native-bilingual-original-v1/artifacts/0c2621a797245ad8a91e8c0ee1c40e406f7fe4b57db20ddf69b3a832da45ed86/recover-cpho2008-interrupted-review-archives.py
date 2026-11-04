"""Recover only owned partial archives, verifying bytes before retiring originals."""
from pathlib import Path
import json,hashlib,os,shutil
B=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def copy_exact(src,dst):
    assert src.resolve().is_relative_to(B) and dst.resolve().is_relative_to(B)
    digest=sha(src)
    if dst.exists() and sha(dst)!=digest:
        dst.rename(dst.with_name(dst.name+'.partial-no-space-'+sha(dst)[:16]))
    if not dst.exists():
        temp=dst.with_name(dst.name+'.recover-writing')
        shutil.copy2(src,temp)
        assert sha(temp)==digest
        os.replace(temp,dst)
    assert sha(dst)==digest
    return dict(path=str(dst),sha256=digest,bytes=dst.stat().st_size)

for n,lang in [(8,'ko'),(8,'en'),(17,'en'),(19,'ko'),(19,'en')]:
    stem=B/f'proofs/{lang}/page{n:02}'
    histories=list((B/'history').glob(f'page{n:02}-{lang}-*'))
    comp=stem.with_suffix('.composition.json')
    if not comp.exists():
        candidates=[h/'page%02d.composition.json'%n for h in []] # explicit search below
        candidates=[h/f'page{n:02}.composition.json' for h in histories if (h/f'page{n:02}.composition.json').exists() and not (h/'history.json').exists()]
        assert len(candidates)==1,(n,lang,candidates)
        comp=candidates[0]
    report=json.loads(comp.read_text('utf8'));digest=report['output_sha256']
    H=B/f'history/page{n:02}-{lang}-{digest[:16]}';H.mkdir(exist_ok=True)
    plan=Path(report['actual_immutable_producing_plan'])
    assert sha(plan)==report['plan_sha256']
    records=[copy_exact(plan,H/plan.name)]
    author=B/f'authoring/page{n:02}-native-language.json'
    if author.exists() and not (H/author.name).exists():
        records.append(copy_exact(author,H/(author.name+'.interrupted-authoring-state')))
    candidates=list(stem.parent.glob(stem.name+'.*'))+list((B/'inspection').glob(f'page{n:02}-{lang}-current144.*'))
    for src in candidates:
        records.append(copy_exact(src,H/src.name));src.unlink()
    archived=H/f'page{n:02}.pdf'
    assert sha(archived)==digest
    archived_comp=H/f'page{n:02}.composition.json'
    assert json.loads(archived_comp.read_text('utf8'))['plan_sha256']==sha(plan)
    records=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)for p in sorted(H.iterdir())if p.is_file() and p.name!='history.json']
    data=dict(reason='Preserved prior positive/reviewed PDF before source-faithful wording repair; recovered interrupted archive after disk exhaustion',actual_proof_sha256=digest,actual_producing_plan_sha256=sha(plan),files=records)
    (H/'history.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
    print('C08_ARCHIVE_RECOVERED',n,lang,digest,flush=True)
