"""Join audited original-style pages using the original shared PDF resources."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re
import numpy as np
import pikepdf
import pymupdf as fitz
import cpho_2023_original_style as b
from pdf_original_style_audit import glyphs,key

AUTHOR=b.ROOT/'tools/ko/cpho/2023/original'
FINAL=b.OUT/'editions'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def join(lang,output_dir=None):
    destination=Path(output_dir)if output_dir is not None else FINAL
    AUTHOR.mkdir(parents=True,exist_ok=True);destination.mkdir(parents=True,exist_ok=True)
    target=destination/f'CPhO_2023_Combined_{lang.upper()}.pdf'
    records=[]
    # Keep the original document's shared font/image/Form objects. Copying 36
    # separate page PDFs duplicates their identical source font programs.
    # Only the reviewed page content streams and new prose fonts are imported.
    with pikepdf.open(b.SOURCE)as out:
        assert len(out.pages)==36
        for number,page in enumerate(out.pages,1):
            proof=b.OUT/f'CPhO_2023_p{number}_{lang.upper()}_proof.pdf'
            q=json.loads(proof.with_suffix('.qa.json').read_text('utf8'))
            assert q['passed']and q['proof_sha256']==sha(proof)
            with pikepdf.open(proof)as doc:
                p=doc.pages[0]
                resources=pikepdf.Dictionary(page.Resources)
                fonts=pikepdf.Dictionary(resources.get('/Font',{}))
                for alias,font in p.Resources.Font.items():
                    if str(alias).startswith(('/Translation','/FigureLanguage')):
                        fonts[alias]=out.copy_foreign(font)
                    else:assert alias in fonts,'Original font alias changed'
                resources.Font=fonts;page.Resources=resources
                streams=list(p.Contents)if isinstance(p.Contents,pikepdf.Array)else[p.Contents]
                page.Contents=pikepdf.Array([out.copy_foreign(s)for s in streams])
            records.append(q)
        out.save(target,compress_streams=False)
    report=dict(source_sha256=sha(b.SOURCE),file=target.name,sha256=sha(target),bytes=target.stat().st_size,pages=36,
        original_page_order=True,original_shared_resources_retained=True,no_autoshrink=True,no_reflow=True,no_equation_rasterization=True,
        redrawn_figures=0,printed_editorial_notes=0,page_audits=[],passed=True)
    source=fitz.open(b.SOURCE);final=fitz.open(target)
    for number,q in enumerate(records,1):
        proof=b.OUT/q['proof'];single=fitz.open(proof)
        def pixels(page):
            p=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
            return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
        changed=int(np.any(pixels(single[0])!=pixels(final[number-1]),axis=2).sum())
        expected=Counter(key(g)for g in glyphs(single[0]));actual=Counter(key(g)for g in glyphs(final[number-1]))
        q['final_vs_reviewed_proof_changed_pixels']=changed
        q['final_vs_reviewed_proof_glyph_metadata_changed']=list((expected-actual).elements())+list((actual-expected).elements())
        q['final_page']=number
        assert changed==0 and expected==actual,(number,changed)
        # Only source Form Chinese subscripts and the explicitly covered Form
        # prose may remain in the text layer. All body prose must be translated.
        form_origins=[g['origin']for g in b.native_form_glyphs(b.SOURCE,number)]
        remaining=[g for g in glyphs(final[number-1])if re.search('[\u3400-\u9fff]',g['c'])and not any(b.close_origin(g['origin'],p)for p in form_origins)]
        q['unexpected_untranslated_body_han']=remaining
        assert not remaining,(number,remaining)
        report['page_audits'].append(q)
        single.close();fitz.TOOLS.store_shrink(100)
        print(lang,number,'final/proof pixels and glyph metadata unchanged',flush=True)
    source.close();final.close()
    (AUTHOR/f'qa-{lang}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lang',choices=['ko','en'],required=True);p.add_argument('--output-dir',type=Path);p.add_argument('--rebuild',action='store_true');a=p.parse_args()
    if a.rebuild:
        data=json.loads((AUTHOR/'body-plan.json').read_text('utf8'))
        translations={k:dict(ko=ko,en=en)for k,ko,en in(x.split('\t')for x in(b.ROOT/'tools/ko/cpho/2023/original-style.tsv').read_text('utf8').splitlines())}
        b.build(data,translations,a.lang,resume=True)
    join(a.lang,a.output_dir)
