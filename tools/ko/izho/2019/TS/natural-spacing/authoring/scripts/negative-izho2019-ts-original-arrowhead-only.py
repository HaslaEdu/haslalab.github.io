from pathlib import Path
from collections import Counter
import sys,json,hashlib,importlib.util,pikepdf,pymupdf as f
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');E=B/'engine';F=B/'natural/2019/TS';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,_traces,_font_programs
from pdf_original_text_ops import widths
spec=importlib.util.spec_from_file_location('izho2019_literal_original_head_audit','D:/CodexBuilds/audit-izho2019-ts-literal-arrowhead-ink.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
source=F/'page04.pdf';before=sha(source);assert before=='8ed92b19b64974e29fd3d78ca5f814e2610b6865ddce061e6b28ca91fe41c16e';plan=json.loads((F/'plans/page04.json').read_text('utf8'));group=plan['reviewed_complete_original_painted_space_arrow_programs']['groups'][1];out=B/'natural/2019-actual-arrowhead-negative-controls';out.mkdir(exist_ok=True)
with page_worker():
 positive=mod.audit(4,report=out/'page04-positive.json');assert positive['passed'];inv=inspect_inline_groups(str(source),1);forms=[v for v in inv['forms']if v['original_raw_sha256']==group['Form_raw_sha256']];assert len(forms)==1;chosen=forms[0];rows=[]
 for kind in['shifted-1pt','removed']:
  dest=out/f'page04-only-literal-U0020-arrowhead-{kind}.pdf'
  with pikepdf.open(source)as doc:
   node=doc.pages[0]
   for index in chosen['path']:
    inst=list(pikepdf.parse_content_stream(node))[index];assert str(inst.operator)=='Do';node=node.Resources.XObject[inst.operands[0]]
   ops=list(pikepdf.parse_content_stream(node));matches=[]
   for i,inst in enumerate(ops):
    if str(inst.operator)not in['Tj','TJ']:continue
    values=list(inst.operands[0])if str(inst.operator)=='TJ'else[inst.operands[0]]
    if any(isinstance(v,pikepdf.String)and bytes(v)==bytes.fromhex('0526')for v in values):matches.append(i)
   assert len(matches)==1;index=matches[0];inst=ops[index]
   if kind=='shifted-1pt':
    ti=max(i for i in range(index)if str(ops[i].operator)=='Tm');assert not any(str(v.operator)in['Tj','TJ']for v in ops[ti+1:index]);operands=list(ops[ti].operands);operands[4]=float(operands[4])+1;ops[ti]=pikepdf.ContentStreamInstruction(operands,pikepdf.Operator('Tm'))
   else:
    font=node.Resources.Font[pikepdf.Name(group['painted_U0020_head_records'][0]['original_font_resource'])];ws,default=widths(font);values=list(inst.operands[0])if str(inst.operator)=='TJ'else[inst.operands[0]];values=[-(ws.get(1318,default))if isinstance(v,pikepdf.String)and bytes(v)==bytes.fromhex('0526')else v for v in values];ops[index]=pikepdf.ContentStreamInstruction([pikepdf.Array(values)],pikepdf.Operator('TJ'))
   node.write(pikepdf.unparse_content_stream(ops));doc.save(dest,compress_streams=False)
  with pikepdf.open(source)as a,pikepdf.open(dest)as b:assert _font_programs(a.pages[0])==_font_programs(b.pages[0])
  with f.open(source)as a,f.open(dest)as b:
   def signature(g):return(g['c'],g['font'],g['trace_gid'],g['size'],tuple(g['origin']),g['render_mode'],str(g['color']))
   aa=Counter(signature(g)for g in _traces(a[0])if not(g['c']==' 'and g['font']=='CambriaMath'and g['trace_gid']==1318));bb=Counter(signature(g)for g in _traces(b[0])if not(g['c']==' 'and g['font']=='CambriaMath'and g['trace_gid']==1318));assert aa==bb
  negative=mod.audit(4,override=dest,report=out/f'page04-only-head-{kind}.json');assert not negative['passed']and negative['actual_literal_CID_font_GID_point_paint_X_Y_errors']and any(r['missing_actual_original_head_pixels']>0 for r in negative['exact_original_encoded_CID_rgb_checks']);rows.append(dict(kind=kind,bad_PDF_sha256=sha(dest),original_fonts_and_every_other_CID_unchanged=True,actual_head_geometry_and_original_program_rejected=True,missing_head_pixels_by_renderer=negative['exact_original_encoded_CID_rgb_checks'],passed=True));print('SOURCE2019_ACTUAL_ORIGINAL_ARROWHEAD_ONLY_BAD_PDF_REJECTED',kind,flush=True)
 assert sha(source)==before;result=dict(positive_proof_sha256=before,positive_proof_unmodified=True,original_source_sha256=plan['original_english_source_sha256'],controls=rows,passed=all(r['passed']for r in rows));(out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
