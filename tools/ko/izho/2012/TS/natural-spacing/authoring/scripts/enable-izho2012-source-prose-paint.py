from pathlib import Path
import hashlib,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');p=B/'engine/izho_initial_fixed_style.py';s=p.read_text('utf8');before=hashlib.sha256(p.read_bytes()).hexdigest()
if 'attach_source_paints(runs,page,paint_scope)'not in s:
 old='    runs=runs_of(page);selected=[];work=[];all_text=defaultdict(str)'
 new="""    runs=runs_of(page);selected=[];work=[];all_text=defaultdict(str)
    if data['source_sha256']=='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db':
        from source_prose_paint import attach_source_paints
        paint_scope={tuple(slot['at'])for slot in data['slots']}
        paint_scope|={tuple(part['style_from'])for slot in data['slots']for part in slot.get('parts',[])if 'style_from'in part}
        attach_source_paints(runs,page,paint_scope)"""
 assert old in s;s=s.replace(old,new)
 old="            style=chunk['style'];size=style['size'];color=tuple(((style['color']>>n)&255)/255 for n in [16,8,0])"
 new=old+"\n            paint=style.get('source_paint',dict(render_mode=0,line_width=0,fill_color=list(color),stroke_color=list(color),fill_opacity=1,stroke_opacity=1))\n            mode=paint['render_mode'];line_width=paint['line_width'];fill=paint['fill_color'];stroke=paint['stroke_color']"
 assert old in s;s=s.replace(old,new)
 old="0 Tc 0 Tw 0 Tr {color[0]:.6f} {color[1]:.6f} {color[2]:.6f} rg 1 0 0 1"
 new="0 Tc 0 Tw {mode} Tr {line_width:.8f} w {fill[0]:.6f} {fill[1]:.6f} {fill[2]:.6f} rg {stroke[0]:.6f} {stroke[1]:.6f} {stroke[2]:.6f} RG 1 0 0 1"
 assert old in s;s=s.replace(old,new)
 old="font='KO_'+chunk['role'].replace('-','_');out.insert_text((x,y),chunk['text'],fontname=font,fontsize=size,color=color,morph=morph)"
 new="font='KO_'+chunk['role'].replace('-','_');out.insert_text((x,y),chunk['text'],fontname=font,fontsize=size,color=stroke,fill=fill,morph=morph,render_mode=mode,border_width=line_width/size if mode==2 else 1,fill_opacity=paint['fill_opacity'],stroke_opacity=paint['stroke_opacity'])"
 assert old in s;s=s.replace(old,new)
 old='point=[x,y],oblique_angle=angle))'
 assert old in s;s=s.replace(old,'point=[x,y],oblique_angle=angle,source_paint=paint))')
 p.write_text(s,'utf8')
(B/'source-prose-paint-preservation.json').write_text(json.dumps(dict(source_sha256='41a2fa97853ffdf4ee0bc3a2e665c79387741beeff41d6cc9df29591335410db',private_engine_before_sha256=before,private_engine_after_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_only_actual_glyph_fill_stroke_programs=True,original_source_point_and_color_preserved=True,source_faux_bold_preserved_by_actual_stroke_width=True,source_fonts_math_and_gray_field_graphics_not_modified=True,body_font_fitting=False),indent=2)+'\n','utf8')
print('SOURCE2012_ACTUAL_PROSE_FILL_STROKE_PRESERVATION_ENABLED')
