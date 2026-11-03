"""Private2012 engine copy; retain shared native guards and migrated donors."""
from pathlib import Path
import json,hashlib
OLD=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions')
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');E=B/'engine';E.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
records=[]
for p in(OLD/'engine').glob('*.py'):
 dest=E/p.name
 if dest.exists():continue
 value=p.read_text('utf8').replace(OLD.as_posix(),B.as_posix()).replace(repr(str(OLD))[1:-1],repr(str(B))[1:-1])
 if p.name=='pdf_original_style_fonts.py':
  value=value.replace('import hashlib,re','import hashlib,re\nfrom haslalab_runtime_paths import map_repository_path')
  value=value.replace("FONT_DIR=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tools/ko/fonts')", "FONT_DIR=map_repository_path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab/tools/ko/fonts')")
 dest.write_text(value,'utf8');records.append(dict(file=p.name,prior_sha256=sha(p),private_sha256=sha(dest)))
mapper=Path('D:/CodexBuilds/haslalab_runtime_paths.py');(E/mapper.name).write_bytes(mapper.read_bytes())
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
plan=json.loads((B/'2012/original_style/page1.json').read_text('utf8'))
selections=[{k:label[k]for k in ['at','substring','source_substring','range']}for label in plan['reviewed_math_font_prose_words']]
policy=dict(source_sha256='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db',reviewed_source_pages={'0':selections},scope='Explicit source2012 page1 narrative English selections in CambriaMath, manually reviewed against the full original page. Ratio1:2:3, ordinal2, variableg, equation references, problem/grade/year digits and every unselected source math glyph remain native.')
policy_path=B/'2012/reviewed-math-font-prose-policy.json';policy_path.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n','utf8');policy_hash=sha(policy_path)
target=E/'izho_initial_fixed_style.py';s=target.read_text('utf8')
needle="        if not(reviewed_2020 or reviewed_2018_at or reviewed_2019_figure_phrase):raise ValueError('Unreviewed math-font prose label')"
replacement=f"""        reviewed_2012=False
        if data['source_sha256']=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db':
            policy_path=Path(__file__).resolve().parents[1]/'2012/reviewed-math-font-prose-policy.json'
            if hashlib.sha256(policy_path.read_bytes()).hexdigest()!={policy_hash!r}:raise ValueError('Source2012 literal-prose policy changed')
            policy=json.loads(policy_path.read_text('utf8'))
            selection={{k:label.get(k)for k in ['at','substring','source_substring','range']}}
            reviewed_2012=(label.get('reviewed')is True and policy['source_sha256']==data['source_sha256']
                and selection in policy['reviewed_source_pages'].get(str(pi),[])
                and runs[tuple(label['at'])]['font']=='CambriaMath'
                and not re.search(r'[0-9]',label['substring']))
        if not(reviewed_2020 or reviewed_2018_at or reviewed_2019_figure_phrase or reviewed_2012):raise ValueError('Unreviewed math-font prose label')"""
if needle in s:
 s=s.replace(needle,replacement)
 needle2="        matches=[s for s in data['slots']if s['at']==label['at']and s.get('substring')==label['substring']and s['text'].strip()==expected_label]"
 replace2="""        if reviewed_2012:
            matches=[s for s in data['slots']if s['at']==label['at']and s.get('range')==label.get('range')
                and s.get('substring')==label.get('source_substring')and s['source_text']==label['substring']
                and s['text']==label['translated_text']]
        else:
            matches=[s for s in data['slots']if s['at']==label['at']and s.get('substring')==label['substring']and s['text'].strip()==expected_label]"""
 assert needle2 in s;s=s.replace(needle2,replace2);target.write_text(s,'utf8')
else:assert 'reviewed_2012=False'in s
(B/'engine-copy-and-source-policy.json').write_text(json.dumps(dict(source_engine=str(OLD/'engine'),private_engine=str(E),copied_initial_records=records,source2012_literal_policy_sha256=policy_hash,shared_native_guard_unchanged=True,native_guard_sha256=sha(E/'pdf_native_inline_reposition.py'),font_donors_use_read_time_migration_mapper=True,actual_page_build_not_run=True),ensure_ascii=False,indent=2)+'\n','utf8')
for name in ['native-baseline']:(B/'2012'/name).mkdir(exist_ok=True)
print('PRIVATE_2012_ENGINE_AND_EXACT_LITERAL_SOURCE_POLICY_PREPARED',E,flush=True)
