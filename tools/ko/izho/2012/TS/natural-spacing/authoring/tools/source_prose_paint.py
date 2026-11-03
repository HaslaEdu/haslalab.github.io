"""Read physical source glyph fill/stroke programs, including faux bold."""
def attach_source_paints(runs,page,selected):
 lookup={}
 def key(font,size,c,point):return(font,round(size,3),c,round(point[0],4),round(point[1],4))
 for trace in page.get_texttrace():
  for cp,gid,point,bbox in trace['chars']:
   if chr(cp).isspace():continue
   lookup.setdefault(key(trace['font'],trace['size'],chr(cp),point),[]).append(trace)
 for at in selected:
  span=runs[at];patterns=[];examples=[]
  for char in span['chars']:
   if char['c'].isspace():continue
   traces=lookup.get(key(span['font'],span['size'],char['c'],char['origin']),[])
   if not traces:raise ValueError(('Source glyph paint not resolved',at,char))
   types={t['type']for t in traces}
   if types not in[{0},{0,1}]:raise ValueError(('Source prose paint needs explicit review',at,types))
   fills=[t for t in traces if t['type']==0];strokes=[t for t in traces if t['type']==1]
   fill=fills[0];stroke=strokes[0]if strokes else fill
   if any(abs(t.get('opacity',1)-1)>.00001 for t in traces):raise ValueError('Source prose opacity needs explicit handling')
   width=float(stroke['linewidth'])if strokes else 0
   def rgb(t):
    color=tuple(t['color']);return color*3 if len(color)==1 else color
   pattern=(2 if strokes else 0,round(width,6),rgb(fill),rgb(stroke))
   patterns.append(pattern)
   examples.append(dict(character=char['c'],origin=list(char['origin']),render_types=sorted(types),line_width=width))
  if not patterns:raise ValueError(('Selected prose has no actual source glyph paint',at))
  if len(set(patterns))!=1:raise ValueError(('Mixed source prose paint requires separate literal slots',at,set(patterns)))
  mode,width,fill,stroke=patterns[0]
  span['source_paint']=dict(render_mode=mode,line_width=width,fill_color=list(fill),stroke_color=list(stroke),fill_opacity=1,stroke_opacity=1,source_only=True,glyphs_checked=len(patterns),actual_glyph_evidence=examples)
