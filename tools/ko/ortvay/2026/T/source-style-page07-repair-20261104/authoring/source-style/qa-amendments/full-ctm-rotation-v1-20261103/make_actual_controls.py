"""One-shot actual PDF controls. Never changes a source proof or layout."""
from pathlib import Path
import hashlib,json,math,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'common'));sys.path.insert(0,str(HERE))
import pymupdf as f
from amended_actual_paint import streams,glyphs,canonical_glyphs,SIX

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),sha256=sha(p))
def numbers(values):return ' '.join(format(v,'.12g') for v in values)
def replace_cm(data,values):
    found=list(re.finditer(SIX+rb'\s+cm',data));assert len(found)==1
    hit=found[0];return data[:hit.start()]+(numbers(values)+' cm').encode()+data[hit.end():]
def raw_tm(data):
    found=re.findall(SIX+rb'\s+Tm',data);assert len(found)==1;return list(map(float,found[0]))
def keep_anchor_cm(data,linear):
    old=list(map(float,re.findall(SIX+rb'\s+cm',data)[0]));tm=raw_tm(data);x,y=tm[4:]
    a,b,c,d=linear
    return replace_cm(data,[a,b,c,d,old[4]+(old[0]-a)*x+(old[2]-c)*y,old[5]+(old[1]-b)*x+(old[3]-d)*y])

def main():
    manifest=HERE/'CASES.json';cases=json.loads(manifest.read_text('utf8'));out=HERE/'actual-pdf-controls'
    assert not out.exists();out.mkdir();made=[]
    p7=cases['cases']['p7_rotated_label'];p1=cases['cases']['2025p1_combined_row_italic']
    with f.open(p7['target']['path']) as doc:
        yaxis=next(v for v in streams(doc[0]) if not v['horizontal'])
        ordinary=next(v for v in streams(doc[0]) if v['font_alias']=='KO_Natural_serif' and v['horizontal'])
    with f.open(p1['target']['path']) as doc:italic=next(v for v in streams(doc[0]) if v['cm'][2]>0)

    def make(name,base,record,newdata=None,prefix=None,half=False,expected='REJECT'):
        source=Path(base['target']['path']);before=sha(source);target=out/(name+'.pdf')
        with f.open(source) as doc:
            page=doc[0];original=page.get_contents();unchanged={x:doc.xref_stream(x) for x in original if x!=record['xref']}
            if newdata is not None:doc.update_stream(record['xref'],newdata)
            if prefix is not None:
                if half:
                    k,v=doc.xref_get_key(page.xref,'Resources')
                    if k=='xref':res=int(v.split()[0])
                    else:
                        assert k=='dict';res=doc.get_new_xref();doc.update_object(res,v);doc.xref_set_key(page.xref,'Resources',f'{res} 0 R')
                    gsx=doc.get_new_xref();doc.update_object(gsx,'<< /Type /ExtGState /ca .5 /CA .5 >>')
                    k,v=doc.xref_get_key(res,'ExtGState')
                    if k=='null':doc.xref_set_key(res,'ExtGState',f'<< /QA_Half {gsx} 0 R >>')
                    elif k=='xref':
                        gx=int(v.split()[0]);value=doc.xref_object(gx,compressed=False);doc.update_object(gx,value.rstrip()[:-2]+f' /QA_Half {gsx} 0 R >>')
                    else:
                        assert k=='dict';doc.xref_set_key(res,'ExtGState',v.rstrip()[:-2]+f' /QA_Half {gsx} 0 R >>')
                first=doc.get_new_xref();doc.update_object(first,'<<>>');doc.update_stream(first,prefix)
                last=doc.get_new_xref();doc.update_object(last,'<<>>');doc.update_stream(last,b'Q\n')
                index=original.index(record['xref']);items=original[:index]+[first,record['xref'],last]+original[index+1:]
                doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{x} 0 R' for x in items)+']')
            doc.save(target,garbage=0,deflate=False)
        assert sha(source)==before
        with f.open(target) as doc:
            assert all(doc.xref_stream(x)==data for x,data in unchanged.items()),'A different content stream changed'
            try:
                ss=streams(doc[0]);parser_result=dict(rejected=False,streams=len(ss))
            except AssertionError as error:parser_result=dict(rejected=True,message=str(error))
        cases['cases'][name]=dict(year=base['year'],page=base['page'],target=pin(target),layout=base['layout'],expected=expected,
            role='actual_pdf_transform_control',source_proof=base['target'],source_new_KO_xref=record['xref'])
        made.append(dict(case=name,expected=expected,source=base['target'],target=pin(target),
            only_named_KO_stream_and_declared_prefix_changed=True,entry_parser=parser_result))

    data=yaxis['data'];cmhit=list(re.finditer(SIX+rb'\s+cm',data))[0]
    def cm_text(text):return data[:cmhit.start()]+text+data[cmhit.end():]
    make('positive_nested_q_Q_restore',p7,yaxis,cm_text(b'q\n1 0 .125 1 17 23 cm\nQ\n0 1 -1 0 0 0 cm'),expected='PASS')
    # PDF row-vector concatenation: second*first=R90, reversed order differs.
    make('positive_noncommuting_CM',p7,yaxis,cm_text(b'2 0 0 1 0 0 cm\n0 1 -.5 0 0 0 cm'),expected='PASS')
    fused=list(f.Matrix(*raw_tm(data))*f.Matrix(0,1,-1,0,0,0));value=cm_text(b'')
    value,n=re.subn(SIX+rb'\s+Tm',(numbers(fused)+' Tm').encode(),value);assert n==1
    make('positive_rotation_in_Tm',p7,yaxis,value,expected='PASS')
    for name,angle in [('negative_body_left_shear',-14),('negative_wrong_right_shear13',13)]:
        make(name,p1,italic,keep_anchor_cm(italic['data'],[1,0,math.tan(math.radians(angle)),1]))
    angle=math.radians(89)
    make('negative_wrong_rotation89',p7,yaxis,keep_anchor_cm(data,[math.cos(angle),math.sin(angle),-math.sin(angle),math.cos(angle)]))
    make('negative_rotated_hidden_left_shear',p7,yaxis,keep_anchor_cm(data,[-math.tan(math.radians(14)),1,-1,0]))
    tm=raw_tm(data);tm[4]+=.01;value,n=re.subn(SIX+rb'\s+Tm',(numbers(tm)+' Tm').encode(),data);assert n==1
    make('negative_Tm_shift_point01',p7,yaxis,value)
    make('negative_scale1point001',p7,yaxis,keep_anchor_cm(data,[0,1.001,-1.001,0]))
    make('negative_drop_vertical_label',p7,yaxis,b'')
    otm=raw_tm(ordinary['data']);x,y=otm[4:];rotation=f.Matrix(0,1,-1,0,x+y,y-x)
    value,n=re.subn(SIX+rb'\s+Tm',(numbers(list(rotation))+' cm\n'+numbers(otm)+' Tm').encode(),ordinary['data']);assert n==1
    make('negative_unplanned_body_rotation',p7,ordinary,value)
    make('negative_inherited_entry_CTM',p1,italic,prefix=b'q\n1 0 0 1 .01 0 cm\n')
    make('negative_inherited_half_opacity',p1,italic,prefix=b'q\n/QA_Half gs\n',half=True)
    manifest.write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n','utf8')
    (out/'creation-manifest.json').write_text(json.dumps(dict(cases=made,source_proofs_never_modified=True),ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(created=len(made),manifest=pin(out/'creation-manifest.json'),cases_manifest=pin(manifest)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
