from izho2014_authoring import begin,around,finish
p=begin(9)
for at,text in{
 '1,0,0':'도선 표면에서 압력이 영이라는 조건을 적용하면 ',
 '5,1,0':'그 에너지 밀도는 다음 식으로 주어진다 ',
 '8,0,0':'따라서 기계적 변형에 저장된 전체 에너지는 ',
 '14,1,0':'이 경우에 적용하면 ',
 '16,0,0':'여기서 ',
 '16,0,2':'은 반지름의 상대 변화이다. ',
 '17,0,0':'따라서 기계적 응력에 따른 반지름 변화는 ',
 '29,0,0':'채점 기준 ',
 '29,2,0':'평가 항목 ',
 '29,3,0':'배점 ',
}.items():p.add(at,text)
around(p,'5,0,0',['',' 기계적 압력으로 결정 격자에 응력이 생기며, '],['8.'])
around(p,'14,0,0',['',' 도선 반지름의 변화는 훅의 법칙으로 정해진다. 이를 '],['9.'])
around(p,'25,0,0',['',' 식 ','와 ','를 비교하면 '],['10.','(15)','(25)'])
for at,literal in [('29,6,0','(1)'),('29,11,0','(2)'),('29,13,0','(3)'),('29,18,0','(4)'),('29,23,0','(5)'),('29,25,0','(6)'),('29,30,0','(7)'),('30,0,0','(8)'),('30,2,0','(9)'),('30,4,0','(10)'),('30,6,0','(11)'),('30,8,0','(12)'),('30,10,0','(13)'),('30,12,0','(14)'),('30,17,0','(15)'),('30,23,0','(16)'),('30,26,0','(17)'),('30,29,0','(18)'),('30,33,0','(19)')]:around(p,at,['식 ',' '],[literal])
for at,literal in [('29,15,0','(3)'),('29,27,0','(6)'),('30,14,0','(14)'),('30,20,0','(15)')]:around(p,at,['식 ','의 올바른 수치 '],[literal])
for slot in p.slots:
 if slot['at']in[[29,2,0],[29,3,0]]:slot['align']='center'
finish(p,[[29,0]],'Full original2014 page9 read at144dpi: pressure profile, elastic energy, mechanical contraction, thermal-expansion coefficient and original grading table. The source duplicated phrase wire pressure is read in its physical context as pressure at the wire surface, consistent with its original boundary condition; no equation is altered. Keep exact source equation-reference order(15)/(25), original2.39e-18 J and1.91e-12 m, all original sigma/epsilon/mu/gamma/CyrillicК math glyphs, physical fractional points, native source counters(22)-(27) and every grading score/grid. Repeated English numerical numerical is translated once as its meaning, without changing grade values. No point fitting.')
