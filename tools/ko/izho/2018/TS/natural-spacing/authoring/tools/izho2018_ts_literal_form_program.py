"""Read literal original native Form CID/Tf/fullTm programs independently."""
from pathlib import Path
import hashlib,pikepdf
from pdf_original_text_ops import source_code_bytes,cmap
sha=lambda b:hashlib.sha256(b).hexdigest()
def read_form(path,page_number,operator_path):
 with pikepdf.open(path)as pdf:
  obj=pdf.pages[page_number-1];resources=obj.Resources
  for index in operator_path:
   op=pikepdf.parse_content_stream(obj)[index];assert str(op.operator)=='Do';obj=resources.XObject[str(op.operands[0])];resources=obj.get('/Resources',resources)
  state=dict(font=None,Tf=None,Tm=None,CTM=[1.,0.,0.,1.,0.,0.],Tc=0.,Tw=0.,Th=100.,Ts=0.,Tr=0);stack=[];entries=[];allops=[]
  for i,op in enumerate(pikepdf.parse_content_stream(obj)):
   name=str(op.operator);values=list(op.operands);allops.append(dict(operator=name,operands=[bytes(v).hex()if isinstance(v,pikepdf.String)else str(v)for v in values]))
   if name=='q':stack.append(dict(state))
   elif name=='Q':state=stack.pop()
   elif name=='Tf':state.update(font=str(values[0]),Tf=str(values[1]))
   elif name=='Tm':state['Tm']=[str(v)for v in values]
   elif name in['Tc','Tw','Tz','Ts','Tr']:state[{'Tz':'Th'}.get(name,name)]=str(values[0])
   elif name=='cm':state['source_cm_program']=[str(v)for v in values]
   elif name in['Tj','TJ']:
    font=resources.Font[state['font']];cb=source_code_bytes(font);mapping=cmap(font);items=list(values[0])if name=='TJ'else[values[0]]
    for part in items:
     if not isinstance(part,pikepdf.String):continue
     raw=bytes(part);assert len(raw)%cb==0
     for start in range(0,len(raw),cb):
      token=raw[start:start+cb];code=int.from_bytes(token,'big');text=mapping[code]
      entries.append(dict(operator_index=i,operator=name,encoded_CID_hex=token.hex(),code=code,unicode=text,font_resource=state['font'],Tf=state['Tf'],full_Tm=state['Tm'],Tc=state['Tc'],Tw=state['Tw'],Th=state['Th'],Ts=state['Ts'],Tr=state['Tr']))
  assert not stack
  fonts=[]
  for alias,font in resources.get('/Font',{}).items():
   face=font.get('/DescendantFonts',[font])[0];descriptor=face.get('/FontDescriptor',{});programs={k:sha(descriptor[k].read_raw_bytes())for k in ['/FontFile','/FontFile2','/FontFile3']if k in descriptor}
   fonts.append(dict(resource=str(alias),BaseFont=str(font.get('/BaseFont')),Subtype=str(font.get('/Subtype')),Encoding=str(font.get('/Encoding')),font_program_raw_sha256=programs,ToUnicode_raw_sha256=sha(font.ToUnicode.read_raw_bytes())if '/ToUnicode'in font else None))
  return dict(literal_Form_raw_sha256=sha(obj.read_raw_bytes()),literal_Form_decoded_sha256=sha(obj.read_bytes()),Matrix=[str(v)for v in obj.get('/Matrix',[1,0,0,1,0,0])],BBox=[str(v)for v in obj.BBox],all_original_Form_operators=allops,all_encoded_CID_Tf_fullTm_programs=entries,original_font_resources=sorted(fonts,key=lambda v:v['resource']))
