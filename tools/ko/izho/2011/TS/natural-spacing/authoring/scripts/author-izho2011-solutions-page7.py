from pathlib import Path
import sys,json
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,7);p.header()
for at,text in{
'3,0,0':'초기조건 ',
'3,3,0':'과 ',
'3,7,0':'에서 다음 최종 해를 얻는다: ',
'10,2,0':'자기장 세기가 작을 때, 최종 변위 조건은 다음과 같다: ',
'11,3,0':'. 방향은 ',
'11,3,2':'축이고, 해당 시각은 ',
'15,0,0':'또는 ',
'19,0,0':'채점 기준 ',
'20,2,0':'항목 ',
'20,3,0':'배점 ',
'20,65,0':'정확한 면 지목 ',
}.items():p.add(at,text,align='center'if at=='19,0,0'else None)
p.add('10,1,0','점','point')
for l,text in{
5:'줄–렌츠 법칙',8:'단위 부피당 발열 일률',11:'식',14:'최종 결과',17:'운동 방정식',20:'이동 거리',23:'평균 속력',26:'평균 속도 벡터',29:'전류 밀도',32:'전기 전도도',35:'전자의 운동 에너지',38:'전달된 총 열량',41:'운동 방정식',44:'운동 방정식',47:'속도',50:'속도',53:'속도 전개',56:'변위',59:'평균 속력',62:'최종 결과',68:'운동 방정식',71:'속도',74:'속도',77:'홀 전기장 세기',80:'홀 전기장 세기',
}.items():
 at=f'20,{l},0';source=p.runs[at]['text'];index=source.index('(');p.prose_range(at,0,index,text+' ');p.protect_range(at,index,len(source),'Original native reference number/range, parentheses and punctuation in the source scoring cell; source fractional point and baseline retained.')
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 if tuple(map(int,at.split(',')))not in translated|fragments:p.protect(at,'Reviewed complete original native mathematical expression, coordinate OY label, integral/fraction/script, table row/score or equation marker. Retain all source fonts/GIDs/fractional points/y, complete native Forms/rules and original scoring decimal punctuation.')
path=p.save();d=json.loads(path.read_text('utf8'));d['centered']=[[20,2],[20,3]];path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print(path)
