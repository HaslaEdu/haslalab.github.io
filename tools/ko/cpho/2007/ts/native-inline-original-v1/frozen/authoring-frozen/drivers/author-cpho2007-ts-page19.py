from cpho2007_ts_authoring import Page
p=Page(19)
for row,part,ko,en in[
 (0,0,'수치를 대입하면','Substituting the data gives'),
 (1,0,'식 (','From ('),
 (1,1,')에서 ', '), for '),
 (1,2,'인 나트륨 원자의 속력은', ', a sodium atom has speed'),
 (2,0,'각도가 ','For '),
 (2,1,'인 나트륨 원자의 속력은', ', the sodium atom has speed'),
 (3,0,'운동 방향과 ','For motion at angles to '),
 (3,1,'축 사이 각이 ', 'in '),
 (3,2,'~', '-'),
 (3,3,'인 원자 중 공명 흡수가 일어나는 나트륨 원자의', ', resonant sodium atoms have'),
 (4,0,'속력 범위는','speeds in the range'),
 (5,0,'식 (','From ('),
 (5,1,')에 따라 공명 흡수 전후 나트륨 원자의 속도 벡터 변화량은', '), the sodium atom\'s velocity change in resonant absorption is'),
 (6,0,'속도 벡터 변화량의 크기는','The magnitude of this velocity change is'),
 (7,0,'수치를 대입하면','Substituting the data gives'),
]:p.put(row,part,ko,en)
p.save('Full original source page19 visually reviewed at144dpi. Completes method2 speed interval and sodium recoil vector/magnitude. All native30/45degree references, numerical ranges, source formulas(11)-(16), powers, vector ez, lambda/M/h/u/V, font programs, source point sizes and every original fraction bar/Y are retained exactly. Every Chinese phrase is explicitly translated without font fitting or formula retyping.')
