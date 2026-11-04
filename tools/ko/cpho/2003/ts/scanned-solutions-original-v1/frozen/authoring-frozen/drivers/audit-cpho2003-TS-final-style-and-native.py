from pathlib import Path
import sys
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
from cpho2003_ts_actual_donor_style import audit as style
from cpho2003_ts_native_ink import audit as native
for n in [int(v)for v in sys.argv[1:]]or list(range(4,11)):
 for lang in ['ko','en']:
  with page_worker():
   reference=T/f'proofs/{lang}/page{n:02}.pdf'
   style(n,lang,output_override=reference.with_suffix('.final-actual-donor-style.json'))
   native(n,lang)
