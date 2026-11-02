"""Refuse cross-edition inputs/writes and fingerprint sealed2024/2025 artifacts."""
from pathlib import Path
import hashlib,json,os,time,ctypes
B=Path(__file__).resolve().parents[1]
C=Path('C:/Users/andre/CodexWork/HaslaLab/translation-proof-work')
LEGACY_C_PROOF_ROOT=C/'proofs/ortvay/2023'
LEGACY_C_CACHE_ROOT=C/'font-cache/ortvay/2023'
PROOF_ROOT=B/'proofs/ortvay/2023'
CACHE_ROOT=B/'composer/ortvay2023-font-cache'
PROFILE_ROOT=B/'source-review/ortvay2023'
STATE=PROFILE_ROOT/'protected-2024-2025-fingerprint.json'
SOURCE=Path('D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/source/ortvay/Ortvay_2023_T_EN.pdf')
SOURCE_SHA='c0a5117145c67edc2dfe8953dcc7865438f65e099fe6e73b2ec19616ab27b5f7'
READ_ALIAS_MANIFEST=B/'archives/C-retained-archive-relief-20261103/retained-archive-locations.json'
def sha(path):
    path=Path(path)
    if path.exists():return hashlib.sha256(path.read_bytes()).hexdigest()
    # Frozen manifests retain their historical C strings. Root moved only
    # these exact archives; resolve reads here without altering old manifests.
    if READ_ALIAS_MANIFEST.exists():
        cfg=json.loads(READ_ALIAS_MANIFEST.read_text('utf8'))
        assert cfg['status']=='RETAINED_ON_D_SHA_VERIFIED' and cfg['frozen_historical_manifests_unchanged']
        candidates=[r for r in cfg['files'] if Path(r['historical_c_path']).resolve()==path.resolve()]
        if candidates:
            assert len(candidates)==1 and candidates[0]['byte_identical']
            entry=candidates[0];target=Path(entry['retained_d_path'])
            assert target.name==path.name;regular_ancestors(target)
            data=target.read_bytes();digest=hashlib.sha256(data).hexdigest()
            assert len(data)==entry['bytes'] and digest==entry['sha256']
            return digest
    raise FileNotFoundError(path)

def resolve_current_artifact(path):
    """Read old C provenance via exact D copies; never rewrite old sidecars."""
    path=Path(path)
    for old,new in [(LEGACY_C_PROOF_ROOT,PROOF_ROOT),(LEGACY_C_CACHE_ROOT,CACHE_ROOT),(C/'source-comparison/ortvay2023/compression-regression',PROFILE_ROOT/'compression-regression')]:
        try:relative=path.relative_to(old)
        except ValueError:continue
        target=new/relative
        if target.exists():return target
    return path

def protected_paths():
    legacy=json.loads((B/'source-review/ortvay2024/protected-2025-fingerprint.json').read_text('utf8'))['files']
    roots=[B/'proofs/ortvay/2025',B/'historical/ortvay/2025',B/'composer/ortvay2025-frozen-engine']
    p25=[p for root in roots for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    p25 += [B/'composer/natural_plan_compose_ortvay2025_final.py',B/'composer/verify_native_vectors_ortvay2025.py']+list((B/'composer').glob('ortvay2025-page*.overrides.json'))
    p25 += [p for p in [B/'staged/ortvay/Ortvay_2025_T_KO.pdf',B/'staged/ortvay/Ortvay_2025_T_KO.qa.json'] if p.exists()]
    p25.append(C/'archives/published-plancks2024-ortvay2025-page-proofs.zip')
    actual25={str(p.resolve()):sha(p) for p in p25}
    assert actual25==legacy,'Sealed2025 fingerprint changed before2023 work'
    paths=list(map(Path,legacy))
    roots24=[B/'historical/ortvay/2024',B/'composer/ortvay2024-frozen-engine']
    paths += [p for root in roots24 for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [p for p in (B/'proofs/ortvay/2024').iterdir() if p.is_file() and p.suffix not in ['.pdf','.png']]
    paths += list((B/'composer').glob('ortvay2024-page*.overrides.json'))
    manifest=json.loads((B/'composer/ortvay2024-frozen-engine/manifest.json').read_text('utf8'))
    paths += [Path(p) for p in manifest['files']]
    paths += [B/'source-review/ortvay2024-scope.json',B/'staged/ortvay2024-READY.json']
    paths += list((B/'source-review/ortvay2024').rglob('*.json'))
    # C holds each immutable master proof. D PDF/PNG duplicates may be reclaimed
    # by root after exact copying; only D metadata is canonical/protected here.
    for n in range(1,14):
        for suffix in ['.pdf','.moved.pdf','.png','.layout.json','.effective-plan.json']:
            paths.append(C/'proofs/ortvay/2024'/f'page{n:02}{suffix}')
    return sorted(set(p.resolve() for p in paths))

def fingerprint():return {str(p):sha(p) for p in protected_paths()}

def initialize_protected_editions():
    assert sha(B/'composer/natural_plan_compose_ortvay2024_final.py')=='dcaa063027552abf40e55e3c1ceb6d9ac5d36fa29bdf05f206c3c7f2e077045c'
    review=B/'proofs/ortvay/2024/visual-review-natural-01-13.json'
    assert sha(review)=='5c300e4ed8dc13a7439b30761afca0583b048c0a269a84b817f871504ab4c078'
    assert sha(B/'composer/ortvay2024-frozen-engine/manifest.json')=='b26b5bbd78b7bdcca09dfb6f1bd2f41e187132c02416546396e44a9833aff567'
    for row in json.loads(review.read_text('utf8'))['pages']:
        n=row['page'];master=C/'proofs/ortvay/2024'/f'page{n:02}.pdf'
        for p,key in [(master,'proof_sha256'),(master.with_suffix('.png'),'png_sha256'),(master.with_suffix('.layout.json'),'layout_sha256'),(master.with_suffix('.effective-plan.json'),'effective_plan_sha256')]:
            assert sha(p)==row[key],('Sealed2024 master differs',p)
    current=fingerprint()
    if STATE.exists():assert current==json.loads(STATE.read_text('utf8'))['files'],'Sealed editions changed'
    else:
        PROFILE_ROOT.mkdir(parents=True,exist_ok=True)
        STATE.write_text(json.dumps({'status':'SEALED2024_AND2025_READ_ONLY_FOR2023','files':current},indent=2),'utf8')
    return current

def _active_batch_boundary():
    """Only a live, fully checked2023 batch may defer redundant inner reads.

    The owner always performs the complete288-file byte check before and after
    its child processes; all2023 per-page source/font/glyph/ink audits still run.
    An interrupted owner cannot authorize another process or a READY record.
    """
    name=os.environ.get('ORTVAY2023_BATCH_ATTESTATION')
    if not name:return False
    token=Path(name)
    assert token.parent.resolve()==(PROFILE_ROOT/'batch-boundaries').resolve()
    assert token.name.startswith('batch-') and token.suffix=='.json'
    regular_ancestors(token)
    raw=token.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==os.environ.get('ORTVAY2023_BATCH_ATTESTATION_SHA256')
    state=json.loads(raw)
    assert state['schema']=='ortvay2023-fully-hashed-protected-batch-v1'
    assert state['protected_manifest_sha256']==sha(STATE)
    assert state['protected_file_count']==288 and state['full_start_hashes_passed'] is True
    assert state['source_sha256']==SOURCE_SHA
    assert 0<=time.time()-state['started_epoch']<6*3600
    assert not token.with_suffix('.closed.json').exists(),'Completed batch token cannot be reused'
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x1000,False,state['owner_pid'])
    assert handle,'Protected batch owner is not active'
    try:
        code=ctypes.c_ulong()
        assert kernel.GetExitCodeProcess(handle,ctypes.byref(code)) and code.value==259
    finally:kernel.CloseHandle(handle)
    return True

def assert_protected_editions(force_full=False):
    if not force_full and _active_batch_boundary():return True
    expected=json.loads(STATE.read_text('utf8'))['files'];current=fingerprint()
    changed=[p for p in expected.keys()|current.keys() if expected.get(p)!=current.get(p)]
    assert not changed,'Protected2024/2025 mutation: '+repr(changed)
    return True

def regular_ancestors(path):
    # Inspect lexical ancestors before resolving; resolving first could conceal
    # a junction that redirects a nominal2023 output into a sealed edition.
    path=Path(os.path.abspath(path))
    for root in [path]+list(path.parents):
        if root.exists():assert not root.is_symlink() and not root.is_junction(),('Reparse point forbidden',root)

def validate_paths(n,plan,target,engine,override=None,layout_only=False):
    assert 1<=n<=13
    for root in [PROOF_ROOT,CACHE_ROOT,PROFILE_ROOT,B/'historical/ortvay/2023']:
        regular_ancestors(root)
    plan=Path(plan).resolve();target=Path(target).resolve();engine=Path(engine).resolve()
    assert plan==(B/'historical/ortvay/2023'/f'page{n:02}.ko.json').resolve()
    expected=PROFILE_ROOT if layout_only else PROOF_ROOT
    assert target.parent==expected.resolve(),('Cross-year output rejected',target)
    if not layout_only:
        assert target==(PROOF_ROOT/f'page{n:02}.pdf').resolve()
        for suffix in ['.pdf','.moved.pdf','.png','.layout.json','.effective-plan.json','.build.log']:
            assert target.with_suffix(suffix).parent==PROOF_ROOT.resolve()
    assert engine==(B/'composer/natural_plan_compose_ortvay2023_final.py').resolve()
    if override:assert Path(override).resolve()==(B/'composer'/f'ortvay2023-page{n:02}.overrides.json').resolve()
    q=json.loads(plan.read_text('utf8'))
    assert q['year']==2023 and q['competition']=='ortvay' and q['page']==n
    assert Path(q['source']).resolve()==SOURCE.resolve() and Path(q['source']).name=='Ortvay_2023_T_EN.pdf'
    assert q['source_sha256']==SOURCE_SHA and sha(SOURCE)==SOURCE_SHA
    if override:
        edits=json.loads(Path(override).read_text('utf8'))
        ids={s['id'] for s in q['slots']}
        extra=[s['id'] for s in edits.get('__extra_slots__',[])]
        assert len(extra)==len(set(extra)) and not ids.intersection(extra),'Duplicate extra-slot ids'
        assert {key for key in edits if not key.startswith('__')}<=ids|set(extra),'Unknown translated slot override id'
        assert set(edits.get('__slot_edits__',{}))<=ids,'Unknown source-slot edit id'
    for root in [plan.parent,target.parent,engine.parent,CACHE_ROOT]:regular_ancestors(root)
    assert CACHE_ROOT.resolve()==(B/'composer/ortvay2023-font-cache').resolve()
    return True
