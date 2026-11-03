from pathlib import Path
import json,hashlib,ast
OLD=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');FROZEN=OLD/'natural/2016-TS-authoring/tools';B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');E=B/'engine';E.mkdir(exist_ok=True);SOURCE='5e83000f5d2abe161186a6f81e5b9cd306a0758d2969744edbfb68fcad413da8';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();records=[]
for source in sorted(FROZEN.glob('*.py')):
 target=E/source.name
 if target.exists():continue
 text=source.read_text('utf8').replace(OLD.as_posix(),B.as_posix()).replace(repr(str(OLD))[1:-1],repr(str(B))[1:-1])
 if source.name in['izho_initial_fixed_style.py','final_translation_font_audit.py']:
  needle="'19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8']";text=text.replace(needle,"'19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8','"+SOURCE+"']",1)
 if source.name=='izho_natural_spacing_rebuild.py':
  needle="(2016,'19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8')]:\n            prose_ats=";replacement="(2016,'19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8'),(2019,'"+SOURCE+"')]:\n            prose_ats=";assert needle in text;text=text.replace(needle,replacement)
 ast.parse(text);target.write_text(text,'utf8');records.append(dict(file=source.name,read_only_frozen_source_sha256=sha(source),private_sha256=sha(target)))
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
(B/'private-engine-copy-policy.json').write_text(json.dumps(dict(read_only_frozen_2016_engine=str(FROZEN),private_C19_engine=str(E),source_sha256=SOURCE,shared_native_guard_sha256=sha(E/'pdf_native_inline_reposition.py'),copies=records,source_2016_only_policies_not_enabled_for_2019=True,all_generated_data_root=str(B),D19_and_B16_files_read_only=True),ensure_ascii=False,indent=2)+'\n','utf8');print('IZHO2019_TS_C_PRIVATE_ENGINE_COPIED_GUARD_UNCHANGED',len(records),flush=True)
