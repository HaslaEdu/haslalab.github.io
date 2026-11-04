"""Source-direct scan QA and independent Poppler for one authored C03 TS page."""
from pathlib import Path
import sys,json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
T=B/'TS'
sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
from cpho_2003_ts_qa import audit
from cpho_2003_ts_poppler_qa import audit as poppler
number=int(sys.argv[1]);languages=sys.argv[2:]or['en','ko']
assert number in range(4,11)and all(x in ['en','ko']for x in languages)
for lang in languages:
 with page_worker():q=audit(number,lang)
 if not q['passed']:raise SystemExit('Source QA failed '+lang)
 with page_worker():q=poppler(number,lang)
 if not q['passed']:raise SystemExit('Poppler QA failed '+lang)
print('CPHO2003_TS_SOURCE_AND_POPPLER_PASS',number,languages,flush=True)
