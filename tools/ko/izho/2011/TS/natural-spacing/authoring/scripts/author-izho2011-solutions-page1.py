from pathlib import Path
import sys,re,json
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,1);p.header()
for at,text in{
'1,0,0':'이론시험 해설 ',
'3,2,0':'정육면체는 퍽이 왼쪽 그림의 위치에 왔을 때 ',
'3,3,0':'뛰어오름을 쉽게 보일 수 있다. 이 순간 정육면체의 ',
'3,4,0':'속도를 ',
'3,4,2':', 질량을 ',
'3,4,4':'이라 하고, ',
'3,5,0':'퍽의 수평 상대 속도를 ',
'3,5,2':', ',
'3,6,0':'질량을 ',
'3,6,2':'이라 하자. 상대 속도는 정육면체를 ',
'3,7,0':'기준으로 한다. 마찰이 전혀 없으므로 계의 ',
'3,8,0':'전체 수평 운동량이 보존되고, ',
'4,13,0':'전체 역학적 에너지도 보존된다. ',
'6,0,0':'순간적으로 정육면체와 함께 움직이는 기준계에서 퍽은 속력 ',
'6,1,1':'로 반지름 ',
'6,1,3':'인 원을 따라 움직인다. 반지름 방향 운동 방정식은 ',
'6,2,0':'다음과 같다: ',
'8,0,0':'뉴턴 제3법칙에 따라 정육면체가 탁자에서 떨어지는 조건은 ',
'8,1,0':'다음과 같다: ',
'11,0,0':'퍽의 최소 속력은 다음 비로 미분하여 얻는다. ',
'12,14,0':'이는 다음 질량비에서 얻어진다: ',
'13,14,0':'채점 기준 ',
'14,2,0':'항목 ',
'14,3,0':'배점 ',
'14,27,0':'무한 전원 회로를 하나의 등가 전원으로 바꾸자. 그 기전력은 ',
'14,28,0':'',
'14,28,2':', 내부 저항은 ',
'14,28,4':'이다. 그러면 왼쪽 그림의 회로를 얻는다. ',
'14,29,0':'다음으로 저항 ',
'14,29,2':'를 떼고 전원을 두 개 더한 뒤 ',
'14,30,0':'저항 ',
'14,30,2':'를 다시 연결하면 오른쪽 그림의 회로를 얻는다. ',
}.items():p.add(at,text,align='center'if at in['1,0,0','13,14,0']else None)
def split_numbers(at,parts):
 source=p.runs[at]['text'];chunks=re.split(r'(\d+(?:\.\d+)?)',source);assert len(parts)==len(chunks[::2]),(at,chunks,parts)
 for i,value in enumerate(chunks):
  if not value:continue
  if i%2:p.protect_fragment(at,value,'Original problem/grade/equation-reference numeral in its exact source font/GID/point/baseline.')
  elif not value.isspace()or parts[i//2]:p.add(at,parts[i//2],value)
p.add('2,0,0','문제 ','Theoretical Question ');p.add('2,0,0','점','points');p.protect_fragment('2,0,0','1 (10 ','Original native problem number, opening parenthesis and grade at the original14.04pt face/baseline.')
for at,token in[('3,0,0','1A (3.5 '),('14,26,0','1В (4 ')]:
 p.add(at,'점','points');p.protect_fragment(at,token,'Original source problem label, grade and punctuation, including original Cyrillic problem-B glyph where printed; no retyping.')
split_numbers('9,14,0',['식 (',')–(',')를 함께 풀면 퍽의 속력은 '])
for l in[5,8,11,14,17,20,23]:p.add(f'14,{l},0','식 ','Formula ')
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
native=[]
for at,r in p.runs.items():
 coords=tuple(map(int,at.split(',')))
 if coords in translated or coords in fragments:continue
 # Every remaining run is explicitly reviewed below against this source page:
 # native equations, numerical scoring, equation markers or picture variables.
 native.append(at)
for at in native:p.protect(at,'Reviewed original complete mathematical content, scoring numeral, original equation marker or native diagram variable. Preserve source font/GID/fractional point, baseline and graphical rule/Form.')
path=p.save();d=json.loads(path.read_text('utf8'));d['centered']=[[2,0],[3,0],[14,26],[14,2],[14,3]];path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print(path)
