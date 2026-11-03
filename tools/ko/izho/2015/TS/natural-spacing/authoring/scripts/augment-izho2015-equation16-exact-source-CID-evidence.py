from pathlib import Path
import sys,json,hashlib,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');O=B/'natural/2015-page04-original-equation16-program';sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();p=O/'witness.json';assert sha(p)=='51e2d2c62eaaf5f7d090753b39fb7b2a7c8e904b177bebb526d680939254b648';w=json.loads(p.read_text('utf8'));source=B/'2015/source/IZhO_2015_TS.pdf';proof=Path(w['proof']);reference=Path(w['source_reference_file'])
def same(a,b):return glyph_key(a)==glyph_key(b)and a['trace_gid']==b['trace_gid']
def entry(inv,g):
 found=[(show,part)for show in inv['top_level_text_shows']for part in show['parts']if any(same(h,g)for h in part['glyphs'])];assert len(found)==1,(g,len(found));show,part=found[0];assert len(part['glyphs'])==1,'Complete original encoded CID cluster required';s=show['state']
 return dict(original_operator=show['operator'],original_operator_index=show['operator_index'],source_encoded_CID_hex=part['raw_hex'],original_code=part['code'],source_font_resource=s['active'],source_Tf=s['tf'],source_Tm_linear=show['text_matrix'][:4],source_text_matrix=show['text_matrix'],source_CTM=s['ctm'],source_text_character_space=s['tc'],source_text_word_space=s['tw'],source_text_horizontal_scale=s['th'],source_text_rise=s['ts'],source_text_render_mode=s['tr'])
with page_worker():
 inventories=[inspect_inline_groups(path,page,include_text_shows=True)for path,page in[(source,4),(reference,1),(proof,1)]]
 with f.open(proof)as doc:actual=_traces(doc[0])
 records=[]
 for g in w['complete_original_display_expression_glyphs']:
  h=next(h for h in actual if same(g,h));a,b,c=[entry(inv,g)for inv in inventories];keys=['source_encoded_CID_hex','original_code','source_font_resource','source_Tf','source_Tm_linear','source_CTM','source_text_character_space','source_text_word_space','source_text_horizontal_scale','source_text_rise','source_text_render_mode'];assert all(a[k]==b[k]==c[k]for k in keys),(g,a,b,c)
  records.append(dict(source_glyph=g,actual_target_glyph=h,requested_dx=0.,exact_original_CID_font_Tf_Tm_CTM_and_paint_preserved=True,original_source_encoded_program=a,independent_original_reference_encoded_program=b,actual_final_encoded_program=c))
 assert len(records)==40;w['exact_original_CID_programs']=records;w['exact_original_CID_programs_checked']=40;w['actual_bad_PDF_controls']=json.loads((B/'natural/2015-native-geometry-negatives/negative-controls.json').read_text('utf8'));w['legacy_native_reference_witness_sha256']=sha(p);w['raw_outline_control_source_sha256']=w['original_input_page_sha256'];w['original_English_source_sha256']=sha(source);w['all_original_encoded_CIDs_Tf_Tm_CTM_paint_and_fractional_points_preserved']=True
 target=O/'witness-with-exact-CID-programs.json';assert not target.exists();target.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE2015_ALL40_ORIGINAL_CIDS_TF_TM_CTM_PAINT_EXACT_FINAL_WITNESS',sha(target),flush=True)
