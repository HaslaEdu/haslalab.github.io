"""Preserve actual v1 PDFs/controls/renderings and recover exact producing plan.

This first review predated immutable per-language compiled inputs. Match the
original actual plan SHA before any archival/removal; never invent a history.
"""
from pathlib import Path
import json,hashlib,shutil
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page01-native-language.json').read_text('utf8'))
reports={lang:json.loads((B/f'proofs/{lang}/page01.composition.json').read_text('utf8'))for lang in('ko','en')}
for lang,report in reports.items():
 text={r['id']:r['translated_text']for r in report['placements']}
 for row in q['rows']:row[lang]=text[row['id']]
text=json.dumps(q,ensure_ascii=False,indent=2)+'\n'
if b'\r\n'in(A/'page01-native-language.json').read_bytes():text=text.replace('\n','\r\n')
raw=text.encode('utf8');digest=hashlib.sha256(raw).hexdigest();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(r['plan_sha256']==digest for r in reports.values()),(digest,[r['plan_sha256']for r in reports.values()])
H=B/'history/page01-review-v1';H.mkdir(parents=True,exist_ok=False);(H/f'exact-producing-bilingual-plan-{digest}.json').write_bytes(raw);records=[]
for lang in('ko','en'):
 proof=B/f'proofs/{lang}/page01.pdf';assert sha(proof)==reports[lang]['output_sha256']
 for p in sorted((B/f'proofs/{lang}').glob('page01.*')):
  assert p.resolve().is_relative_to(B.resolve())and p.is_file();dest=H/lang/p.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(p,dest);assert sha(p)==sha(dest);records.append(dict(path=str(dest),sha256=sha(dest),bytes=dest.stat().st_size));p.unlink()
 for p in sorted((B/'inspection').glob(f'page01-{lang}-current144.*')):
  dest=H/lang/p.name;shutil.copy2(p,dest);assert sha(p)==sha(dest);records.append(dict(path=str(dest),sha256=sha(dest),bytes=dest.stat().st_size));p.unlink()
(H/'history.json').write_text(json.dumps(dict(reason='Original full-page source/current review found English grammar/semantic wording refinements. KO visually sound, both v1 proofs preserved before rebuilding with immutable language-specific input snapshots.',actual_producing_plan_sha256=digest,original_source_unchanged=True,files=records),ensure_ascii=False,indent=2)+'\n','utf8');print('ACTUAL_V1_REVIEW_PDFS_AND_EXACT_PRODUCING_PLAN_PRESERVED',digest)
