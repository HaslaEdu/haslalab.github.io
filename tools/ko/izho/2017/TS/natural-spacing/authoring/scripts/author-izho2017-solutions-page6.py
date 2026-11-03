from izho2017_authoring import begin,around,finish
p=begin(6)
for at,text in {
 '1,0,0':'이로부터 다음 방정식을 얻는다 ',
 '9,0,0':'그 해는 다음과 같다 ',
 '17,0,0':'다음 조건 ',
 '17,0,4':'은 ',
 '17,0,6':'일 때 성립해야 하므로 작은 쪽 근만 물리적 의미가 있다. ',
 '17,1,0':'따라서 최종적으로 ',
 '27,0,2':'충돌을 피하는 최소 속력 ',
 '27,0,5':'은 우주선이 구름에 접하는 경우에 해당한다. ',
 '27,1,0':'그 궤적을 아래 그림에 나타냈다. ',
 '28,0,0':'이때도 속도의 방사 성분은 영이 되며, 에너지 보존 법칙과 ',
 '28,1,0':'각운동량 보존 법칙은 다음과 같이 쓸 수 있다 ',
 '35,3,0':'이로부터 ',
 '40,0,2':'구름을 두께 ',
 '40,1,0':'인 얇은 층으로 차례로 분리하여 항상 구대칭을 유지한다고 하자. ',
 '40,2,0':'구름의 반지름이 ',
 '40,2,2':'일 때 얇은 층 하나를 떼어 내는 데 필요한 일은 ',
 '46,0,0':'따라서 구름 전체를 분해하는 데 필요한 일은 ',
 '51,2,0':'평가 항목 ',
 '51,3,0':'배점 ',
 '53,0,0':'쿨롱 법칙과 뉴턴의 만유인력 법칙 사이의 ',
 '57,1,1':' 및 ',
 '64,0,0':'다음의 수치 ',
 '66,1,1':' 또는 ',
 '66,3,0':'다음의 수치 ',
}.items():p.add(at,text)
for at,label in [('27,0,1','[1.0 '),('40,0,1','[0.6 ')]:around(p,at,['','점',' '],[label,']'])
around(p,'53,1,0',['유사성 ',' '],['(1):'])
for at,n in [('59,1,0',2),('62,0,0',4),('65,1,0',5),('65,4,0',6)]:around(p,at,['식 ',' '],[f'({n})'])
for slot in p.slots:
 if slot['at']in[[51,2,0],[51,3,0]]:slot['align']='center'
finish(p,[],'Full original2017 page6 read at144dpi. Keep serif12pt source prose, original bold bracketed scores and exact scoring grid/columns. Display labels34–41 fixed. The original cloud trajectory diagram is unmodified. All long root expressions and original complete native fractions are retained; same-cell formula labels pack with complete glyphs/scripts/rules while true distinct scoring columns and1.1/1.2 cell labels remain fixed. No point fitting or recreated math.')
