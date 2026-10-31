"""Save source/translated enlargements and language/native-feature mask views."""
from pathlib import Path
import argparse,io,json,hashlib
import numpy as np
import pymupdf as fitz
from PIL import Image,ImageDraw
from izho_bitmap_features import feature_masks

ROOT=Path(__file__).resolve().parents[1]
COLORS={'planet_surfaces':(40,230,90),'gray_white_asteroid_points':(40,210,255),'colored_orbits':(255,190,40)}

def generate(year,kind):
    folder=ROOT/'tools/ko/izho'/str(year)/kind/'original_style';scratch=ROOT/'tmp/original-style-repair'/str(year)/kind
    output=scratch/'qa-bitmap';output.mkdir(exist_ok=True)
    report=[]
    for plan in sorted(folder.glob('page*.json')):
        data=json.loads(plan.read_text('utf8'));labels=data.get('raster_language_overlays',[])
        if not labels:continue
        page_number=data['page']+1;source=fitz.open(ROOT/data['source']);page=source[page_number-1]
        proof_path=scratch/f'page{page_number}.pdf';proof=fitz.open(proof_path)
        infos=page.get_image_info(xrefs=True,hashes=True)
        qa=json.loads(proof_path.with_suffix('.qa.json').read_text('utf8'))
        actual_sha=hashlib.sha256(proof_path.read_bytes()).hexdigest()
        if qa['proof_sha256']!=actual_sha:raise ValueError('Review input differs from the audited proof')
        for index in sorted({label['image']for label in labels}):
            items=[label for label in labels if label['image']==index];info=infos[index]
            pixels=np.array(Image.open(io.BytesIO(source.extract_image(info['xref'])['image'])).convert('RGB'))
            language=np.zeros(pixels.shape[:2],bool)
            for label in items:
                x0,y0,x1,y1=label['source_ink_rect_px'];roi=pixels[y0:y1,x0:x1].astype(np.int16)
                if label['background']=='white':ink=roi.min(2)<240
                else:ink=(roi[:,:,0]>70)&(roi[:,:,0]>=roi[:,:,1]-20)
                language[y0:y1,x0:x1]|=ink
            masks={};profile=next((row.get('protect_features')for row in items if row.get('protect_features')),None)
            if profile:masks=feature_masks(pixels,profile,[label['source_ink_rect_px']for label in items])
            combined=pixels.astype(float)
            for name,mask in masks.items():combined[mask]=combined[mask]*.35+np.array(COLORS[name])*.65
            combined[language]=combined[language]*.25+np.array([255,40,70])*.75
            view=Image.fromarray(np.uint8(np.clip(combined,0,255)))
            draw=ImageDraw.Draw(view)
            for label in items:draw.rectangle(label['source_ink_rect_px'],outline=(255,40,70),width=1)
            mask_path=output/f'page{page_number}-image{index}-language-vs-native-mask.png'
            view.resize((view.width*3,view.height*3),Image.Resampling.NEAREST).save(mask_path)
            region=fitz.Rect(info['bbox'])
            for placement in qa['raster_language_overlays']:
                if placement['image']==index:region|=fitz.Rect(placement['language_rect_pdf'])
            region+=(-2,-2,2,2)
            source_path=output/f'page{page_number}-image{index}-source-4x.png'
            translated_path=output/f'page{page_number}-image{index}-ko-4x.png'
            page.get_pixmap(matrix=fitz.Matrix(4,4),clip=region,colorspace=fitz.csRGB,alpha=False).save(source_path)
            proof[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=region,colorspace=fitz.csRGB,alpha=False).save(translated_path)
            report.append(dict(page=page_number,image=index,original_image_digest=info['digest'].hex(),
                original_english_label_count=len(items),original_english_labels=[row['source_text']for row in items],
                korean_labels=[row['text']for row in items],mask_legend=dict(language_ink='red',**{key:str(value)for key,value in COLORS.items()}),
                mask_notes='Language ink is colour-filtered only inside reviewed English glyph rectangles. Native feature masks use the explicit planet bounds and colour criteria stored in the plan. The full picture remains separately compared outside the language regions.',
                feature_source_pixel_counts={key:int(mask.sum())for key,mask in masks.items()},
                native_picture_feature_masks=qa.get('native_picture_feature_masks',[]),
                changed_native_picture_feature_pixels_inside_language_regions=qa.get('changed_native_picture_feature_pixels_inside_language_regions',0),
                changed_native_picture_feature_pixels_outside_language_regions=qa.get('changed_native_picture_feature_pixels_outside_language_regions',0),
                changed_pixels_outside_language_regions=qa['changed_pixels_outside_raster_language_regions'],
                changed_visible_nonlanguage_graphic_pixels=qa['changed_pixels_in_visible_raster_graphics'],
                source_bitmap_bytes_and_coordinates_unchanged=qa['source_images_bytes_and_rects_unchanged'],
                proof_sha256=hashlib.sha256(proof_path.read_bytes()).hexdigest(),
                review_artifacts=[str(path.relative_to(ROOT))for path in [mask_path,source_path,translated_path]]))
        source.close();proof.close()
    result=dict(year=year,kind=kind,pages=report,full_figure_pixel_equality_claimed=False,visual_review_required=True)
    (folder/'bitmap-label-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(images=len(report),labels=sum(row['original_english_label_count']for row in report)),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);p.add_argument('kind');a=p.parse_args();generate(a.year,a.kind)
