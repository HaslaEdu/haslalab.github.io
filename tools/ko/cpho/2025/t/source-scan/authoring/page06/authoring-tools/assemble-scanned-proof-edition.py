"""Append reviewed PDF pages; verify unchanged rendering and actual programs."""
from pathlib import Path
import sys,json,hashlib,subprocess,time
from collections import Counter
import numpy as np,pikepdf,pymupdf as fitz
sys.path[:0]=['D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools','D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
import pdf_original_raster_math as raster
from pdf_original_style_audit import glyphs,key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def png_array(p):
 from PIL import Image
 return np.asarray(Image.open(p).convert('RGB'))

def build(spec_path):
 spec=json.loads(Path(spec_path).read_text('utf8'));output=Path(spec['output']);output.parent.mkdir(parents=True,exist_ok=True)
 for row in spec['proofs']:assert sha(row['pdf'])==row['sha256']
 with pikepdf.Pdf.new()as final:
  for row in spec['proofs']:
   with pikepdf.open(row['pdf'])as proof:
    assert len(proof.pages)==1;final.pages.append(proof.pages[0])
  final.save(output,compress_streams=False)
 report=dict(output=str(output),sha256=sha(output),bytes=output.stat().st_size,pages=[],passed=True,renderers=['MuPDF4xRGB','Poppler144dpiRGB'])
 renderdir=output.parent/(output.stem+'-assembly-render');renderdir.mkdir(exist_ok=True)
 for number,row in enumerate(spec['proofs'],1):
  with page_worker(),fitz.open(output)as joined,fitz.open(row['pdf'])as proof:
   a=proof[0];b=joined[number-1];pa=a.get_pixmap(matrix=fitz.Matrix(4,4),alpha=False);pb=b.get_pixmap(matrix=fitz.Matrix(4,4),alpha=False)
   assert(pa.width,pa.height)==(pb.width,pb.height)
   mu=int(np.any(np.frombuffer(pa.samples,np.uint8).reshape(pa.height,pa.width,3)!=np.frombuffer(pb.samples,np.uint8).reshape(pb.height,pb.width,3),axis=2).sum())
   del pa,pb
   metadata=Counter(key(g)for g in glyphs(a))==Counter(key(g)for g in glyphs(b))
   with pikepdf.open(row['pdf'])as ap,pikepdf.open(output)as bp:
    aa=ap.pages[0];bb=bp.pages[number-1]
    fonts=raster.program(aa.Resources.get('/Font'))==raster.program(bb.Resources.get('/Font'))
    # Only memoize repeated references within each PDF. Clear between files so
    # unrelated objects with matching xref numbers can never share a digest.
    original=raster.program_sha
    def instances(page):
     cache={}
     def cached(obj):
      ident=obj.objgen
      if ident==(0,0):return original(obj)
      if ident not in cache:cache[ident]=original(obj)
      return cache[ident]
     raster.program_sha=cached
     try:return raster.original_image_instances(page,page.Resources)
     finally:raster.program_sha=original
    images=instances(aa)==instances(bb)
    group=raster.program(aa.obj.get('/Group'))==raster.program(bb.obj.get('/Group'))
   left=renderdir/f'page{number:02d}-proof';right=renderdir/f'page{number:02d}-joined'
   for source,page,prefix in [(row['pdf'],1,left),(str(output),number,right)]:
    subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-r','144','-singlefile','-png',source,str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
   ppa=png_array(str(left)+'.png');ppb=png_array(str(right)+'.png');assert ppa.shape==ppb.shape;pop=int(np.any(ppa!=ppb,axis=2).sum());del ppa,ppb
   result=dict(page=number,source_page=row['source_page'],proof_sha256=row['sha256'],mupdf_4x_changed_pixels=mu,poppler_144dpi_changed_pixels=pop,actual_font_programs_and_glyph_metadata_identical=bool(fonts and metadata),original_encoded_images_masks_icc_and_ctms_identical=bool(images),page_group_identical=bool(group))
   result['passed']=mu==pop==0 and all([metadata,fonts,images,group]);report['pages'].append(result);report['passed'] &= result['passed']
   print(json.dumps(result),flush=True)
  time.sleep(.6)
 target=output.with_suffix('.assembly-qa.json');target.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');assert report['passed'];return report

if __name__=='__main__':build(sys.argv[1])
