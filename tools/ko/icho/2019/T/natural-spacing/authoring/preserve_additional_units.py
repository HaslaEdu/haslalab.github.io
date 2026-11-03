"""Retain missed scientific literals as original native glyphs, unchanged prose."""
from pathlib import Path
import argparse,copy,hashlib,json,os,re
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('pages',nargs='+',type=int);p.add_argument('--audit-only',action='store_true');a=p.parse_args()
pattern=re.compile(r'(?<![A-Za-z])mL(?![A-Za-z])|w%|(?<![A-Za-z0-9])\(?2K(?![A-Za-z0-9])|(?<![A-Za-z0-9])3(?=D|차원)|^D(?=\s|구조|$)|^[’\'′](?!s(?:\s|$))|[\[\]~]');journal=[];manual=[]
for n in a.pages:
    path=B/f'page{n:02}.overrides.json';before=path.read_bytes();q=json.loads(before);plan=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'));originals=plan['slots']+list(q.get('__extra_slots__',[]));edits=q.setdefault('__slot_edits__',{});extras=q.setdefault('__extra_slots__',[])
    for original in originals:
        s=dict(original,**edits.get(original['id'],{}))
        if s.get('skip'):continue
        source=s['source'];text=q.get(s['id'],s.get('text',''));sm=list(pattern.finditer(source));tm=list(pattern.finditer(text))
        if not sm:continue
        if len(sm)!=len(tm)or[m.group()for m in sm]!=[m.group()for m in tm]:
            manual.append(dict(page=n,id=s['id'],reason='Literal occurrence/order mismatch',source=source,text=text))
            if a.audit_only:continue
            raise AssertionError(manual[-1])
        parts=[];sa=ta=0
        for si,(src,dst)in enumerate(zip(sm,tm)):
            parts.append((sa,src.start(),ta,dst.start()));sa=src.end();ta=dst.end()
        parts.append((sa,len(source),ta,len(text)));reconstructed=[]
        for si,(ss,se,ts,te)in enumerate(parts):
            src=source[ss:se];dst=text[ts:te];reconstructed.append(dst)
            if si<len(sm):reconstructed.append(sm[si].group())
            if src==dst or not src.strip()and not dst.strip():continue
            if not(src and any(c.strip()for c in src)):
                manual.append(dict(page=n,id=s['id'],reason='Translated prose has no source characters',source=source,text=text))
                if a.audit_only:break
                raise AssertionError(manual[-1])
            extra=copy.deepcopy(s);extra.update(id=s['id']+f':unit-prose-{si}',source=src,text=dst,char_start=s.get('char_start',0)+ss,char_end=s.get('char_start',0)+se);extra.pop('skip',None);extra.pop('skip_reason',None)
            if si and ((sm[si-1].group()==']'and src.startswith('catenane')and dst.startswith('카테네인'))or(sm[si-1].group()=='3'and src.startswith('D')and dst.startswith('차원'))):extra['join_left']=True
            extras[:]=[v for v in extras if v['id']!=extra['id']];extras.append(extra)
        else:
            assert ''.join(reconstructed)==text
        if manual and manual[-1]['page']==n and manual[-1]['id']==s['id']:continue
        edits[s['id']]=dict(edits.get(s['id'],{}),skip=True,skip_reason='Original scientific unit/formula-prefix/bracket/approximation glyphs retain exact source GIDs/fonts/point sizes and native advances; only source-bound surrounding Korean prose is emitted by the extra fragments.')
        journal.append(dict(page=n,source_slot_id=s['id'],source=source,unchanged_korean_text=text,unit_literals=[m.group()for m in sm],korean_text_conservation=True))
    q['additional_native_unit_preservation_review']='Missed mL units and formula-boundary2K/bracket/approximation glyphs retain original native programs and exact physical typography; do not edit the frozen shared matcher or change any source or translated sentence.'
    if not a.audit_only:
        temporary=path.with_suffix('.json.new');temporary.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');os.replace(temporary,path)
    print(json.dumps(dict(page=n,affected_slots=sum(v['page']==n for v in journal),before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(path.read_bytes()).hexdigest())),flush=True)
out=B/('additional-literal-audit.json'if a.audit_only else'additional-unit-preservation-'+','.join(map(str,a.pages))+'.json');out.write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,rows=journal,manual_cases=manual,audit_only=a.audit_only,strict_text_conservation=True),ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(dict(manual_cases=manual,audit_only=a.audit_only,planned_slots=len(journal)),ensure_ascii=False),flush=True)
