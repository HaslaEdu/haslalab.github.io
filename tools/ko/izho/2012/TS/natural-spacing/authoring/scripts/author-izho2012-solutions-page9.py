from izho2012_authoring import begin,around,finish
p=begin(9)
around(p,'1,0,0',['문제 ','  '],['3'])
p.add('1,1,0','핵의 액체 방울 ','Nuclear droplet ');p.add('1,1,0','점','points')
p.protect_fragment('1,1,0','(10 ','Original source score numeral and opening parenthesis.')
p.protect_fragment('1,1,0',')','Original source score closing parenthesis.')
around(p,'2,0,0',['',' ','점',' 원자핵 안 양성자의 전체 정전기 에너지를 '],['3.1','[2 ',']'])
for at,text in{
 '2,1,0':'계산한다. 액체 방울 모형에서 핵의 전하 ',
 '2,1,2':'는 ',
 '2,2,0':'반지름 ',
 '2,2,2':'인 구에 균일하게 분포한다. 따라서 부피 전하 밀도는 다음과 같다. ',
 '6,0,0':'가우스 법칙을 이용해 구의 내부와 외부 전기장을 구한다. ',
 '13,0,0':'따라서 다음을 얻는다. ',
 '32,0,0':'전체 정전기 에너지는 다음 적분으로 주어진다. ',
 '39,3,0':'및 ',
 '39,10,0':'를 이용하면 정전기 에너지가 ',
 '40,0,0':'바이츠제커 반경험식의 세 번째 항에 해당함을 알 수 있다. 따라서 ',
 '45,0,0':'이로부터 ',
 '57,0,0':'표면 에너지는 바이츠제커 반경험식의 두 번째 항에 ',
 '57,1,0':'해당한다. 따라서 ',
 '58,0,0':'이로부터 ',
}.items():p.add(at,text)
around(p,'39,0,0',['',' ','점',' 식 ',', '],['3.2','[1 ',']','(5)'])
around(p,'49,0,0',['',' ','점',' 핵물질의 밀도는 다음과 같다. '],['3.3','[1 ',']'])
around(p,'54,0,0',['',' ','점',' 표면 에너지는 표면 장력에 따라 결정된다. '],['3.4','[1 ',']'])
finish(p,[[1,0],[1,1]],'Full original page9 viewed at144dpi. Preserve original centered15.96pt title, source fill/stroke faux-bold paint, all gray source fields, all11 original displayed equations and integral programs, native Q=Ze and radius expression, exact primes/Greek symbols/scripts, original source numerical exponents and apparent source formula typos. Every subsection numeral, grade, square bracket and complete equation reference is actual source text, never retyped. No font fitting.')
