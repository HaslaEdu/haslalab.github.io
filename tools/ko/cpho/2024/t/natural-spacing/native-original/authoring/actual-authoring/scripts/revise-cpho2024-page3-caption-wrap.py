from pathlib import Path
import json,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural');p=B/'authoring/T/page03.natural.tsv';history=B/'authoring/T/revisions/page3-original-caption-wrap';history.mkdir(exist_ok=True)
if not(history/p.name).exists():shutil.copyfile(p,history/p.name)
changes={11:{2:'Laser passes a linear polarizer normal to'},12:{2:'the page {m26}, then full mirror {m27}, splitter'},14:{1:'{m29}에서 광로 {m30}, {m31}로 나뉜다. {m32}의 빛은 거울 {m33}에서',2:'{m29} splits into paths {m30},{m31}; {m32} hits mirror {m33}.'},15:{2:'reflects fully, then crosses the {m35} waveplate with fast axis {m34}, to splitter'}}
rows=[];revisions=[]
for line in p.read_text('utf8').splitlines():
 if not line or line.startswith('#'):rows.append(line);continue
 cells=line.split('\t');rid=int(cells[0])
 for col,value in changes.get(rid,{}).items():revisions.append(dict(row=rid,language='KO'if col==1 else'EN',before=cells[col],after=value));cells[col]=value
 rows.append('\t'.join(cells))
p.write_text('\n'.join(rows)+'\n','utf8');(history/'review.json').write_text(json.dumps(dict(source_page=3,source_caption_baseline=300.2587585449219,source_next_paragraph_baseline=303.8399963378906,source_wrapped_column_right=289.4,original_native_math_rows_and_baselines_unchanged=True,revisions=revisions,reason='The original Word layout keeps the paragraph beside the optical figure caption, which extends below the bitmap. Preserve this original column on row14; complete equivalent clauses are distributed over the same original prose rows without changing native math rows or font sizes.'),ensure_ascii=False,indent=2)+'\n','utf8');print('REVISED source caption/paragraph wrap, all original points and math rows retained.')
