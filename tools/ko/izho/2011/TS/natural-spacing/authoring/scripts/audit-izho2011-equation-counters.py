from pathlib import Path
import sys
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from izho_2011_equation_counters import audit
pages=list(map(int,[s for s in sys.argv[1:]if not s.startswith('--')]))or range(1,11);failed=[]
for n in pages:
 q=audit(B/f'natural/2011/TS/plans/page{n:02}.json');bad=[(r['number'],[round(e['source_x_difference'],5)if e['source_x_difference']is not None else None for e in r['font_gid_point_x_y_and_paint_errors']])for r in q['rows']if not r['passed']];print('ORIGINAL_NATIVE_EQUATION_COUNTERS',n,q['equation_counters_checked'],q['passed'],bad,flush=True)
 if not q['passed']:failed.append(n)
if failed and'--allow-fail'not in sys.argv:raise SystemExit(1)
