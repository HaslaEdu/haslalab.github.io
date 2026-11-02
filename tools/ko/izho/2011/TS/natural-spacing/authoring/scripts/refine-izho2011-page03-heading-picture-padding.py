from pathlib import Path
import sys,json,shutil,hashlib
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from izho_2011_picture_layout import apply_reviewed_layout
F=B/'natural/2011/TS';P=F/'plans/page03.json';out=F/'negative-heading-omitted-native-tokens';out.mkdir(exist_ok=True)
if not(out/'page03.pdf').exists():
 assert hashlib.sha256((F/'page03.pdf').read_bytes()).hexdigest()=='3b0ad41041cae3574f67255f1554357137a3628acf436cba4db25f41c321d817'
 for suffix in['.pdf','.qa.json','.audit.json','.source-alignment.json']:shutil.copy2((F/'page03.pdf').with_suffix(suffix),out/('page03'+suffix))
 shutil.copy2(P,out/'page03-plan.json')
 q=json.loads((out/'page03.qa.json').read_text('utf8'));row=next(r for r in q['lines']if abs(r['baseline']-84.84)<.02);assert not row['gaps']
 (out/'negative-control.json').write_text(json.dumps(dict(proof_sha256='3b0ad41041cae3574f67255f1554357137a3628acf436cba4db25f41c321d817',rejected=True,reason='Visual comparison shows overlap/gap in the mixed original-native/Korean1C(2.5points) heading. Its line journal has zero native-to-Korean and Korean-to-closing-parenthesis boundaries. Final validation requires both exact zero-gap boundaries; source bitmap white-padding metadata is measured independently and full picture pixel QA remains unchanged.',mixed_heading_required_boundary_count=2,actual_boundary_count=0,passed=True),indent=2)+'\n','utf8')
d=json.loads(P.read_text('utf8'));apply_reviewed_layout(d);P.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('EXACT_SOURCE_WHITE_BITMAP_PADDING_REVIEWED',d['reviewed_original_picture_white_padding']['measured_top_white_padding_pt'])
