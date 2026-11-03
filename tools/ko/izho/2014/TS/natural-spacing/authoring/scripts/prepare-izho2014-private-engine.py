from pathlib import Path
import hashlib,json
OLD=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');B=OLD.with_name('izho2014-complete-solutions');E=B/'engine';E.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();records=[]
for source in sorted((OLD/'engine').glob('*.py')):
 target=E/source.name
 if target.exists():continue
 text=source.read_text('utf8').replace(OLD.as_posix(),B.as_posix()).replace(repr(str(OLD))[1:-1],repr(str(B))[1:-1])
 if source.name in['izho_initial_fixed_style.py','final_translation_font_audit.py']:
  text=text.replace("=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db':", " in ['41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db','1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c']:",1)
 target.write_text(text,'utf8');records.append(dict(file=source.name,prior_sha256=sha(source),private_sha256=sha(target)))
mapper=Path('D:/CodexBuilds/haslalab_runtime_paths.py');(E/mapper.name).write_bytes(mapper.read_bytes())
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
for path in['2014/native-baseline','natural/2014/TS/plans']:(B/path).mkdir(parents=True,exist_ok=True)
counts=[]
for n in range(1,11):
 plan=json.loads((B/f'2014/original_style/page{n}.json').read_text('utf8'));assert plan['source_sha256']=='1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c';assert not plan.get('reviewed_math_font_prose_words');counts.append(dict(page=n,prose_selections=len(plan['slots'])))
(B/'engine-copy-and-source-policy.json').write_text(json.dumps(dict(source_engine=str(OLD/'engine'),private_engine=str(E),copied_initial_records=records,source_sha256='1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c',explicit_translation_plans=counts,all10_full_original_pages_visually_read=True,shared_native_guard_unchanged=True,native_guard_sha256=sha(E/'pdf_native_inline_reposition.py'),source_2012_specific_profiles_not_enabled_for_2014=True,original_prose_paint_independently_read_for_2014=True,font_donors_use_read_time_migration_mapper=True,actual_page_build_not_run=True),ensure_ascii=False,indent=2)+'\n','utf8')
print('PRIVATE_IZHO2014_ENGINE_ALL10_PROSE_PLANS_PREPARED',sum(v['prose_selections']for v in counts),flush=True)
