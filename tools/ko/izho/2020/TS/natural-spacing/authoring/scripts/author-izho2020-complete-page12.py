from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2020,12);p.header()
p.add('10,2,0','항목 ',align='center');p.add('10,3,0','배점 ',align='center');p.add('71,0,0','조건','Condition')
for at in ['12,0,0','17,0,0','20,0,0','36,0,0','52,0,0','65,0,0','82,0,0']:p.add(at,'식','Equation')
for at in ['16,0,0','16,4,0','23,0,0','23,4,0','24,0,0','26,4,0','26,8,0','27,0,0','32,0,0','41,1,0','44,0,0','48,1,0','56,0,0','56,4,0','56,8,0','58,4,0','58,8,0','61,0,0','72,0,0','75,0,0','78,0,0','85,1,0','88,0,0']:p.add(at,'식','Formula')
print(p.save())
