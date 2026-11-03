from izho2015_authoring import begin,around,finish
p=begin(6)
for at,text in{
 '16,0,0':'거리 ',
 '16,3,0':'에서는 다음과 같이 단순해진다 ',
 '23,0,0':'최종적으로 ',
 '31,1,1':'는 자기장의 반지름 성분 ',
 '33,0,0':'',
 '33,1,0':'에 의해 생긴다. 축에 가까운 곳에서는 ',
 '33,2,0':'이 성분을 자기장의 축 방향 성분으로 ',
 '33,3,0':'나타낼 수 있다. 이를 위해 자기 선속에 대한 ',
 '33,4,0':'가우스 법칙을 이용한다. ',
 '34,0,0':'자기장의 축과 같은 축을 갖는 ',
 '34,1,0':'얇은 원기둥 모양의 닫힌 면을 택한다. ',
 '34,2,0':'이 면을 지나는 자기 선속이 영이라는 조건을 쓰면 ',
 '34,3,0':'다음과 같다 ',
 '35,33,0':'이 방정식으로부터 ',
 '37,0,0':'앙페르 법칙을 쓰면 고리에 작용하는 힘은 ',
 '37,1,0':'다음과 같다 ',
 '39,1,0':'각진동수 공식으로 주어진다 ',
 '42,1,0':'자석이 움직이면 원판에 회전 전기장이 유도되어 ',
 '42,2,0':'맴돌이 전류가 흐른다. 이 전류의 자기장은 ',
 '42,3,0':'자석에 힘을 가한다. 원판의 맴돌이 전류가 ',
 '42,4,0':'만드는 자기장을 구하기 위해, 원판의 크기가 ',
 '42,5,0':'자석까지의 거리에 비해 작다는 점을 이용한다. ',
 '42,6,0':'따라서 원판도 자기 쌍극자로 볼 수 있다. ',
 '42,7,0':'원판에 유도된 자기 모멘트를 구한 다음, ',
 '42,8,0':'그 자기장을 구하는 데 식 ',
 '43,0,0':'반지름이 ',
 '43,0,2':'이고 두께가 ',
 '43,0,4':'인 얇은 고리를 보자. 이 안의 회전 전기장 ',
 '43,1,0':'세기는 패러데이의 전자기 유도 법칙에서 다음과 같이 구한다: ',
}.items():p.add(at,text)
around(p,'30,0,0',['',' 고리에 작용하는 앙페르 힘 '],['1.1.2'])
around(p,'39,0,0',['',' 진동의 각진동수는 잘 알려진 용수철 진자의 '],['1.2.1'])
around(p,'42,0,0',['',' 원판이 자석에 미치는 되먹임은 다음과 같다. '],['1.2.2'])
around(p,'42,9,0',['','를 적용하면 된다. '],['(4)'])
finish(p,[],'Full original2015 page6 read at144dpi. Preserve all original magnetic dipole/radial field/force/damping notation, native vector arrows, actual source fractional Times/Symbol points and all original diagrams (field-ring/cylinder/annular disk). Original displayed dB_z in source(4) is not silently corrected. Native source b and beta definitions, source equation labels(3)-(10), every fraction/radical/vector rule and scripts remain exact. Source Word prose offsets around F_A/B_r are retained physically and require explicit logical-row atom profiles during natural packing; no source math Y/font/point changes. Only narrative is translated.')
