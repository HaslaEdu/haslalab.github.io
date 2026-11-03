from izho2016_authoring import begin,around,score,finish
p=begin(3)
for at,text in{
 '1,0,2':'만약 ','1,4,0':'가 ','1,8,0':'보다 크면, 액면이 높아질 때 계의 에너지가 감소하므로 ',
 '1,9,0':'액면은 계속 높아진다. 반대의 경우에는 낮아진다. 평형 위치에서는 ',
 '1,10,0':'전체 에너지 변화가 영이어야 하므로 ',
 '4,0,0':'수치를 대입하면 다음과 같다 ',
 '7,1,2':'계의 표면 에너지 변화를 구하자. ','7,2,0':'변화량 ',
 '7,6,0':'는 수위가 추가로 ','7,7,0':'높아진 양 ',
 '7,8,1':'에 대해 다음과 같다 ',
 '10,0,0':'여기서 ','10,8,0':'는 관의 반지름이며, 해당 높이는 ',
 '10,8,2':'이다. ','10,9,2':'중력 퍼텐셜 에너지 변화 ',
 '11,3,0':'는 수위가 추가로 ','11,4,0':'높아진 양 ',
 '11,5,1':'에 대해 다음과 같다 ',
 '11,21,2':'앞과 같이, 평형 위치에서는 ',
 '11,22,0':'두 에너지 변화량의 절댓값이 같으므로 ',
 '13,0,0':'높이 ','13,0,2':'에서 관 반지름의 식을 대입하면 ',
 '16,0,0':'여기에 매개변수 ','16,1,2':'를 도입하면 ',
 '24,0,2':'얻은 방정식은 ','24,0,4':'에 대한 이차방정식이다. 따라서 ',
 '27,0,0':'이 식의 오른쪽에 있는 이차함수의 ',
 '28,0,0':'근은 ','28,4,0':'과 ','29,2,0':'이다. 따라서 ',
 '30,0,0':'최댓값은 ','30,5,0':'이며, 이때 ',
 '34,2,0':'이다. 그 외에는 두 근이 있다. 관의 ',
 '35,0,0':'주어진 매개변수에서 ','35,10,0':'이므로 ',
 '36,0,0':'평형 위치도 두 개이다. 두 근 중 작은 근은 ',
}.items():p.add(at,text)
around(p,'7,0,0',['',' 수직 원뿔형 관 안의 물 ','점',' '],['3.','(4.0 ',')'])
around(p,'24,1,0',['근의 존재 조건을 살펴보자. 식 ','를 다음과 같이 쓰면 '],['(12)'])
around(p,'32,0,0',['이다. 식 ','는 다음 경우에 실근이 없다 '],['(12)'])
for at in ['1,0,1','7,1,1','10,9,1','11,21,1','24,0,1']:score(p,at)
finish(p,[[7,0]],'Full original2016 page3 read at144dpi. Keep all exact original native MathType formulas, absolute-value bars around DeltaUS, every fractional Tf/Tm and8/9 left-column display labels atx390.67; no formula recreation or baseline/point changes. Original conical tube figure atupper right and original parabola figure atlower right define separate narrow prose columns. All moving h=R/tg(alpha), R/(4tg(alpha))cos(alpha), h=R/(2tg(alpha)), inequality and25mm expressions must bind entire original CID/form/rules/clip groups with one common dx. Original display equations6–13, all scripts and source question numbers remain stationary. Page ends mid-sentence into page4 exactly as source.')
