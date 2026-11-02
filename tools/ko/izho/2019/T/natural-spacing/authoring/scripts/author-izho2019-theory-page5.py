from pathlib import Path
import sys
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2019,5);p.header();p.add('1,0,0','문제 ','Problem ',align='center');p.add('1,0,0','레이저','Laser',align='center');p.add('1,0,0','점','points',align='center')
for at,text in {
'1,1,0':'양자론에 따르면 분자는 특정한 상태들에만 있을 수 있다. 각 상태의 ',
'1,2,0':'에너지는 다음과 같이 불연속적인 값을 가진다: ',
'1,13,0':'. 이 상태들은 ',
'1,14,0':'수직 에너지 축 위의 수평선으로 나타낸다. ',
'1,18,1':'. 이를 바닥상태라 한다. ',
'1,19,0':'나머지는 들뜬상태라 한다. 분자는 빛의 양자, 즉 광자를 ',
'1,20,0':'흡수하거나 방출하여 다른 에너지 상태로 전이할 수 있다. 아래에서 ',
'1,21,0':'빛의 세기는 광자속 밀도 ',
'1,21,2':'로 나타낸다. 이는 단위 시간에 ',
'1,22,0':'단위 면적을 수직으로 지나는 광자 수이며, 그 차원은 다음과 같다: ',
'1,34,0':'이후의 논의를 위해 빛이 매질을 통과할 때 일어나는 ',
'1,35,0':'다음 과정들을 고려해야 한다. ',
'2,0,0':'흡수.',
'2,2,0':'광자의 에너지가 들뜬상태와 바닥상태의 ',
'2,3,0':'에너지 차이와 같을 때만 전이가 가능하다: ',
'2,13,0':'. 여기서 ',
'2,15,1':'는 ',
'3,0,0':'광자의 진동수이고, ',
'3,8,1':'는 플랑크 상수이다. 바닥상태에 ',
'3,10,1':'개의 분자가 있다면, ',
'3,11,2':'는 광자를 흡수하여 들뜬상태로 전이한 분자의 수이다. ',
'3,12,0':'매우 짧은 시간 ',
'3,12,2':'동안의 값은 다음과 같다: ',
'5,0,0':'여기서 ',
'5,3,0':'는 흡수 단면적이며, 분자의 성질에 따라 ',
'5,4,0':'결정된다. ',
'6,0,0':'유도 방출.',
'6,0,1':'분자가 들뜬 ',
'6,3,1':'인 광자의 영향으로 ',
'6,5,0':'원래 광자와 완전히 같은 광자를 하나 더 방출한다. 두 광자는 ',
'6,6,0':'진행 방향과 에너지, 편광이 모두 같다. 이러한 전이의 수 ',
'6,7,0':'는 매우 짧은 시간 ',
'8,0,0':'여기서 ',
'8,4,1':'이고, ',
'8,7,0':'는 유도 방출 ',
'8,8,0':'단면적이다. ',
'9,0,0':'자발 방출. ',
'9,0,1':'들뜬상태의 분자는 광자를 방출하며 ',
'9,1,0':'자발적으로 바닥상태로 전이할 수 있다. 유도 방출과 ',
'9,2,0':'달리, 방출되는 광자의 방향과 편광은 모두 ',
'9,3,0':'무작위이며 에너지도 조금 달라질 수 있다. 따라서 ',
'9,4,0':'자발 방출은 빛의 세기를 증가시키는 데 ',
'9,5,0':'기여하지 않는다. 자발 전이 수 ',
'9,6,0':'매우 짧은 시간 ',
'9,6,2':'동안의 값은 다음과 같다: ',
'11,0,0':'여기서 ',
'11,4,1':'이고, ',
'11,4,3':'는 전이 ',
'11,5,0':'확률 또는 아인슈타인 계수이다. 그 역수인 ',
'11,11,0':'를 들뜬상태의 수명이라고 ',
'11,12,0':'한다. ',
'12,0,0':'분자의 각 상태 ',
'12,0,2':'를 나타낼 때 그 상태에 있는 분자의 전체 수 ',
'12,2,1':'대신 ',
'12,3,0':'이를 매질 속의 전체 분자 수 ',
'12,3,2':'으로 나눈 값을 사용하는 것이 편리하다: ',
'14,0,0':'이 값을 상태의 점유율이라고 한다. 점유율은 정규화 조건을 만족한다. ',
'14,1,0':'즉, 분자의 모든 상태에 대한 점유율의 합은 일이다: ',
}.items():p.add(at,text)
def fragments(at,parts):
 source=p.runs[at]['text'];remaining=source
 for literal,text in parts:
  assert remaining.startswith(literal),(at,literal,remaining)
  if text is None:p.protect_fragment(at,literal,'Original native state index or equation-reference numeral at its exact source font, point and baseline.')
  else:p.add(at,text,literal)
  remaining=remaining[len(literal):]
 assert not remaining,(at,remaining)
fragments('1,15,0',[('energy, starting from ','에너지가 증가하는 순서대로 상태 번호를 '),('0',None),('. In the absence of external influence, the molecule is found in the state ','부터 매긴다. 외부의 영향이 없으면 분자는 ' )])
fragments('1,16,0',[('with the number ','번호가 '),('0',None),(' and the lowest possible energy ','이고, 가능한 가장 낮은 에너지가 ' )])
fragments('2,0,1',[(' If a molecule is found in the ground state ','분자가 바닥상태 '),('0',None),(', then it can ','에 있으면, 광자를 ' )])
fragments('2,1,0',[('absorb a photon and be raised to the excited state ','흡수하여 들뜬상태 '),('1',None),('. Such a transition is ','로 전이할 수 있다. ' )])
fragments('3,11,0',[('ground state ','바닥상태 '),('0',None),(', then the number of molecules ','에 대해 전이 수 ' )])
fragments('6,1,0',[('state ','상태 '),('1',None),(', then under the influence of a photon with the frequency ','에 있으면, 진동수가 ' )])
fragments('6,4,0',[('can be forced to move to the ground state ','바닥상태 '),('0',None),(' with the emission of ','으로 전이할 수 있다. 이때 ' )])
fragments('6,7,2',[(' is described by the formula similar to formula ','동안의 값은 식 '),('(1)',None),(' as  ','과 비슷하게 다음과 같다: ' )])
fragments('8,2,1',[(' denotes the number of molecules in the excited state ','는 들뜬상태 '),('1',None),(' with energy ','에 있는 분자의 수이다. 이 상태의 에너지는 ' )])
fragments('9,5,2',[(' from the excited state ','는 들뜬상태 '),('1',None),(' to the ground state ','에서 바닥상태 '),('0',None),(' for a very ','으로 전이한 분자의 수이다. ' )])
fragments('11,2,1',[(' still designates the number of molecules in the excited state ','는 들뜬상태 '),('1',None),(' with energy ','에 있는 분자의 수이며, 에너지는 ' )])
# Whole original display equations, their original equation markers, all
# MathType variables/scripts/units and all original vector fraction rules stay native.
native=[]
for at in p.runs:
 b,l,s=map(int,at.split(','))
 if b in [4,7,10,13]or(b==1 and l in list(range(3,13))+list(range(23,33))):native.append(at)
native+=['1,17,0','1,18,0','1,21,1','2,14,0','2,15,0','3,8,0','3,9,0','3,10,0','3,11,1','3,12,1','5,1,0','5,2,0','6,2,0','6,3,0','6,6,1','6,7,1','8,1,0','8,2,0','8,3,0','8,4,0','8,5,0','8,6,0','9,5,1','9,6,1','11,1,0','11,2,0','11,3,0','11,4,0','11,4,2','11,6,0','11,7,0','11,8,0','11,9,0','11,10,0','12,0,1','12,1,0','12,2,0','12,3,1']
native += [at for at in p.runs if int(at.split(',')[0])==2 and 4<=int(at.split(',')[1])<=12]
native += [at for at in p.runs if int(at.split(',')[0])==3 and 1<=int(at.split(',')[1])<=7]
for at in sorted(set(native)):p.protect(at,'Reviewed original mathematical expression or physical state variable: retain encoded glyph/font program, original fractional point, script placement, baseline and native rule/Form geometry. No mathematical retyping.')
print(p.save())
