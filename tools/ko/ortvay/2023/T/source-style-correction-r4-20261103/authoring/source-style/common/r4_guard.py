"""Private R4 namespace and exact source/input/runtime snapshot guards."""
from pathlib import Path
import hashlib,json,os,re,shutil

ROOT=Path(__file__).resolve().parents[1]
FIVE={(2023,1),(2024,3),(2025,1),(2026,1),(2026,3)}

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def regular(path):
    path=Path(path).absolute()
    for parent in [path,*path.parents]:
        if parent.exists() and (parent.is_symlink() or parent.is_junction()):raise ValueError('Reparse point is forbidden: '+str(parent))
    return path.resolve()
def inside(path,base=ROOT):
    path=regular(path);base=regular(base)
    if path==base or base not in path.parents:raise ValueError('Path escaped the private R4 namespace: '+str(path))
    return path
def ledger():
    path=ROOT/'input-ledger.json';data=json.loads(path.read_text('utf8'))
    assert data['schema']=='r4-exact-source-and-private-input-ledger-v1'
    return path,data
def rules(base):
    base=regular(base);year=int(base.name);assert year in (2023,2024,2025,2026)
    path,data=ledger();entry=data['years'][str(year)];rp=inside(entry['rules_path'])
    assert rp==base/'rules.json' and sha(rp)==entry['rules_sha256']
    cfg=json.loads(rp.read_text('utf8'));assert regular(cfg['private_base'])==base and cfg['year']==year
    return cfg
def assert_all_inputs():
    path,data=ledger();checked=set()
    for row in data['immutable_original_pins'].values():
        key=(str(regular(row['read_path'])),row['sha256'])
        if key in checked:continue
        assert sha(key[0])==key[1],('Immutable source/prior/publication changed',key[0]);checked.add(key)
    for name,digest in data['private_input_sha256'].items():
        path=inside(name);assert sha(path)==digest,('Pinned private input changed',name)
    return dict(unique_original_files=len(checked),private_inputs=len(data['private_input_sha256']))
def validate_plan(base,plan,overrides=None):
    cfg=rules(base);plan=inside(plan);value=json.loads(plan.read_text('utf8'));n=value['page']
    expected=cfg['base_plans'][str(n)];assert plan==regular(expected['path']) and sha(plan)==expected['sha256']
    assert value['source_sha256']==cfg['source_sha256'] and regular(value['source'])==regular(cfg['source_path'])
    assert sha(value['source'])==cfg['source_sha256']
    expected=cfg['overrides'].get(str(n))
    if expected:
        assert overrides is not None and regular(overrides)==regular(expected['path']) and sha(overrides)==expected['sha256']
    else:assert overrides is None
    return cfg,value
def experiment_go():
    path,data=ledger();token=json.loads((ROOT/'EXPERIMENT-GO.json').read_text('utf8'))
    assert token['status']=='ROOT_GO_PRIVATE_IMPLEMENTATION_AND_FIVE_EXPERIMENTS_ONLY'
    assert {tuple(v) for v in token['allowed_cases']}==FIVE and token['input_ledger_sha256']==sha(path)
    assert token['final48_generation_authorized'] is False
    return token
def validate_output(year,page,target):
    target=inside(target)
    assert target.name==f'page{page:02}.pdf' and 1<=page<=rules(ROOT/str(year))['pages']
    exp=ROOT/'experiments'
    if exp in target.parents:
        experiment_go();relative=target.relative_to(exp)
        assert len(relative.parts)==3 and re.fullmatch(r'attempt-[a-zA-Z0-9_-]+',relative.parts[0])
        assert relative.parts[1]==str(year) and (year,page) in FIVE
        return 'root-authorized-five-case-experiment'
    expected=ROOT/str(year)/f'proofs/ortvay/{year}'/target.name
    assert target==expected
    token_path=ROOT/'FINAL48-GO.json'
    if not token_path.exists():raise ValueError('Full48-page generation still requires fresh root GO')
    token=json.loads(token_path.read_text('utf8'));path,data=ledger()
    assert token['status']=='ROOT_GO_FINAL48_SOURCE_STYLE_WIDTH_CORRECTION'
    assert token['input_ledger_sha256']==sha(path)
    frozen=ROOT/'PREPARATION-FROZEN.json';assert token['preparation_sha256']==sha(frozen)
    assert_runtime_frozen()
    return 'root-authorized-final48'
def output_directory(base,year):
    assert regular(base)==ROOT/str(year)
    value=os.environ.get('R4_OUTPUT_DIRECTORY')
    path=inside(value) if value else ROOT/str(year)/f'proofs/ortvay/{year}'
    # validate_output is still mandatory for the exact page before any write.
    return path
def validate_write(base,plan,target,overrides=None):
    cfg,value=validate_plan(base,plan,overrides)
    validate_output(cfg['year'],value['page'],target)
    assert_runtime_snapshot()
    if shutil.disk_usage(ROOT).free<256*1024*1024:raise ValueError('Private R4 drive has less than256MiB free')
    return cfg,value
def runtime_files(year):
    paths=list((ROOT/'common').glob('*.py'))+list((ROOT/str(year)/'composer').glob('*.py'))
    paths += list((ROOT/str(year)/f'composer/ortvay{year}-frozen-engine').rglob('*.py'))
    return sorted(set(paths))
def capture_runtime_snapshot(year,directory):
    directory=inside(directory);directory.mkdir(parents=True,exist_ok=False)
    hashes={}
    for source in runtime_files(year):
        relative=source.relative_to(ROOT);target=directory/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target);digest=sha(source);assert sha(target)==digest
        hashes[str(source)]=dict(sha256=digest,retained_copy=str(target))
    path,data=ledger();result=dict(schema='r4-live-runtime-source-snapshot-v1',year=year,input_ledger_sha256=sha(path),files=hashes)
    manifest=directory/'runtime-snapshot.json';manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    return manifest
def assert_runtime_snapshot():
    name=os.environ.get('R4_RUNTIME_SNAPSHOT')
    if not name:raise ValueError('A retained per-run runtime source snapshot is required')
    path=inside(name);assert ROOT/'experiments' in path.parents or ROOT/'runtime-snapshots' in path.parents
    data=json.loads(path.read_text('utf8'));lp,_=ledger();assert data['input_ledger_sha256']==sha(lp)
    assert {str(v) for v in runtime_files(data['year'])}==set(data['files']),'Runtime source file inventory changed mid-run'
    for name,row in data['files'].items():
        assert sha(inside(name))==row['sha256'] and sha(inside(row['retained_copy']))==row['sha256'],('Runtime code changed mid-run',name)
    return data
def assert_runtime_frozen():
    frozen=json.loads((ROOT/'PREPARATION-FROZEN.json').read_text('utf8'))
    for name,digest in frozen['runtime_sha256'].items():assert sha(inside(name))==digest,('Frozen final R4 code changed',name)
    return True
