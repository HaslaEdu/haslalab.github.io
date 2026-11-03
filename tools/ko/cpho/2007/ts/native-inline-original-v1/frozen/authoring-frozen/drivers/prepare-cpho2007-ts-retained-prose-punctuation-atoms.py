from pathlib import Path
import json,sys,re,hashlib,shutil,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'));from pdf_memory_gate import page_worker;from pdf_native_inline_reposition import _traces;from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=B/'inputs/CPhO_2007_Chinese_original.pdf';data=json.loads((B/'inputs/original-all20-source-slots.json').read_text('utf8'));assert sha(source)==data['source_sha256']=='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9'
records=[];atoms=[]
with page_worker(),f.open(source)as doc:
 for page in data['pages']:
  n=page['source_page']
  if n<5:continue
  physical={glyph_key(g):g for g in _traces(doc[n-1])if g['c'].strip()}
  for slot in page['slots']:
   selected=[c for c in slot['source_characters']if c['c'].strip()and(slot.get('retain_native')or c['index']in slot.get('retained_source_indices',[]))]
   if not selected:continue
   glyphs=[physical[glyph_key(c)]for c in selected];ys=[g['origin'][1]for g in glyphs];xs=[g['origin'][0]for g in glyphs];assert max(ys)-min(ys)<.001
   rect=[min(xs)-.002,min(ys)-.002,max(xs)+.002,max(ys)+.002];label='Original retained prose punctuation '+slot['id']
   atoms.append(dict(page=n,label=label,rect=rect,baseline=slot['origin'][1],expected_physical_glyphs=len(glyphs),vector_rects=[],reason='Exact original punctuation CID glyphs in an authored prose row. Keep original font/GID/point/paint/Y and original glyph advance; pack horizontally with adjacent translated words and native variables, instead of leaving an erased-Chinese-phrase-width gap. The rectangle selects only original glyph origins; it never crops source ink or changes glyph size.'))
   records.append(dict(page=n,source_slot=slot['id'],source_prose=slot['source'],source_native_glyphs=glyphs,origin_selector_rect=rect,expected_physical_glyphs=len(glyphs)))
folder=B/'tools/ko/cpho/2007/natural';folder.mkdir(parents=True,exist_ok=True);path=folder/'atomic-inline.json';assert not path.exists();path.write_text(json.dumps(dict(source_sha256=data['source_sha256'],atoms=atoms),ensure_ascii=False,indent=2)+'\n','utf8');(B/'authoring/retained-original-prose-punctuation-evidence.json').write_text(json.dumps(dict(source_sha256=data['source_sha256'],reviewed_source_slot_policy='Retain every original punctuation selected by the frozen original source-slot plan as native; only its natural horizontal prose placement changes.',atoms=records),ensure_ascii=False,indent=2)+'\n','utf8');assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';print('CPHO2007_TS_EXACT_NATIVE_PROSE_PUNCTUATION_ATOMS_PREPARED',len(atoms),flush=True)
