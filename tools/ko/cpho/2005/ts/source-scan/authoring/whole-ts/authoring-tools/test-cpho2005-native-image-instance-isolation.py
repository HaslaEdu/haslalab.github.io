from pathlib import Path
import pikepdf,re
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
source=B/'proofs/en/page04.pdf';target=B/'proofs/en/page04.unique-native-instances.pdf'
with pikepdf.open(source) as d:
 p=d.pages[0];count=0
 for content in p.Contents:
  raw=content.read_bytes()
  if b'/OriginalRasterMath'not in raw:continue
  def replace(m):
   global count
   count+=1;old=p.Resources.XObject[m[1].decode()]
   clone=d.make_stream(old.read_bytes())
   for k,v in old.items():
    if str(k)not in ['/Length','/Filter','/DecodeParms','/Resources']:clone[k]=v
   resources=pikepdf.Dictionary(old.Resources);images=pikepdf.Dictionary()
   for alias,image in old.Resources.XObject.items():
    im=d.make_stream(image.read_raw_bytes())
    for k,v in image.items():
     if str(k)!='/Length':im[k]=v
    images[alias]=im
   resources.XObject=images;clone.Resources=resources
   name='/IndependentNativeImageInstance'+str(count);p.Resources.XObject[name]=clone
   return (name+' Do').encode()
  content.write(re.sub(rb'(/OriginalRasterMath\d+) Do',replace,raw))
 d.save(target,compress_streams=False)
print('EXACT_SOURCE_NATIVE_IMAGE_COPIES',count,flush=True)
with f.open(target) as d:
 d[0].get_pixmap(matrix=f.Matrix(6,6),clip=f.Rect(435,157,665,177),alpha=False).save(B/'source-renders/page04-caption-en-unique-native.png')
