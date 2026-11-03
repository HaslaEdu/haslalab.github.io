"""Read actual embedded output glyph outlines and actual native caption paths."""
from pathlib import Path
from io import BytesIO
import hashlib,json,re,sys
import pymupdf as f
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'engine'))
import latex_native_motion as motion
import icho2019_write_guard as g
import natural_plan_compose_icho2019 as c
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(n):
    path=g.PROOFS/f'page{n:02}.pdf';g.assert_output(path,n);q=json.loads(path.with_suffix('.layout.json').read_text('utf8'));labels=q.get('outlined_vector_labels',[])+q.get('raster_labels',[])+q.get('selected_graphic_labels',[])
    assert q['page']==n and Path(q['source']).resolve()==g.SOURCE and q['source_sha256']==g.SOURCE_SHA
    if not labels:return None
    assert sha(path)==q['output_sha256'];doc=f.open(path);page=doc[0];fonts={};fullfonts={};actual=[]
    for entry in page.get_fonts():
        if not entry[4].startswith('KO_Natural_Raster_'):continue
        font=TTFont(BytesIO(doc.extract_font(entry[0])[3]));role=entry[4].removeprefix('KO_Natural_Raster_').replace('_','-');fonts[role]=font
        fullfonts[role]=TTFont(c.FONTS[role])
    for t in page.get_texttrace():
        if t['type']==3 or not t['font'].startswith('Noto'):continue
        for cp,gid,origin,bbox in t['chars']:
            if chr(cp).strip():actual.append(dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),color=list(t['color']),opacity=t['opacity'],render_type=t['type'],colorspace=t['colorspace']))
    inv=motion.inspect_inline_groups(path,1);rows=[]
    for label in labels:
        font=fonts[label['font_role']];full=fullfonts[label['font_role']];fullset=full.getGlyphSet();fullcm=full.getBestCmap();glyphset=font.getGlyphSet();order=font.getGlyphOrder();cm=font.getBestCmap();unit=font['head'].unitsPerEm;x,y=label['point'];rects=[];glyphrows=[];rotate=label.get('rotate',0);dx,dy={0:(1,0),90:(0,-1),180:(-1,0),270:(0,1)}[rotate]
        fullface=full['name'].getDebugName(6);face=lambda s:re.sub('[^a-z0-9]','',s.lower())
        color=label.get('color',0);expected_color=[((color>>k)&255)/255 for k in[16,8,0]]if isinstance(color,int)else list(color)
        assert unit==full['head'].unitsPerEm
        for char in label['text']:
            name=cm[ord(char)];advance=font['hmtx'].metrics[name][0]/unit*label['size']
            if char.strip():
                want=[v for v in actual if v['c']==char and abs(v['size']-label['size'])<.001 and max(abs(v['origin'][0]-x),abs(v['origin'][1]-y))<.001]
                assert len(want)==1,(label['id'],char,x,y,want)
                v=want[0];assert v['gid']>0;actual.remove(v);gn=order[v['gid']];assert gn==name,(label['id'],v,name,gn)
                fullgn=fullcm[ord(char)];fullgid=full.getGlyphID(fullgn)
                assert v['gid']==fullgid,(label['id'],char,v['gid'],fullgid)
                assert face(v['font'])==face(fullface),(label['id'],v['font'],fullface)
                assert v['color']==expected_color and v['opacity']==label.get('opacity',1.)and v['render_type']==0 and v['colorspace']==3
                a=DecomposingRecordingPen(fullset);fullset[fullgn].draw(a);b=DecomposingRecordingPen(glyphset);glyphset[gn].draw(b)
                assert a.value==b.value,(label['id'],char,'Subset outline differs from the pinned full Korean font')
                assert font['hmtx'].metrics[gn]==full['hmtx'].metrics[fullgn]
                v.update(full_reference_font_gid=fullgid,full_reference_glyph_name=fullgn,subset_outline_and_hmtx_equal_full_font=True,drawn_outline_sha256=hashlib.sha256(json.dumps(a.value,separators=(',',':')).encode('utf8')).hexdigest())
                pen=BoundsPen(glyphset);glyphset[gn].draw(pen);r=pen.bounds;assert r
                matrix={0:(1,0,0,-1),90:(0,-1,-1,0),180:(-1,0,0,1),270:(0,1,1,0)}[rotate];a0,b0,c0,d0=matrix;points=[(v['origin'][0]+(a0*u+c0*w)/unit*v['size'],v['origin'][1]+(b0*u+d0*w)/unit*v['size'])for u,w in[(r[0],r[1]),(r[0],r[3]),(r[2],r[1]),(r[2],r[3])]]
                rects.append([min(p[0]for p in points),min(p[1]for p in points),max(p[0]for p in points),max(p[1]for p in points)]);glyphrows.append(v)
            x+=dx*advance;y+=dy*advance
        r=[min(v[0]for v in rects),min(v[1]for v in rects),max(v[2]for v in rects),max(v[3]for v in rects)];error=None
        if label.get('expected_new_korean_ink_bounds'):
            error=max(abs(a-b)for a,b in zip(r,label['expected_new_korean_ink_bounds']));assert error<=.001,(label['id'],r,label['expected_new_korean_ink_bounds'],error)
        if label.get('source_word_right_edge_preserved')is not None:assert abs(r[2]-label['source_word_right_edge_preserved'])<=.001
        edges=[]
        if label.get('source_form_raw_sha256'):
            edit=[e for e in q['reviewed_vector_prose_suppression_audit']if e['source_raw_stream_sha256']==label['source_form_raw_sha256']];assert len(edit)==1;e=edit[0]
            ff=[v for v in inv['forms']if v['original_raw_sha256']==e['translated_raw_stream_sha256']];assert len(ff)==1;ff=ff[0]
        for indices in label.get('source_native_caption_edge_path_indices',[]):
            jj=[j for j,p in enumerate(e['source_form_own_vector_paths'])if p['operator_indices']==indices];assert len(jj)==1
            old=e['source_form_own_vector_paths'][jj[0]];new=ff['own_vector_paths'][jj[0]];clip=f.Rect(label['english_clip_rect']);assert not clip.intersects(f.Rect(old['rect']))
            wanted=[v+(label['native_caption_path_dx_pt']if i%2==0 else 0)for i,v in enumerate(old['rect'])];assert max(abs(a-b)for a,b in zip(wanted,new['rect']))<=1e-7
            edges.append(new['rect'])
        bounds=[r]+edges;center=(min(v[0]for v in bounds)+max(v[2]for v in bounds))/2;center_error=None
        if label.get('source_caption_center_x')is not None:
            center_error=abs(center-label['source_caption_center_x']);assert center_error<=.001,(label['id'],center,label['source_caption_center_x'])
        rows.append(dict(id=label['id'],source_label_kind=label['source_label_kind'],actual_embedded_glyphs=glyphrows,actual_embedded_outline_ink_bbox=r,expected_ink_geometry_error_pt=error,actual_unchanged_native_caption_edge_path_bboxes=edges,actual_mixed_caption_outline_center_x=center,source_caption_center_x=label.get('source_caption_center_x'),center_error_pt=center_error,source_font_point_metadata_available=label.get('source_font_point_and_baseline_metadata_available',False),inference=label.get('outline_inference',label.get('source_font_size_basis')),selected_Korean_full_font=dict(path=str(c.FONTS[label['font_role']]),sha256=sha(c.FONTS[label['font_role']]),postscript_face=fullface,units_per_em=full['head'].unitsPerEm,independent_actual_gid_outline_hmtx_color_opacity_and_render_mode_verified=True)))
    result=dict(page=n,passed=True,proof_sha256=sha(path),measurement_code_sha256=sha(__file__),rows=rows,actual_outline_and_glyph_geometry_tolerance_pt=.001,unchanged_native_caption_path_tolerance_pt=1e-7,new_label_vs_protected_original_ink_pixels=q['new_korean_intrusion_on_native_ink_pixels'])
    assert result['new_label_vs_protected_original_ink_pixels']==0
    q['actual_graphic_label_geometry_audit']=result
    if q.get('outlined_vector_labels'):q['actual_outlined_vector_label_geometry_audit']=result
    path.with_suffix('.layout.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');path.with_suffix('.graphic-label-geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');doc.close();return result
