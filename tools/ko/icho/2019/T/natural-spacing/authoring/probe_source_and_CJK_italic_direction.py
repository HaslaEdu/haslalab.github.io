"""Measure actual source and authored CJK stem slopes in page coordinates."""
from pathlib import Path
import hashlib,json,math,sys
import pikepdf,pymupdf as f,numpy as np
import natural_plan_compose_icho2019 as c
from engine.source_renderer_font import SourceRendererFontReader,fingerprint
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;out=B/'italic-direction-repro';out.mkdir(exist_ok=True)
source=g.SOURCE.read_bytes();reader=SourceRendererFontReader(source);p=reader.doc[42]
native=[dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(o),bbox=list(b))for t in p.get_texttrace()if t['type']==0 for cp,gid,o,b in t['chars']if chr(cp)=='l'and 'Italic'in t['font']and abs(o[1]-367.8499755859375)<.001]
assert native;chosen=native[0]
refs=[]
for item in p.get_fonts(full=True):
    obj=reader.pdf.get_object((item[0],0));name=str(obj.get('/BaseFont',''));angle=float(obj.get('/FontDescriptor',{}).get('/ItalicAngle',0.))
    if name=='/'+chosen['font']and str(obj.get('/Subtype'))=='/TrueType'and angle:refs.append((obj,angle))
assert len(refs)==1,[(str(v.get('/BaseFont')),a)for v,a in refs];font,angle=refs[0];buffer,kind=reader.resolve(font);source_metric=f.Font(fontbuffer=buffer)
assert source_metric.has_glyph(ord('l'))==chosen['gid'],(source_metric.has_glyph(ord('l')),chosen)
size=chosen['size'];point=f.Point(100,100);scale=48;rows=[]
cases=[('source-native-italic-l','l',buffer,0.),('new-CJK-upright','ㅣ',c.subset_buffer(c.FONTS['serif'],'ㅣ'),0.),('new-CJK-current-descriptor-sign','ㅣ',c.subset_buffer(c.FONTS['serif'],'ㅣ'),angle),('new-CJK-reversed-descriptor-sign','ㅣ',c.subset_buffer(c.FONTS['serif'],'ㅣ'),-angle)]
for name,text,packet,shearangle in cases:
    doc=f.open();pg=doc.new_page(width=220,height=140);pg.insert_font(fontname='Repro',fontbuffer=packet)
    if name.startswith('source'):pg.insert_text(point,text,fontname='Repro',fontsize=size,color=(0,0,0))
    else:c.insert_prose_text(pg,point,text,'Repro',size,(0,0,0),shearangle)
    output=out/(name+'.pdf');doc.save(output,deflate=False);reopened=f.open(output);trace=[t for t in reopened[0].get_texttrace()if t['type']==0];assert len(trace)==1
    cp,gid,origin,bbox=trace[0]['chars'][0]
    if name.startswith('source'):assert gid==chosen['gid']
    pix=reopened[0].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csGRAY,alpha=False,clip=f.Rect(90,80,115,105));png=out/(name+'.png');pix.save(png);a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width);mask=a<128;yy,xx=np.nonzero(mask);lo,hi=int(yy.min()),int(yy.max());height=hi-lo
    centers=[]
    for y in range(lo+math.ceil(height*.2),lo+math.floor(height*.8)+1):
        xs=np.nonzero(mask[y])[0]
        if len(xs):centers.append(((pix.y+y)/scale,(pix.x+float(xs.mean()))/scale))
    ys=np.array([v[0]for v in centers]);xs=np.array([v[1]for v in centers]);slope=float(np.dot(ys-ys.mean(),xs-xs.mean())/np.dot(ys-ys.mean(),ys-ys.mean()))
    up=[x for y,x in centers if y<=ys.min()+(ys.max()-ys.min())*.25];down=[x for y,x in centers if y>=ys.min()+(ys.max()-ys.min())*.75]
    row=dict(case=name,original_pdf_ItalicAngle=angle,authored_pdf_shear_angle=shearangle,actual_character=chr(cp),actual_font=trace[0]['font'],actual_gid=gid,actual_point_size=trace[0]['size'],actual_origin=origin,page_coordinate_stem_dx_per_upward_pt=-slope,upper_minus_lower_stem_center_x_pt=float(np.mean(up)-np.mean(down)),physical_direction='right'if slope<-.01 else'left'if slope>.01 else'upright',pdf=str(output),pdf_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),png=str(png),png_sha256=hashlib.sha256(png.read_bytes()).hexdigest(),raster_scale=scale,threshold=128,middle_stem_bands=[.2,.8]);rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True);reopened.close();doc.close()
assert not reader.doc.is_dirty;report=dict(source_sha256=g.SOURCE_SHA,source_page=43,actual_original_glyph=chosen,source_font_dictionary_sha256=fingerprint(font),source_font_descriptor_ItalicAngle=angle,source_renderer_program_sha256=hashlib.sha256(buffer).hexdigest(),source_renderer_kind=kind,source_renderer_audit=reader.audit,source_font_buffer_unicode_gid_matches_actual_original_trace=True,original_source_pdf_unmodified=True,selected_new_Korean_font=dict(path=str(c.FONTS['serif']),sha256=c.sha(c.FONTS['serif'])),rows=rows,method='Actual source font dictionary resolved by MuPDF without name fallback, actual source l GID retained, and production insert_prose_text used for the Korean vertical jamo stem. All glyphs use the original physical point size. Slopes measured from actual rendered middle-stem ink in PDF page coordinates (upward positive); descriptor convention and emitted PDF cm sign are recorded separately.',probe_program_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(out/'italic-direction-actual-ink-measurement.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
