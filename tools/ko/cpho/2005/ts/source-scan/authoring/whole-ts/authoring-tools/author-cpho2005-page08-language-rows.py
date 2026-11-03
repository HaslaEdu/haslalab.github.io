"""Human-read source lines, bilingual prose and independent CJK sample windows."""
from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');rows=[];samples=[]
def row(id,hint,ko,en,sample,window):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en))
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=sample,source_measurement_window=window))
row('recovery-force-first',1,'식 [[eq1-7]], [[eq11-12]]를 쓰고 식 [[eq3]]의 외력을 [[F-old]] 대신 [[F-prime]]로','Use [[eq1-7]], [[eq11-12]], replacing [[F-old]] in [[eq3]] by [[F-prime]],','式中的外',[282,57,337,76])
row('recovery-force-second',3,'나타내면','to obtain','表示',[61,77,87,94])
row('linear-fixed',15,'[[fixed-k-alpha-mu]], [[fixed-x]]가 정해지면 식 [[eq10]], [[eq13]]의 첫','Fixed [[fixed-k-alpha-mu]], [[fixed-x]]: in [[eq10]], [[eq13]], the first term','已确定的',[191,165,243,185])
row('linear-coefficients',17,'항과 [[dx-coefficient]]의 계수는 일정하다. 따라서 [[F-linear]], [[Fp-linear]]는 [[dx-linear]]의 선형','and the [[dx-coefficient]] coefficient are fixed; [[F-linear]], [[Fp-linear]]: linear in [[dx-linear]],','的系数均',[163,185,217,205])
row('linear-constant',20,'함수이다. [[F-sum]] 또는 [[Fp-sum]]는 일정한 힘 [[F0]], [[F0p]]와','so [[F-sum]] or [[Fp-sum]] is a sum of a constant force, [[F0]] or [[F0p]],','看成是由',[200,204,253,224])
row('linear-variable',22,'[[dx-proportional]]에 비례하는 힘 [[Kdx]], [[Kpdx]]의 합이다. 즉','and a force proportional to [[dx-proportional]], [[Kdx]] or [[Kpdx]]. Thus','成正比的',[100,224,154,243])
row('coefficients',31,'여기서','where','式中',[61,281,90,299])
row('compression-work',58,'[[dx-compression]]가 영에서 [[dxm-compression]]까지 증가할 때 [[F-work]]가 한 일은','As [[dx-compression]] grows from zero to [[dxm-compression]], the work by [[F-work]] is','由零增加',[103,442,155,460])
row('recovery-work',2,'[[dx-recovery]]가 [[dxm-recovery]]에서 영까지 감소할 때 [[Fp-work]]가 한 일은','As [[dx-recovery]] falls from [[dxm-recovery]] to zero, the work by [[Fp-work]] is','减小到零',[515,66,570,84])
row('absorption',8,'식 [[eq20-21]]과 흡수율의 정의에서','From [[eq20-21]] and the definition of absorption,','式及吸收',[507,122,560,140])
row('efficiency',16,'식 [[eq16-19]]를 쓰고 주어진 값을 대입하면','Using [[eq16-19]] and substituting the given data yields','代入有关',[565,170,622,192])
row('section-five',21,'5.','5.','五、',[462,209,484,225])
row('excited-energy',23,'[[part-one]] 들뜬 상태 핵의 에너지는','[[part-one]] The energy of the excited nucleus is','激发态核',[473,227,526,245])
row('emission-first',30,'방출 중 운동량은 보존된다. 핵의 방출 후 운동량을 [[p-recoil]],','Emission conserves momentum. Recoiling nucleus: [[p-recoil]];','发射光子',[448,264,501,282])
row('emission-second',32,'광자 진동수를 [[nu0]], 광자 진행 방향을 양으로 잡으면','photon frequency: [[nu0]]. Positive axis: photon propagation.','表示光子',[483,282,537,300])
row('recoil-momentum',39,'반동하는 바닥상태 핵의 운동량은','The recoil momentum of the ground-state nucleus is','基态核因',[438,331,491,347])
row('emission-energy',47,'방출 과정에서 에너지가 보존되므로','Energy conservation during emission gives','因发射过',[437,377,492,396])
row('relativistic-first',55,'[[mass-m]]은 바닥상태 핵의 상대론적 질량이다. 반동 속도를 [[speed-v]]라 하면','Ground-state nucleus: mass [[mass-m]], recoil speed [[speed-v]].','表示基态',[478,419,532,438])
row('relativistic-second',57,'바닥상태 핵의 운동량과 상대론적 질량은','Its momentum and relativistic mass are','基态核的',[482,438,537,455])
for name,data in [('authoring/page08-language-row-proposals.json',dict(rows=rows,reviewed=False,scope='Explicit bilingual source-line translations; no retyped mathematical symbols, equation numbers or source digits.')),
 ('page08-row-baseline-proposals.json',dict(rows=samples,scope='Manually read source CJK measurement samples; not erase geometry.'))]:
 (B/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
for old,new in [('calibrate-cpho2005-page07-per-row-type.py','calibrate-cpho2005-page08-per-row-type.py'),('calibrate-cpho2005-page07-row-weights.py','calibrate-cpho2005-page08-row-weights.py')]:
 s=Path('D:/CodexBuilds',old).read_text('utf8').replace('page07','page08').replace('source[6]','source[7]').replace('original[6]','original[7]').replace('page=7','page=8').replace("'section-four'","'section-five'").replace("'compression-first'","'excited-energy'")
 Path('D:/CodexBuilds',new).write_text(s,'utf8')
print('PAGE08_EXPLICIT_SOURCE_LANGUAGE_AND_MEASUREMENT_SAMPLES',len(rows),flush=True)
