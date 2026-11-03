from izho2014_authoring import begin,around,finish
p=begin(5)
for at,text in{
 '7,0,2':'가 로켓에 작용하면, 고유 기준계에서 계의 전체 ',
 '8,16,0':'또는 기호 ',
 '8,20,0':'를 쓰면 ',
 '9,0,0':'상대성 원리에 따라 이 방정식의 형태는 어느 관성 기준계에서도 같으며, ',
 '9,1,0':'메셰르스키 방정식이라고 부른다. ',
 '10,0,0':'여기에 ',
 '10,3,0':'를 대입하면 최종적으로 ',
 '11,3,0':'. 조건 ',
 '14,0,0':'초기 조건 ',
 '14,7,0':'를 적용하면 최종적으로 ',
 '17,14,0':'와 ',
 '22,1,0':'이때 중력이 한 일은 최소가 된다. 따라서 최적의 연료 ',
 '22,2,0':'소모율은 ',
 '23,14,0':'중력이 로켓의 속도에 영향을 줄 시간이 없으므로, ',
 '26,0,0':'따라서 로켓이 도달하는 최대 높이는 ',
 '29,0,2':'인 기준계를 생각하자. 이 기준계는 실험실 기준계에 대해 ',
 '29,1,0':'속도 ',
 '29,1,2':'로 움직인다. 이때 입자의 실험실 기준계 속도 ',
 '29,1,4':'는 ',
 '29,2,0':'다음 상대론적 속도 합성식으로 주어진다 ',
}.items():p.add(at,text)
around(p,'3,0,0',['',' 지표면에서의 원 궤도 속도는 다음과 같다 '],['2.'])
around(p,'4,15,0',['식 ','에서 로켓의 초기 질량을 구하면 '],['(2)'])
around(p,'7,0,0',['',' 외력 '],['3.'])
around(p,'7,1,0',['운동량이 변하므로, 식 ','은 다음과 같이 바뀐다 '],['(1)'])
around(p,'11,0,0',['',' 로켓이 일정한 높이에 정지해 있어야 하므로 '],['4.'])
around(p,'11,6,0',['을 식 ','에 대입하고 시간에 대해 미분하면 '],['(7)'])
around(p,'17,0,0',['',' 다음 두 식 '],['5.'])
around(p,'17,22,0',['를 식 ','에 대입하면 '],['(7)'])
around(p,'22,0,0',['',' 연료가 거의 순간적으로 모두 연소할 때 로켓은 최대 속도에 도달한다. '],['6.'])
around(p,'23,15,0',['치올콥스키 공식 ','를 사용할 수 있다 '],['(2)'])
around(p,'29,0,0',['',' 입자의 속도가 '],['7.'])
finish(p,[],'Full original2014 page5 read at144dpi: complete classical variable-mass rocket solution and start of relativity. All25 native display/inline formula programs, original source signs and gravity convention, fractional points11.46-12.15 and all subscripts remain source-native. Retain exact initial conditions, logarithms/exponentials, original4870 kg value, native optimal-consumption infinity, native H_max expression, and v/v-prime/w variables. Translation follows source reasoning without correcting equations or retyping mathematics. Physical source rows, enumerators and all right-margin equation labels are retained.')
