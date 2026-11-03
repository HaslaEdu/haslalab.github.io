from pathlib import Path
import json,hashlib,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');D=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-complete-solutions');OLD=D.with_name('izho2015-complete-solutions');E=B/'engine';E.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();copies=[]
for p in(OLD/'engine').glob('*.py'):
 t=p.read_text('utf8').replace(OLD.as_posix(),B.as_posix()).replace(repr(str(OLD))[1:-1],repr(str(B))[1:-1]);target=E/p.name
 if target.exists():assert target.read_text('utf8')==t,'Never overwrite a reviewed private engine'
 else:target.write_text(t,'utf8')
 copies.append(dict(source=str(p),source_sha256=sha(p),private_copy=str(target),sha256=sha(target)))
for folder in['2018/source','2018/inspection','2018/original_style','2018/native-baseline','legacy-semantics']:(B/folder).mkdir(parents=True,exist_ok=True)
for p in [D/'source-policy.json',D/'legacy-semantics/translation.json',D/'2018/source/IZhO_2018_TS.pdf']+list((D/'2018/inspection').glob('*-runs.json')):
 target=B/p.relative_to(D);shutil.copy2(p,target);assert sha(p)==sha(target)
SOURCE='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49';assert sha(B/'2018/source/IZhO_2018_TS.pdf')==SOURCE
# Exact source-selected prose paint applies to every source18 serif/sans
# source run. Mathematical paints/fonts/glyphs are still native and protected.
p=E/'izho_initial_fixed_style.py';t=p.read_text('utf8');needle="if data['source_sha256'] in ['41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db','c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde']:";replacement="if data['source_sha256'] in ['41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db','c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde','"+SOURCE+"']:";assert needle in t;t=t.replace(needle,replacement);p.write_text(t,'utf8')
p=E/'izho_natural_spacing_rebuild.py';t=p.read_text('utf8');needle="(2015,'c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde')]:";assert needle in t;t=t.replace(needle,"(2015,'c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde'),(2018,'"+SOURCE+"')]:");p.write_text(t,'utf8')
p=E/'final_translation_font_audit.py';t=p.read_text('utf8');needle="p['original_english_source_sha256'] in ['41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db','c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde']";assert needle in t;t=t.replace(needle,"p['original_english_source_sha256'] in ['41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db','c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde','"+SOURCE+"']");p.write_text(t,'utf8')
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
(B/'engine-copy-and-source-policy.json').write_text(json.dumps(dict(source_sha256=SOURCE,original_D_source_inputs_read_only=True,private_generated_root=str(B),copied_from_frozen_source15_engine=str(OLD/'engine'),copies=copies,source_specific_2015_branches_stay_hash_bound_and_do_not_apply_to_2018=True,native_guard_sha256=sha(E/'pdf_native_inline_reposition.py')),ensure_ascii=False,indent=2)+'\n','utf8')
print('C18_PRIVATE_ENGINE_AND_HASH_VERIFIED_SOURCE_METADATA_READY_NO_D_INPUT_MUTATION')
