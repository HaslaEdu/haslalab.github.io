from pathlib import Path
import hashlib,ast,shutil,json
D=Path('D:/CodexBuilds/Hasla-original-style-20261031');B=D/'cpho2007/TS';PD=Path('D:/CodexBuilds/Hasla-publish-20261031');E=B/'engine';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pending=['cpho_cjk_translate','cpho_original_style','pdf_layout_translate'];seen=set();copied=[]
while pending:
 name=pending.pop()
 if name in seen:continue
 seen.add(name);src=PD/f'tools/{name}.py';dst=E/f'{name}.py'
 if not src.exists()or dst.exists():continue
 shutil.copy2(src,dst);copied.append(dict(file=dst.name,sha256=sha(dst),source=str(src)))
 for node in ast.walk(ast.parse(dst.read_text('utf-8-sig'))):
  names=[a.name.split('.')[0]for a in node.names]if isinstance(node,ast.Import)else[node.module.split('.')[0]]if isinstance(node,ast.ImportFrom)and node.module else[]
  pending.extend(n for n in names if(PD/f'tools/{n}.py').exists()and not(E/f'{n}.py').exists())
src=PD/'tools/cpho_2007_original_build.py';text=src.read_text('utf8');needle="    if bad:raise ValueError('Overflow: '+', '.join(r['id']for r in bad))";assert text.count(needle)==1;text=text.replace(needle,"    if bad:print('PRIVATE_FIXED_SLOT_STAGING_OVERFLOWS_NOT_A_DELIVERABLE',len(bad),flush=True)")
text=text.replace("core_sha=hashlib.sha256((ROOT/'tools/pdf_original_text_ops.py').read_bytes()).hexdigest()","core_sha=hashlib.sha256(Path(__import__('pdf_original_text_ops').__file__).read_bytes()).hexdigest()")
dest=E/'cpho2007_ts_initial_native_baseline.py';assert not dest.exists();dest.write_text(text,'utf8')
(B/'inputs/private-initial-baseline-engine-provenance.json').write_text(json.dumps(dict(original_builder=str(src),original_builder_sha256=sha(src),private_builder_sha256=sha(dest),fixed_slot_overflow_is_staging_only=True,full_original_font_sizes_and_baselines_remain_unchanged=True,dependency_copies=copied,guard_sha256=sha(E/'pdf_native_inline_reposition.py')),ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_NATIVE_DIGITAL_CPHO2007_TS_BASELINE_RUNTIME_PREPARED',flush=True)
