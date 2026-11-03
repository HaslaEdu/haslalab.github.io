from izho2013_authoring import begin,around,finish
p=begin(10)
for at,num in[('1,1,0','9'),('1,5,0','10'),('2,6,0','13'),('2,9,0','14'),('3,1,0','16'),('3,6,0','17'),('3,9,0','18')]:around(p,at,['식 ',' '],[f'({num})'])
around(p,'2,1,0',['보존 법칙 ',' '],['(12)'])
for at in['1,8,0','2,12,0','3,12,0']:p.add(at,'올바르게 계산한 ')
p.add('3,14,0','합계 ')
finish(p,[],'Complete original2013 page10 viewed at144dpi. Preserve the exact original continuation table geometry, source scores/enumerators/decimal10,0, every original native equation reference, native E1/tau1/N in original font roles/points/script baselines. Prose only is translated at source sizes; grid and math remain original encoded source, no figure or font-size substitution.')
