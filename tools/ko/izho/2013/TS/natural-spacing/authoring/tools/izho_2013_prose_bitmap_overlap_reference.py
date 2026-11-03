from pathlib import Path
import hashlib,json,math
import numpy as np
import pymupdf as f
from pdf_text_motion_ink import ink_envelope
SOURCE='2804ded48ad009bf58884b871f0f4817c64762b8a0f586e42056908fc4be10f1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit_reference(plan,figure,original_pixels,final_pixels,folder,fresh_render):
 matches=[r for r in plan.get('reviewed_original_prose_bitmap_overlap_references',[])if r['rect']==figure['rect']]
 if not matches:return figure
 if len(matches)!=1 or plan['original_english_source_sha256']!=SOURCE or plan['source_page']!=2:raise ValueError('Unexpected original prose/bitmap overlap source profile')
 profile=matches[0];assert sha(profile['reference_provenance'])==profile['reference_provenance_sha256'];p=json.loads(Path(profile['reference_provenance']).read_text('utf8'))
 assert p['original_source_sha256']==SOURCE and p['source_page']==2 and p['original_prose_at']==[5,1,2]and 'vaporized'in p['original_prose_text']
 glyph=p['exact_erased_original_English_prose_glyph'];assert glyph['c']=='p'and glyph['font']=='TimesNewRomanPSMT'and glyph['size']==12 and abs(glyph['origin'][1]-154.22000122070312)<.001
 assert p['shared_native_guard_sha256']=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
 assert sha(profile['control'])==profile['control_sha256']==p['control_sha256']
 control=fresh_render(profile['control'],1,folder/'qa-renders/02-original-selected-English-p-only-reference.png');assert control.shape==original_pixels.shape==final_pixels.shape
 assert sha(plan['original_english_source'])==SOURCE
 removed=np.any(original_pixels!=control,axis=2)
 with f.open(plan['original_english_source'])as source:actual_glyph_ink,uses=ink_envelope(source[1],[glyph['origin']],4)
 if uses!=1 or np.any(removed&~actual_glyph_ink):raise ValueError('Reference changes pixels outside the actual original selected English p outline envelope')
 x0,y0,x1,y1=[math.ceil(v*4-.5)for v in figure['rect']];region=(slice(max(0,y0),y1),slice(max(0,x0),x1));local=removed[region];count=int(local.sum())
 if count!=profile['expected_original_prose_only_pixels_inside_bitmap_rectangle']or not count:raise ValueError('Original English descender overlap no longer matches its reviewed13 physical pixels')
 if not np.all(control[region][local]==255):raise ValueError('An overlap reference would suppress actual nonwhite native bitmap ink')
 changed=np.any(control!=final_pixels,axis=2);result=dict(figure);result.update(reference='Original source with only the explicitly translated English p erased; every native bitmap program and all other original glyphs retained',changed_pixels=int(changed[region].sum()),original_selected_English_prose_pixels_removed_from_transparent_bitmap_padding=count,independent_reference_control_sha256=profile['control_sha256'],reference_provenance_sha256=profile['reference_provenance_sha256'],every_removed_overlap_pixel_is_pure_white_without_the_original_English_prose=True,all_other_full_bitmap_rectangle_pixels_still_require_exact_equality=True)
 return result
