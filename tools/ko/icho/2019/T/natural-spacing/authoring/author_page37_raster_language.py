from pathlib import Path
import hashlib,json
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import author_outlined_vector_labels as a
import natural_plan_compose_icho2019 as c
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;profile=B/'graphic-language-audit-01-56-20261103/page37-source-raster-legend-profile.json';data=json.loads(profile.read_text('utf8'));face=TTFont('C:/Windows/Fonts/times.ttf');unit=face['head'].unitsPerEm;cm=face.getBestCmap();glyphset=face.getGlyphSet();x=0;rects=[]
for char in'azobenzene':
    gn=cm[ord(char)];pen=BoundsPen(glyphset);glyphset[gn].draw(pen);r=pen.bounds;rects.append([x+r[0]/unit,r[1]/unit,x+r[2]/unit,r[3]/unit]);x+=face['hmtx'].metrics[gn][0]/unit
shape=a.rect_union(rects);size=sum(v['page_ink_bbox_pt'][3]-v['page_ink_bbox_pt'][1]for v in data['labels'])/2/(shape[3]-shape[1]);labels=[]
for i,v in enumerate(data['labels']):
    r=v['page_ink_bbox_pt'];kr=a.korean_bounds('아조벤젠','serif',size);baseline=r[3]+shape[1]*size;right=r[2];point=[right-kr[2],baseline];mask=[r[0]-.33,r[1]-.33,r[2]+.33,r[3]+.33]
    labels.append(dict(id=f'p37-raster-azobenzene-{i}',source_sha256=g.SOURCE_SHA,source_text='azobenzene',text='아조벤젠',source_image_path=data['image']['path'],source_image_raw_sha256=data['source_image_stream_raw_sha256'],rect=mask,point=point,size=size,font_role='serif',preserved_source_suffix_bbox=v['suffix_page_bbox_pt'],preserved_suffix=v['preserve_suffix'],source_label_kind='raster-only-language',source_font_metadata_available=False,source_point_size_metadata_available=False,source_font_size_basis='Original indexed bitmap has no font/point metadata. Serif role read from original legend; one common physical em size inferred from the mean original azobenzene ink height and the Times New Roman outline role, with original pixel quantization uncertainty kept separate from exact body/math typography.',source_physical_ink_bbox=r,source_word_right_edge_preserved=right,original_gap_to_scientific_suffix_pt=v['suffix_page_bbox_pt'][0]-right,review='Only the ordinary English prefix bitmap area receives a white PDF language mask; original bitmap stream and placement stay byte-identical. Original (trans)/(cis) pixels remain uncovered at exact original positions. Right-align Korean to the original word edge so the original small prefix/suffix gap remains unchanged.'))
p=B/'page37.overrides.json';q=json.loads(p.read_text('utf8'));q['__raster_labels__']=labels;p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');(B/'page37-raster-language-authoring-review.json').write_text(json.dumps(dict(source_profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),labels=labels,source_font_point_metadata_inferred_not_direct=True),ensure_ascii=False,indent=2)+'\n','utf8');print(size,flush=True)
