from izho2016_authoring import begin,around,finish
p=begin(1)
for at,text in{
 '1,0,0':'이론시험 문제 ',
 '2,0,0':'해설 ',
 '3,0,0':'주의 ',
 '3,3,0':'케플러 운동의 전체 에너지와 공전 주기는 ',
 '3,4,0':'긴반지름에만 의존한다. 돌의 궤도에서는 이 값이 ',
 '3,5,0':'행성의 반지름과 같다(',
 '3,5,2':'). 출발점은 ',
 '3,6,0':'짧은반지름 위에 있다. 행성 중심인 초점까지의 ',
 '3,7,0':'거리가 ',
 '3,7,2':'이기 때문이다(그림 참조). 그림에서 ',
 '4,5,0':'이 결과는 에너지와 각운동량 보존으로 세운 연립방정식을 ',
 '4,6,0':'풀어서도 얻을 수 있다. ',
 '5,0,0':'돌의 비행 거리는 ',
 '7,1,0':'채점 기준 ',
 '7,3,0':'평가 항목 ',
 '7,4,0':'배점 ',
 '7,6,0':'최대 높이를 구함 ',
 '7,7,0':'에너지 보존 ',
 '7,8,0':'각운동량 보존 ',
 '7,9,0':'연립방정식을 올바르게 풂 ',
 '8,0,0':'또는 ',
 '8,1,0':'긴반지름 ',
 '8,1,2':'을 구함 ',
 '8,2,0':'긴반지름 값에 대한 근거 제시 ',
 '8,3,0':'올바른 개략도 ',
 '8,4,0':'답 ',
 '9,10,0':'각 ',
 '11,1,0':'질문에 대한 올바른 답 ',
 '13,0,0':'합계 ',
 '14,1,0':'정의에 따라 열용량은 다음과 같다 ',
 '20,8,0':'점 ',
 '20,8,2':'에서 기체의 상태량을 (',
 '20,9,0':'다음과 같다 ',
 '26,0,0':'작은 변화에 대해 ',
 '35,0,0':'상태방정식 ',
 '35,0,7':'를 이용하면 최종적으로 ',
 '41,0,0':'채점 기준 ',
 '41,2,0':'평가 항목 ',
 '41,3,0':'배점 ',
 '41,5,0':'미분계수를 포함하는 열용량 ',
 '41,5,2':'의 식 ',
 '41,8,0':'다음 점에서 미분계수를 구함: ',
}.items():p.add(at,text)
around(p,'3,1,0',['문제 ','점',' '],['1 (10.0 ',')'])
around(p,'3,2,0',['문제 ','점',' '],['1A (4.0 ',')'])
around(p,'9,10,2',['를 구함',''],['('])
around(p,'14,0,0',['문제 ','점',' '],['1В (3.0 ',')'])
around(p,'20,8,11',['','라 하자. 그러면 과정의 식은 '],[')'])
for slot in p.slots:
 if slot['at']in[[7,3,0],[7,4,0],[41,2,0],[41,3,0]]:slot['align']='center'
finish(p,[[1,0],[2,0],[3,0],[3,1],[3,2],[7,1],[8,0],[14,0],[41,0]],'Full original2016 page1 read at144dpi. Keep9.96pt Arial bold header, original15.96pt bold italic two-line title and14.04pt titles, source Attention heading and original left-column1A center beside the unchanged orbital sketch. Preserve every native Cambria Math equation,8.52/8.04/6.96pt script, inline l=2Rphi=2R(pi/2-alpha) with its original fraction rule, source P0/V0/T0 tuple and state equation, exact table grades/decimal commas. Original italic scoring descriptors retain source italic style/points. Same-cell run-in a=R and phi=pi/2-alpha must pack as complete native expressions with their labels, preserving grid/scores, rather than keep erased English-width holes. Only explicit English prose is translated; no source equation, unit or point fitting.')
