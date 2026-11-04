"""Real damaged PDFs, each changing one source/design requirement."""
from pathlib import Path
from io import BytesIO
from decimal import Decimal
import sys,json,hashlib,re
import pikepdf,pymupdf as f,numpy as np
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups
from cpho2008_original_CID_states import audit as cid_audit
from cpho2008_independent_native_qa import audit as native_audit
from cpho2008_new_prose_qa import audit as prose_audit
from cpho2008_bitmap_language_qa import audit as bitmap_audit,rgb
from cpho2008_atomic_authoring import atomic_text
S=B/'source/CPhO_2008_original_combined_ZH.pdf';SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text('utf8'))
H=B/'actual-negative-PDF-controls';H.mkdir(exist_ok=True)
def chunks(page):return list(page.Contents)if isinstance(page.Contents,pikepdf.Array)else[page.Contents]
class Tokens(pikepdf.TokenFilter):
    def __init__(self):super().__init__();self.items=[]
    def handle_token(self,token):self.items.append((token.type_,token.raw_value));return token
def exact_operator_replacements(page,stream_index,replacements):
    all_chunks=chunks(page);stream=all_chunks[stream_index];page.Contents=stream
    tokens=Tokens();raw=page.get_filtered_contents(tokens);ops=list(pikepdf.parse_content_stream(page));ranges=[];start=offset=0
    for kind,value in tokens.items:
        offset+=len(value)
        if kind==pikepdf.TokenType.word:ranges.append((start,offset,value.decode('ascii')));start=offset
    assert len(ranges)==len(ops)and all(r[2]==str(o.operator)for r,o in zip(ranges,ops))
    parts=[];cursor=0
    for index,replacement in sorted(replacements.items()):
        a,z,_=ranges[index];parts.extend([raw[cursor:a],re.match(rb'\s*',raw[a:z])[0],replacement]);cursor=z
    parts.append(raw[cursor:]);stream.write(b''.join(parts));page.Contents=pikepdf.Array(all_chunks)
def original_stream_index(page):
    content=chunks(page);assert content[0].read_bytes()==b'q\n' and content[2].read_bytes()==b'\nQ\n'
    return 1
def first_original_show(page):
    stream_index=original_stream_index(page);ops=list(pikepdf.parse_content_stream(chunks(page)[stream_index]));active=None
    for i,op in enumerate(ops):
        if str(op.operator)=='Tf':active=i
        if str(op.operator)in('Tj','TJ'):
            strings=[v for v in op.operands[0]if isinstance(v,pikepdf.String)]if str(op.operator)=='TJ'else[op.operands[0]]
            if any(bytes(v)for v in strings):assert active is not None;return ops,i,active,stream_index
    raise ValueError('No actual original native show')
def append_white(pdf,rect):
    page=pdf.pages[0];height=float(page.MediaBox[3]);x,y,w,h=rect
    program=f'q 1 1 1 rg {x:.8f} {height-y-h:.8f} {w:.8f} {h:.8f} re f Q\n'.encode()
    page.Contents=pikepdf.Array(chunks(page)+[pdf.make_stream(program)])
def make(kind,n):
    source=B/f'proofs/ko/page{n:02}.pdf';positive=sha(source);target=H/f'{kind}-source{n:02}-positive-{positive[:16]}.pdf';details={}
    if target.exists():return target,positive,details
    with pikepdf.open(source)as pdf:
        page=pdf.pages[0]
        if kind=='single-original-fraction-bar-dx':
            inv=inspect_inline_groups(source,1);candidates=[v for v in inv['vector_paths']if v['rect'][3]-v['rect'][1]<1 and 10<v['rect'][2]-v['rect'][0]<80 and 90<v['rect'][0]<400]
            chosen=candidates[0];stream_index=original_stream_index(page);ops=list(pikepdf.parse_content_stream(chunks(page)[stream_index]));replacements={};prefix=sum(len(list(pikepdf.parse_content_stream(s)))for s in chunks(page)[:stream_index])
            for combined_index in chosen['operator_indices']:
                i=combined_index-prefix
                op=ops[i];name=str(op.operator);args=list(op.operands)
                if name in('m','l','re'):args[0]=Decimal(str(args[0]))+Decimal('2')
                else:continue
                replacements[i]=pikepdf.unparse_content_stream([pikepdf.ContentStreamInstruction(args,op.operator)]).rstrip()
            assert replacements;exact_operator_replacements(page,stream_index,replacements);details=dict(original_path=chosen,only_selected_path_operator_x_delta=2)
        elif kind=='one-original-native-Tf-point':
            ops,show,at,index=first_original_show(page);op=ops[at];args=list(op.operands);args[1]=Decimal(str(args[1]))+Decimal('.25');exact_operator_replacements(page,index,{at:pikepdf.unparse_content_stream([pikepdf.ContentStreamInstruction(args,op.operator)]).rstrip()});details=dict(original_Tf=list(map(str,op.operands)),delta_pt=.25)
        elif kind=='one-original-native-ancestor-clip':
            ops,show,at,index=first_original_show(page);literal=pikepdf.unparse_content_stream([ops[show]]).rstrip();exact_operator_replacements(page,index,{show:b'q 0 0 1 1 re W n\n'+literal+b'\nQ'});details=dict(native_show_index=show,added_clip=[0,0,1,1])
        elif kind=='one-new-prose-glyph-Tf-point':
            index=next(i for i,s in enumerate(chunks(page))if b'/C08Translated'in s.read_bytes());ops=list(pikepdf.parse_content_stream(chunks(page)[index]));at=next(i for i,op in enumerate(ops)if str(op.operator)=='Tf');op=ops[at];args=list(op.operands);args[1]=Decimal(str(args[1]))+Decimal('.25');exact_operator_replacements(page,index,{at:pikepdf.unparse_content_stream([pikepdf.ContentStreamInstruction(args,op.operator)]).rstrip()});details=dict(new_glyph_stream=index,delta_pt=.25)
        elif kind=='added-original-absent-PageGroup':
            assert '/Group'not in page.obj;page.obj.Group=pikepdf.Dictionary(S=pikepdf.Name('/Transparency'),CS=pikepdf.Name('/DeviceRGB'),I=True,K=False);details=dict(original_PageGroup=None,added_ordinary_transparency_group=True)
        elif kind=='one-unrelated-circuit-wire-pixel-white':
            report=read(B/'proofs/ko/page04.bitmap-language-native-source-audit.json');aa=rgb(report['actual_original_graphics_control_path']);roi=aa[1600:1840,510:700];yy,xx=np.where(roi.min(2)<32);assert len(xx);x,y=int(xx[len(xx)//2]+510),int(yy[len(yy)//2]+1600);append_white(pdf,[x/4,y/4,.25,.25]);details=dict(original_wire_RGB=aa[y,x].tolist(),exact_original_4x_pixel=[x,y],white_cover_point_rect=[x/4,y/4,.25,.25])
        elif kind=='complete-new-island-label-over-circuit-wire':
            indices=[i for i,s in enumerate(chunks(page))if b'/C08BitmapLabelSerifBold'in s.read_bytes()][:4];assert len(indices)==4
            for index in indices:
                ops=list(pikepdf.parse_content_stream(chunks(page)[index]));at=next(i for i,op in enumerate(ops)if str(op.operator)=='Tm');op=ops[at];args=list(op.operands);args[4]=Decimal(str(args[4]))+Decimal('20');exact_operator_replacements(page,index,{at:pikepdf.unparse_content_stream([pikepdf.ContentStreamInstruction(args,op.operator)]).rstrip()})
            details=dict(complete_first_translated_label_glyphs=4,original_point_font_and_baseline_unchanged=True,dx_pt=20)
        else:raise ValueError(kind)
        pdf.save(target,compress_streams=False)
    assert sha(source)==positive and sha(target)!=positive
    atomic_text(target.with_suffix('.mutation.json'),json.dumps(dict(kind=kind,original_source_sha256=SHA,source_page=n,positive_proof_sha256=positive,actual_bad_PDF_sha256=sha(target),actual_bad_PDF_bytes=target.stat().st_size,details=details),indent=2)+'\n')
    return target,positive,details
cases=[('single-original-fraction-bar-dx',15,'native'),('one-original-native-Tf-point',15,'cid'),('one-original-native-ancestor-clip',15,'cid'),('one-new-prose-glyph-Tf-point',1,'prose'),('added-original-absent-PageGroup',1,'native'),('one-unrelated-circuit-wire-pixel-white',4,'bitmap'),('complete-new-island-label-over-circuit-wire',4,'bitmap')]
summary=[]
for kind,n,phase in cases:
    with page_worker():
        positive=B/f'proofs/ko/page{n:02}.pdf';proof_pin=sha(positive);target,pin,details=make(kind,n);c=read(positive.with_suffix('.composition.json'));result=None;error=None
        try:
            if phase=='native':result=native_audit(n,'ko',target)
            elif phase=='prose':result=prose_audit(n,'ko',target)
            elif phase=='cid':result=cid_audit(S,n,target,read(B/f'inspection/page{n:02}-original-native-programs.json'),inspect_inline_groups(target,1,include_text_shows=True),c['erased_original_language_glyphs'])
            else:result,_=bitmap_audit(n,'ko',target,c,dict(changed_nonselected_native_graphical_pixels=-1))
            rejected=result['passed']is False
        except Exception as exc:rejected=True;error=repr(exc)
        assert rejected,(kind,result);assert sha(positive)==proof_pin
        row=dict(kind=kind,source_page=n,phase=phase,original_source_sha256=SHA,positive_proof_sha256=proof_pin,actual_bad_PDF_path=str(target),actual_bad_PDF_sha256=sha(target),actual_bad_PDF_bytes=target.stat().st_size,actual_PDF_rejected=True,positive_PDF_unmodified=True,actual_failed_audit=result,actual_rejection_exception=error)
        atomic_text(target.with_suffix('.actual-rejection.json'),json.dumps(row,ensure_ascii=False,indent=2)+'\n');summary.append(row);print('C08_ACTUAL_BAD_PDF_REJECTED',kind,sha(target),flush=True)
assert len({r['actual_bad_PDF_sha256']for r in summary})==7
atomic_text(H/'all7-actual-source-native-design-negatives.json',json.dumps(dict(original_source_sha256=SHA,actual_unique_bad_PDFs=summary,passed=all(r['actual_PDF_rejected']and r['positive_PDF_unmodified']for r in summary)),ensure_ascii=False,indent=2)+'\n')
