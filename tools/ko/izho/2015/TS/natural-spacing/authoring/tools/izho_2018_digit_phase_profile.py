"""Two immutable native-font/SVG phase witnesses; no global tolerance changes."""
from pathlib import Path
import hashlib
SOURCE='0782ab2ced4c911ce92b550aa2fd86cb7f6c9a6e24d7a60f64b13275df1e38ba'
PINS={
3:dict(proof='158a40a7f283452974ac1930cb41e5304bb13acf220032600023a8cb0de34f41',count=1,gid=887,c='5',cid='0377',baseline=631.63,raw_delta=1,raw_bbox=[275.,627.75,275.25,628.],protected=216),
4:dict(proof='6e42e9c12e1094dc5654040f5ba69445b3502349130e55eb1a7db2f8746b343d',count=3,gid=885,c='3',cid='0375',baseline=124.37,raw_delta=2,raw_bbox=[143.75,123.25,429.,125.75],protected=229)}
def verify(result,plan,path,w):
 n=plan['source_page'];p=PINS.get(n)
 if p is None:return False
 raw=result['original_input_outline_native_ink_audit'];promote=w['original_CID_promotion'];measure=w['native_CID_reference_measurements'];high=w['high_resolution_unhinted_SVG'];negative=w['negative_actual_original_CID_omission']
 exact=[]
 for a in w['checks']:
  s,t=a['source'],a['actual_destination']
  exact.append(all(s[k]==t[k]for k in ['c','font','size','trace_gid','render_mode','color','opacity'])and s['c']==p['c']and s['font']=='Cambria Math'and s['size']==12 and s['trace_gid']==p['gid']and abs(s['origin'][1]-p['baseline'])<.005 and abs(t['origin'][1]-s['origin'][1])<.001 and abs(t['origin'][0]-s['origin'][0]-a['requested_dx'])<.001)
 expected={(r,s,i)for r in ['MuPDF','Poppler']for s in [4,8,12]for i in range(p['count'])}
 tests=[plan['original_english_source_sha256']==SOURCE,w['original_language_source_sha256']==SOURCE,w['source_page']==n,
 result['output_sha256']==w['proof_sha256']==p['proof'],w['source_base_page_sha256']==raw['source_sha256'],w['proof_unmodified'],w['delivered_pdf_modified']is False,w['mathematics_retyped']is False,w['passed'],
 len(exact)==p['count'],all(exact),w['source_move_qa']['passed'],w['other_text_erasure']['passed'],promote['passed'],promote['original_font_programs_unchanged'],promote['no_new_unicode_or_font_program'],promote['native_encoded_CIDs_preserved'],promote['positions_unchanged'],
 len(promote['promoted_native_paints'])==p['count'],all(g['c']==p['c']and g['gid']==p['gid']and g['size']==g['source_Tf']==12 and g['source_encoded_cid_hex']==p['cid']and g['source_font_resource']=='/F9'and g['source_Tm_linear']==[1.,0.,0.,1.]for g in promote['promoted_native_paints']),
 {(m['renderer'],m['scale'],m['index'])for m in measure}==expected,all(m['reference_deep_dark_pixels']>0 and m['missing_original_CID_pixels']==m['actual_reference_nonwhite_RGB_errors']==0 for m in measure),
 {(m['index'],m['scale'])for m in high}=={(i,s)for i in range(p['count'])for s in [8,12]},all(m['passed']and m['svg_missing']==0 for m in high),
 negative['passed'],negative['native_erasure_qa']['passed'],{t['renderer']for t in negative['checks']}=={'MuPDF','Poppler'},all(t['rejected']and t['reference_dark_pixels_missing']>0 for t in negative['checks']),
 raw['protected_native_glyphs']==p['protected'],raw['newly_missing_native_ink_pixels']==p['raw_delta'],raw['missing_bbox']==p['raw_bbox'],not raw['missing_requested_source_glyphs'],not raw['missing_final_native_glyphs'],raw['source_outline_audit']['passed']]
 if not all(tests):
  result['native_phase_witness_rejected_conditions']=[i for i,t in enumerate(tests)if not t]
  return False
 result['native_ink_reference_profile']=dict(kind='2018-original-native-Cambria-digit-phase-v1',method='The exact original encoded source CID/font/Tf/Tm/paint is authoritative for these four reviewed curved digits. Original native reference nonwhite RGB matches final exactly in independent MuPDF and Poppler at4x/8x/12x; independent unhinted SVG checks at8x/12x also have zero missing ink. Raw4x SVG phase diagnostic retained, thresholds and delivered proof unchanged; actual-CID omission negatives rejected.',source_page=n,source_character=p['c'],source_gid=p['gid'],source_encoded_cid=p['cid'],source_font_resource='/F9',source_point_size=12,source_glyphs_checked=p['count'],original_4x_svg_dark_pixel_delta=p['raw_delta'],native_reference_nonwhite_RGB_errors=0,native_reference_renderers=['MuPDF','Poppler'],native_reference_scales=[4,8,12],svg_8x_missing_pixels=0,svg_12x_missing_pixels=0,actual_CID_omission_negative_rejected=True,witness=str(path),witness_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),proof_unmodified=True)
 result['verified_original_native_ink_missing_pixels']=0
 return True
