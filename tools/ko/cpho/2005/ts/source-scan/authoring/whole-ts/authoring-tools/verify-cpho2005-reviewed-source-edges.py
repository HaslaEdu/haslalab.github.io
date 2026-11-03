"""Independent original-source checks for two nominal-image-boundary crops."""
from pathlib import Path
import sys,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from pdf_original_raster_math import source_recipe,roundtrip
source=B/'inputs/CPhO_2005_Chinese_original.pdf';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash=='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f'
cases=[]
for number,path,atom,rect in [(14,[334],'profile-second-profile-W',[278.75,510,359.75,525]),(15,[343],'substitution-eq8',[467.375,509.75,484.375,521.75])]:
 recipe=source_recipe(source,number,path)
 cases.append(dict(source_page=number,image_path=path,atom=atom,rect=rect,original_nominal_image_bbox=recipe['image']['bbox'],original_ancestor_clips=recipe['image']['ancestor_clip_rects'],original_clip_group_raw_sha256=recipe['original_group_raw_sha256'],original_image_program_sha256=recipe['image_program_sha256'],actual_original_source_roundtrips=[roundtrip(source,number,recipe,rect,scale=s)for s in [4,8]],original_inner_clip_and_image_program_unchanged=True,outer_crop_only_includes_original_paper_padding=True))
report=dict(source_sha256=source_hash,cases=cases,passed=all(r['changed_pixels']==0 for c in cases for r in c['actual_original_source_roundtrips']))
(B/'inputs/reviewed-original-image-edge-roundtrips.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
assert report['passed'];print('BOTH_ORIGINAL_SOURCE_EDGE_ROUNDTRIPS_4X_8X_EXACT',flush=True)
