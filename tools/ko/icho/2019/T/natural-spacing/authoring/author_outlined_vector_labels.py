"""Author reviewed Korean graphic-language labels, with honest outline inference."""
from pathlib import Path
import json,hashlib
import pymupdf as f
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import icho2019_write_guard as g
import natural_plan_compose_icho2019 as c
B=Path(__file__).resolve().parent;P=B/'source-vector-labels';fonts={};rows={}

def rect_union(rects):return[min(r[0]for r in rects),min(r[1]for r in rects),max(r[2]for r in rects),max(r[3]for r in rects)]

def font_shape(word,bold,reference_face=None):
    filename=reference_face or('arialbd.ttf'if bold else'arial.ttf')
    if filename not in fonts:fonts[filename]=TTFont('C:/Windows/Fonts/'+filename)
    font=fonts[filename];cm=font.getBestCmap();x=0;rects=[];unit=font['head'].unitsPerEm
    for ch in word:
        gn=cm[ord(ch)];glyph=font['glyf'][gn]
        if glyph.numberOfContours:rects.append([x+glyph.xMin,glyph.yMin,x+glyph.xMax,glyph.yMax])
        x+=font['hmtx'].metrics[gn][0]
    return [v/unit for v in rect_union(rects)],filename

def korean_bounds(text,role,size):
    filename=str(c.FONTS[role])
    if filename not in fonts:fonts[filename]=TTFont(filename)
    font=fonts[filename];glyphset=font.getGlyphSet();cm=font.getBestCmap();unit=font['head'].unitsPerEm;x=0;rs=[]
    for ch in text:
        gn=cm[ord(ch)]
        if not ch.isspace():
            pen=BoundsPen(glyphset);glyphset[gn].draw(pen);r=pen.bounds;assert r
            rs.append([x+r[0]/unit*size,r[1]/unit*size,x+r[2]/unit*size,r[3]/unit*size])
        x+=font['hmtx'].metrics[gn][0]/unit*size
    return rect_union(rs)

def form(n):
    if n==45:return json.loads((P/'page45-form152-profile.json').read_text('utf8'))['form']
    return json.loads((P/f'page{n:02}-language-profile.json').read_text('utf8'))['forms'][0]

def add(n,id,word,ko,starts,*,bold=False,clip=None,english_start=None,native_prefix_edge=None,native_suffix_edge=None,left_anchor=False,fit_word=None,reference_face=None,korean_role=None):
    info=form(n);paths=[v for v in info['own_vector_paths']if v['operator_indices'][0]in starts];assert len(paths)==len(starts),(n,id,starts)
    source=rect_union([v['rect']for v in paths]);English=[v for v in paths if v['operator_indices'][0]not in[native_prefix_edge,native_suffix_edge]and(english_start is None or v['rect'][2]>english_start)]or paths
    ink=rect_union([v['rect']for v in English]);shape,face=font_shape(fit_word or word,bold,reference_face);size=(ink[3]-ink[1])/(shape[3]-shape[1]);baseline=ink[3]+shape[1]*size
    role=korean_role or('sans-bold'if bold else'sans');kr=korean_bounds(ko,role,size);kw=kr[2]-kr[0];center=(source[0]+source[2])/2;dx=0.;edge_indices=[]
    if native_prefix_edge is not None:
        edge=[v for v in paths if v['operator_indices'][0]==native_prefix_edge][0];edge_indices=[edge['operator_indices']]
        assert english_start is not None
        dx=center-(source[0]+english_start+kw)/2;kleft=english_start+dx
    elif native_suffix_edge is not None:
        edge=[v for v in paths if v['operator_indices'][0]==native_suffix_edge][0];edge_indices=[edge['operator_indices']]
        gap=edge['rect'][0]-ink[2];nw=edge['rect'][2]-edge['rect'][0]
        kleft=ink[0]if left_anchor else center-(kw+gap+nw)/2
        dx=kleft+kw+gap-edge['rect'][0]
    else:kleft=ink[0]if left_anchor else center-kw/2
    clip=clip or[ink[0]-.3,ink[1]-.3,ink[2]+.3,ink[3]+.3]
    label=dict(id=id,source_sha256=g.SOURCE_SHA,source_form_raw_sha256=info['original_raw_sha256'],source_form_path=info['path'],source_text=word,text=ko,source_paths=paths,english_clip_rect=clip,source_caption_rect=source,source_native_caption_edge_path_indices=edge_indices,native_caption_path_dx_pt=dx,point=[kleft-kr[0],baseline],size=size,font_role=role,source_caption_center_x=center if not left_anchor else None,expected_new_korean_ink_bounds=[kleft,baseline-kr[3],kleft+kw,baseline-kr[1]],source_label_kind='outlined-vector',source_font_metadata_available=False,source_point_size_metadata_available=False,source_style_inferred_from_reviewed_outline=('Times-like 'if role.startswith('serif')else'Arial-like ')+('bold'if bold else'regular')+(' serif'if role.startswith('serif')else' sans serif'),source_font_size_basis='No font or point-size metadata exists: original Form glyph_count=0. Physical vertical em scale and baseline inferred by fitting the reviewed original English outline ink height to the '+face+' outline role; exact original font/point metadata is not asserted. This inference is separate from the strict directly measured body/math typography.',outline_inference=dict(reference_face=face,reference_word=fit_word or word,reference_em_bbox=shape,reviewed_source_ink_bbox=ink,inferred_vertical_em_size_pt=size,inferred_baseline_pt=baseline,horizontal_em_size_estimate_pt=(ink[2]-ink[0])/(shape[2]-shape[0])),preserved_native_caption_edge_paths=edge_indices)
    rows.setdefault(n,[]).append(label)

if __name__=='__main__':
    add(45,'p45-catalyst','catalyst','촉매',[1542])
    add(52,'p52-3D-structure','structure','구조',[857,901,939,986,1020,1046,1078,1111,1145,1177,1203],clip=[243.3,267.7,276.4,274.5],english_start=243.702794191179,native_prefix_edge=857)
    add(52,'p52-perspective-formula','perspective formula','투시식',[1241,1281,1319,1345,1392,1432,1470,1503,1537,1561,1583,1621,1653,1688,1714,1755,1787,1804])
    add(57,'p57-L-lysine-hydrochloride','Lysine hydrochloride','라이신 염산염',[228,236,357],clip=[262.8,291.5,352.2,300.9],english_start=263.25,native_prefix_edge=228)
    add(58,'p58-L-lysine','Lysine','라이신',[228,236],bold=True,clip=[131.6,155.3,163.8,165.4],english_start=132.,native_prefix_edge=228)
    add(58,'p58-hydrochloride','hydrochloride','염산염',[346],bold=True)
    add(58,'p58-diluted-HCl','diluted','묽은',[1230,1362],clip=[364.2,142.8,394.,150.8],native_suffix_edge=1362,left_anchor=True)
    add(58,'p58-aqueous-buffer','aqueous buffer','완충 수용액',[1450,1635],left_anchor=True)
    add(58,'p58-reagent-H','reagent','시약',[3031,3208],native_suffix_edge=3208)
    add(58,'p58-reactive-intermediate','reactive intermediate','반응성 중간체',[7248,7414])
    add(58,'p58-levobupivacaine','Levobupivacaine','레보부피바카인',[3346],bold=True)
    add(58,'p58-benzyloxycarbonyl-chloride','(benzyloxycarbonyl chloride)','(벤질옥시카보닐 클로라이드)',[4966,5305])
    add(58,'p58-DCC-full-name',"N,N′-dicyclohexylcarbodiimide)",'디시클로헥실카르보디이미드)',[5540,5552,5569,5580,5597],clip=[276.8,466.2,393.7,476.4],english_start=277.125,native_prefix_edge=5540,fit_word="dicyclohexylcarbodiimide)")
    add(58,'p58-TsCl-full-name','toluenesulfonyl chloride)','톨루엔설포닐 클로라이드)',[6269,6281,6310,6596],clip=[414.5,465.8,525.3,476.],english_start=414.75,native_prefix_edge=6269)
    add(60,'p60-Mosher-acid',"Mosher's acid",'모셔산',[292,354,530],clip=[273.3,415.9,340.1,424.7],english_start=273.875,native_prefix_edge=292)

    for n,labels in rows.items():
        path=B/f'page{n:02}.overrides.json';q=json.loads(path.read_text('utf8'));q['__outlined_vector_labels__']=labels;path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(dict(page=n,labels=[dict(id=v['id'],size=v['size'],baseline=v['point'][1],dx=v['native_caption_path_dx_pt'])for v in labels]),ensure_ascii=False),flush=True)
    (B/'outlined-vector-label-authoring-review.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,pages=rows,exact_source_font_point_metadata_claimed=False,review='Original page45/52/57/58/60 PNGs and high-resolution label crops read; original scientific L-/3D/N,N′-/p-/H/(S)- outline paths retained. Narrow language paths only; original chemical structures/arrows, programs and all remaining coordinates are protected.'),ensure_ascii=False,indent=2)+'\n','utf8')
