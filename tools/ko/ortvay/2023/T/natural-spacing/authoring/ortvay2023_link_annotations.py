"""Translate each original O2023 link Rect with its own native URL subset."""
from pathlib import Path
import hashlib,math
import pikepdf
import pymupdf as fitz

SOURCE_SHA='c0a5117145c67edc2dfe8953dcc7865438f65e099fe6e73b2ec19616ab27b5f7'
EXPECTED={
    1:[('https://youtu.be/ROnxjj5jPDs','https://youtu.be/ROnxjj5jPDs'),
       ('https://en.wikipedia.org/wiki/Tensegrity','https://en.wikipedia.org/wiki/Tensegrity')],
    6:[('https://www.youtube.com/@TrainExperiments','https://www.youtube.com/@TrainExperiments')],
}

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def glyphs(page):
    return [dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),
                 bbox=list(bbox),color=t['color'])
            for t in page.get_texttrace() if t['type']!=3
            for cp,gid,origin,bbox in t['chars']]

def same_origin(a,b,tolerance=1e-5):
    return len(a)==len(b) and max(abs(x-y) for x,y in zip(a,b))<=tolerance

def settings(annotation):
    return {str(k):(('indirect',v.objgen) if getattr(v,'is_indirect',False)
                   else v.unparse() if hasattr(v,'unparse') else repr(v))
            for k,v in annotation.items() if str(k)!='/Rect'}

def adjust_links(target,source,proof,qa):
    page=qa['page']
    assert page in EXPECTED and qa['source_sha256']==SOURCE_SHA
    assert source.number+1==page and proof.number==0
    assert sha(source.parent.name)==SOURCE_SHA,'Actual original document SHA mismatch'
    assert sha(proof.parent.name)==qa['output_sha256'],'Actual reviewed proof SHA mismatch'
    links=[v for v in source.get_links() if v.get('uri')]
    assert len(links)==len(EXPECTED[page])
    original=glyphs(source);visible=glyphs(proof);reports=[]
    for number,(link,(uri,fragment)) in enumerate(zip(links,EXPECTED[page])):
        assert link['uri']==uri
        source_rect=list(link['from']);box=fitz.Rect(source_rect)
        selected=[v for v in original if (fitz.Rect(v['bbox']).tl+fitz.Rect(v['bbox']).br)*.5 in box]
        assert selected and ''.join(v['c'] for v in selected)==fragment
        refs=[];deltas=[];max_error=0.
        for g in selected:
            moved=[(i,j,s) for i,s in enumerate(qa['native_shifts'])
                   for j,v in enumerate(s['glyphs'])
                   if g['c']==v['c'] and same_origin(g['origin'],v['origin'])]
            assert len(moved)<=1,'Ambiguous original URL movement'
            assert not any(g['c']==v['c'] and same_origin(g['origin'],v['origin'])
                           for v in qa['selected_glyphs']),('URL glyph hidden as prose',g)
            index,position,shift=moved[0] if moved else (None,None,None)
            if shift:
                bound=shift['glyphs'][position]
                assert bound['gid']==g['gid'] and bound['font']==g['font']
                assert abs(bound['size']-g['size'])<=.001 and same_origin(bound['bbox'],g['bbox'],.001)
            dx=float(shift['dx']) if shift else 0.
            assert math.isfinite(dx)
            deltas.append(dx)
            expected_origin=[g['origin'][0]+dx,g['origin'][1]]
            matches=[v for v in visible if v['c']==g['c'] and v['gid']==g['gid']
                     and v['font']==g['font'] and abs(v['size']-g['size'])<=.001
                     and same_origin(v['origin'],expected_origin,.001)]
            assert len(matches)==1,('URL native glyph not preserved',g,dx)
            actual=matches[0]
            expected_bbox=[value+(dx if axis%2==0 else 0) for axis,value in enumerate(g['bbox'])]
            error=max([abs(x-y) for x,y in zip(actual['bbox'],expected_bbox)]
                      +[abs(x-y) for x,y in zip(actual['origin'],expected_origin)]
                      +[abs(actual['size']-g['size'])])
            assert error<=.001 and actual['color']==g['color']
            max_error=max(max_error,error)
            refs.append(dict(source_glyph=g,native_shift_index=index,shift_glyph_index=position,dx=dx))
        assert max(deltas)-min(deltas)<1e-8,('One original link rectangle spans differing movements',page,number,deltas)
        dx=deltas[0]
        annots=[v for v in target.obj.get('/Annots',[]) if v.get('/Subtype')==pikepdf.Name('/Link')
                and str(v.get('/A',{}).get('/URI',''))==uri
                and same_origin(list(fitz.Rect(list(map(float,v['/Rect'])))*source.transformation_matrix),source_rect,.001)]
        assert len(annots)==1,('Original annotation URI+rectangle missing or ambiguous',page,number)
        annotation=annots[0]
        assert '/QuadPoints' not in annotation,'Unreviewed quadrilateral hyperlink geometry'
        before=list(map(float,annotation['/Rect']));saved=settings(annotation)
        after=[before[0]+dx,before[1],before[2]+dx,before[3]]
        if dx:annotation['/Rect']=pikepdf.Array(after)
        assert settings(annotation)==saved
        reports.append(dict(schema='reviewed-source-url-subset-v1',page=page,
                            source_link_index=number,uri=uri,display_fragment=fragment,
                            source_rect_pdf=before,target_rect_pdf=after,source_rect_mupdf=source_rect,
                            expected_target_rect_mupdf=[source_rect[0]+dx,source_rect[1],source_rect[2]+dx,source_rect[3]],
                            dx=dx,glyph_references=refs,source_url_glyphs=len(selected),
                            native_url_glyphs_verified_in_proof=True,max_url_glyph_geometry_error_pt=max_error,
                            position_tolerance_pt=.001,only_horizontal_rect_translation=True,
                            other_annotation_settings_preserved=True))
    return reports
