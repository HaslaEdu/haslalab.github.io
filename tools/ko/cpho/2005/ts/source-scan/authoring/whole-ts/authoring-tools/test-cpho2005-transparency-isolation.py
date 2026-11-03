from pathlib import Path
import pikepdf,subprocess,sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
source=B/'proofs/en/page04.pdf'
for variant in ['atom-isolation','page-isolation','overlay-isolation']:
 target=B/f'proofs/en/page04.{variant}.pdf'
 with pikepdf.open(source)as d:
  p=d.pages[0]
  group=pikepdf.Dictionary(S=pikepdf.Name.Transparency,I=True,K=False,CS=pikepdf.Name.DeviceRGB)
  if variant=='atom-isolation':
   for name,x in p.Resources.XObject.items():
    if str(name).startswith('/IndependentNativeImageInstance'):x.Group=group
  elif variant=='page-isolation':p.obj.Group=group
  else:
   streams=list(p.Contents);mark=next(i for i,s in enumerate(streams)if b'/IndependentNativeImageInstance'in s.read_bytes())
   # The replay stream starts Q, closing the q which surrounds all old content.
   # Keep that closing state token on the original page before isolating the
   # newly introduced mathematical/prose overlay. Original source paint intact.
   assert streams[mark].read_bytes().startswith(b'Q\n')
   overlay=d.make_stream(streams[mark].read_bytes()[2:]+b'\n'+b'\n'.join(s.read_bytes()for s in streams[mark+1:]));overlay.Type=pikepdf.Name.XObject;overlay.Subtype=pikepdf.Name.Form;overlay.FormType=1;overlay.BBox=pikepdf.Array(p.MediaBox);overlay.Resources=pikepdf.Dictionary(p.Resources);overlay.Group=group
   resources=pikepdf.Dictionary(p.Resources);resources.XObject=pikepdf.Dictionary(p.Resources.XObject);resources.XObject.IsolatedTranslationOverlay=overlay;p.Resources=resources
   p.Contents=pikepdf.Array([*streams[:mark],d.make_stream(b'Q\nq\n/IsolatedTranslationOverlay Do\nQ\n')])
  d.save(target,compress_streams=False)
 outfile=B/f'source-renders/page04-caption-en-{variant}.png'
 code="import pymupdf as f;d=f.open("+repr(str(target))+");p=d[0];p.get_pixmap(matrix=f.Matrix(6,6),clip=f.Rect(435,157,665,177),alpha=False).save("+repr(str(outfile))+")"
 r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True);print(variant,r.returncode,r.stderr,flush=True)
