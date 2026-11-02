from pathlib import Path
import sys,json,shutil,hashlib
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'));F=B/'natural/2011/TS'
from izho_2011_equation_counters import apply_reviewed_counters,audit
P=F/'plans/page04.json';proof=F/'page04.pdf';out=F/'negative-display-equation-counter-drift';out.mkdir(exist_ok=True)
if not(out/'page04.pdf').exists():
 assert hashlib.sha256(proof.read_bytes()).hexdigest()=='aec6e4a5fa56a9731b552d981fcd57aadf3e53ab08f1f216c86bb994dd16c5ce'
 for suffix in['.pdf','.qa.json','.audit.json','.inline-fractions.json','.equation-counters.json']:shutil.copy2(proof.with_suffix(suffix),out/('page04'+suffix))
 shutil.copy2(P,out/'original-plan.json')
d=json.loads(P.read_text('utf8'));apply_reviewed_counters(d);P.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');q=audit(P,final_override=out/'page04.pdf',report_override=out/'actual-source-counter-drift-negative.json');assert not q['passed'];bad=[r for r in q['rows']if not r['passed']];assert len(bad)==1 and bad[0]['number']==3;print('ACTUAL_ORIGINAL_DISPLAY_COUNTER_DRIFT_NEGATIVE_REJECTED',bad[0]['number'],[r['source_x_difference']for r in bad[0]['font_gid_point_x_y_and_paint_errors']],flush=True)
