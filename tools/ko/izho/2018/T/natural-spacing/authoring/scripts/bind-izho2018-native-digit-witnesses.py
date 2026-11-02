from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original/natural/2018/T')
for n in [3,4]:
 p=B/f'plans/page{n:02}.json';j=json.loads(p.read_text('utf8'))
 j.update(native_ink_witness_profile='2018-original-native-Cambria-digit-phase-v1',native_ink_witness=f'page{n:02}-native-digit-phase/witness.json')
 p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
 print('BOUND_REVIEWED_SOURCE_CID_WITNESS_WITHOUT_PDF_MODIFICATION',n)
