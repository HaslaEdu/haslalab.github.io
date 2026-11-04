"""Derive private C03 scan tools; completed T masters are never touched."""
from pathlib import Path
import json,sys,hashlib,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
T=B/'TS';E=T/'engine';E.mkdir(parents=True,exist_ok=True)
S=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS/master-v1/authoring-whole-ts')
SHA='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
def save(p,q):
 assert not p.exists(),p
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
for old,new in [('cpho_2005_ts_compose.py','cpho_2003_ts_compose.py'),('cpho_2005_ts_qa.py','cpho_2003_ts_qa.py'),('cpho_2005_ts_poppler_qa.py','cpho_2003_ts_poppler_qa.py')]:
 p=E/new;assert not p.exists(),p
 s=(S/'page-tools'/old).read_text('utf8').replace('cpho_2005_ts_compose','cpho_2003_ts_compose').replace('cpho_2005_ts_qa','cpho_2003_ts_qa').replace('9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',SHA).replace('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS',str(T).replace('\\','/')).replace('CPhO_2005_Chinese_original.pdf','CPhO_2003_Chinese_original.pdf').replace('Private2005','Private2003')
 p.write_text(s,'utf8')
p=E/'cpho_2003_ts_compose.py';s=p.read_text('utf8')
s=s.replace("SOURCE=BASE/'inputs/CPhO_2003_Chinese_original.pdf'","SOURCE=BASE.parent/'inputs/CPhO_2003_Chinese_original.pdf'")
s=s.replace("if face=='SimSun':return Path('C:/Windows/Fonts/simsun.ttc')","if face=='SimSun':return Path('D:/CodexBuilds/Hasla-original-style-20261031/english-face-repair/font-faces/SimSun-5.24.ttf')")
s=s.replace("raw=target.read_bytes()","from cpho2003_native_runtime import isolated_new_english_subset\n    if 'SimSun'in path.name or 'simhei'in path.name.lower():target=isolated_new_english_subset(target,'serif'if 'SimSun'in path.name else'sans')\n    raw=target.read_bytes()",1)
s=s.replace("def isolate_native_raster_instances(path,expected):","def restore_actual_source_group(path,number):\n    temporary=Path(path).with_suffix('.actual-group.pdf')\n    with pikepdf.open(SOURCE)as source,pikepdf.open(path)as out:\n        value=source.pages[number-1].obj.get('/Group')\n        if value is not None:out.pages[0].obj.Group=out.copy_foreign(source.make_indirect(value))\n        elif '/Group'in out.pages[0].obj:del out.pages[0].obj['/Group']\n        out.save(temporary,compress_streams=False)\n    temporary.replace(path)\n\ndef isolate_native_raster_instances(path,expected):")
s=s.replace("doc.save(out,garbage=0,deflate=False);doc.close()","doc.save(out,garbage=0,deflate=False);doc.close();restore_actual_source_group(out,number)")
s=s.replace("target=stem.with_suffix('.pdf');doc.save(target,garbage=0,deflate=False);doc.close()","target=stem.with_suffix('.pdf');assert not target.exists(),target;doc.save(target,garbage=0,deflate=False);doc.close();restore_actual_source_group(target,number)")
p.write_text(s,'utf8')
q=json.loads((B/'inputs/original-all10-source-slots.json').read_text('utf8'))
sys.path[:0]=[str(B/'engine'),str(E)]
import pymupdf as f
from pdf_native_inline_reposition import _traces
with f.open(B/'inputs/CPhO_2003_Chinese_original.pdf')as d:
 for n in range(4,11):
  page=q['pages'][n-1];tr=_traces(d[n-1]);footer=[c for c in tr if c['origin'][1]>540];assert footer
  native=[r for r in page['slots']if r['origin'][1]<=540]
  for slot in native:
   if slot['size']>=14:
    slot['original_horizontal_center']=(slot['source_rect'][0]+slot['source_rect'][2])/2;slot['align']='center';slot['allowed_rect']=[54,slot['allowed_rect'][1],410,slot['allowed_rect'][3]]
  native.append(dict(id=f'{n}-full-footer',source=''.join(c['c']for c in footer),source_font='SimSun',source_characters=footer,size=9,origin=footer[0]['origin'],source_rect=[min(c['bbox'][0]for c in footer),min(c['bbox'][1]for c in footer),max(c['bbox'][2]for c in footer),max(c['bbox'][3]for c in footer)],align='center',original_horizontal_center=(min(c['bbox'][0]for c in footer)+max(c['bbox'][2]for c in footer))/2,right=490,allowed_rect=[350,545,490,565],render_mode=0,line_width=None))
  page['slots']=native
save(T/'inputs/native-slots.json',q)
headers=[dict(source_slot='4-0-0',source_prose_face='SimSun',translations=dict(ko='제20회 전국 중학생 물리 경시대회 결선',en='20th National High School Physics Final')),dict(source_slot='4-1-0',source_prose_face='SimSun',translations=dict(ko='참고 해설 및 채점 기준',en='Solutions and Scoring Standards')),dict(source_slot='4-full-footer',source_prose_face='SimSun',translations=dict(ko='1 / 7쪽',en='Page 1 of 7'))]
save(T/'authoring/page04.json',dict(source_sha256=SHA,source_page=4,printed_solution_page=1,native_headers=headers,original_digit_CIDs_font_point_paint_and_baseline_must_be_retained=True,original_horizontal_centers_from_source_slot_inventory=True))
print('Prepared C03 TS own engines/header inventory')
