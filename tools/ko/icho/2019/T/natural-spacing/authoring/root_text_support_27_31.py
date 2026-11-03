"""Apply the root's source-reviewed prose edits; no PDF or engine mutation."""
from pathlib import Path
import hashlib,json,shutil

B=Path(__file__).resolve().parent
MANUSCRIPTS=B.parent/'2019'
OUT=B/'root-text-review-27-31-20261103'
NEW_TEXT={
27:{
'p27:b2:l0:s0-0:c7-99':'년, 해조류 재를 다루던 쿠르투아는 구리 용기가 평소보다 빨리 부식됨을',
'p27:b2:l1:s0-0':'관찰했다. 이를 연구하던 중 그의 고양이가 실험실에 들어와 진한 황산 용액을',
'p27:b2:l6:s0-0:c0-56':'오늘날에는 다음 반응물로 아이오딘을 제조한다: (',
'p27:b7:l0:s0-0':'물에서 아이오딘의 용해도는 매우 낮지만, 아이오딘화 이온을 넣으면 크게 증가한다.',
'p27:b9:l2:s2-2:c0-43':')은 ',
'p27:b9:l2:s4-4:c0-31':'의 다이클로로메테인 추출로 연구할 수 있다. ',
'p27:b10:l1:s2-2:c0-33':'는 녹는다. 추출 후 물 속 농도의 ',
'p27:b10:l1:s2-2:c35-63':'배가',
'p27:b10:l2:s0-0':'다이클로로메테인 속 농도이다.',
'p27:b10:l5:s0-0':'다이클로로메테인을 넣어 평형까지 세게 흔든 뒤, 두 상을 분리했다.',
'p27:b10:l7:s0-0:c76-80':'을 녹여 총 ',
'p27:b10:l7:s0-0:c87-101':'로 만듦)으로 적정했다.',
},
28:{
'p28:b4:l0:s3-3':' 도식의 각 단계(',
'p28:b4:l0:s7-7':')에 대응하는',
'p28:b4:l1:s0-0':'개략도를(기호: ',
'p28:b6:l0:s3-3':' 적정 중 수용액상에서 아이오딘 화학종과 티오황산 나트륨',
'p28:b6:l1:s0-0':'사이에 일어날 수 있는 두 반응의 균형 반응식을.',
},
29:{},
30:{
'p30:b7:l0:s0-0:c10-25':': 아조벤젠–',
'p30:b7:l0:s0-0:c26-54':'-사이클로덱스트린:',
'p30:b7:l1:s0-0':'나노 기계 형성을 위한 착물',
'p30:b9:l0:s13-13':'연결선을.',
'p30:b9:l1:s0-0':'연결선은 서로 가장 먼 두 탄소 원자를 잇는다. ',
'p30:b16:l0:s0-0:c6-49':' – 다음 화합물의 합성 반응물 후보: ',
'p30:b17:l0:s3-3:c0-61':'는 간단한 반응물로부터 두 단계로 합성할 수 있다(그림 ',
'p30:b17:l1:s4-4':') 중 생성물 ',
'p30:b17:l1:s6-6':'을 매우 높은 위치 선택성으로 주는 것들을. 첫 단계의 시약은',
'p30:b17:l2:s2-2':'), 즉 아질산 나트륨이며, 차가운 염산 수용액에서 사용한다.',
},
31:{
'p31:b3:l0:s0-0':'회합 상수 결정: ',
'p31:b4:l2:s0-0:c35-96':'에서는 분광법으로 회합 상수 ',
'p31:b4:l3:s0-0:c0-56':'를 구한다. 이는 포접 착물 ',
'p31:b4:l3:s2-2:c0-21':'의 형성에 해당한다(그림 ',
'p31:b4:l3:s2-2:c22-24':').',
'p31:b5:l1:s0-0:c6-26':' – ',
'p31:b5:l1:s4-4':'포접 착물의 형성.',
'p31:b6:l1:s0-0':'농도는 [',
'p31:b6:l1:s9-9':'이다. [',
'p31:b6:l1:s14-14':'는 모든 용액에서 같고, [',
'p31:b6:l1:s18-18':'는 달리한다.',
'p31:b6:l2:s0-0':'고정 파장에서 흡광도 차이 ',
'p31:b6:l3:s3-3':'용액의 흡광도 차이이다. 다음 물질들의 몰 흡수 계수를,',
'p31:b6:l4:s11-11':'은 시료를 지나는 빛의 경로 길이이다.',
'p31:b6:l5:s0-0':'흡광도를 무시할 수 있는 물질은 ',
'p31:b6:l5:s5-5':')이다.',
'p31:b7:l0:s10-10':']임을. 또 ',
'p31:b7:l0:s14-14':'를 알려진 상수들로.',
}}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def apply():
    OUT.mkdir(exist_ok=True)
    report_path=OUT/'text-review-report.json'
    assert not report_path.exists(),'Already handed off; do not overwrite another author edits.'
    rows=[]
    for n,edits in NEW_TEXT.items():
        override=B/f'page{n:02}.overrides.json'
        original=json.loads(override.read_text('utf8'))
        plan_path=MANUSCRIPTS/f'page{n:02}.ko.json'
        plan=json.loads(plan_path.read_text('utf8'))
        slots={s['id']:s for s in plan['slots']+original.get('__extra_slots__',[])}
        snapshots={}
        for label,path in {'override':override,'plan':plan_path,'profile':B/'source-profile'/f'page{n:02}.json','source_png':B/'source-review'/f'page{n:02}.png'}.items():
            target=OUT/'originals'/f'page{n:02}'/path.name
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert sha(target)==sha(path)
            else:shutil.copy2(path,target)
            assert sha(path)==sha(target)
            snapshots[label]={'path':str(path),'copy':str(target),'sha256':sha(path)}
        updated=json.loads(json.dumps(original))
        changes=[]
        for key,text in edits.items():
            assert key in slots,key
            effective=dict(slots[key],**original.get('__slot_edits__',{}).get(key,{}))
            assert not effective.get('skip'),key
            assert text and isinstance(text,str)
            previous=effective.get('text')
            changes.append({'id':key,'source':slots[key]['source'],'before':previous,'after':text,'baseline':slots[key]['point'][1],'point_size':slots[key]['size']})
            updated.setdefault('__slot_edits__',{}).setdefault(key,{})['text']=text
        assert {k:v for k,v in updated.items()if k!='__slot_edits__'}=={k:v for k,v in original.items()if k!='__slot_edits__'}
        assert all(updated['__slot_edits__'][key]==value for key,value in original.get('__slot_edits__',{}).items()if key not in edits)
        if edits:override.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n','utf8')
        else:assert sha(override)==snapshots['override']['sha256']
        rows.append({'page':n,'snapshots':snapshots,'override_sha256':sha(override),'changes':changes,'other_override_keys_unchanged':True,'composition_pending':True})
    report={'status':'SOURCE_REVIEWED_TEXT_HANDOFF_COMPOSITION_AND_VISUAL_QA_PENDING','program_sha256':sha(Path(__file__)),'source_sha256':'5821bab3b65b216cc74df99d7ec643389d212c15b4d88c95a7da22de8baf97d8','pages':rows,'notes':['27 solution mass/volume phrased as final total solution volume, preserving original values and units.','28 stage/picture matching and both possible reactions retained.','29 short existing question reviewed without modifying its override.','30 title uses the original two baselines, same chemical names and purpose; source-native beta and formula remain untouched.','31 fixed wavelength moved to the following original prose baseline; all concentrations, constants and species remain in source order.','Every original underlined action word remains unchanged.','Caption alignment and scientific punctuation cuts are owned by the main 2019 compositor agent.']}
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print('TEXT_EDITS_APPLIED',len([n for n,v in NEW_TEXT.items()if v]),sum(len(v)for v in NEW_TEXT.values()),sha(report_path),flush=True)

if __name__=='__main__':apply()
