from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2020,13);p.header()
for at in ['6,0,0','14,0,0']:p.add(at,'식','Equation')
for at in ['1,0,0','21,4,0','25,1,0','29,1,0']:p.add(at,'식','Formula')
p.add('21,0,0','조건','Condition');p.add('34,0,0','합계 ')
print(p.save())
