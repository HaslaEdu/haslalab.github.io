from pathlib import Path
import sys,re,json
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,10);p.header()
for at,text in{
'5,0,0':'온도가 영으로 갈 때 압력은 ',
'5,1,0':'일정한 값에 접근한다: ',
'8,0,0':'압력의 온도 의존성에 대한 개략적인 ',
'12,0,0':'채점 기준 ',
'13,2,0':'항목 ',
'13,3,0':'배점 ',
}.items():p.add(at,text,align='center'if at=='12,0,0'else None)
p.references('8,1,0',['그래프는 그림 ','와 같다. '])
for at,text in{
'13,6,0':'정규화 조건',
'13,10,0':'입자 수 계산',
'13,17,0':'내부 에너지의 일반식',
'14,2,0':'내부 에너지 계산',
'14,5,0':'고전적 극한 계산',
'14,8,0':'저온 극한 계산',
'14,15,0':'몰열용량의 일반식',
'15,2,0':'몰열용량 계산',
'15,5,0':'고전적 극한 계산',
'15,8,0':'저온 극한 계산',
'15,11,0':'개략도',
'15,18,0':'평균 힘의 일반식',
'15,22,0':'압력의 일반식',
'16,2,0':'압력 계산',
'16,5,0':'고전적 극한 계산',
'16,8,0':'저온 극한 계산',
'16,11,0':'개략도',
}.items():
 source=p.runs[at]['text'];m=re.search(r'(?<![A-Za-z])(?:С_V|U|P)(?![A-Za-z])|\(',source);assert m,(at,source);i=m.start();p.prose_range(at,0,i,text+' ');p.protect_range(at,i,len(source),'Original physical U/P or Cyrillic source С_V identifier, reference numeral, parentheses and source punctuation. Preserve literal original font/GID/point/baseline and source mathematical typography.')
p.add('18,0,0','그림 ','Fig.');p.protect_fragment('18,0,0','2','Original source caption numeral at original font/GID/point/baseline; original whole-caption center preserved.')
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 if tuple(map(int,at.split(',')))not in translated|fragments:p.protect(at,'Reviewed complete original thermal/statistical expression or fraction/exponential, plot variable, native table index/score/rubric marker. Preserve all source font programs/GIDs/fractional points/y, original score decimal punctuation and complete native Forms/rules.')
path=p.save();d=json.loads(path.read_text('utf8'));d['centered']=[[13,2],[13,3]];path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print(path)
