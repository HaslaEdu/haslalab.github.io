from pathlib import Path
import json,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');folder=B/'2017/translation-row-revision';folder.mkdir(exist_ok=True)
changes={
 2:{(5,19,0):'의 신호가 동시에 사라질 점을 그려라. 셋째 파원의 세기를 구하라.'},
 4:{(3,2,2):'사각뿔 행성 꼭짓점의 중력 가속도 ',(3,3,0):'행성의 밀도는 균일하며 다음과 같다: '},
 5:{(7,0,2):'다음 계수의 점화식을 구하라: ',(7,4,0):'를 이전 항 ',(8,9,0):'로 나타내라. 역으로 ',(8,18,0):'를 ',(9,3,0):'로 나타내라.'},
 6:{(9,2,2):'의 식을 구하라. 항 번호는'},
 7:{(2,27,2):'최소 ',(2,27,4):'을 구하라. 각기둥 저항의 ',(2,28,3):'에 대한 상대편차는 2% 이하여야 한다.'}
}
history=[]
for n,edits in changes.items():
 p=B/f'2017/original_style/page{n}.json';q=json.loads(p.read_text('utf8'));shutil.copy2(p,folder/p.name)
 for at,text in edits.items():
  hits=[s for s in q['slots']if tuple(s['at'])==at]
  if len(hits)>1:raise ValueError('Translation slot is not unique')
  if not hits:q['slots'].append(dict(at=list(at),text=text));before=None
  else:before=hits[0]['text'];hits[0]['text']=text
  history.append(dict(page=n,at=at,before=before,after=text,reason='Equivalent complete Korean prose redistributed within adjacent original source rows, preserving every native math token, source point size and mathematical baseline.'))
 p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
(folder/'history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n','utf8');print('Revised',len(history),'original prose slots, no math/font fitting.')
