from izho2016_authoring import begin,around,score,finish
p=begin(4)
for at,text in{
 '1,0,0':'안정 평형 위치를, 큰 근은 불안정 평형 위치를 준다. 두 근의 수치는 ',
 '1,1,0':'다음과 같다 ',
 '11,0,0':'따라서 ','11,3,0':'일 때 수위는 높이 ',
 '11,4,2':'에서 멈춘다. 한편, ',
 '11,5,0':'초기 수위가 ',
 '11,6,2':'를 넘으면 물이 관 전체를 채운다. ',
 '11,7,2':'물은 초기 수위 ','11,8,0':'다음 조건이 성립하면 그러하다 ',
 '14,0,0':'또는 ',
 '17,1,2':'구멍의 수면이 불안정해져야만 물이 구멍을 통해 흘러나오기 시작한다. ',
 '17,2,0':'이는 중력 퍼텐셜 에너지의 감소량이 표면 에너지 절댓값의 증가량보다 클 때 ',
 '17,3,0':'일어난다. 이 조건은 다음 부등식으로 나타난다 ',
 '17,4,0':' ',
 '20,0,0':'여기서 다음을 얻는다 ',
 '22,0,0':'채점 기준 ','22,2,0':'평가 항목 ','22,3,0':'배점 ',
 '22,6,0':'경계의 한 구간을 선택함 ',
 '23,44,0':'에너지 변화량의 ', '23,45,0':'등식 ', '23,46,0':' ',
 '23,47,0':' ','23,48,0':' ','23,49,0':' ','23,50,0':' ',
 '28,1,0':'올바른 수치(유효숫자 고려) ',
}.items():p.add(at,text)
around(p,'11,7,4',['의 값에 관계없이, 식 ','에 실근이 없으면 관 전체를 채운다. '],['(12)'])
around(p,'17,0,0',['',' 물의 유출 ','점',' '],['4.','(3.0 ',')'])
around(p,'22,9,0',['구간의 평형 조건 ',' '],['(2)'])
for at,reference in [('23,1,0','(4)'),('23,29,0','(5)'),('27,2,0','(7)'),('31,1,0','(8)'),('33,1,0','(9)'),('33,16,0','(10)')]:
 around(p,at,['식 ',' '],[reference])
for at in ['11,7,1','17,1,1']:score(p,at)
for slot in p.slots:
 if slot['at']in[[22,2,0],[22,3,0]]:slot['align']='center'
finish(p,[[17,0],[22,0]],'Full original2016 page4 visually read at144dpi. Keep original upper native root branches and exact source inequality signs/subscripts, unlabeled preceding root solution, then display labels14–16 only. Standalone(6) atsource23,51,0 is a prose reference inside the rubric, not a display counter. Preserve true separate score columns, decimal comma grades and bold sum cells, full table grids. Translate all widely justified source prose word spans on rubric rowy568.87 into naturally spaced Korean, with whole source formula below stationary. Same-row rubric Formula4/5/7/8/9/10 and balance-condition labels must pack together with complete original MathType expressions including fraction rules. All exact fractional source points and glyphs remain native.')
