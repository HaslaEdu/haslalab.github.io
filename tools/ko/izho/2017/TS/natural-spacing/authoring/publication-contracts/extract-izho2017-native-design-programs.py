"""Read actual source/references/final programs. Does not alter any PDF/plan.

The original page program supplies encoded CIDs and literal Tf/Tm/ancestor
clips. The actual final PDF supplies wrapper dictionaries/programs, glyphs,
invocation order and fraction geometry. Publication resolves files by SHA.
"""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,copy
import pikepdf,pymupdf as fitz
B=Path(__file__).resolve().parents[1];E=B/'engine';F=B/'natural/2017/TS';O=Path(__file__).resolve().parent
sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key,widths,source_code_bytes
from izho_2017_independent_original_math_geometry import infer,same,translated
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))
SOURCE='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1'
PROOFS={6:'0f751352301d8ec901bcc1c06180cce70490e3f6d6eb328aa8cdae290c475b25',7:'685e9c601a8e1350244b39dc775a94e57a6b366c484ef6e092e0b95094033db4'}

def obj(v):
    if isinstance(v,pikepdf.Stream):return {'stream_sha256':hashlib.sha256(v.read_bytes()).hexdigest(),'dictionary':{str(k):obj(x)for k,x in v.items()if str(k)not in('/Length','/Filter','/DecodeParms')}}
    if isinstance(v,pikepdf.Dictionary):return {str(k):obj(x)for k,x in sorted(v.items())}
    if isinstance(v,pikepdf.Array):return [obj(x)for x in v]
    if isinstance(v,pikepdf.String):return {'hex':bytes(v).hex()}
    if isinstance(v,pikepdf.Name):return str(v)
    if v is None or isinstance(v,(bool,int,float,str)):return v
    try:return float(v)
    except Exception:return str(v)

def fd(font):
    return obj(font)

def cid_records(page,inv):
    """Original encoded CID + full literal Tm and computed per-CID Tm.

    Cursor advances are independently reconstructed from embedded original
    widths and literal TJ numbers. An inspector's per-show stale Tm is not
    accepted as the physical matrix for every CID in the same run.
    """
    shows={s['operator_index']:s for s in inv['top_level_text_shows']};out=[]
    tm=[1.,0.,0.,1.,0.,0.];tlm=tm[:];leading=0.;stack=[]
    def advance(t,x):
        t[4]+=t[0]*x;t[5]+=t[1]*x
    for oi,op in enumerate(pikepdf.parse_content_stream(page)):
        name=str(op.operator);vals=list(op.operands)
        if name=='q':stack.append(leading)
        elif name=='Q':leading=stack.pop()
        elif name=='BT':tm=[1.,0.,0.,1.,0.,0.];tlm=tm[:]
        elif name=='Tm':tm=list(map(float,vals));tlm=tm[:]
        elif name=='TL':leading=float(vals[0])
        elif name in('Td','TD'):
            x,y=map(float,vals)
            if name=='TD':leading=-y
            tlm[4]+=tlm[0]*x+tlm[2]*y;tlm[5]+=tlm[1]*x+tlm[3]*y;tm=tlm[:]
        elif name=='T*':
            tlm[4]-=tlm[2]*leading;tlm[5]-=tlm[3]*leading;tm=tlm[:]
        if oi not in shows:continue
        assert name in('Tj','TJ'),'Closed original program uses explicit text shows only'
        s=shows[oi];st=s['state'];font=page.Resources.Font[pikepdf.Name(st['active'])];ws,default=widths(font);cb=source_code_bytes(font)
        parts=iter(s['parts']);values=list(vals[0])if name=='TJ'else[vals[0]]
        for value in values:
            if not isinstance(value,pikepdf.String):advance(tm,-float(value)*st['tf']*st['th']/1000);continue
            raw=bytes(value)
            for offset in range(0,len(raw),cb):
                encoded=raw[offset:offset+cb];part=next(parts);code=int.from_bytes(encoded,'big');assert part['raw_hex']==encoded.hex()
                out.append(dict(operator_index=oi,encoded_CID_hex=encoded.hex(),CID=code,font_resource=st['active'],font_signature=fd(font),original_Tf=st['tf'],literal_original_Tm=s['text_matrix'],computed_per_CID_Tm=tm[:],original_CTM=st['ctm'],original_Tc=st['tc'],original_Tw=st['tw'],original_Tz=st['th'],original_Ts=st['ts'],original_Tr=st['tr'],original_ancestor_clips=st['clips'],glyphs=part['glyphs']))
                advance(tm,(ws.get(code,default)/1000*st['tf']+st['tc']+(st['tw']if cb==1 and code==32 else 0))*st['th'])
        assert next(parts,None)is None
    return out

def form_at(doc,page_number,path):
    node=doc.pages[page_number-1]
    for i in path:
        inst=list(pikepdf.parse_content_stream(node))[i];assert str(inst.operator)=='Do';node=node.Resources.XObject[inst.operands[0]]
    return node

def before_ko(doc,page_number,inv,path):
    first=min(s['operator_index']for s in inv['top_level_text_shows']if any('\uac00'<=g['c']<='\ud7a3'for part in s['parts']for g in part['glyphs']))
    stack=[]
    for i,op in enumerate(list(pikepdf.parse_content_stream(doc.pages[page_number-1]))[:first]):
        if str(op.operator)=='q':stack.append(i)
        elif str(op.operator)=='Q':stack.pop()
    assert stack and len(path)==1 and path[0]<stack[-1]
    return dict(wrapper_Do_operator_path=path,first_Korean_text_show_operator=first,first_Korean_prose_q_operator=stack[-1],wrapper_before_first_Korean_prose_q=True)

def match_records(gs,records):
    keys={glyph_key(g)for g in gs};rows=[r for r in records if any(glyph_key(g)in keys for g in r['glyphs'])]
    assert {glyph_key(g)for r in rows for g in r['glyphs']}==keys
    assert len(rows)==len(gs)
    return rows

def compatible(a,b):
    # Operator indices change when unrelated original Do calls are omitted.
    for key in('encoded_CID_hex','CID','font_resource','font_signature','original_Tf','literal_original_Tm','original_CTM','original_Tc','original_Tw','original_Tz','original_Ts','original_Tr'):
        assert a[key]==b[key],key
    assert [x['rect']for x in a['original_ancestor_clips']]==[x['rect']for x in b['original_ancestor_clips']]
    assert max(abs(x-y)for x,y in zip(a['computed_per_CID_Tm'],b['computed_per_CID_Tm']))<1e-8
    assert a['glyphs']==b['glyphs']

def extract():
    pages={}
    for n in(6,7):
        p=read(F/'plans'/f'page{n:02}.json');source=Path(p['original_english_source']);assert sha(source)==p['original_english_source_sha256']==SOURCE
        proof=F/f'page{n:02}.pdf';assert sha(proof)==PROOFS[n];base=Path(p['source_base']);assert sha(base)==p['source_base_sha256'];r=p['reviewed_source2017_complete_original_expression_program_isolation'];assert r['passed']
        expected=[9,6]if n==6 else[4,24,4,14,4,14];assert [len(x['original_glyphs'])for x in r['programs']]==expected
        original=inspect_inline_groups(source,n,include_text_shows=True);actual=inspect_inline_groups(proof,1,include_text_shows=True);initial=inspect_inline_groups(base,n,include_text_shows=True)
        with pikepdf.open(source)as src,pikepdf.open(proof)as final,pikepdf.open(base)as init,fitz.open(proof)as fm:
            original_records=cid_records(src.pages[n-1],original);actual_glyphs=_traces(fm[0]);groups=[]
            for g in r['programs']:
                assert not g['original_source_Form_paths'],'Closed p6/p7 groups are all original top-level CIDs'
                gs=g['original_glyphs'];records=match_records(gs,original_records);refpath=Path(g['reference']);assert sha(refpath)==g['reference_sha256'];ri=inspect_inline_groups(refpath,1,include_text_shows=True)
                with pikepdf.open(refpath)as ref:
                    rr=match_records(gs,cid_records(ref.pages[0],ri));assert len(records)==len(rr)
                    for a,b in zip(records,rr):compatible(a,b)
                    ref_content=ref.pages[0].Contents.read_bytes();refdict=fd(ref.pages[0].Resources.Font)
                af=[v for v in actual['forms']if v['original_raw_sha256']==g['Form_raw_sha256']];bf=[v for v in initial['forms']if v['original_raw_sha256']==g['Form_raw_sha256']];assert len(af)==len(bf)==1
                target=form_at(final,1,af[0]['path']);initialform=form_at(init,n,bf[0]['path']);assert '/Group'not in target and '/Group'not in initialform
                assert target.read_bytes()==initialform.read_bytes();rawsha=hashlib.sha256(target.read_raw_bytes()).hexdigest();assert rawsha==g['Form_raw_sha256']
                decoded=target.read_bytes();assert decoded in(ref_content,b'q\n'+ref_content+b'\nQ',b'q\n'+ref_content+b'\nQ\n'),repr((decoded[:20],ref_content[:20],decoded[-20:],ref_content[-20:]))
                (O/f'page{n:02}-expression{g["index"]}-actual-original-program.bin').write_bytes(target.read_raw_bytes())
                assert fd(target.Resources.Font)==refdict
                dx=infer(gs,actual_glyphs);matches=[]
                for s in gs:
                    hits=[a for a in actual_glyphs if same(s,a)and abs(a['origin'][0]-s['origin'][0]-dx)<.001];assert len(hits)==1;matches.append(hits[0])
                rules=[]
                for v in g['original_source_vector_paths']:
                    hit=[w for w in af[0]['own_vector_paths']if w['paint_operator']==v['paint_operator']and translated(v['rect'],w['rect'],dx)];assert len(hit)==1;rules.append(dict(source=v,actual=hit[0],independent_common_dx=dx,passed=True))
                groups.append(dict(index=g['index'],native_CIDs=len(gs),official_original_CID_records=records,original_reference_CID_records=rr,original_reference_pdf_sha256=sha(refpath),original_reference_decoded_page_program_sha256=hashlib.sha256(ref_content).hexdigest(),wrapper_original_program_sha256=rawsha,wrapper_decoded_program_sha256=hashlib.sha256(decoded).hexdigest(),wrapper_dictionary={k:obj(v)for k,v in target.items()if str(k)not in('/Resources','/Length','/Filter','/DecodeParms')},ordinary_Form_has_no_added_Page_Group=True,original_reference_program_verbatim=True,actual_original_font_resources_identical=True,initial_invocation=before_ko(init,n,initial,bf[0]['path']),actual_invocation=before_ko(final,1,actual,af[0]['path']),original_glyphs=gs,actual_final_glyphs=matches,independently_inferred_common_dx=dx,original_native_fraction_rules=rules,source_CIDs_Tf_Tm_fonts_GIDs_points_paint_clips_and_relative_geometry_preserved=True))
            original_group=obj(src.pages[n-1].obj.get('/Group'));assert obj(final.pages[0].obj.get('/Group'))==original_group==obj(init.pages[n-1].obj.get('/Group'))
        pages[n]=dict(source_page=n,source_sha256=SOURCE,proof_sha256=sha(proof),source_base_sha256=sha(base),original_outer_Page_Group=original_group,original_outer_Page_Group_unchanged=True,groups=groups,all_original_native_records_preserved=True,passed=True)
        print('EXTRACTED_ACTUAL_SOURCE_PROGRAMS',n,expected,flush=True)
    result=dict(kind='source2017-actual-original-CID-program-and-invocation-extraction-v1',original_source_sha256=SOURCE,pages=pages,PDFs_plans_or_proofs_modified=False,passed=True)
    (O/'actual-source-program-extraction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
if __name__=='__main__':
    with page_worker():extract()
