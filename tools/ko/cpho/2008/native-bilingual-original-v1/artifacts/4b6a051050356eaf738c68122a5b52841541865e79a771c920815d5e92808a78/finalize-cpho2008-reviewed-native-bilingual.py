"""Native append only after all current source/proof checks and full visual read."""
from pathlib import Path
import sys,json,hashlib,subprocess
import pikepdf,pymupdf as f,numpy as np
from PIL import Image
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from cpho2008_atomic_authoring import atomic_text
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))
S=B/'source/CPhO_2008_original_combined_ZH.pdf';SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d'
POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
assert sha(S)==SHA
visual=read(B/'inspection/current-full-page-visual-review.json');assert visual['all42_current_pages_approved']and len(visual['pages'])==42
v={(r['source_page'],r['language']):r for r in visual['pages']}
checks=['independent-native-audit','original-encoded-CID-states','new-prose-style-spacing-visibility','kept-ink-collision']
for n in range(1,22):
    for lang in ('ko','en'):
        pdf=B/f'proofs/{lang}/page{n:02}.pdf';pin=sha(pdf);assert v[n,lang]['proof_sha256']==pin
        for kind in checks:
            q=read(pdf.with_suffix('.'+kind+'.json'));assert q['passed']and q['proof_sha256']==pin,(n,lang,kind)
outdir=B/'editions';outdir.mkdir(exist_ok=True);results=[]
for kind,pages in [('T',list(range(1,7))),('TS',list(range(7,22)))]:
    for lang in ('ko','en'):
        target=outdir/f'CPhO_2008_{kind}_{lang.upper()}.pdf';manifest=target.with_suffix('.native-append.json')
        inputs=[dict(source_page=n,path=str(B/f'proofs/{lang}/page{n:02}.pdf'),sha256=sha(B/f'proofs/{lang}/page{n:02}.pdf'))for n in pages]
        if target.exists():
            previous=read(manifest);assert previous['proof_inputs']==inputs and previous['final_pdf_sha256']==sha(target)
        else:
            with page_worker(),pikepdf.Pdf.new()as final:
                for item in inputs:
                    with pikepdf.open(item['path'])as proof:assert len(proof.pages)==1;final.pages.append(proof.pages[0])
                final.save(target,compress_streams=False)
            atomic_text(manifest,json.dumps(dict(original_source_sha256=SHA,kind=kind,language=lang,proof_inputs=inputs,final_pdf_sha256=sha(target),bytes=target.stat().st_size,append_changed_no_original_page_design=True),indent=2)+'\n')
        proof_rows=[]
        for index,item in enumerate(inputs):
            with page_worker():
                with f.open(target)as doc,f.open(item['path'])as proof:
                    a=doc[index].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);b=proof[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False)
                    aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,3);native=int(np.any(aa!=bb,2).sum())
                prefix=outdir/f'.final-{kind}-{lang}-page{index+1:02}'
                subprocess.run([POP,'-f',str(index+1),'-l',str(index+1),'-singlefile','-r','144','-png',str(target),str(prefix)],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                generated=prefix.with_suffix('.png');prior=B/f"inspection/page{item['source_page']:02}-{lang}-current144.png"
                aa=np.array(Image.open(generated).convert('RGB'));bb=np.array(Image.open(prior).convert('RGB'));poppler=int(np.any(aa!=bb,2).sum());assert native==poppler==0,(kind,lang,index,native,poppler)
                witness=dict(source_page=item['source_page'],final_page=index+1,proof_sha256=item['sha256'],native_MuPDF4x_changed_RGB_pixels=native,independent_Poppler144_changed_RGB_pixels=poppler,actual_final_Poppler_png_sha256=sha(generated),actual_reviewed_proof_Poppler_png_sha256=sha(prior))
                # Reproducible temporary identical final preview; the reviewed
                # proof PNG and both SHA pins remain immutable evidence.
                assert generated.resolve().parent==outdir.resolve();generated.unlink()
                proof_rows.append(witness);print('C08_FINAL_NATIVE_APPEND_ZERO_RGB',kind,lang,index+1,flush=True)
        report=dict(original_source_sha256=SHA,final_pdf_path=str(target),final_pdf_sha256=sha(target),kind=kind,language=lang,pages=proof_rows,passed=all(r['native_MuPDF4x_changed_RGB_pixels']==r['independent_Poppler144_changed_RGB_pixels']==0 for r in proof_rows))
        atomic_text(target.with_suffix('.final-render-zero-RGB.json'),json.dumps(report,indent=2)+'\n');results.append(report)
atomic_text(outdir/'all4-native-append-render-checks.json',json.dumps(dict(original_source_sha256=SHA,editions=results,passed=all(r['passed']for r in results)),indent=2)+'\n')
