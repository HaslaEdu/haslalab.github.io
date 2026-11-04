from pathlib import Path
import pikepdf,pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory/natural/2017/T')
for path in [B/'page03.old-source.pdf',B/'page03.pdf']:
 print('\nPDF',path.name)
 with fitz.open(path)as doc:print('MUPDF',[(r['xref'],r['width'],r['height'],r['bbox'])for r in doc[0].get_image_info(xrefs=True)])
 with pikepdf.open(path)as doc:
  def walk(node,res,path=()):
   for i,o in enumerate(pikepdf.parse_content_stream(node)):
    op=str(o.operator)
    if op=='Do':
     v=res.XObject[o.operands[0]];t=str(v.get('/Subtype'))
     if t=='/Image':print('DO',path+(i,),v.objgen,v.Width,v.Height)
     elif t=='/Form':walk(v,v.get('/Resources',res),path+(i,))
    elif op=='INLINE IMAGE':print('INLINE',path+(i,),repr(o)[:300])
  walk(doc.pages[0],doc.pages[0].Resources)
