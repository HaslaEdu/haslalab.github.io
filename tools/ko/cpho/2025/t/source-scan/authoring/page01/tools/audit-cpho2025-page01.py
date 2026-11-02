from pathlib import Path
from collections import Counter,defaultdict
from io import BytesIO
import sys,json,hashlib,re,time
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');PUB=Path('D:/CodexBuilds/Hasla-publish-20261031')
sys.path[:0]=['D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools',str(PUB/'tools')]
import pymupdf as fitz,pikepdf
import numpy as np,cv2
from fontTools.ttLib import TTFont
from pdf_scanned_translation_ink_qa import audit_scan_page,render,summary
from pdf_memory_gate import page_worker
import pdf_new_prose_outlines as outlines
from izho_new_prose_outline_qa import trace_font_resources
SOURCE=B/'CPhO_2025_T_original-explicit-page-clip.pdf';OUT=B/'page01-draft'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def math_visibility(control,final,prose,output):
    # Reference only: union original replay ink while removing opaque padding.
    # The actual PDF, source images, source clips and source scale remain intact.
    with pikepdf.open(control)as pdf:
        page=pdf.pages[0];streams=[s.read_bytes()for s in page.Contents]
        candidates=[b for b in streams if b.startswith(b'Q\nq\n/OriginalRasterReset gs')]
        if len(candidates)!=1:raise ValueError('No unique complete original-math replay stream')
        page.Resources.ExtGState.OriginalRasterReset.BM=pikepdf.Name.Multiply
        page.Contents=pdf.make_stream(b'q\n'+candidates[0]);pdf.save(output,compress_streams=False)
    expected=render(output);actual=render(final);new=render(prose)
    missing=(expected<160)&(actual>240);overlap=(expected<180)&(new<180)
    return dict(method='QA-only isolated original-image clip replay union with Multiply; final PDF unchanged.',reference_sha256=sha(output),original_math_ink_expected_pixels=int((expected<160).sum()),missing=summary(missing,4),overlap_new_prose=summary(overlap,4),passed=not missing.any()and not overlap.any())
def style_audit(target,evidence):
    entries=[dict(p,alias='/'+p.get('alias','DraftBody'))for p in evidence['prose_placements']if p['text'].strip()]
    entries +=[dict(p,alias='/Header'+p['face'],stroke=p['user_space_stroke_width_pt'])for p in evidence['header_prose_placements']if p['text'].strip()]
    expected=Counter();actual=defaultdict(list);errors=[]
    with pikepdf.open(target)as pdf,fitz.open(target)as doc:
        page=doc[0];metrics={};font_shas={}
        for alias,font in pdf.pages[0].Resources.Font.items():
            desc=font.DescendantFonts[0].FontDescriptor;key=next(k for k in['/FontFile2','/FontFile3']if k in desc)
            data=desc[key].read_bytes();font_shas[str(alias)]=hashlib.sha256(data).hexdigest()
            # Match the actual postscript name for analysis only; PDF bytes stay untouched.
            if key=='/FontFile2':
                with TTFont(BytesIO(data))as f:font.BaseFont=pikepdf.Name('/'+f['name'].getDebugName(6))
        mapped,_=trace_font_resources(pdf,page);traces=page.get_texttrace()
        for xref,ext,kind,name,alias,encoding in page.get_fonts():metrics['/'+alias]=fitz.Font(fontbuffer=doc.extract_font(xref)[3])
        widths=[]
        for i,p in enumerate(entries):
            metric=metrics[p['alias']];w=sum(p['size']/4 if c==' 'else metric.text_length(c,fontsize=p['size'])for c in p['text']);widths.append(w)
            expected[i]=sum(not c.isspace()for c in p['text'])
        for g in mapped:
            if g['c'].isspace():continue
            matches=[i for i,p in enumerate(entries)if p['alias']==g['font_alias']and abs(p['size']-g['size'])<.001 and abs(p['point'][1]-g['origin'][1])<.001 and p['point'][0]-.001<=g['origin'][0]<p['point'][0]+widths[i]+.001]
            if len(matches)!=1:errors.append(dict(reason='No unique authored size/baseline/face interval',glyph=g));continue
            i=matches[0];p=entries[i];actual[i].append(g)
            if g['render_type']!=2:errors.append(dict(reason='New prose lost declared fill-and-stroke mode',glyph=g))
            strokes=[t['linewidth']for t in traces if t['type']==1 and abs(t['size']-g['size'])<.001 and any(cp==ord(g['c'])and gid==g['gid']and max(abs(point[k]-g['origin'][k])for k in[0,1])<.001 for cp,gid,point,bbox in t['chars'])]
            if not strokes or any(abs(s-p['stroke'])>1e-5 for s in strokes):errors.append(dict(reason='Original-source-estimated font stroke changed',glyph=g,expected=p['stroke'],actual=strokes))
        for i,p in enumerate(entries):
            chars=''.join(g['c']for g in sorted(actual[i],key=lambda g:g['origin'][0]))
            wanted=''.join(p['text'].split())
            if chars!=wanted:errors.append(dict(reason='Authored language glyph sequence differs',entry=i,expected=wanted,actual=chars))
    return dict(actual_new_prose_glyphs_checked=sum(len(a)for a in actual.values()),actual_embedded_font_programs=font_shas,style_size_baseline_paint_or_sequence_failures=errors,passed=not errors)
def audit(lang):
    target=OUT/f'page01-{lang}-draft.pdf';e=json.loads(target.with_suffix('.json').read_text('utf8'));plan=json.loads((B/'authoring/page01-draft-layout.json').read_text('utf8'))
    assert sha(target)==e['proof_sha256']and sha(SOURCE)==e['source_sha256']and sha(B/'authoring/page01-draft-layout.json')==e['authoring_sha256']
    with page_worker():
        # Metric text bboxes can exclude real Noto Sans overhang. Declare only
        # actual intended prose component bounds from the independent blank-page
        # reference, including AA; never relax source figure/math protection.
        with fitz.open(OUT/f'page01-{lang}-prose-only.pdf')as d:
            pix=d[0].get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csGRAY,alpha=False)
        ink=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<255
        _,_,stats,_=cv2.connectedComponentsWithStats(ink.astype(np.uint8),8)
        new_boxes=[[int(x)/4,int(y)/4,int(x+w)/4,int(y+h)/4]for x,y,w,h,area in stats[1:]]
        del ink,stats,pix
        q=audit_scan_page(SOURCE,1,target,OUT/f'page01-{lang}-pre-prose.pdf',OUT/f'page01-{lang}-prose-only.pdf',
            language_erase_rects=[[155,85,447,107],[230,106,375,124],[82,137,497,163]]+[r for row in plan['rows']for r in row['erase_rects']],
            new_prose_rects=new_boxes,
            original_inline_math_rects=[a['source_rect']for a in e['math_replay']['atoms']],
            moved_inline_math_rects=[a['destination_rect']for a in e['math_replay']['atoms']],
            protected_source_rects=[[407.5,176,536.5,264.4],[397,562,535,593.2],[145,508.5,456,528],[376,684,467,721],[220,721.5,374,765]],
            replayed_math_records=e['math_replay']['atoms'])
        old=outlines.PREFIXES
        try:outlines.PREFIXES=('/Draft','/Header');q['actual_new_prose_outlines']=outlines.audit(target)
        finally:outlines.PREFIXES=old
        q['actual_new_prose_styles']=style_audit(target,e)
        q['independent_original_replayed_math_visibility']=math_visibility(OUT/f'page01-{lang}-pre-prose.pdf',target,OUT/f'page01-{lang}-prose-only.pdf',target.with_suffix('.math-union-reference.pdf'))
        q['new_prose_allowed_bounds_source']='Actual4x blank-page prose-only reference connected ink component bounds, including antialiasing and source-estimated stroke; source math/figures independently protected without change.'
        q['actual_prose_ink_components']=len(new_boxes)
        q['passed']=q['passed']and q['actual_new_prose_outlines']['passed']and q['actual_new_prose_styles']['passed']and q['independent_original_replayed_math_visibility']['passed']
        q['status']='DRAFT_QA_PASS_REQUIRES_VISUAL_REVIEW'if q['passed']else'DRAFT_QA_FAILED_NOT_FOR_PUBLICATION'
        target.with_suffix('.scan-qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
        print(json.dumps(dict(language=lang,passed=q['passed'],outside=q['outside_declared_language_and_math_motion'],protected=q['independent_protected_source_ink_lost'],collision=q['new_prose_overlap_original_or_replayed_nonlanguage_ink'],missing=q['new_prose_expected_dark_pixels_missing'],style_errors=len(q['actual_new_prose_styles']['style_size_baseline_paint_or_sequence_failures']))),flush=True)
    time.sleep(.6)
for lang in(sys.argv[1:]or['ko','en']):audit(lang)
