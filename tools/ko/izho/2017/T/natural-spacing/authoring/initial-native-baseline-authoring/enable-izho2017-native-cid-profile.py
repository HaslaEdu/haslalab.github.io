from pathlib import Path
import json
p=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory/natural/2017/T/plans/page01.json');q=json.loads(p.read_text('utf8'));q['native_ink_witness']='all-original-CID-witness/witness.json';q['native_ink_witness_profile']='2017-T1-all-original-CIDs';p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('Pinned all96 original source CIDs as the independent native-font reference; raw SVG diagnostic retained.')
