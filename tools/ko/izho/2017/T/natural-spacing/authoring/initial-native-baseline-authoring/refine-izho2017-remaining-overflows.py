from pathlib import Path
import json,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');folder=B/'2017/translation-row-revision-2';folder.mkdir(exist_ok=True)
changes={4:{(7,2,0):'인 균일한 거대 먼지 구름을 만난다. 밀도는 '},5:{(17,5,0):'는 상수다. 가능한 ',(17,5,2):'값을 구하고, 정확한 해를 구성하라.',(17,6,0):'위의 모든 조건을 만족해야 한다.'}}
history=[]
for n,edits in changes.items():
 p=B/f'2017/original_style/page{n}.json';q=json.loads(p.read_text('utf8'));shutil.copy2(p,folder/p.name)
 for at,text in edits.items():
  hits=[s for s in q['slots']if tuple(s['at'])==at];assert len(hits)==1
  history.append(dict(page=n,at=at,before=hits[0]['text'],after=text,reason='Complete equivalent Korean clause at unchanged source point size; the previously empty third original instruction row now carries its original condition clause. Native mathematics retains its original row/baseline.'));hits[0]['text']=text
 p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
(folder/'history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n','utf8')
print('Revised4 prose slots; original math/font size/y unchanged.')
