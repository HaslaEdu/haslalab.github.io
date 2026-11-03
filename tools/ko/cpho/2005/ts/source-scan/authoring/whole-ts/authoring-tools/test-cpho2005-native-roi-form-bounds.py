from pathlib import Path
import pikepdf,json
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
for lang in ['ko','en']:
 plan=json.loads((B/'authoring/page04-layout.json').read_text('utf8'));atoms=[a for r in plan['rows']for a in r['atoms']]
 source=B/f'proofs/{lang}/page04.pdf';target=B/f'proofs/{lang}/page04.roi-form-bounds.pdf'
 with pikepdf.open(source) as d:
  p=d.pages[0];height=595.3200073242188
  for i,a in enumerate(atoms):
   x0,y0,x1,y1=a['rect'];p.Resources.XObject['/IndependentNativeImageInstance'+str(i+1)].BBox=pikepdf.Array([x0,height-y1,x1,height-y0])
  d.save(target,compress_streams=False)
 with f.open(target) as d:
  d[0].get_pixmap(matrix=f.Matrix(2,2),alpha=False).save(B/f'proofs/{lang}/page04-roi-form-bounds-preview.png')
  d[0].get_pixmap(matrix=f.Matrix(6,6),clip=f.Rect(435,157,665,177),alpha=False).save(B/f'source-renders/page04-caption-{lang}-roi-form-bounds.png')
 print(lang,target,flush=True)
