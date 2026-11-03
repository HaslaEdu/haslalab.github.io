from izho2012_authoring import begin,around,finish
p=begin(3)
for at,text in{
 '4,0,0':'여기서 ',
 '4,4,0':'는 그래프로 주어진 함수 ',
 '4,8,0':'의 역함수이다. ',
 '7,1,0':'평가 항목 ',
 '7,2,0':'배점 ',
 '7,4,0':'병렬 연결에서는 전류를 더함 ',
 '7,7,0':'함수 그래프 ',
 '7,12,0':'및 ',
 '8,1,0':'병렬 연결에서는 전압을 더함 ',
 '8,4,0':'가로 방향 합산 ',
 '8,7,0':'계산점 수: ',
 '9,4,0':'대안 풀이(구현한 아이디어): ',
 '9,5,1':'함수 관계를 근사; ',
 '9,6,1':'방정식을 직접 풂; ',
 '10,4,0':'합계 ',
}.items():p.add(at,text)
around(p,'6,0,0',['채점 기준: 문제 ',''],['1B'])
around(p,'8,9,0',['','개 점; '],['3'])
around(p,'8,11,0',['','개 점. '],['6'])
for slot in p.slots:
 if slot['at']in[[7,1,0],[7,2,0]]:slot['align']='center'
finish(p,[[6,0]],'Full original page3 viewed at144dpi. Keep the exact original curve plot, gray equation fields, full inverse-function expression, actual U/I subscripts, all score-table native values and rules, source faux-bold headings/Total and original source line baselines. Row3 source says parallel although its surrounding circuit discussion uses series; literal source wording is retained without changing native source content. No type-size fitting or math retyping.')
