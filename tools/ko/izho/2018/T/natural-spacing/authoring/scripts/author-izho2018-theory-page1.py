from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2018,1);p.header()
for at,text in {
'1,3,0':'이론시험 ',
'2,0,0':'2018년 1월 12일 ',
'3,1,0':'먼저 다음 안내를 읽으시오. ',
'5,0,1':'지급된 펜만 사용하시오. ',
'6,0,1':'수치 계산에는 개인 계산기를 사용할 수 있다. 계산기가 없으면 ',
'6,1,0':'대회 진행 요원에게 요청하시오. ',
'7,0,1':'지급된 ',
'7,0,2':'답안지 ',
'7,0,3':'와 여분의 종이를 확인하시오. 여분의 종이에는 ',
'7,1,0':'풀이 초안을 써도 되지만 채점하지 않는다. 채점받을 최종 풀이는 ',
'7,2,0':'반드시 ',
'7,2,1':'답안지',
'7,2,2':'에 쓰시오. 문장은 되도록 적게 쓰고, ',
'7,3,0':'식·수치·그림·그래프를 주로 사용하시오. ',
'8,0,1':'앞면만 사용하고, ',
'8,0,2':'답안지',
'8,0,3':'의 ',
'8,0,4':'테두리 안에만 쓰시오. ',
'9,0,1':'각 문제의 풀이는 새 답안지에서 시작하시오. ',
'10,0,1':'각 답안지 위쪽 칸에 국가(',
'10,0,2':'국가), ',
'10,0,3':'참가자 ',
'10,1,0':'코드(',
'10,1,1':'참가자 코드',
'10,1,2':'), 문제 번호(',
'10,1,3':'문제 번호)',
'10,1,4':', 답안지의 순서 ',
'10,2,0':'번호 ',
'10,2,1':'(쪽 번호',
'10,2,2':'), 사용한 ',
'10,2,3':'답안지',
'10,2,4':'의 총수(',
'10,2,5':'총 ',
'10,3,0':'쪽수',
'10,3,1':')를 적으시오. 빈 ',
'10,3,2':'답안지',
'10,3,3':'를 메모에 사용하여 채점받지 않으려면, ',
'11,0,1':'시험이 끝나면 각 문제의 종이를 다음 순서로 정리하시오. ',
'12,0,1':'작성한 ',
'12,0,2':'답안지',
'12,0,3':'를 순서대로 놓으시오. ',
'12,1,1':'채점받지 않을 종이를 놓으시오. ',
'12,2,1':'사용하지 않은 종이와 인쇄된 문제지를 놓으시오. ',
'12,3,0':'종이를 봉투에 넣고 모두 책상 위에 두시오. 시험실 밖으로는 ',
'12,4,0':'어떤 종이도 가져갈 수 없다. ',
}.items():p.add(at,text,align='center'if at in ['1,3,0','2,0,0','3,1,0']else None)
p.add('4,1,1','이론시험 시간은 ','The time available for the theoretical competition is ')
p.protect_fragment('4,1,1','4','Original native exam-duration numeral; exact encoded source font/glyph/12pt baseline retained.')
p.add('4,1,1','시간이며, 문제는 세 개이다. ',' hours. There are three questions. ')
p.add('10,4,0','종이 전체에 큰 ','put a large ')
p.protect_fragment('10,4,0','X','Original native X crossing-out instruction glyph; exact original font/point retained.')
p.add('10,4,0','를 표시하고 답안지 번호와 총수에 포함하지 마시오. ',' across the entire sheet and do not include it in your numbering. ')
print(p.save())
