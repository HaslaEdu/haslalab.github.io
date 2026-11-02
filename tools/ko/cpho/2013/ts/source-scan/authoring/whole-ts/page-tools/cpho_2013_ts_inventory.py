"""Prepare read-only OCR/paint hints; no unreviewed hint can erase source ink."""
from pathlib import Path
import json,hashlib,re
from pdf_native_inline_reposition import inspect_inline_groups

ROOT=Path.cwd();AUTHOR=ROOT/'tools/ko/cpho/2013/original'
SOURCE=ROOT/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'
PIN='612d676f525ddc35ad3b417a8f25141d3467f48309d52dfdbcab7bd222201d68'
OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/authoring')

def prepare():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==PIN
    slots=json.loads((AUTHOR/'native-slots.json').read_text('utf8'));OUT.mkdir(parents=True,exist_ok=True);summary=[]
    for number in range(4,15):
        target=OUT/f'page{number:02d}.json'
        if target.exists():
            old=json.loads(target.read_text('utf8'))
            if old['source_sha256']!=PIN or old['source_page']!=number:raise ValueError('Existing plan has another source')
            summary.append(dict(source_page=number,logical_page=number-3,native_headers=len(old['native_headers']),images=len(old['source_images']),hints=len(old['ocr_location_hints']),plan=str(target)))
            continue  # Preserve all later manual edits exactly.
        inventory=inspect_inline_groups(SOURCE,number);ocr=json.loads((AUTHOR/f'ocr-page{number:02d}-draft.json').read_text('utf8'));texts={}
        for line in(AUTHOR/f'page{number:02d}.tsv').read_text('utf8').splitlines():
            if line.strip():key,ko,en=line.split('\t');texts[key]=dict(ko=ko,en=en)
        headers=[]
        for slot in slots['pages'][number-1]['slots']:
            headers.append(dict(source_slot=slot['id'],source_text=slot['source'],source_font=slot['source_font'],size=slot['size'],origin=slot['origin'],
                align=slot.get('align','left'),center=slot.get('original_horizontal_center'),right=slot['right'],translations=texts[slot['id']],
                preserve_existing_ascii_digit_cids=True,reviewed=True))
        hints=[]
        for index,line in enumerate(ocr['lines']):
            polygon=line['polygon'];s=ocr.get('render_scale',ocr.get('scale'));box=[min(p[0]for p in polygon)/s,min(p[1]for p in polygon)/s,max(p[0]for p in polygon)/s,max(p[1]for p in polygon)/s]
            center=[(box[0]+box[2])/2,(box[1]+box[3])/2]
            images=[im['path']for im in inventory['images']if im['bbox'][0]<=center[0]<=im['bbox'][2]and im['bbox'][1]<=center[1]<=im['bbox'][3]]
            if not images:continue  # Native header/footer is handled separately.
            hints.append(dict(id=f'p{number}-ocr{index}',ocr_text=line['text'],approximate_rect=box,image_paths=images,
                kind_hint='possible_language_or_math_Han'if re.search('[\u3400-\u9fff]',line['text'])else'possible_math_or_number',
                manual_review_required=True,may_erase=False))
        data=dict(source=str(SOURCE),source_sha256=PIN,source_page=number,edition_page=number-3,edition_pages=11,
            scope_complete=False,publication_ready=False,native_headers=headers,
            source_images=inventory['images'],ocr_location_hints=hints,font_profiles=[],language_rows=[],inline_math_atoms=[],figure_language_regions=[],
            requirements=dict(original_bitmap_scale=1,word_space_em=.25,autoshrink=False,display_math_and_figures_stationary=True,
                math_ocr_retypesetting=False,manual_source_language_rois_required=True,old_ink_classification_required=True,
                preserve_original_printed_page_totals_even_if_incorrect=True))
        target.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8');summary.append(dict(source_page=number,logical_page=number-3,native_headers=len(headers),images=len(inventory['images']),hints=len(hints),plan=str(target)))
    (OUT/'source-inventory.json').write_text(json.dumps(dict(source_sha256=PIN,kind='TS',source_pages=list(range(4,15)),pages=summary),ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':prepare()
