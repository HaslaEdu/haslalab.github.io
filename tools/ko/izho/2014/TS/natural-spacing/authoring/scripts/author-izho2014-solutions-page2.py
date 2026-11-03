from izho2014_authoring import begin,around,finish
p=begin(2)
around(p,'1,0,0',['문제 ','점',' '],['1В (5 ',')'])
for at,text in{
 '1,1,0':'첫 번째 풀이. ',
 '2,0,0':'회로의 왼쪽 부분을 보자. 그 부하 특성 ',
 '2,1,0':'(전압 ',
 '2,1,2':'와 전류 ',
 '2,1,4':'의 관계)는 직선이다. 이와 같은 ',
 '3,0,0':'등가 전원의 매개변수는 ',
 '4,0,0':'다음 등가 회로에서 ',
 '5,0,0':'발생한 전체 열량은 ',
 '7,6,0':'. 저항 ',
 '7,6,2':'에서 발생한 열량은 ',
 '8,0,0':'다음과 같이 간단한 비례식으로 구한다 ',
 '18,0,0':'두 번째 풀이. ',
 '19,0,0':'키르히호프 법칙으로 얻는 연립방정식은 다음과 같다 ',
 '28,0,0':'여기서 ',
 '28,0,3':'과 ',
 '28,0,6':'를 소거하면 다음 관계식을 얻는다 ',
 '32,0,0':'양변에 ',
 '32,0,2':'를 곱하면 ',
 '35,0,0':'따라서 ',
 '40,0,0':'그러므로 ',
 '49,0,0':'조건 ',
 '49,4,0':'과 ',
 '49,9,0':'를 대입하면 최종적으로 다음을 얻는다 ',
}.items():p.add(at,text)
finish(p,[[1,0]],'Complete original2014 page2 read at144dpi. Preserve all three original circuit diagrams, every native Q/epsilon/r/R/C/I/q symbol and original script, native fractional point values, exact matrix bracket/fraction/integral rules and all charge initial/final conditions. The original printed Cyrillic conjunction between I1 and I2 is prose and explicitly translated. Keep source CyrillicВ in the title. First and second solution headings retain original12pt Times bold; title retains original14.04pt centered bold. Only explicit narrative slots are translated, with no mathematics/font-size fitting.')
