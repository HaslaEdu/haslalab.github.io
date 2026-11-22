"""The author's paper with the HPhO header and nothing else changed (see hpho_pdf.py).

  python3 -I tools/hpho-mock/relogo.py IN.pdf OUT.pdf [first-last] [--lang ko|en]

An optional page range (1-based, inclusive) keeps only those pages, to split a combined paper into its problem pages,
answer sheet and writing sheets."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pymupdf
from hpho_pdf import logo, header

args = [a for a in sys.argv[1:]]
lang = 'ko'
if '--lang' in args:
    i = args.index('--lang'); lang = args[i + 1]; del args[i:i + 2]
src, out = args[0], args[1]
doc = pymupdf.open(src)
if len(args) > 2:
    a, b = map(int, args[2].split('-'))
    doc.select(list(range(a - 1, b)))
missing = []
for page in doc:
    if not logo(page):
        missing.append(page.number + 1)
    header(page, lang)
if missing:
    sys.exit(f'no logo found on pages {missing}')
doc.save(out, garbage=3, deflate=True)
print(out, len(doc))
