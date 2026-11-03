from izho2014_authoring import begin,around,finish
p=begin(7)
for at,text in{
 '1,5,0':'초기 조건 ',
 '2,3,0':'시간에 대한 다항식의 각 계수를 영으로 놓음 ',
 '2,56,0':'합계 ',
 '3,6,0':'. 이 층의 컨덕턴스 ',
 '3,6,3':'는 ',
 '5,0,0':'따라서 전체 컨덕턴스는 다음과 같다 ',
 '10,0,0':'그러므로 도선의 저항은 ',
 '14,17,0':'정상 상태에서는 같은 양의 열이 도선 표면을 통해 주변으로 ',
 '14,18,0':'빠져나가야 하므로, 뉴턴·리히만 법칙에 따라 ',
 '15,26,0':'이로부터 ',
 '19,0,2':'인 원기둥 내부에서 단위 시간에 발생하는 열량을 구하자. ',
 '19,1,0':'이를 위해 도선 내부의 전기장 세기를 구한다. 옴의 법칙에 따르면 ',
 '19,2,0':'전류 밀도는 ',
 '20,17,0':'따라서 전체 전류는 다음과 같다 ',
}.items():p.add(at,text)
for at,literal in [('1,1,0','(8)'),('2,0,0','(9)'),('2,8,0','(10)'),('2,10,0','(11)'),('2,12,0','(12)'),('2,15,0','(13)'),('2,19,0','(14)'),('2,21,0','(15)'),('2,24,0','(16)'),('2,29,0','(17)'),('2,31,0','(18)'),('2,33,0','(19)'),('2,35,0','(20)'),('2,42,0','(21)'),('2,44,0','(22)'),('2,46,0','(23)')]:around(p,at,['식 ',' '],[literal])
around(p,'2,38,0',['식 ','를 적용하여 식 ','를 구함 '],['(19)','(22)'])
around(p,'2,49,0',['식 ','의 올바른 수치 '],['(25)'])
around(p,'2,53,0',['식 ','의 올바른 수치 '],['(26)'])
around(p,'3,0,0',['문제 ',' 메타물질','점',' '],['3',' (10 ',')'])
around(p,'3,1,0',['',' 반지름 방향으로 다음 구간에 있는 전도성 층을 생각하자 '],['1.'])
around(p,'13,0,0',['',' 도선에서 단위 시간에 발생하는 열량은 줄의 법칙으로 정해진다 '],['2.'])
around(p,'19,0,0',['',' 반지름이 '],['3.'])
finish(p,[[3,0]],'Full original2014 page7 read at144dpi, including complete continued rocket grading grid and metamaterials solution. Preserve source reference(26) in the grading table even though the preceding displayed list ends at25, literal10,0 total, all actual source quarter/half-point scores and combined bold subtotal cells. All original rho/sigma/beta/R/L/I/T symbols, originalCyrillicК unit, native radial interval and integral/fraction rules remain encoded native programs. The quantity rho=d(sigma*S/L) is translated as conductance; the original equations and variable names are unchanged. Only English prose is translated; no font or points fitting.')
