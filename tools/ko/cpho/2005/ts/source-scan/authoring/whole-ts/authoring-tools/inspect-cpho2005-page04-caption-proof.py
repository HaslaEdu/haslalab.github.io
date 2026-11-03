from pathlib import Path
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
for name,src,pageno in [('source',B/'inputs/CPhO_2005_Chinese_original.pdf',3),('en-before-prose',B/'proofs/en/page04.pre-prose.pdf',0),('en-final',B/'proofs/en/page04.pdf',0),('ko-final',B/'proofs/ko/page04.pdf',0)]:
 with f.open(src)as d:
  pix=d[pageno].get_pixmap(matrix=f.Matrix(6,6),clip=f.Rect(435,157,665,177),alpha=False)
  pix.save(B/f'source-renders/page04-caption-check-{name}.png')
