from izho2012_authoring import begin,around,finish
p=begin(4)
around(p,'1,0,0',['문제 ',' 평판 렌즈'],['1.C.'])
for at,text in{
 '2,0,0':'평판에 상 ',
 '2,0,3':'가 생기려면 광학적 경로 길이 ',
 '2,6,0':'가 ',
 '2,7,0':'광원에서 나와 평판에서 굴절하는 모든 광선에 대해 같아야 한다(렌즈의 ',
 '2,8,0':'등시성 조건). ',
 '3,0,0':'축에서 일정 거리 떨어진 곳에 입사하는 광선을 생각하자. 다음을 가정하여 ',
 '4,2,0':', 즉 ',
 '4,2,1':'근축 근사를 사용한다. 거리 ',
 '4,2,3':'는 피타고라스 정리와 ',
 '4,3,0':'다음 근사를 이용해 구한다: ',
 '4,6,0':'. 따라서 ',
 '13,0,0':'같은 방법으로 구한 거리 ',
 '23,2,0':'따라서 광학적 경로 길이 ',
 '23,4,2':'는 다음과 같다. ',
 '43,2,0':'이 값이 ',
 '43,2,2':'에 무관하려면, 즉 모든 광선에서 같으려면 다음 ',
 '43,3,0':'계수가 영이어야 한다: ',
 '47,2,0':'이를 다시 쓰면 ',
 '50,2,0':'이 식은 다음 얇은 렌즈 공식과 같은 형태이다: ',
}.items():p.add(at,text)
around(p,'53,2,0',['여기서 ','는 초점 거리이다. '],['F'])
around(p,'54,0,0',['식 ','와 ','을 비교하면 평판의 초점 거리를 얻는다: '],['(5)','(6)'])
around(p,'56,2,0',['식 ','에서 평판과 상 사이의 거리도 구한다: '],['(5)'])
finish(p,[],'Full original page4 viewed at144dpi. Flat graded-index lens derivation is translated without retyping any original formula. Keep all eight equation tags, radical/large-parenthesis shapes, true native vector fraction rules, original letter primes, subscripts, source gray fields, faux-bold section title and exact source points/baselines. Inline native r<<a, SA and BS-prime must travel only as complete source expressions when Korean spacing is packed. No font fitting.')
