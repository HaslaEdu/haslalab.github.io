from pathlib import Path
import json,sys
import pymupdf as f
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'engine'))
import latex_native_motion as m
import icho2019_write_guard as g
inv=m.inspect_inline_groups(g.SOURCE,13);doc=f.open(g.SOURCE);page=doc[12]
draws=page.get_drawings();second=[d for d in draws if abs(d['rect'].x0-88.824)<.01 and abs(d['rect'].y0-348.77)<.01];assert len(second)==1
draw=second[0];paths=[v for v in inv['vector_paths']if max(abs(a-b)for a,b in zip(v['rect'],draw['rect']))<.001];assert len(paths)==1
glyphs=[dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(bbox),paint=t['type'])for t in page.get_texttrace()if t['type']!=3 for cp,gid,origin,bbox in t['chars']if chr(cp)=='1'and abs(origin[0]-150.57074)<.001 and abs(origin[1]-347.57)<.01];assert len(glyphs)==1
baseline=glyphs[0]['origin'][1]
ref=dict(id='p13-coefficient-native1-original-underline',kind='original-prose-underline-containing-native-numeral',source_sha256=g.SOURCE_SHA,glyphs=glyphs,vector_path=paths[0],rendered_source_rect=list(draw['rect']),fill=list(draw['fill']),affects_typographic_bounds=False,source_baseline=baseline,source_text='coefficient of 1 for water.',target_prose_slot_ids=['p13:b13:l1:s0-0:c0-15','p13:b13:l1:s0-0:c16-27'],review='Original underlined phrase contains a native numeral. The original numeral and complete underline path move together by the natural Korean numeral displacement. The underline remains a decoration, reserves no English width, retains its exact program/width/colour/y, and must cover the whole Korean counterpart.')
p=B/'page13.overrides.json';q=json.loads(p.read_text('utf8'));q['__layout_scope__']['reviewed_native_vector_attachments']=[ref];edits=q.setdefault('__slot_edits__',{})
edits['p13:b13:l0:s3-3']=dict(text='액체 물이 분해되는 반응의 균형 반응식을. 이때 화학량론 계수는')
edits['p13:b13:l1:s0-0:c0-15']=dict(text='물에 대하여')
edits['p13:b13:l1:s0-0:c16-27']=dict(text='로 하라.')
raw=page.get_text('rawdict');slot=next(s for s in json.loads((g.PLANS/'page13.ko.json').read_text('utf8'))['slots']if s['id']=='p13:b13:l0:s3-3');b,l,a,z=slot['at'];chars=[c for s in raw['blocks'][b]['lines'][l]['spans'][a:z+1]for c in s['chars']];text=''.join(c['c']for c in chars);start=text.index('using a stoichiometric');target=chars[start:start+len('using a stoichiometric')];left=min(c['bbox'][0]for c in target);right=max(c['bbox'][2]for c in target);y=target[0]['origin'][1]
first=[v for v in inv['vector_paths']if abs(v['rect'][0]-left)<2 and abs(v['rect'][2]-right)<2 and .3<v['rect'][1]-y<2 and v['rect'][3]-v['rect'][1]<1.5];assert len(first)==1,dict(left=left,right=right,baseline=y,nearby_paths=[v for v in inv['vector_paths']if 0<v['rect'][1]-y<4])
v=first[0];spec=dict(id='p13-original-stoichiometric-underline',slot_id=slot['id'],target_text='이때 화학량론 계수는',source_baseline=y,operator_indices=v['operator_indices'],paint_operator=v['paint_operator'],source_rect=v['rect'],source_text='using a stoichiometric',review='Original stoichiometric emphasis retains its exact native path, width, colour and y; its center follows the corresponding Korean source-bound wording.')
q['__prose_vector_decorations__']=[d for d in q.get('__prose_vector_decorations__',[])if d['id']!=spec['id']]+[spec]
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');(B/'page13-native-underline-profile.json').write_text(json.dumps(dict(attachment=ref,first_line_emphasis=spec),ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(dict(native_numeral=ref['glyphs'],native_underline=ref['vector_path'],first_line_emphasis=spec),ensure_ascii=False),flush=True)
