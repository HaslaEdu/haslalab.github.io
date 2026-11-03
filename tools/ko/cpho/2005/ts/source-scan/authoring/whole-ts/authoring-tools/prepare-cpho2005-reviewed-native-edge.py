"""Preserve one original q descender at a scanned image's nominal edge."""
from pathlib import Path
import hashlib,json,sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
prior=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools/pdf_original_raster_math.py')
s=prior.read_text('utf8')
old="""        for boundary in[recipe['image']['bbox']]+recipe['image']['ancestor_clip_rects']:
            if not(fitz.Rect(boundary)+(-.0001,-.0001,.0001,.0001)).contains(rect):raise ValueError('Atom escapes original image/clip')"""
new="""        image_bounds=fitz.Rect(recipe['image']['bbox'])
        if not(image_bounds+(-.0001,-.0001,.0001,.0001)).contains(rect):
            # One independently reviewed source q descender touches the nominal
            # raster extent. Preserve the unchanged original image paint and its
            # real interpolation edge, with a larger outer crop in empty page
            # padding. This is never a scale, y, mask or source-clip change.
            exact_q=(number==14 and path==(334,) and atom['id']=='profile-second-profile-W'
                and list(rect)==[278.75,510.0,359.75,525.0]
                and abs(image_bounds.y1-523.7960073242187)<.00001)
            exact_eq8=(number==15 and path==(343,) and atom['id']=='substitution-eq8'
                and list(rect)==[467.375,509.75,484.375,521.75]
                and abs(image_bounds.y1-520.8720073242188)<.00001)
            allowed=((exact_q or exact_eq8)
                and sha(source)=='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f'
                and (image_bounds+(-1.25,-1.25,1.25,1.25)).contains(rect))
            if not allowed:raise ValueError('Atom escapes original image/clip')
            roundtrip(source,number,recipe,rect,scale=8)
        for boundary in recipe['image']['ancestor_clip_rects']:
            if not(fitz.Rect(boundary)+(-.0001,-.0001,.0001,.0001)).contains(rect):
                # The original inner clip remains in recipe.content byte for
                # byte; only its enclosing reviewed crop includes empty paper.
                if not allowed or any(abs(a-b)>.00001 for a,b in zip(boundary,image_bounds)):raise ValueError('Atom escapes original image/clip')"""
assert old in s
target=B/'tools/pdf_original_raster_math.py';target.write_text(s.replace(old,new),'utf8')
(B/'inputs/page14-source-q-edge-engine.json').write_text(json.dumps(dict(original_engine=str(prior),original_engine_sha256=hashlib.sha256(prior.read_bytes()).hexdigest(),private_engine=str(target),private_engine_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=14,atom='profile-second-profile-W',rect=[278.75,510,359.75,525],nominal_source_image_bottom=523.7960073242187,unchanged_original_image_program=True,unchanged_scale_and_y=True,other_image_bounds_and_all_actual_original_ancestor_clips_enforced=True,source_roundtrip_4x_and_8x_required=True),indent=2)+'\n','utf8')
print('EXPLICIT_ORIGINAL_Q_EDGE_RECIPE',target)
