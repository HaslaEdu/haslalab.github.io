from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path.insert(0,str(B/'engine'))
from izho_natural_spacing import boundary_gap
def token(text,kind,x0=0,x1=30):return dict(text=text,kind=kind,size=12,x0=x0,x1=x1)
for suffix in ['와 여분의 종이','에 쓰시오.','의 테두리','를 순서대로']:
 assert boundary_gap(token('답안지','korean'),token(suffix,'korean',60,100))==0
assert boundary_gap(token('답안지','korean'),token('사용 방법','korean',60,100))==3
assert boundary_gap(token('F','native'),token('를 구하시오.','korean',60,100))==0
assert boundary_gap(token('x','native'),token('y','native',60,70))==30
print('KOREAN_PARTICLES_ATTACH_ACROSS_PROSE_STYLE_SPANS; ORDINARY_WORD_SPACES_AND_NATIVE_MATH_INTERNAL_GAPS_RETAINED')
