from izho2012_authoring import begin,around,finish
p=begin(5)
for at,text in{
 '1,0,0':'대안 풀이: 기하 광학 근사. ',
 '1,1,0':'원칙적으로 이 문제는 기하 광학으로도 풀 수 있다. ',
 '1,1,1':'이 복잡한 ',
 '1,2,0':'풀이의 주요 단계는 다음과 같다: ',
 '2,0,0':'- 스넬의 굴절 법칙 적용; ',
 '2,1,0':'- 임의의 광선을 택하고 평판 입사각 계산; ',
 '2,2,0':'- 평판 앞면에서 굴절한 뒤의 각도 계산; ',
 '2,3,0':'- 평판 내부 광선 궤적의 미분방정식 도출; ',
 '2,4,0':'- 이차 근사로 미분방정식 풀이; ',
 '2,5,0':'- 평판을 나가기 직전의 각도 계산(음수여야 함); ',
 '2,6,0':'- 뒷면에서 굴절한 뒤의 각도 계산; ',
 '2,7,0':'- 평판의 축과 만나는 지점까지의 거리 계산; ',
 '2,8,0':'- 모든 광선에서 이 거리가 같음을 증명; ',
 '2,9,0':'- 렌즈 공식 도출; ',
 '2,10,0':'- 초점 거리 공식 정리. ',
 '4,2,0':'배점 ',
 '4,4,0':'핵심 원리: 모든 광선 경로에서 ',
 '4,5,0':'전파 시간이 같음 ',
 '5,1,0':'작은 각도에 대한 이차 근사 사용 ',
 '5,4,0':'거리 계산 ',
 '5,4,2':'및 ',
 '5,7,0':'- 정확한 식; ',
 '5,8,0':'- 근사식 전개; ',
 '7,13,0':'합계 ',
 '9,0,0':'기하 광학 근사의 채점 기준(대안 풀이) ',
 '9,3,0':'배점 ',
 '9,5,0':'굴절 법칙 ',
 '9,8,0':'작은 각도에 대한 이차 근사 두 개 ',
 '9,11,0':'평판 입사각 ',
 '9,14,0':'평판 내부 광선 궤적의 미분방정식 ',
 '9,17,0':'이차 근사 해 ',
 '9,20,0':'뒷면에 도달하기 직전의 각도 ',
 '9,23,0':'뒷면에서 굴절한 뒤의 각도 ',
 '9,26,0':'광축과의 교점 ',
 '9,32,0':'얇은 렌즈 공식과 같은 형태의 식 ',
 '9,37,0':'합계 ',
}.items():p.add(at,text)
around(p,'3,0,0',['채점 기준: 문제 ',''],['1C'])
for at,label,ref in [('7,1,0','광학적 경로 길이 ','(3)'),('7,4,0','얇은 렌즈 공식 ','(4)'),('7,7,0','렌즈의 초점 거리 ','(7)'),('7,10,0','상까지의 거리 ','(8)')]:around(p,at,[label,' '],[ref])
around(p,'9,29,0',['모든 굴절 광선에서 거리 ','가 같음 '],['b'])
p.protect_fragment('9,34,0','10 ','Original complete tenth-row enumerator stays in its original left grid cell, including its source separator space.')
p.add('9,34,0','초점 거리 공식 ','The formula for the focal length ')
for slot in p.slots:
 if slot['at']in[[4,2,0],[9,3,0]]:slot['align']='center'
finish(p,[[3,0],[9,0]],'Full original page5 viewed at144dpi. Preserve original11.04pt upper alternative derivation and12pt tables, exact two grading grids, all decimal-comma scores, repeated source row5, native distance SA/BS-prime and reference glyphs, source b and10, true faux-bold headings/Total and source gray fields. Original diagram and mathematical programs are not redrawn; no font fitting.')
