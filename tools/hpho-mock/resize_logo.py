"""Re-fits the HPhO logo on PDFs that relogo.py already processed (after a change to hpho_pdf.logo).
  python3 -I tools/hpho-mock/resize_logo.py FILE.pdf ..."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pymupdf
from hpho_pdf import logo
for f in sys.argv[1:]:
    doc = pymupdf.open(f)
    n = sum(1 for page in doc if logo(page))
    doc.save(f + '.tmp', garbage=3, deflate=True); doc.close()
    Path(f + '.tmp').replace(f)
    print(f, n, 'pages')
