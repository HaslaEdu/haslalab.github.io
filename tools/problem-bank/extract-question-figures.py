"""Extract original, manually verified figure rectangles into PRIVATE staged assets.

No redraw, OCR, solution import, canonical mutation or automatic public admission.
PNG contains only rendered crop pixels. Native SVG is optional and refused when
an intersecting raster/vector object extends outside the verified rectangle.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import pymupdf
from private_paths import private_directory, source_path
from source_identity import source_key


def sha(value):return hashlib.sha256(value).hexdigest()


def rectangle(page,bbox):
    if (not isinstance(bbox,list) or len(bbox)!=4 or
        any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in bbox) or
        bbox[0]>=bbox[2] or bbox[1]>=bbox[3]):raise ValueError('Expected normalized figure rectangle')
    p=page.rect
    return pymupdf.Rect(p.x0+bbox[0]*p.width,p.y0+bbox[1]*p.height,p.x0+bbox[2]*p.width,p.y0+bbox[3]*p.height)


def native_svg(page,rect):
    """Never hide a complete scanned page or out-of-crop vector path in SVG."""
    if page.rotation:return None,{'available':False,'reason':'rotated_page_requires_raster_crop'}
    padded=rect+(-0.01,-0.01,0.01,0.01)
    overlaps=lambda box:box.x0<=rect.x1 and box.x1>=rect.x0 and box.y0<=rect.y1 and box.y1>=rect.y0
    for image in page.get_image_info():
        box=pymupdf.Rect(image['bbox'])
        if overlaps(box) and not padded.contains(box):
            return None,{'available':False,'reason':'intersecting_image_extends_outside_figure'}
    for drawing in page.get_drawings():
        box=pymupdf.Rect(drawing['rect'])
        if overlaps(box) and not padded.contains(box):
            return None,{'available':False,'reason':'intersecting_vector_extends_outside_figure'}
    for block in page.get_text('rawdict')['blocks']:
        for line in block.get('lines',[]):
            for span in line.get('spans',[]):
                for char in span.get('chars',[]):
                    box=pymupdf.Rect(char['bbox'])
                    if overlaps(box) and not padded.contains(box):
                        return None,{'available':False,'reason':'intersecting_text_extends_outside_figure'}
    copy=pymupdf.open()
    try:
        copy.insert_pdf(page.parent,from_page=page.number,to_page=page.number,links=False,annots=False,widgets=False)
        selected=copy[0]
        selected.clip_to_rect(rect)
        retained=selected.get_text('text')
        # Text is physically removed before changing CropBox. A viewBox alone
        # would retain other questions/solutions in the SVG source.
        selected.set_cropbox(rect)
        value=selected.get_svg_image(text_as_path=True)
        if '<script' in value.lower() or '<foreignobject' in value.lower():raise ValueError('Unexpected active SVG content')
        return value.encode('utf-8'),{'available':True,'method':'physically_remove_outside_then_crop_native_pdf','text_as_path':True,'retained_text_for_private_review':retained}
    finally:copy.close()


def extract(root,spec,out,dpi=220,native=False):
    if not 100<=dpi<=400:raise ValueError('Figure DPI must be between100 and400')
    root=Path(root);out=private_directory(out)
    if spec.get('version')!=1 or not isinstance(spec.get('figures'),list) or len(spec['figures'])>20:raise ValueError('Expected bounded figure spec, at most20 entries')
    registry=json.loads((root/'solution-bank/source-index.json').read_text(encoding='utf-8'))['normalized_sources']
    sources={source_key(s):s for s in registry}
    canonical=json.loads((root/'solution-bank/question-index.json').read_text(encoding='utf-8'))['questions']
    admitted={(source_key(q['source']),q['locator']):q for q in canonical}
    output=[];checked_sources={}
    for item in spec['figures']:
        if item.get('source_bbox_visually_verified') is not True or item.get('statement_figure_not_solution') is not True:
            raise ValueError('Original source rectangle and question-figure purpose require explicit visual verification')
        key=source_key(item['source']);source=sources[key];locator=item['locator']
        if (key,locator) not in admitted:raise ValueError('Figure question is not in the canonical question index')
        if item['source_pdf_sha256']!=source['sha256']:raise ValueError('Figure source PDF hash does not match registered revision')
        qid='q_'+sha((source['id']+'\0'+locator).encode())
        if item.get('question_id',qid)!=qid:raise ValueError('Figure canonical question ID mismatch')
        pdf=source_path(source['local_path'],root/'runtime-path-map.json')
        if source['id'] not in checked_sources:
            if sha(pdf.read_bytes())!=source['sha256']:raise ValueError('Actual figure source PDF bytes changed')
            checked_sources[source['id']]=True
        with pymupdf.open(pdf) as document:
            number=item['page']
            if not isinstance(number,int) or isinstance(number,bool) or not 1<=number<=len(document):raise ValueError('Invalid figure source page')
            page=document[number-1];rect=rectangle(page,item['bbox'])
            stable=sha((qid+'\0'+json.dumps({'page':number,'bbox':item['bbox']},sort_keys=True,separators=(',',':'))).encode())
            asset_id='original-figure-'+stable[:24];png=page.get_pixmap(clip=rect,dpi=dpi,alpha=False,annots=False).tobytes('png')
            if len(png)>4*1024*1024:raise ValueError('Figure PNG exceeds private inline-asset limit')
            image_path=out/(stable+'.png');image_path.write_bytes(png)
            svg_info={'available':False,'reason':'native_svg_not_requested'}
            if native:
                svg,svg_info=native_svg(page,rect)
                if svg is not None:
                    svg_path=out/(stable+'.svg');svg_path.write_bytes(svg);svg_info.update(local_path=str(svg_path),sha256=sha(svg))
            output.append({'question_id':qid,'source_id':source['id'],'source':item['source'],'source_pdf_sha256':source['sha256'],
                'locator':locator,'original_number':admitted[key,locator]['original_number'],'figure_label':item.get('figure_label'),
                'role':'figure','asset_id':asset_id,'expected_canonical_asset_id':'a_'+sha((qid+'\0'+asset_id).encode()),
                'local_path':str(image_path),'mime_type':'image/png','sha256':sha(png),'byte_length':len(png),
                'spans':[{'page':number,'bbox':item['bbox']}],'render_dpi':dpi,
                'source_bbox_visually_verified':True,'statement_figure_not_solution':True,
                'extraction':'original_pdf_region_render_no_redraw','native_svg':svg_info,
                'final_extracted_image_visually_verified':False,'canonical_server_readback_verified':False,
                'public_admission':'pending_final_visual_and_server_review','publication_ready':False})
    result={'schema':'haslalab.private.staged-original-question-figures.v1','version':1,'private':True,'paid_api_calls':0,
        'original_source_files_unchanged':True,'solution_assets_imported':0,'figures':output}
    (out/'staged-figures.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--private-root',type=Path,required=True)
    parser.add_argument('--spec',type=Path,required=True);parser.add_argument('--out-dir',type=Path,required=True)
    parser.add_argument('--dpi',type=int,default=220);parser.add_argument('--native-svg',action='store_true');args=parser.parse_args()
    result=extract(args.private_root,json.loads(args.spec.read_text(encoding='utf-8')),args.out_dir,args.dpi,args.native_svg)
    print(json.dumps({'staged_figures':len(result['figures']),'native_svg_available':sum(f['native_svg']['available'] for f in result['figures']),'public_admission':False}))
