from pathlib import Path
import shutil,json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native').resolve();archive=B/'proof-history/en-all-before-font-identity-isolation';assert not archive.exists();archive.mkdir(parents=True)
bad=B/'natural/2003/en/page02.pdf';negative=B/'evidence/negative-controls/actual-Poppler-native-math-loss-before-font-isolation.pdf';negative.parent.mkdir(parents=True,exist_ok=True);assert not negative.exists();shutil.copy2(bad,negative)
assert hashlib.sha256(negative.read_bytes()).hexdigest()=='a0a17d84a27d7af494ba3ff8def3cbb8752adc462d3319de46dac56e03699206'
for rel in ['natural/2003/en','native-baseline/en','initial-fixed-slot-staging/en','proof-renders-144/en']:
 source=(B/rel).resolve();target=(archive/rel).resolve();assert source.is_relative_to(B)and target.is_relative_to(archive.resolve())and source.exists()and not target.exists();target.parent.mkdir(parents=True,exist_ok=True);source.rename(target)
(archive/'reason.json').write_text(json.dumps(dict(reason='Actual native glyph metadata and MuPDF were intact, but Poppler dropped original native display/inline math when old/new font identities overlapped. Preserve all passing preliminary reports and all failed-render proofs; no READY was issued. New prose font name tables alone will be isolated; source fonts/math programs and every source point/paint remain unchanged.',actual_negative_pdf=str(negative),sha256=hashlib.sha256(negative.read_bytes()).hexdigest()),ensure_ascii=False,indent=2)+'\n','utf8')
