from izho2015_authoring import begin,around,finish
p=begin(1)
for at,text in{
 '1,0,0':'이론시험 문제 ', '2,0,0':'해설 ',
 '4,1,0':'핵심은 전체 계의 질량 중심이 정지해 있다는 것이다! 먼저 초기 위치에서의 ',
 '4,2,0':'질량 중심을 구하자. 선분 ',
 '4,9,0':'점 ',
 '4,11,1':'을 점 ',
 '4,13,1':'과 연결하고 선분 ',
 '4,17,0':'을 이등분한다(점 ',
 '4,19,1':'). 이 점 ',
 '4,21,1':'가 계의 질량 ',
 '4,22,0':'중심이다. 세 번째 구의 위치는 다음과 같이 구한다. ',
 '4,23,0':'선분 ',
 '4,29,2':')를 구한 뒤, 이 점에서 질량 중심을 향하는 ',
 '4,30,0':'직선을 긋는다. 질량 중심 ',
 '4,32,1':'에서 선분 ',
 '4,36,0':'을 그리되, 그 길이가 ',
 '4,37,0':'선분 ',
 '4,41,0':'의 길이와 같도록 한다. 점 ',
 '4,43,1':'가 세 번째 구의 위치이다! ',
 '5,1,0':'채점 기준 ',
 '6,2,0':'질량 중심의 위치가 일정하다는 ',
 '6,3,0':'핵심 발상을 제시함 ',
 '8,1,0':'질량 중심의 위치를 구함 ',
 '9,5,0':'세 번째 구의 위치를 구함: ',
}.items():p.add(at,text)
around(p,'3,1,0',['문제 ',' 작도','점',' '],['1.',' (7 ',')'])
around(p,'4,0,0',['문제 ',' '],['1.1'])
around(p,'4,6,0',['을 ','로 내분한다(점 '],['2:1'])
around(p,'4,27,0',['을 ','로 내분하여 점 '],['2:1'])
for at,num in [('8,2,0','1'),('8,3,0','2'),('8,4,0','3'),('9,6,0','1')]:around(p,at,['- 동그라미 ',' 안에 표시; '],[num])
finish(p,[[1,0],[2,0],[3,1],[4,0],[5,1]],'Full original2015 page1 read at144dpi. Retain exact10.08pt Arial bold header/year/edition,16.08pt Times bold italic two-line title,12pt bold problem headings, original A/B/C variables with all original fractional script points, native2:1 ratios, complete original grid/construction/charge diagram and all grading decimal commas. Original reference to circle1/2/3 is translated as marking within the corresponding circle. Only narrative is translated; no mathematics, diagram, font-size fitting or original source line-baseline modification.')
