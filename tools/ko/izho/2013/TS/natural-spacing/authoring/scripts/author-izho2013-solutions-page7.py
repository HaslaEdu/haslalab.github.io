from izho2013_authoring import begin,around,finish
p=begin(7)
p.add('2,0,0','채점 기준 ')
p.add('3,2,0','평가 항목 ');p.add('3,3,0','배점 ')
around(p,'3,6,0',['북극 ','과 남극 ','를 올바르게 표시 '],['N','S'])
refs={
 '3,10,0':('1','식 '),'3,16,0':('2','식 '),'3,19,0':('3','식 '),
 '3,22,0':('4','식 '),'3,25,0':('5','식 '),'3,28,0':('6','해 '),
 '3,31,0':('7','식 '),'3,36,0':('8','식 '),'3,39,0':('9','식 '),
 '4,1,0':('11','식 '),'5,16,0':('12','식 '),'6,21,0':('13','식 '),
 '7,1,0':('14','식 '),'7,4,0':('15','관계식 '),'7,7,0':('16','준탄성력 '),
 '7,10,0':('17','운동 방정식 '),'7,13,0':('19','평형점 '),'7,16,0':('20','조건 '),
 '9,1,0':('18','진동수 '),'9,6,0':('22','식 '),'10,1,0':('23','식 '),
 '10,7,0':('24','식 '),'10,22,0':('25','옴의 법칙 '),'10,27,0':('26','운동 방정식 '),
}
for at,(num,target)in refs.items():around(p,at,[target,' '],[f'({num})'])
for at in['3,42,0','8,1,0','9,9,0']:p.add(at,'계산한 ')
around(p,'7,19,0',['식 ','의 '],['(21)'])
for line in[1,4,7,10,13]:p.add(f'5,{line},0','그래프 ')
for line in[1,5,9,13,17]:p.add(f'6,{line},0','그래프 ')
for line in[10,14,18]:p.add(f'10,{line},0','그래프 ')
for at,text in{
 '5,1,3':'의 축 이름과 눈금 표시 ',
 '5,4,3':'에 등속 구간이 있음 ',
 '5,7,3':'에 등가속도 구간이 있음 ',
 '5,10,3':'가 연속임 ',
 '5,13,3':'의 올바른 수치 ',
 '6,2,2':'의 축 이름과 눈금 표시 ',
 '6,6,2':'에 일정한 전류 구간이 있음 ',
 '6,10,2':'에 전류가 영인 구간이 있음 ',
 '6,14,2':'가 불연속임 ',
 '6,18,2':'의 올바른 수치 ',
 '10,11,2':'의 축 이름과 눈금 표시 ',
 '10,15,2':'에 전류 진동 두 주기가 있음 ',
 '10,19,2':'의 올바른 진폭 ',
}.items():p.add(at,text)
for slot in p.slots:
 if slot['at']in[[3,2,0],[3,3,0]]:slot['align']='center'
finish(p,[[2,0]],'Complete original2013 page7 grading table viewed at144dpi. Preserve every original table rectangle and score/enumerator, all exact encoded native N/S, v(t), I(t), t0, F_min with original source Times/Symbol fonts, complete scripts and native word-math spacing. All equation references are protected source fragments and move only as complete reviewed native atoms. Source min is an unchanged mathematical index. Korean body uses normal word gaps and source12pt/table roles; centered marking-scheme title and table headers retain the original centers. No prose colons are added against source grid lines.')
