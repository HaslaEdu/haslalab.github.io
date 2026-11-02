"""Keep each original O2024 link rectangle with its own visible URL glyphs."""
from pathlib import Path
import pikepdf
import pymupdf as fitz

SOURCE_SHA='d7b856084d0159122329b2a3f86f123a2517d99b2f2a05607d9df93acf02f2c9'
EXPECTED=[
 ('https://www.idokep.hu/webkamera/piszkesteto_allsky','https://www.idokep.hu/webkamera/piszkes-'),
 ('https://www.idokep.hu/webkamera/piszkesteto_allsky','teto_allsky'),
 ('https://ccdsh.konkoly.hu/share/allsky/','https://ccdsh.konkoly.hu/share/allsky/'),
 ('https://www.heavens-above.com/AllSats.aspx','https://www.heavens-above.com/AllSats.aspx'),
 ('https://stellarium-web.org/','https://stellarium-web.org/'),
 ('http://stellarium.org/','http://stellarium.org/'),
]

def glyphs(page):
 return [dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(o),bbox=list(bb),color=t['color'])
  for t in page.get_texttrace()if t['type']!=3 for cp,gid,o,bb in t['chars']]

def same_origin(a,b,tolerance=1e-5):
 return max(abs(x-y)for x,y in zip(a,b))<=tolerance

def settings(annotation):
 return {str(k):(('indirect',v.objgen)if getattr(v,'is_indirect',False)else v.unparse()if hasattr(v,'unparse')else repr(v))
  for k,v in annotation.items()if str(k)!='/Rect'}

def adjust_links(target,source,proof,qa):
 assert qa['page']==2 and qa['source_sha256']==SOURCE_SHA
 links=[l for l in source.get_links()if l.get('uri')]
 assert len(links)==len(EXPECTED)
 original=glyphs(source);visible=glyphs(proof);reports=[]
 for number,(link,(uri,fragment))in enumerate(zip(links,EXPECTED)):
  assert link['uri']==uri
  source_rect=list(link['from']);box=fitz.Rect(source_rect)
  selected=[g for g in original if(fitz.Rect(g['bbox']).tl+fitz.Rect(g['bbox']).br)*.5 in box]
  assert ''.join(g['c']for g in selected)==fragment
  assert selected
  refs=[];deltas=[];max_error=0
  for g in selected:
   moved=[(i,j,s)for i,s in enumerate(qa['native_shifts'])for j,v in enumerate(s['glyphs'])
    if g['c']==v['c']and same_origin(g['origin'],v['origin'])]
   assert len(moved)<=1
   assert not any(g['c']==v['c']and same_origin(g['origin'],v['origin'])for v in qa['selected_glyphs']),('URL glyph hidden as prose',g)
   index,position,shift=moved[0]if moved else(None,None,None)
   dx=float(shift['dx'])if shift else 0.0;deltas.append(dx)
   expected_origin=[g['origin'][0]+dx,g['origin'][1]]
   matches=[v for v in visible if v['c']==g['c']and v['gid']==g['gid']and v['font']==g['font']
    and abs(v['size']-g['size'])<=.001 and same_origin(v['origin'],expected_origin,.001)]
   assert len(matches)==1,('URL native glyph not preserved',g,dx)
   actual=matches[0];expected_bbox=[v+(dx if i%2==0 else 0)for i,v in enumerate(g['bbox'])]
   error=max(abs(x-y)for x,y in zip(actual['bbox'],expected_bbox))
   assert error<=.001 and actual['color']==g['color'];max_error=max(max_error,error)
   refs.append(dict(source_glyph=g,native_shift_index=index,shift_glyph_index=position,dx=dx))
  assert max(deltas)-min(deltas)<1e-8,('A single original link rectangle spans differing movements',number,deltas)
  dx=deltas[0]
  annots=[a for a in target.obj.get('/Annots',[])if a.get('/Subtype')==pikepdf.Name('/Link')
   and str(a.get('/A',{}).get('/URI',''))==uri
   and same_origin(list(fitz.Rect(list(map(float,a['/Rect'])))*source.transformation_matrix),source_rect,.001)]
  assert len(annots)==1,('Original annotation rectangle missing/ambiguous',number)
  annotation=annots[0];assert '/QuadPoints'not in annotation
  before=list(map(float,annotation['/Rect']));saved=settings(annotation)
  after=[before[0]+dx,before[1],before[2]+dx,before[3]]
  if dx:annotation['/Rect']=pikepdf.Array(after)
  assert settings(annotation)==saved
  reports.append(dict(schema='reviewed-source-url-subset-v1',page=2,source_link_index=number,uri=uri,display_fragment=fragment,
   source_rect_pdf=before,target_rect_pdf=after,source_rect_mupdf=source_rect,
   expected_target_rect_mupdf=[source_rect[0]+dx,source_rect[1],source_rect[2]+dx,source_rect[3]],
   dx=dx,glyph_references=refs,source_url_glyphs=len(selected),native_url_glyphs_verified_in_proof=True,
   max_url_glyph_geometry_error_pt=max_error,position_tolerance_pt=.001,
   only_horizontal_rect_translation=True,other_annotation_settings_preserved=True))
 assert reports[0]['dx']!=0 and reports[1]['dx']==0 and reports[0]['uri']==reports[1]['uri']
 assert reports[2]['dx']==0
 return reports
