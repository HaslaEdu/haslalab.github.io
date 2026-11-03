from izho2015_authoring import begin,around,finish
p=begin(5)
for at,text in{
 '11,0,0':'수치를 대입하면 ',
 '12,0,0':'채점 기준 ',
 '12,2,0':'평가 항목 ',
 '12,3,0':'배점 ',
 '75,2,0':'합계 ',
 '76,2,0':'비오·사바르 법칙과 중첩 원리로 구하면 ',
 '76,3,0':'간단하다. 고리 미소 부분의 자기장 ',
 '76,3,2':'성분은 ',
 '76,4,0':'다음과 같이 주어진다 ',
 '76,5,0':'',
 '78,0,0':'기하학적 관계를 이용하면 ',
 '84,0,0':'고리의 모든 미소 부분에 대해 합하면 최종적으로 다음을 얻는다 ',
}.items():p.add(at,text)
for at,num in [('12,6,0','1'),('14,0,0','2'),('14,2,0','3'),('14,4,0','4'),('16,0,0','5'),('21,0,0','6'),('26,0,0','7'),('26,3,0','8'),('26,7,0','9'),('26,10,0','10'),('31,1,0','11'),('33,3,0','12'),('33,6,0','13'),('38,0,0','14'),('56,0,0','15'),('57,0,0','16'),('75,0,0','17')]:around(p,at,['식 ',''if p.runs[at]['text'].endswith(')')else' '],[f'({num})'])
around(p,'76,0,0',['문제 ',' 지연과 감쇠','점',' '],['3.',' (16 ',')'])
around(p,'76,1,0',['',' 전류가 흐르는 원형 고리의 자기장은 '],['1.1.1'])
for slot in p.slots:
 if slot['at']in[[12,2,0],[12,3,0]]:slot['align']='center'
finish(p,[[12,0],[76,0]],'Full original2015 page5 read at144dpi: completion of heat formula, complete detailed water-vessel grading table and start of current-ring magnetic-field solution. Retain all original Cambria Math table expressions/parentheses/equation references, full source square roots/fraction rules/grid geometry, source row score0.25/0.5 and7,0 total, original17.0kJ versus table17,0kJ punctuation, native Cyrillic heading is translated as 배점. Preserve all original Biot-Savart r/R/z/theta/I/dl vector glyphs, script points and complete source diagram. New prose stays in the original column beside that diagram; no mathematics, diagram or font-size redesign.')
