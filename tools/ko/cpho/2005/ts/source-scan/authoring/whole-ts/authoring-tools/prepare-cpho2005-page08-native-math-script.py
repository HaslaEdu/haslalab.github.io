from pathlib import Path
s=Path('D:/CodexBuilds/propose-cpho2005-page07-native-math.py').read_text('utf8')
a=s.index('specs=[]');b=s.index('S=8;out=[]',a)
spec='''specs=[]
def add(id,rect,path,center=None):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=center))
for id,rect in {
 'eq1-7':[72,57,133,76], 'eq11-12':[156,57,218,76], 'eq3':[261,57,283,76],
 'F-old':[349,57,365,76], 'F-prime':[389,56,405,76],
 'fixed-k-alpha-mu':[76,165,140,185], 'fixed-x':[151,165,193,185],
 'eq10':[285,165,315,185], 'eq13':[325,165,355,185],
 'dx-coefficient':[139,184,164,204], 'F-linear':[299,184,314,204], 'Fp-linear':[323,183,341,204], 'dx-linear':[354,183,379,204],
 'F-sum':[146,203,161,224], 'Fp-sum':[178,202,195,224], 'F0':[302,203,322,224], 'F0p':[339,202,359,224],
 'dx-proportional':[76,223,100,243], 'Kdx':[181,222,213,243], 'Kpdx':[233,222,270,243]
}.items():add(id,rect,259)
for id,rect in {'dx-compression':[77,442,103,461], 'dxm-compression':[167,441,195,461], 'F-work':[264,442,280,461]}.items():add(id,rect,268)
for id,rect in {'dx-recovery':[450,64,476,85], 'dxm-recovery':[490,64,518,85], 'Fp-work':[639,64,656,85]}.items():add(id,rect,277)
for id,rect in {'eq20-21':[448,121,508,141], 'eq16-19':[472,171,545,192], 'part-one':[461,227,475,244], 'p-recoil':[645,263,662,283], 'nu0':[469,281,485,302]}.items():add(id,rect,286)
for id,rect in {'mass-m':[463,418,482,439], 'speed-v':[620,418,637,439]}.items():add(id,rect,295)
'''
s=s[:a]+spec+s[b:]
a=s.index('corrections=');b=s.index('boxes=',a)
s=s[:a]+'''corrections={
 'eq1-7':[74,57,133,76], 'eq11-12':[159.25,57,218,76], 'eq3':[262,57,283,76],
 'F-old':[349,57,361,76], 'fixed-x':[153,165,193,185],
 'eq10':[288,165,315,185], 'eq13':[328,165,355,185],
 'F-linear':[299,184,311,204], 'Fp-linear':[326,183,341,204],
 'F-sum':[146,203,158.5,224], 'F0':[302,203,320,224],
 'Kdx':[181,222,211,243], 'Kpdx':[233,222,268,243],
 'eq20-21':[451,121,508,141], 'eq16-19':[476.5,171,545,192],
 'p-recoil':[649,263,662,283], 'speed-v':[626,418,637,439]
}
for spec in specs:
 if spec['id'] in corrections:spec['search_rect']=corrections[spec['id']]
'''+s[b:]
s=s.replace('page07','page08').replace("original.pdf',7)","original.pdf',8)").replace('page=d[6]','page=d[7]').replace('page=7','page=8')
Path('D:/CodexBuilds/propose-cpho2005-page08-native-math.py').write_text(s,'utf8')
print('PAGE08_MANUAL_NATIVE_MATH_WINDOW_SCRIPT_READY')
