from izho2017_authoring import begin,around,finish
p=begin(8)
for at,n in [('1,0,0',38),('2,0,0',39),('8,0,0',40),('10,4,0',41)]:around(p,at,['식 ',' '],[f'({n})'])
for at in ['6,0,0','13,0,0']:p.add(at,'다음의 수치 ')
p.add('13,2,0','합계 ')
around(p,'13,7,0',['문제 ','. 각기둥의 저항 (','점',' '],['3','10.0 ',')'])
around(p,'14,0,0',['','. 수학적 준비 (','점',' '],['1','3.0 ',')'])
for at,n in [('14,1,1','0.2'),('15,0,1','0.4'),('66,0,1','0.7'),('68,22,1','0.2')]:around(p,at,['','점',' '],[f'[{n} ',']'])
for at,text in {
 '14,1,2':'학교 수학에서 배운 것처럼 등비수열의 일반항은 ',
 '14,2,0':'다음과 같이 나타낼 수 있다 ',
 '15,0,2':'다음 항 ',
 '15,1,2':'를 앞 항 ',
 '15,17,0':'로 나타내고 다음과 같이 변형하면 ',
 '31,0,0':'이 등식으로부터 필요한 점화식을 얻는다 ',
 '43,0,0':'마찬가지로 역방향 관계는 다음과 같다 ',
 '54,0,0':'따라서 ',
 '66,0,2':'주어진 초기 조건 ',
 '68,22,2':'다음 관계에 주목하자 ',
}.items():p.add(at,text)
around(p,'66,9,0',['에서 계수를 차례로 계산하면 훨씬 쉽다. 결과는 표 ','에 제시하였다. '],['1'])
around(p,'67,0,0',['표 ',' '],['1.'])
finish(p,[[13,7],[14,0],[67,0]],'Full original2017 page8 visually read at144dpi. Retain original main13.92pt and subsection12pt bold centered roles;12pt body serif. Preserve all mathematical source glyphs/fractional points, recurrence formulas and original k/pk/qk numeric table, including header roles and actual grid. Prior grading continuation scores/subtotals/Total retain exact original columns. Original complete inline lambda powers and p0/q0 conditions are retained natively; prose has ordinary Korean gaps, no resized fonts.')
