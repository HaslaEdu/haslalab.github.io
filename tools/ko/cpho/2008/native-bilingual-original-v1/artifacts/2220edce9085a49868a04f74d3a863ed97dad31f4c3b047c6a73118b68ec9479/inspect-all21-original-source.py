"""Prepare read-only original source evidence before classifying any pages."""
from pathlib import Path
import json,hashlib,sys,shutil,subprocess
import pymupdf as f,pikepdf
B=Path(__file__).resolve().parents[1];O=B/'inspection';S=B/'source';O.mkdir(exist_ok=True);S.mkdir(exist_ok=True)
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=Path('C:/Users/andre/CodexWork/HaslaLab/haslalab/tmp/source-audit/CPhO_2008_TS.pdf');pin='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d';assert sha(src)==pin
target=S/'CPhO_2008_original_combined_ZH.pdf'
if not target.exists():shutil.copy2(src,target)
assert sha(target)==pin
rows=[]
for n in range(1,22):
    with page_worker(),f.open(target)as doc,pikepdf.open(target)as pdf:
        assert len(doc)==21;pg=doc[n-1];png=O/f'page{n:02}-source144.png'
        if not png.exists():pg.get_pixmap(matrix=f.Matrix(2,2),colorspace=f.csRGB,alpha=False).save(png)
        text=pg.get_text('dict')
        for block in text['blocks']:
            for key,value in list(block.items()):
                if isinstance(value,bytes):block[key]={'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}
        (O/f'page{n:02}-native-runs.json').write_text(json.dumps(text,ensure_ascii=False,indent=2)+'\n','utf8')
        chars=sum(len(s['text'])for b in text['blocks']if b['type']==0 for l in b['lines']for s in l['spans'])
        fonts=sorted({(s['font'],round(s['size'],8))for b in text['blocks']if b['type']==0 for l in b['lines']for s in l['spans']})
        row=dict(source_page=n,source_sha256=pin,rect=list(pg.rect),native_text_characters=chars,fonts=fonts,images=[dict(xref=i[0],width=i[2],height=i[3],bpc=i[4],colorspace=i[5])for i in pg.get_images(full=True)],native_text=pg.get_text(),source_Page_Group_present='/Group'in pdf.pages[n-1].obj,source_preview=dict(path=str(png),sha256=sha(png),dpi=144))
        rows.append(row);print('SOURCE',n,'native',chars,'images',len(row['images']),'fonts',fonts,flush=True)
(O/'all21-original-source-inventory.json').write_text(json.dumps(dict(original_source_path=str(src),source_copy=str(target),original_source_sha256=pin,source_pages=21,all21_original_144dpi_previews_prepared=True,classification_pending_complete_full_page_visual_review=True,pages=rows),ensure_ascii=False,indent=2)+'\n','utf8')
