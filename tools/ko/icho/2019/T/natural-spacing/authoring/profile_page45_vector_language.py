from pathlib import Path
import hashlib,json,sys
import pymupdf as f,pikepdf
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'engine'))
import latex_native_motion as m
import icho2019_write_guard as g
inv=m.inspect_inline_groups(g.SOURCE,45);forms=[v for v in inv['forms']if v['path']==[152]];assert len(forms)==1;form=forms[0]
assert form['original_raw_sha256']=='520c2e901afd21f2ed7f9b119953c4a9fee56854e4f9e01cb24bcfb6637d5351'
paths=[v for v in form['own_vector_paths']if f.Rect(v['rect']).intersects(f.Rect(260,150,310,168))]
pdf=pikepdf.Pdf.open(g.SOURCE);pg=pdf.pages[44];instructions=pikepdf.parse_content_stream(pg);ins=instructions[152];assert str(ins.operator)=='Do';obj=pg.Resources.XObject[ins.operands[0]];assert hashlib.sha256(obj.read_raw_bytes()).hexdigest()==form['original_raw_sha256']
out=B/'source-vector-labels';out.mkdir(exist_ok=True);(out/'page45-form152-original.decoded').write_bytes(obj.read_bytes())
data=dict(source_sha256=g.SOURCE_SHA,form=form,source_form_dictionary={str(k):str(v)[:1500]for k,v in obj.items()if str(k)not in['/Length']},label_region_candidate=[260,150,310,168],paths_in_candidate_region=paths)
(out/'page45-form152-profile.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
doc=f.open(g.SOURCE);doc[44].get_pixmap(matrix=f.Matrix(4,4),alpha=False,clip=f.Rect(260,150,310,168)).save(out/'page45-catalyst-source4x.png')
print(json.dumps(dict(dictionary=data['source_form_dictionary'],paths=paths),ensure_ascii=False),flush=True)
