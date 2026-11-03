from pathlib import Path
import json,hashlib,shutil
R=Path('D:/CodexBuilds');OLD=R/'Hasla-original-style-20261031/izho2012-complete-solutions';B=OLD.with_name('izho2015-complete-solutions');E=B/'engine';E.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source_sha=sha(B/'2015/source/IZhO_2015_TS.pdf')
plans=[json.loads((B/f'2015/original_style/page{n}.json').read_text('utf8'))for n in range(1,12)];assert all(p['source_sha256']==source_sha for p in plans);words=[(p['page'],w)for p in plans for w in p['reviewed_math_font_prose_words']];assert len(words)==1 and words[0][0]==8
policy={'source_sha256':source_sha,'reviewed_source_pages':{str(pi):[{k:w.get(k)for k in['at','substring','source_substring','range']}for p,w in words if p==pi]for pi in{p for p,w in words}},'reason':'Full originals1-11 visually read. Only the literal English conjunction and and its surrounding source prose spaces inside p9 Cambria Math are translated. Every adjacent native mathematical parenthesis/p-dot/combining accent remains protected. No digit or mathematical identifier is prose.'}
policy_path=B/'2015/reviewed-math-font-prose-policy.json';assert not policy_path.exists();policy_path.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n','utf8');policy_sha=sha(policy_path);records=[]
for source in sorted((OLD/'engine').glob('*.py')):
 target=E/source.name;assert not target.exists();text=source.read_text('utf8').replace(OLD.as_posix(),B.as_posix()).replace(repr(str(OLD))[1:-1],repr(str(B))[1:-1])
 if source.name in['izho_initial_fixed_style.py','final_translation_font_audit.py']:
  needle="=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db':";assert needle in text;text=text.replace(needle,f" in ['41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db','{source_sha}']:",1)
 if source.name=='izho_initial_fixed_style.py':
  needle='        reviewed_2012=False\n';assert text.count(needle)==1
  insert=f"""        reviewed_2015_and=False
        if data['source_sha256']=={source_sha!r}:
            policy_path=Path(__file__).resolve().parents[1]/'2015/reviewed-math-font-prose-policy.json'
            if hashlib.sha256(policy_path.read_bytes()).hexdigest()!={policy_sha!r}:raise ValueError('Source2015 exact conjunction-prose policy changed')
            policy=json.loads(policy_path.read_text('utf8'));selection={{k:label.get(k)for k in ['at','substring','source_substring','range']}}
            reviewed_2015_and=(pi==8 and label.get('reviewed')is True and label['at']==[54,1,1]and label['substring'].strip()=='and'and label['translated_text']==' 및 'and policy['source_sha256']==data['source_sha256']and selection in policy['reviewed_source_pages'].get(str(pi),[])and runs[tuple(label['at'])]['font']=='Cambria Math'and runs[tuple(label['at'])]['text']==')   and    𝑝̇')
"""
  text=text.replace(needle,insert+needle);text=text.replace('reviewed_2019_figure_phrase or reviewed_2012):','reviewed_2019_figure_phrase or reviewed_2012 or reviewed_2015_and):');assert 'or reviewed_2015_and):'in text
  needle='        if reviewed_2012:\n';assert text.count(needle)==1;text=text.replace(needle,'        if reviewed_2012 or reviewed_2015_and:\n')
 target.write_text(text,'utf8');records.append(dict(file=source.name,source_sha256=sha(source),private_sha256=sha(target)))
(E/'haslalab_runtime_paths.py').write_bytes((R/'haslalab_runtime_paths.py').read_bytes());assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
for name in['2015/native-baseline','natural/2015/TS/plans']:(B/name).mkdir(parents=True,exist_ok=True)
builder=R/'build-izho2015-solutions-baseline-page.py';assert not builder.exists();builder.write_text((R/'build-izho2014-solutions-baseline-page.py').read_text('utf8').replace('2014','2015'),'utf8')
(B/'engine-copy-and-source-policy.json').write_text(json.dumps(dict(source_sha256=source_sha,source_engine=str(OLD/'engine'),private_engine=str(E),files=records,all11_source_pages_visually_read=True,prose_selections=sum(len(p['slots'])for p in plans),exact_Cambria_Math_English_conjunction_policy_sha256=policy_sha,shared_native_guard_sha256=sha(E/'pdf_native_inline_reposition.py'),source2012_specific_policies_not_enabled_for_2015=True,actual_page_build_not_run=True),ensure_ascii=False,indent=2)+'\n','utf8')
print('PRIVATE_IZHO2015_ENGINE_11_SOURCE_PLANS_PREPARED',source_sha,policy_sha,flush=True)
