from pathlib import Path
import sys,json,shutil,hashlib
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'));F=B/'natural/2011/TS'
from izho_2011_complete_inline_fractions import apply_reviewed_fractions,audit
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n in[4,8]:
 plan=F/f'plans/page{n:02}.json';proof=F/f'page{n:02}.pdf';out=F/'negative-glyph-only-fraction-motion'/str(n);out.mkdir(parents=True,exist_ok=True)
 if not(out/proof.name).exists():
  for suffix in['.pdf','.qa.json','.audit.json','.source-alignment.json','.font-source-style.json']:shutil.copy2(proof.with_suffix(suffix),out/(proof.stem+suffix))
  shutil.copy2(plan,out/'original-plan.json')
 d=json.loads(plan.read_text('utf8'));apply_reviewed_fractions(d);plan.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
 bad=out/proof.name;q=audit(plan,final_override=bad,report_override=out/'actual-missing-common-fraction-rule-motion.json');assert not q['passed']and any(not r['passed']for r in q['groups']);print('REAL_GLYPH_ONLY_FRACTION_MOTION_NEGATIVE_REJECTED',n,sha(bad),q['original_fraction_rules_checked'],flush=True)
