from pathlib import Path
import subprocess,sys,os,hashlib,json
import pikepdf
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory');f=B/'natural/2017/T';folder=B/'2017/source-native-witness-regressions';folder.mkdir(exist_ok=True)
target=folder/'actual-native-glyph-white-cover.pdf';source=f/'page01.pdf';digest=hashlib.sha256(source.read_bytes()).hexdigest()
with pikepdf.open(source)as doc:
 p=doc.pages[0];h=float(p.MediaBox[3])-float(p.MediaBox[1]);old=list(p.Contents)if isinstance(p.Contents,pikepdf.Array)else[p.Contents]
 p.Contents=pikepdf.Array([*old,doc.make_stream(('q 1 g 286 %.8f 12 14 re f Q\n'%(h-388)).encode('ascii'))]);doc.save(target,compress_streams=False)
with (folder/'negative.log').open('w',encoding='utf8')as log:r=subprocess.run([sys.executable,'-u',str(B/'witness_2017_T_page1_all_native.py'),str(target)],stdout=log,stderr=subprocess.STDOUT)
text=(folder/'negative.log').read_text('utf8');assert r.returncode!=0 and 'assert missing==0'in text
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
report=dict(source_proof_sha256=digest,analysis_only_negative_pdf=str(target),negative_returncode=r.returncode,original_native_metadata_unchanged_but_white_cover_rejected=True,publication_pdf_unmodified=True,passed=True)
(folder/'regression.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print('PASS: actual original-font CID pixels reject white cover after font/GID/point/paint checks.')
