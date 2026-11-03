from pathlib import Path
import hashlib,json,shutil
BASE=Path(__file__).resolve().parent
PLANS=(BASE.parent/'2019').resolve()
SOURCE=(BASE.parent/'english-missing/IChO_2019_T_EN.pdf').resolve()
SOURCE_SHA='5821bab3b65b216cc74df99d7ec643389d212c15b4d88c95a7da22de8baf97d8'
METADATA=Path('D:/CodexBuilds/Hasla-poi-natural-20261102/proofs/icho/2019-final').resolve()
PROOFS=METADATA
CACHE=(BASE/'composer/font-cache').resolve()
MIN_FREE=256*1024*1024
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def assert_protected_2024():
    provenance=json.loads((BASE/'bootstrap-provenance.json').read_text('utf8'))
    for e in provenance['entries']:
        if sha(Path(e['source']))!=e['source_sha256']:raise ValueError('Frozen2024 source changed: '+e['source'])
def assert_plan(plan_path,plan):
    if Path(plan_path).resolve().parent!=PLANS or plan.get('year')!=2019 or plan.get('competition')!='icho':raise ValueError('Cross-year IChO plan rejected')
    if Path(plan['source']).resolve()!=SOURCE or plan.get('source_sha256')!=SOURCE_SHA or sha(SOURCE)!=SOURCE_SHA:raise ValueError('IChO2019 exact source guard failed')
    if not 1<=plan.get('page',0)<=60:raise ValueError('IChO2019 page outside source')
    if plan.get('contains_solutions')is not False:raise ValueError('IChO2019 source scope must retain contains_solutions=false')
    assert_protected_2024()
def assert_output(path,page):
    p=Path(path)
    if not p.is_absolute()or p.resolve().parent!=PROOFS or p.name!=f'page{page:02}.pdf':raise ValueError('Cross-year/nonabsolute proof output rejected')
    for directory in[PROOFS,METADATA,CACHE]:
        if shutil.disk_usage(directory.anchor).free<MIN_FREE:raise ValueError('256MiB output/cache/metadata minimum reached: '+str(directory))
        directory.mkdir(parents=True,exist_ok=True)
    return p.resolve()
def assert_override(path,page):
    if path is not None and Path(path).resolve()!=BASE/f'page{page:02}.overrides.json':raise ValueError('Cross-year override path rejected')
