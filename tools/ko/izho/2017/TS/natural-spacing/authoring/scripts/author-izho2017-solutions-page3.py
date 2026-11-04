from izho2017_authoring import begin,around,finish
p=begin(3)
for at,text in {
 '1,0,0':'평가 항목 ',
 '1,1,0':'배점 ',
 '1,2,0':'간섭을 이용하여 파동을 상쇄 ',
 '1,4,0':'상쇄 간섭 조건을 사용함: 파동의 위상이 반대 ',
 '1,6,0':'거리 차이는 반파장의 정수배여야 함 ',
 '1,8,0':'두 원군을 그림 ',
 '1,10,0':'교점을 이용함 ',
 '1,14,0':'합계 ',
 '3,1,2':'쿨롱 힘과 뉴턴의 만유인력 사이의 유사성을 이용하는 것이 ',
 '3,2,0':'이 문제를 푸는 가장 간단한 방법이다 ',
 '7,1,1':' 및 ',
 '9,0,0':'가우스 정리에 따르면, 무한히 넓은 대전 평면의 전기장은 ',
 '9,1,0':'면전하 밀도가 ',
 '9,1,2':'일 때 다음과 같다 ',
 '11,3,0':'대전 평면과의 유사성을 이용하면 행성에 대해서도 다음 결과를 얻는다 ',
 '15,4,0':'무한 평면을 얇은 고리들로 나누어 적분해도 ',
 '15,5,0':'같은 결과를 쉽게 얻을 수 있다 ',
 '15,7,0':'질량이 ',
 '15,7,2':'반지름이 ',
 '15,7,4':'인 고리가 ',
 '15,8,0':'거리 ',
 '15,8,2':'에서 작용하는 인력은 다음과 같다 ',
 '20,0,0':'높이가 ',
 '23,0,0':'기하학적 관계에서 다음을 얻는다 ',
 '25,1,2':'일 때 다음과 같다 ',
 '29,0,0':'이는 정전기장과의 유사성으로 구한 결과와 같다. ',
 '29,1,2':'무한 평면 가까이에 있는 관측자에게 평면의 입체각은 ',
 '29,2,0':'다음과 같음이 분명하다 ',
 '31,2,0':'따라서 문제의 조건에서 다음을 얻는다 ',
 '32,1,1':' 또는 ',
 '32,4,2':'각뿔을 두께 ',
 '32,4,4':'인 밑면과 평행한 얇은 층으로 나눈다. ',
 '32,5,0':'각뿔 꼭짓점에서 보면 모든 층의 입체각은 ',
 '32,5,3':'로 같다. 이는 ',
}.items():p.add(at,text)
around(p,'1,12,0',['강조된 영역 안의 ','개 점을 모두 정확히 표시 '],['6'])
around(p,'2,0,0',['문제 ','. 우주를 향한 환상적인 여행 (','점',' '],['2','10.0 ',')'])
around(p,'3,0,0',['','. 특이한 모양의 행성 (','점',' '],['1','4.0 ',')'])
for at,value in [('3,1,1','0.7'),('29,1,1','0.5'),('32,4,1','0.7')]:around(p,at,['','점',' '],[f'[{value} ',']'])
around(p,'20,0,2',['인 평면을 두께 ','인 얇은 고리로 나눈다. 그러면 '],['dr'])
around(p,'20,1,0',['반지름','인 고리가 작용하는 중력은 다음과 같다 '],[' r '])
# The original Latin F in prose is a physical mathematical variable, not regenerated.
around(p,'25,1,0',['위 식을 대입해 적분하면 전체 힘 ','는 물체의 질량이 '],['F'])
p.add('32,6,0','전체 입체각의 육분의 일이다. 정육면체 안의 중심에서 바라보는 것과 같다 ')
for slot in p.slots:
 if slot['at']in[[1,0,0],[1,1,0]]:slot['align']='center'
finish(p,[[2,0],[3,0]],'Full original2017 page3 visually read at144dpi. Original13.92pt main subsection,12pt ordinary prose/table,10.08pt italic alternative-solution prose and every native mathematical point and baseline are retained. The native source Latin F/r/dr variables remain encoded; all Cambria Math display fractions, integrals, original ring diagram and table scoring positions remain unchanged. Complete same-row inline math moves rigidly with original rules/scripts/Forms when prose packs. Source spelling and original formulae remain literal.')
