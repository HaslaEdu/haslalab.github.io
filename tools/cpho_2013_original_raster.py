"""Manually reviewed source-language overlays for the pinned 2013 scan.

Pixels are original image coordinates, never OCR replacement coordinates.
Every size/baseline was measured before fitting translated text.  The image
streams themselves are preserved by the shared white-raster compositor.
"""
from pathlib import Path
import json
import pymupdf as fitz
import cpho_2013_original_extract as source
from pdf_white_raster_original_style import apply, preflight
from cpho_2013_original_fonts import english_face

ROOT=source.ROOT;AUTHOR=source.AUTHOR

def plans(number,language):
    path=AUTHOR/f'raster-page{number:02}.json'
    if not path.exists():return []
    value=json.loads(path.read_text('utf8'))
    if value['source_sha256']!=source.SOURCE_SHA or value['source_page']!=number:raise ValueError('Wrong raster source')
    with fitz.open(source.SOURCE)as doc:
        page=doc[number-1];images=page.get_image_info(xrefs=True);result=[]
        for item in value['regions']:
            transform=fitz.Matrix(images[item['image']]['transform'])
            w,h=images[item['image']]['width'],images[item['image']]['height']
            def rect(box):
                return list(fitz.Rect(box[0]/w,box[1]/h,box[2]/w,box[3]/h)*transform)
            row={k:v for k,v in item.items()if k not in ['erase_pixels','protected_pixels','translations','point_px','right_px','font_role','blank_background_pixels']}
            x,y=item['point_px'];point=fitz.Point(x/w,y/h)*transform
            right=fitz.Point(item['right_px']/w,y/h)*transform
            row.update(erase_rects=[rect(r)for r in item['erase_pixels']],
                protected_rects=[rect(r)for r in item.get('protected_pixels',[])],
                point=list(point),right=right.x,text=item['translations'][language],
                font_path=str(ROOT/'tools/ko/fonts'/('Noto'+('Sans'if item['font_role']=='sans-bold'else'Serif')+'CJKkr'+('-Bold'if item['font_role']=='sans-bold'else'-Regular')+'.otf'))if language=='ko'else
                    str(Path('C:/Windows/Fonts')/'arialbd.ttf'if item['font_role']=='sans-bold'else english_face('SimSun')))
            row['reviewed_blank_background_rects']=[dict(rect=rect(bg['rect']),reviewed=True,
                source_sha256=source.SOURCE_SHA,source_ink_bbox=rect(bg['source_ink_bbox']),
                reason='Scan dust in manually reviewed blank prose background',
                evidence=value['evidence_source_crop']+'; image pixel bbox '+repr(bg['rect']))for bg in item.get('blank_background_pixels',[])]
            result.append(row)
        preflight(result,page.rect)
        return result

def overlay(number,language,base,target):
    regions=plans(number,language)
    if not regions:raise ValueError('Missing reviewed scan prose')
    try:return apply(source.SOURCE,number,base,target,regions,source.BASE/'fonts')
    except ValueError:
        manifest=json.loads((AUTHOR/f'raster-page{number:02}.json').read_text('utf8'))
        if number!=3 or manifest.get('reviewed_guard_profile')!='2013-p3-scan-circle-old-prose-guard-witness':raise
        audit_path=Path(target).with_suffix('.raster-qa.json')
        if not audit_path.exists():raise
        qa=json.loads(audit_path.read_text('utf8'));checks=qa['checks']
        if checks['changed_original_nonlanguage_guard_pixels']!=9 or any(checks[k]for k in checks if k!='changed_original_nonlanguage_guard_pixels'and(k.startswith('changed_')or k.endswith('_changed'))):raise
        if not checks['original_image_programs_and_raw_bytes_and_filters_and_smask_and_ctm_unchanged']:raise
        import cpho_2013_original_raster_guard as witness
        erased=Path(target).with_suffix('.scan-erasure-control.pdf');witness.control(base,erased,regions)
        profile=witness.audit(base,erased,target,regions)
        if not profile['passed']:raise
        qa['document_specific_old_prose_guard_witness']=profile
        qa['document_specific_preservation_passed']=True
        audit_path.write_text(json.dumps(qa,ensure_ascii=False,indent=2),'utf8')
        return qa

if __name__=='__main__':
    for language in ['ko','en']:
        for row in plans(3,language):print(language,row['id'],row['size'],row['point'],row['text'])
