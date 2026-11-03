from cpho2007_ts_authoring import Page
p=Page(11)
for row,part,ko,en in[
 (0,0,'. 중간 세 점의 전위를 각각 ','. Let the intermediate potentials be '),
 (0,3,'라 하자 (그림). 등가 회로에서 각 점에','as shown. At each node,'),
 (1,0,'연결된 축전기 판 네 개의 전하량 대수합은 0이어야 하므로','the algebraic sum of charges on the four connected capacitor plates is zero:'),
 (2,0,'네 절연체의 전압 합은 ','The four insulator voltages sum to '),
 (2,1,'이어야 한다.','; thus'),
 (3,0,'다음과 같이 놓으면','Define'),
 (4,0,'식 (','Rearranging ('),
 (4,1,')를 정리하여',') gives'),
 (5,0,'수치를 대입하면','Substituting the data gives'),
 (6,0,'식 (','Solving ('),
 (6,1,')를 풀면',') gives'),
]:p.put(row,part,ko,en)
p.save('Full original source page11 visually reviewed at144dpi: two native equivalent-circuit diagrams, node-charge conservation and voltage-difference linear system. Preserve both original diagrams in full, all C0/C1/C2/U0/U1/U2/U3 labels and source brace systems, delta variables, formulas(9)-(13), decimal results, encoded fonts/points/paint/Y and every fraction/vector program. Only Chinese narrative is translated. Native mathematical multi-line systems are stationary complete source objects; no retyping or resizing. The magenta original figure-reference paint is retained.')
