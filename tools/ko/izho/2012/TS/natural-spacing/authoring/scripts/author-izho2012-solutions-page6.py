from izho2012_authoring import begin,around,finish
p=begin(6)
around(p,'1,0,0',['문제 ','  '],['2'])
p.add('1,1,0','피스톤의 모험 ','Adventures of a piston ');p.add('1,1,0','점','points')
p.protect_fragment('1,1,0','(10 ','Original complete source score numeral and opening parenthesis.')
p.protect_fragment('1,1,0',')','Original score closing parenthesis.')
def graded(at,value,text):around(p,at,['','점',text],['['+value+' ',']'])
graded('2,0,1','0.5',' 피스톤의 평형 조건에서 기체의 압력을 구한다. ')
around(p,'5,2,0',['',' 및 ',''],['2.2','2.3.'])
graded('5,2,1','2',' 첫 단계에서 기체는 압축되어 어떤 ')
for at,text in{
 '5,3,0':'온도까지 가열된다. ',
 '5,3,1':'용기의 벽과 피스톤은 열전도성이 낮은 재료로 ',
 '5,4,0':'만들어져 기체의 압축을 단열 과정으로 볼 수 있다. 그러나 비평형 ',
 '5,5,0':'과정이므로 단열 방정식을 적용할 수 없다. 피스톤과 기체로 이루어진 계가 ',
 '5,6,0':'처음 상태에서 마지막 상태로 변할 때 외력인 중력과 대기압이 ',
 '5,7,0':'한 일은 다음과 같다. ',
 '6,31,0':'문제의 조건에 따라 이 일의 절반만 기체 내부 에너지를 증가시킨다. ',
 '8,2,0':'여기서 ',
 '10,17,0':'여기서 ',
 '10,18,0':'이상 기체 상태 방정식을 쓰면 다음과 같다. ',
 '22,3,0':'주변 온도와 같아져 다음 값을 갖는다. ',
 '24,3,0':'구한다. ',
 '27,6,0':'다음 결과를 얻는다. ',
}.items():p.add(at,text)
around(p,'10,17,2',['는 몰수이고, ','은 보편 기체 상수이다. 처음과 마지막 상태에 '],['R'])
around(p,'13,19,0',['연립방정식 ','—','을 풀면 다음과 같다. '],['(2)','(6)'])
graded('19,50,1','0.5',' 피스톤은 계속 평형이므로 압력은 다음과 같다. ')
graded('22,2,1','0.5',' 충분히 긴 시간이 지나면 용기 안의 기체 온도가 ')
graded('24,0,1','0.5',' 높이 ')
around(p,'24,2,1',['는 식 ',' 및 ','과 기체의 상태 방정식으로 '],['(9)','(10)'])
graded('26,19,1','2',' 다음 형태의 단열 방정식에서 ')
finish(p,[[1,0],[1,1]],'Full original page6 viewed at144dpi. Preserve exact original CambriaMath header size15.96pt, original fill/stroke title boldness, all original graded square brackets/decimal scores, subsection numbers, twelve equation tags, units Pa/K/cm, native R/nu/H/T/p/alpha/gamma programs, complete fraction/radical/vector rules and all source display mathematics. The first compression is irreversible, so the prose correctly distinguishes an adiabatic process from the equilibrium adiabatic relation. No source glyph, score, unit or formula is retyped and no point fitting occurs.')
