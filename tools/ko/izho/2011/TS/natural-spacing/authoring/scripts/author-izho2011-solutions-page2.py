from pathlib import Path
import sys,json
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,2);p.header()
for at,text in{
'1,0,0':'전원 셀 수는 무한하므로 두 회로는 모든 저항값에 대해 등가여야 한다: ',
'4,0,0':'직류 회로 법칙으로 다음 두 명제가 성립함을 보일 수 있다: ',
'4,6,0':'과 ',
'4,11,0':'을 직렬로 연결하자. 이때 ',
'4,12,0':'등가 전원의 기전력은 ',
'4,20,0':', 내부 저항은 ',
'4,34,0':'과 ',
'4,39,0':'을 병렬로 연결하자. 이때 ',
'4,40,0':'등가 전원의 기전력은 ',
'4,58,0':', 내부 저항은 ',
'4,72,0':'왼쪽 그림의 회로가 되어야 하므로 다음 관계가 성립한다: ',
'11,0,0':'연립방정식의 해는 다음과 같다: ',
'20,0,0':'따라서 저항 ',
'20,0,2':'에 흐르는 전류는 ',
'22,0,0':'채점 기준 ',
'23,2,0':'항목 ',
'23,3,0':'배점 ',
'23,5,0':'등가 회로 ',
}.items():p.add(at,text,align='center'if at=='22,0,0'else None)
for at,number in[('4,1,0','1'),('4,29,0','2')]:
 p.add(at,'두 전원 ','Let us take two current sources with ');p.protect_fragment(at,number+'. ','Original native list numeral and punctuation at exact source font/GID/12pt/baseline.')
p.add('4,71,0','오른쪽 그림의 회로에 명제 ','Now, applying ');p.protect_fragment('4,71,0','1','Original native rule reference numeral.')
p.add('4,71,0','과 ',' and ');p.protect_fragment('4,71,0','2','Original native rule reference numeral.');p.add('4,71,0','를 적용하면 ',' to the circuit shown on the right hand side, we should obtain the ')
for l in[8,11]:p.add(f'23,{l},0','명제 ','Rule ')
for l in[14,17,20,23,26]:p.add(f'23,{l},0','식 ','Formula ')
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
native=[at for at in p.runs if tuple(map(int,at.split(',')))not in translated|fragments]
for at in native:p.protect(at,'Reviewed original native circuit equation, complete fraction, physical unit, numerical scoring, formula counter or original diagram variable. Preserve every original encoded source font/GID/point/baseline and native Form/rule.')
path=p.save();d=json.loads(path.read_text('utf8'));d['centered']=[[23,2],[23,3]];path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print(path)
