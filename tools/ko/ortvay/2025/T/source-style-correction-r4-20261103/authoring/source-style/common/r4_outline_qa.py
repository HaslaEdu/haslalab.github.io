"""Bind actual CID/TJ/W paints and master outlines to physical glyph geometry."""
from pathlib import Path
from io import BytesIO
from decimal import Decimal
from collections import defaultdict
import hashlib,math,re
import pymupdf as f
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from r4_actual_paint import streams
from r4_font_widths import decimals,to_unicode,ref

def outline_bounds(glyphset,name,matrix):
    pen=BoundsPen(glyphset);glyphset[name].draw(TransformPen(pen,matrix));return pen.bounds

def audit(target,matched,cfg):
    fonts={};masters={};resources={};errors=[];maximum=0.;origin_max=0.;physical=[];count=0
    # MuPDF xref_get_key formats reals to fewer decimal places. Read actual
    # resource numbers independently with PikePDF so exact /W evidence is exact.
    exact_widths={}
    with pikepdf.Pdf.open(target) as pdf:
        for name,font in pdf.pages[0].Resources.Font.items():
            alias=str(name).lstrip('/')
            if alias.startswith('KO_Natural_'):
                desc=font.DescendantFonts[0]
                exact_widths[alias]=decimals(desc.W,desc.get('/DW',1000))
    with f.open(target) as doc:
        pg=doc[0];aliases={v[4]:v for v in pg.get_fonts(full=True) if v[4].startswith('KO_Natural_')}
        for alias,entry in aliases.items():
            xref=entry[0];program=doc.extract_font(xref)[3];font=TTFont(BytesIO(program),recalcTimestamp=False)
            fonts[alias]=font
            descendant=ref(re.findall(r'\d+\s+0\s+R',doc.xref_get_key(xref,'DescendantFonts')[1])[0])
            wk,wr=doc.xref_get_key(descendant,'W')
            if wk=='xref':wr=doc.xref_object(ref(wr),compressed=False);wk='array' if wr.lstrip().startswith('[') else wk
            assert wk=='array'
            widths,default=exact_widths[alias]
            unicode_map=to_unicode(doc.xref_stream(ref(doc.xref_get_key(xref,'ToUnicode')[1])))
            kind,value=doc.xref_get_key(descendant,'CIDToGIDMap')
            if (kind=='name' and value=='/Identity') or (kind=='null' and doc.xref_get_key(descendant,'Subtype')==('name','/CIDFontType2')):gidmap=lambda cid:cid
            elif kind=='xref':
                data=doc.xref_stream(ref(value));gidmap=lambda cid,data=data:int.from_bytes(data[cid*2:cid*2+2],'big')
            elif doc.xref_get_key(descendant,'Subtype')==('name','/CIDFontType0'):
                # MuPDF's CFF Identity-H CID equals the retained original glyph id.
                order=font.getGlyphOrder();charset=font['CFF '].cff.topDictIndex[0].charset
                mapping={int(name[3:]):i for i,name in enumerate(charset) if name.startswith('cid')}
                gidmap=lambda cid,mapping=mapping:mapping.get(cid,cid if cid==0 else -1)
            else:raise ValueError(('Unexpected actual CID/GID encoding',alias,kind,value))
            resources[alias]=dict(widths=widths,default=default,unicode_map=unicode_map,gidmap=gidmap,
                program_sha256=hashlib.sha256(program).hexdigest())
        encoded=defaultdict(list)
        for stream in streams(pg):
            alias=stream['font_alias'];r=resources[alias];cursor=0.;raw=stream['data'];arrays=re.findall(rb'\[(.*?)\]\s*TJ',raw,re.S)
            assert len(arrays)==1,('Unexpected text paint operator',stream['xref'])
            tokens=re.findall(rb'<([0-9A-Fa-f]+)>|([-+]?(?:\d+(?:\.\d*)?|\.\d+))',arrays[0])
            tm=f.Matrix(*stream['text_matrix']);cm=f.Matrix(*stream['cm']);matrix=tm*cm*pg.transformation_matrix
            for hexadecimal,adjustment in tokens:
                if adjustment:cursor-=float(adjustment)*stream['size']/1000;continue
                data=bytes.fromhex(hexadecimal.decode());assert len(data)%2==0
                for i in range(0,len(data),2):
                    cid=int.from_bytes(data[i:i+2],'big');text=r['unicode_map'][cid];assert len(text)==1
                    point=f.Point(cursor,0)*matrix
                    if not text.isspace():encoded[(ord(text),alias)].append(dict(origin=list(point),gid=r['gidmap'](cid),cid=cid,
                        matrix=list(matrix),size=stream['size'],xref=stream['xref'],W=str(r['widths'].get(cid,r['default']))))
                    cursor+=float(r['widths'].get(cid,r['default']))*stream['size']/1000
        details=[];checked_outlines=set()
        for pair in matched:
            expected,actual=pair['expected'],pair['actual'];role=expected['role']
            alias=('KO_Natural_Raster' if cfg['year']==2026 else 'KO_Natural_Raster_'+role.replace('-','_')) if expected['label'] else 'KO_Natural_'+role.replace('-','_')
            candidates=encoded[(expected['cp'],alias)];assert candidates,('Missing encoded actual glyph',expected['cp'],alias)
            j=min(range(len(candidates)),key=lambda j:max(abs(a-b) for a,b in zip(actual['origin'],candidates[j]['origin'])))
            observed=candidates.pop(j);origin_error=max(abs(a-b) for a,b in zip(actual['origin'],observed['origin']));origin_max=max(origin_max,origin_error)
            assert origin_error<=.001,('Actual W/TJ replay differs from trace',observed,actual,origin_error)
            assert observed['gid']==expected['gid']==actual['gid'] and abs(observed['size']-expected['size'])<=1e-6
            path=expected['master_path']
            if path not in masters:masters[path]=TTFont(path,fontNumber=0 if Path(path).suffix.lower()=='.ttc' else -1,recalcTimestamp=False)
            master,subset=masters[path],fonts[alias];gid=expected['gid'];mn=master.getGlyphOrder()[gid];sn=subset.getGlyphOrder()[gid]
            mg,sg=master.getGlyphSet(),subset.getGlyphSet();mu=master['head'].unitsPerEm;su=subset['head'].unitsPerEm;assert mu==su
            assert master['hmtx'][mn]==subset['hmtx'][sn]
            if cfg['year']==2026 and alias=='KO_Natural_serif':
                exact=Decimal(master['hmtx'][mn][0])*Decimal(1000)/Decimal(mu)
                assert Decimal(observed['W'])==exact,('Actual encoded Batang W differs from full-master exact hmtx',gid,observed['W'],str(exact))
            outlinekey=(path,alias,gid)
            if outlinekey not in checked_outlines:
                a,b=DecomposingRecordingPen(mg),DecomposingRecordingPen(sg);mg[mn].draw(a);sg[sn].draw(b)
                assert a.value==b.value,('Master/subset outline changed',alias,gid);checked_outlines.add(outlinekey)
            scale=expected['size']/mu;angle=expected['angle'];rotation=expected['rotation'];x,y=expected['origin']
            if rotation==0:wanted=(scale,0,math.tan(math.radians(angle))*scale,-scale,x,y)
            else:
                # Page y-down physical transform for original rotated raster labels.
                a,b,c,d={90:(0,-1,-1,0),180:(-1,0,0,1),270:(0,1,1,0)}[rotation]
                wanted=(a*scale,b*scale,c*scale,d*scale,x,y)
            am=observed['matrix'];paintscale=observed['size']/su
            actualmatrix=(am[0]*paintscale,am[1]*paintscale,am[2]*paintscale,am[3]*paintscale,*actual['origin'])
            left=outline_bounds(mg,mn,wanted);right=outline_bounds(sg,sn,actualmatrix)
            if left is None:assert right is None;continue
            assert right is not None
            error=max(abs(a-b) for a,b in zip(left,right));maximum=max(maximum,error);count+=1
            if error>.001:errors.append(dict(character=chr(expected['cp']),gid=gid,expected_ink_bbox=left,actual_ink_bbox=right,delta=error,actual_stream=observed))
            if angle:physical.append(dict(character=chr(expected['cp']),source_slot=expected['placement']['id'],actual_cm_c=am[2],master_outline_bbox=left,actual_outline_bbox=right,delta=error))
            details.append(dict(character=chr(expected['cp']),cid=observed['cid'],gid=gid,alias=alias,actual_origin=actual['origin'],replayed_origin=observed['origin'],encoded_W=observed['W']))
        assert not any(encoded.values()),'Actual encoded KO paint contains unaccounted glyphs'
        assert not errors,errors[:8]
    for font in list(fonts.values())+list(masters.values()):font.close()
    return dict(passed=True,actual_CID_TJ_W_glyphs_verified=len(matched),actual_W_TJ_replay_max_origin_error_pt=origin_max,
        actual_master_outline_bounds_verified=count,unique_original_master_subset_outlines_exact=len(checked_outlines),
        master_hmtx_and_gid_exact=True,actual_font_program_sha256={k:v['program_sha256'] for k,v in resources.items()},
        max_transformed_outline_error_pt=maximum,tolerance_pt=.001,errors=[],source_correct_physical_shear_glyphs=physical,encoded_glyph_details=details)
