from pathlib import Path
import hashlib,shutil,json,datetime
D=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2017-complete-solutions');C=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2017-complete-solutions');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
for source in sorted(D.rglob('*')):
 if not source.is_file()or '__pycache__'in source.parts:continue
 dest=C/source.relative_to(D);dest.parent.mkdir(parents=True,exist_ok=True);pin=sha(source)
 if dest.exists():assert sha(dest)==pin,('Independent C outputs must not be overwritten',dest)
 else:shutil.copy2(source,dest)
 assert sha(source)==sha(dest)==pin;rows.append(dict(path=source.relative_to(D).as_posix(),bytes=source.stat().st_size,sha256=pin))
modified=[]
for p in (C/'engine').glob('*.py'):
 raw=p.read_bytes();new=raw.replace(D.as_posix().encode(),C.as_posix().encode()).replace(str(D).replace('\\','\\\\').encode(),str(C).replace('\\','\\\\').encode())
 if raw!=new:p.write_bytes(new);modified.append(dict(file=p.name,old_sha256=hashlib.sha256(raw).hexdigest(),new_sha256=sha(p)))
scripts=['build-izho2017-solutions-natural-page.py','recheck-izho2017-current-proof.py','check-and-preview-izho2017-extra-prose.py','render-izho2017-reviewed-previews.py','archive-izho2017-rejected-proofs.py','prepare-izho2017-solutions-natural.py','isolate-izho2017-source-cell-expression-programs.py','inspect-izho2017-source-cell-native-programs.py']
for name in scripts:
 p=Path('D:/CodexBuilds')/name;raw=p.read_bytes();new=raw.replace(D.as_posix().encode(),C.as_posix().encode());assert new!=raw;p.write_bytes(new)
assert sha(C/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
report=dict(checked_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason='D drive has3MB free; all new substantial outputs now generated on C. Original authoring data and source inputs remain unchanged at their original D locations.',original_D_untouched=True,copied_files=rows,bytes=sum(r['bytes']for r in rows),new_private_runtime_output_paths_modified=modified,new_runtime_root=str(C),future_scripts=scripts,shared_native_guard_unchanged=True)
(C/'new-output-location-copy-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('ORIGINAL_D_UNCHANGED_ALL_CURRENT2017_FILES_COPIED_SHA_VERIFIED_AND_FUTURE_OUTPUTS_ON_C',len(rows),report['bytes'],len(modified),flush=True)
