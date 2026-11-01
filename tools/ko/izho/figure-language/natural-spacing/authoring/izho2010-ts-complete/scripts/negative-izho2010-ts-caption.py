from pathlib import Path
import sys,json
import pikepdf
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');C=B/'figure-language';sys.path[:0]=[str(C/'engine'),str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from audit_figure_labels import audit
from pdf_memory_gate import page_worker
source=C/'2010/TS/page04.pdf';folder=C/'analysis-only-negative';folder.mkdir(exist_ok=True);negative=folder/'page04-extra-ink.pdf';report=folder/'page04-extra-ink.audit.json'
with pikepdf.open(source)as doc:
 page=doc.pages[0];h=float(page.MediaBox[3])-float(page.MediaBox[1]);contents=page.Contents;values=list(contents)if isinstance(contents,pikepdf.Array)else[contents];page.Contents=pikepdf.Array(values+[pikepdf.Stream(doc,('q 0 0 0 rg 30 %.9f 1 1 re f Q\n'%(h-31)).encode('ascii'))]);doc.save(negative,compress_streams=False)
with page_worker():
 try:audit(2010,4,analysis_target=negative,analysis_report=report)
 except ValueError:
  q=json.loads(report.read_text('utf8'));assert not q['passed']and q['pixel_audit']['added_ink_outside_independent_actual_font_reference']==16 and q['original_native_ink']['passed'];print('REAL_EXTRA_INK_NEGATIVE_REJECTED',q['pixel_audit'])
 else:raise AssertionError('A real extra black rectangle was not rejected')
