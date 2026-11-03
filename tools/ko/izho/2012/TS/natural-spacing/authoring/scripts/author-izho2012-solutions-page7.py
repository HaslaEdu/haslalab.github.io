from izho2012_authoring import begin,around,finish
p=begin(7)
for at,text in{
 '3,2,0':'피스톤이 평형 위치에서 작은 높이 ',
 '3,3,0':'압력 변화는 다음과 같다. ',
 '8,2,0':'피스톤의 운동 방정식은 다음과 같다. ',
 '14,2,0':'따라서 미소 진동의 진동수는 ',
 '17,3,0':'다음과 같다. ',
 '20,2,0':'즉 ',
 '21,13,2':' 이때 ',
 '21,14,0':'입자 ',
 '21,14,1':'수와 에너지가 모두 균형을 이루어야 한다. 입자 수 보존 법칙은 ',
 '21,15,0':'다음과 같다. ',
 '28,2,0':'에너지 보존 법칙에는 각 분자의 병진 운동 에너지뿐 아니라 ',
 '28,3,0':'회전 운동 에너지도 포함해야 한다. 따라서 각 분자가 ',
 '28,4,0':'운반하는 전체 에너지는 다음과 같다. ',
 '29,21,0':'그러면 에너지 보존 법칙은 다음과 같다. ',
 '38,2,0':'즉 ',
 '42,23,0':'그리고 온도는 ',
 '44,2,0':'즉 ',
}.items():p.add(at,text)
around(p,'3,2,2',['만큼 변위되면 식 ','에서 '],['(13)'])
around(p,'17,2,1',['','점',' 일정한 속도로 움직일 때에도 피스톤은 평형이므로 압력은 '],['[1 ',']'])
around(p,'21,13,0',['',' 및 ',''],['2.9','2.10.'])
around(p,'21,13,1',['','점',' 용기 안에 어떤 정상 온도가 형성되었다고 하자.'],['[3 ',']'])
around(p,'35,2,0',['식 ','과 ','를 풀면 최종적으로 다음을 얻는다. '],['(18)','(19)'])
finish(p,[],'Full original page7 viewed at144dpi. Keep every actual native equation13..24, all original physical units including sourceomega/Hz wording, source equation references18/19, exact complete radicals/fractions and original delta/nu/gamma symbols. The original Word split m|ust is narrative English, so both explicit Cambria prose fragments are translated; it is not a physical mass variable. Keep the11.04pt source sentence fragment at its actual point, all12pt body rows, source scores and square brackets. No type-size fitting.')
