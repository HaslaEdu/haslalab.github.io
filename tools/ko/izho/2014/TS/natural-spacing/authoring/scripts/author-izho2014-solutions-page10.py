from izho2014_authoring import begin,around,finish
p=begin(10)
for at,literal in [('1,3,0','(20)'),('1,7,0','(21)'),('1,9,0','(22)'),('1,12,0','(23)'),('1,16,0','(24)'),('1,21,0','(25)'),('1,25,0','(26)'),('1,30,0','(27)')]:around(p,at,['식 ',' '],[literal])
for at,literal in [('1,0,0','(19)'),('1,18,0','(24)'),('1,27,0','(26)'),('1,33,0','(27)')]:around(p,at,['식 ','의 올바른 수치 '],[literal])
p.add('1,35,0','합계 ')
finish(p,[],'Full original2014 page10 read at144dpi: final continued metamaterials grading table. Preserve exact original physical table dimensions, all0.25/0.5/1.0 grouped scores, Roman/decimal source punctuation, row numbers7-10, complete native equation references(19)-(27) and literal10,0 bold total. Only English Formula/Correct numerical value/Total and the fixed header prose are translated, at the original12pt or9.96pt fonts roles. No score, grid, page geometry or point fitting.')
