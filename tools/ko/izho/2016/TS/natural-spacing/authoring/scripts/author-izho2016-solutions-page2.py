from izho2016_authoring import begin,around,score,finish
p=begin(2)
for at,text in{
 '1,1,0':'올바른 답 (','1,1,4':' 또는 ','1,3,0':'합계 ',
 '1,7,0':'대칭성에 따라, 부피 전체에 균일하게 전하가 분포한 구의 중심 전위는 ',
 '1,8,0':'무한대의 전위를 기준으로 다음과 같다 ',
 '6,9,0':'여기서 ','6,9,2':'는 비례계수이며 구의 크기에 관계없이 같다. ',
 '7,0,0':'이는 균일한 부피 전하 밀도의 두 구를 중첩한 것이다. 하나는 반지름이 ','7,0,2':'이고 ',
 '7,1,2':'이며, 다른 하나는 반지름 ','7,1,6':'이다. 따라서 ',
 '7,2,0':'중심에서의 전위는 다음과 같다 ','8,10,0':'여기서 ',
 '11,11,0':'채점 기준 ','11,13,0':'평가 항목 ','11,14,0':'배점 ',
 '11,16,0':'중심 전위에 대한 식 ','11,17,0':'중심 전위의 유도 ',
 '11,18,0':'중심 전위의 계수가 잘못됨 ','11,19,0':'전위 유도가 잘못됨 ',
 '13,2,0':'중첩 원리를 적용함 ','13,5,0':'올바른 답 ','13,7,0':'합계 ',
 '15,1,2':'체·고체 경계면의 표면 에너지 변화는 다음과 같다 ',
 '15,23,0':'액적 경계의 작은 구간 ','15,25,1':'에 대한 힘의 평형 조건은 ',
 '15,26,0':'다음과 같다 ',
 '17,19,2':'계의 표면 에너지 변화를 구하자. ',
 '17,20,0':'변화량 ','17,24,0':'는 수위가 추가로 ',
 '17,26,1':'만큼 조금 높아질 때 다음과 같다 ',
 '18,25,0':'여기서 ','18,34,0':'는 액체와 관 내벽 사이의 접촉 면적 ',
 '18,35,0':'변화이다. ','18,36,2':'중력 퍼텐셜 에너지 변화 ',
 '18,41,0':'는 수위가 추가로 ','18,42,0':'높아진 양 ',
 '18,43,1':'에 대해 다음과 같다 ',
 '20,0,0':'이때 상승한 액체의 질량은 ',
 '20,11,0':'이며, 상승한 높이는 ','20,11,2':'이다. ',
}.items():p.add(at,text)
around(p,'1,6,0',['문제 ','점',' '],['1С (3.0 ',')'])
around(p,'7,1,0',['전하 밀도가 ',''],['+'])
around(p,'7,1,4',[', 전하 밀도 ',''],['-2'])
around(p,'14,0,0',['문제 ',' 퍼텐셜 에너지로 본 평형 ','점',' '],['2.','(10.0 ',')'])
around(p,'15,0,0',['',' 도입 ','점',' '],['1.','(1.0 ',')'])
around(p,'16,25,0',['식 ','과 ','에서 '],['(1)','(2)'])
around(p,'17,18,0',['',' 수직 원통형 관 안의 물 ','점',' '],['2.','(2.0 ',')'])
score(p,'15,1,1','액')
for at in ['17,19,1','18,36,1']:score(p,at)
for slot in p.slots:
 if slot['at']in[[11,13,0],[11,14,0]]:slot['align']='center'
finish(p,[[1,6],[11,11],[14,0],[15,0],[17,18]],'Full original2016 page2 reviewed at144dpi. Preserve original9.96pt header and two distinct source grade tables, every original score and source9.96pt penalty descriptors; preserve left-column equation4/5 labels atx390.67 and all native Symbol/Cambria Math/MathType fractional transforms. The original capillary-tube diagram narrows only the lower right paragraph region; do not create full-width prose over it. All translated in-cell run-in formulas must pack with their labels as complete native CID groups, including CV-R and R/2 separately around translated or. Original electrostatic display roots/fraction bars and all tube energy equations stay stationary. Every original mathematical point, native literal and paint retained.')
