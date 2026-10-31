"""Fresh-process image/palette evidence; never rebuild or rewrite a PDF."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,os,math
import numpy as np
from PIL import Image,ImageDraw
import pymupdf as fitz
import pikepdf
import cpho_2005_original_build as b


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def semantic(value,ancestors=()):
    """Follow palette/ICC/Mask streams as well as the main pixel-index stream."""
    if isinstance(value,pikepdf.Stream):
        if value.objgen in ancestors:raise ValueError('Recursive image stream graph')
        return dict(dictionary={str(k):semantic(v,ancestors+(value.objgen,))for k,v in value.items()},
            raw_sha256=hashlib.sha256(value.read_raw_bytes()).hexdigest(),decoded_sha256=hashlib.sha256(value.read_bytes()).hexdigest())
    if isinstance(value,pikepdf.Dictionary):return{str(k):semantic(v,ancestors)for k,v in value.items()}
    if isinstance(value,pikepdf.Array):return[semantic(v,ancestors)for v in value]
    if isinstance(value,pikepdf.String):return dict(pdf_string_hex=bytes(value).hex())
    return str(value)


def render(path,folder):
    path=Path(path);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with fitz.open(path)as doc:
        for i in range(3):
            for scale,tag in [(2,'2x'),(.8,'contact')]:
                doc[i].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False).save(folder/f'{i+1}-{tag}.png')


def audit():
    root=b.BASE.parent/'root-review'/'isolated';root.mkdir(parents=True,exist_ok=True)
    paths={'source':b.source.SOURCE,'ko':b.BASE.parent/'CPhO_2005_T_KO.pdf','en':b.BASE.parent/'CPhO_2005_T_EN.pdf'}
    for name,path in paths.items():
        subprocess.run([sys.executable,'-X','utf8',__file__,'--render',str(path),'--out',str(root/name)],check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
    rows=[]
    with fitz.open(paths['source'])as src,pikepdf.open(paths['source'])as sp:
        for name in ['ko','en']:
            with fitz.open(paths[name])as dst,pikepdf.open(paths[name])as dp:
                for i in range(3):
                    with Image.open(root/'source'/f'{i+1}-2x.png')as image:a=np.array(image.convert('RGB'))
                    with Image.open(root/name/f'{i+1}-2x.png')as image:z=np.array(image.convert('RGB'))
                    originals=src[i].get_image_info(xrefs=True);current=dst[i].get_image_info(xrefs=True)
                    if len(originals)!=len(current):raise ValueError('Image paint count changed')
                    images=[]
                    for j,(old,new)in enumerate(zip(originals,current)):
                        same=semantic(sp.get_object((old['xref'],0)))==semantic(dp.get_object((new['xref'],0)))
                        r=fitz.Rect(old['bbox']);x0=max(0,math.floor(r.x0*2));x1=min(a.shape[1],math.ceil(r.x1*2));y0=max(0,math.floor(r.y0*2));y1=min(a.shape[0],math.ceil(r.y1*2))
                        count=int(np.any(a[y0:y1,x0:x1]!=z[y0:y1,x0:x1],axis=2).sum())
                        images.append(dict(image_index=j,source_bbox=list(old['bbox']),whole_image_bbox_changed_pixels=count,
                            full_image_dictionary_and_raw_decoded_palette_icc_mask_program_graph_identical=same))
                    row=dict(language=name,page=i+1,final_sha256=sha(paths[name]),image_audits=images,
                        passed=all(v['whole_image_bbox_changed_pixels']==0 and v['full_image_dictionary_and_raw_decoded_palette_icc_mask_program_graph_identical']for v in images))
                    rows.append(row);print(json.dumps(row),flush=True)
    contact=Image.new('RGB',(1800,2550),'white');draw=ImageDraw.Draw(contact)
    for column,name in enumerate(['source','ko','en']):
        for row in range(3):
            with Image.open(root/name/f'{row+1}-contact.png')as image:
                picture=image.convert('RGB');picture.thumbnail((590,820));contact.paste(picture,(column*600+5,row*850+25))
            draw.text((column*600+5,row*850+5),f'{name} / page{row+1} / isolated process',fill='black')
    contact_path=root.parent/'contact-isolated.png';contact.save(contact_path)
    report=dict(method='One fresh Python/MuPDF process per complete PDF, then PNG-only contact assembly; no shared cross-document renderer cache.',
        delivered_pdfs_modified=False,scale=2,contact=str(contact_path),source_sha256=b.source.SOURCE_SHA,
        files={name:dict(path=str(path),sha256=sha(path))for name,path in paths.items()},
        pages=rows,passed=all(r['passed']for r in rows))
    (b.AUTHOR/'T-isolated-image-palette-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--render');p.add_argument('--out');args=p.parse_args()
    if args.render:render(args.render,args.out)
    else:raise SystemExit(not audit()['passed'])
