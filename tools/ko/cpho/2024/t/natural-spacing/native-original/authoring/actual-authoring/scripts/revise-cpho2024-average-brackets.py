from pathlib import Path
import sys,json,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural');sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from cpho2024_events import events
history=B/'authoring/T/revisions/complete-average-brackets';history.mkdir(parents=True,exist_ok=True)
for p in [B/'authoring/T/page01.events.json',B/'authoring/T/page01.natural.tsv']:
 if not(history/p.name).exists():shutil.copyfile(p,history/p.name)
data=events(1);(B/'authoring/T/page01.events.json').write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n','utf8')
path=B/'authoring/T/page01.natural.tsv';text=path.read_text('utf8');old="all beads' cycle-mean kinetic energy";new="the beads' cycle-mean kinetic energy";assert text.count(old)==1;text=text.replace(old,new);path.write_text(text,'utf8')
(history/'review.json').write_text(json.dumps(dict(reason='All four original vector strokes of the E_k cycle-average brackets form one rigid native expression. The former automatic proximity heuristic selected only the left pair. Complete source math is now carried; English definite plural the beads retains the whole-set meaning at unchanged source point size.',source_page=1,atom='m100',right_bracket_original_operator_indices=[[3018,3019,3020],[3028,3029,3030]],english_revision=dict(before=old,after=new)),ensure_ascii=False,indent=2)+'\n','utf8')
print('REVISED complete original average brackets and equivalent English wording.')
