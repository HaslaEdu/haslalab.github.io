from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural');p=B/'authoring/T/page01.natural.tsv';text=p.read_text('utf8');old="the beads' cycle-mean kinetic energy";new='total cycle-mean kinetic energy';assert text.count(old)==1;p.write_text(text.replace(old,new),'utf8')
report=B/'authoring/T/revisions/complete-average-brackets/review.json';q=json.loads(report.read_text('utf8'));q['english_revision']['after']=new;q['english_revision']['meaning']='Total over all beads, averaged over one oscillation cycle, as in the original Chinese instruction. Native E_k average brackets and all other variables are unchanged.';report.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('Complete equivalent aggregate-energy wording; original font size retained.')
