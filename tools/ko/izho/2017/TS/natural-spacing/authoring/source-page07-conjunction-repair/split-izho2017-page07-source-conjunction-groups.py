from pathlib import Path
import sys,json,hashlib,pymupdf as f
B=Path(__file__).resolve().parents[1];E=B/'engine';F=B/'natural/2017/TS';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_original_text_ops import glyph_key
P=F/'plans/page07.json';p=json.loads(P.read_text('utf8'));assert p['source_page']==7 and p['original_english_source_sha256']=='fb90239d8da3dea3dcfe104551243f444802632a74a47a139374013aa16080f1'
before=P.parent/'history'/sha(P);before.mkdir(parents=True,exist_ok=True);(before/P.name).write_bytes(P.read_bytes());old=p['explicit_native_math_atoms'];profiles=p['reviewed_independent_original_expression_geometry_profiles'];assert len(old)==30 and len(profiles)==27
original=json.loads((B/'2017/inspection/page07-original-native-inline-inventory.json').read_text('utf8'));out=[];evidence=[];review=[]
def refkeys(at,text):
 matches=[r for r in p['reviewed_source_prose_native_reference_glyphs']if r['source_at']==at and r['source_text']==text];assert len(matches)==1;return{glyph_key(g)for g in matches[0]['source_glyphs']if g['c'].strip()}
for i,a in enumerate(old):
 e=profiles[i]if i<len(profiles)else None
 if i not in[4,16,17]:
  out.append(a)
  if e is not None:evidence.append(e)
  continue
 sourcekeys={glyph_key(g)for g in a['source_native_glyphs']}
 if i==4:
  first=refkeys([14,0,0],'(10)');second=refkeys([14,0,0],'(11)');buckets=[first,sourcekeys-first];assert second<=buckets[1]and len(first)==4 and len(buckets[1])==24;labels=['Original native reference(10)','Original native reference(11) and BOTH complete original equations10/11'];ats=[14,0,0];word=' and ';Korean='과 '
 else:
  number=23 if i==16 else 24;ats=[51,0,0]if i==16 else[51,2,0];first=refkeys(ats,f'({number})');buckets=[first,sourcekeys-first];assert len(first)==4 and len(buckets[1])==14;labels=[f'Original native reference({number})',f'Complete original equation{number}, after translated or analogous'];word=' or analogous ';Korean=' 또는 이와 동등한 식 '
 assert set.union(*buckets)==sourcekeys and not(buckets[0]&buckets[1]);parts=[]
 for j,(keys,label)in enumerate(zip(buckets,labels)):
  gs=[g for g in a['source_native_glyphs']if glyph_key(g)in keys];assert len(gs)==len(keys);box=f.Rect()
  for g in gs:box|=f.Rect(g['bbox']);box.include_point(f.Point(g['origin']))
  # Use physical native x extents; no old-English-width gap survives inside
  # either group. The full source row y band includes all stacked rules.
  rect=[box.x0-.001,a['rect'][1]-.001,box.x1+.001,a['rect'][3]+.001]
  rule={k:v for k,v in a.items()if k not in['source_form_path','source_form_bbox','source_complete_clip_operator_indices','use_complete_original_clip']};rule.update(rect=rect,source_native_glyphs=gs,source_grid_table_math=True,reviewed_source2017_page07_program_group=True,reviewed_source2017_page07_reference_only=(j==0),reviewed_source2017_page07_label=label,reason='Full original2017 source page7 reviewed: '+label+'. Source selected English conjunction remains OUTSIDE this complete native group in its exact original reading order. Every original native CID/font/GID/fractional Tf/Tm/point/paint/Y and fraction/root rule and ancestor clip remains native; exact full-program ordinary Form isolation/zeroRGB proof is required before composition. No retyping, fitting, source-wide cell atom or threshold change.')
  paths=[v for v in original['vector_paths']if f.Rect(rect).contains(f.Rect(v['rect']))];entry=dict(reviewed_rect=rect,logical_prose_baseline=rule['baseline'],original_glyphs=[g for g in e['original_glyphs']if glyph_key(g)in keys],original_vector_paths=paths,native_program='Complete exact original native CID/ancestor-clip/fraction-rule programme, independently isolated from translated source conjunction',reviewed_page07_conjunction_group=label)
  assert len(entry['original_glyphs'])==len(gs);out.append(rule);evidence.append(entry);parts.append(dict(label=label,original_native_glyphs=len(gs),source_rect=rect,original_rule_paths=len(paths)))
 review.append(dict(source_at=ats,source_word=word,Korean=Korean,physical_original_baseline=a['baseline'],complete_original_native_groups=parts,source_conjunction_kept_between_native_groups=True))
assert len(out)==33 and len(evidence)==30 and sum(len(a['source_native_glyphs'])for a in out)==sum(len(a['source_native_glyphs'])for a in old)
p['explicit_native_math_atoms']=out;p['reviewed_independent_original_expression_geometry_profiles']=evidence;p['reviewed_source2017_page07_original_conjunction_groups']=review;P.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');print('SPLIT_SOURCE2017_P7_THREE_CONJUNCTION_ROWS_INTO_SIX_COMPLETE_NATIVE_PROGRAM_GROUPS',[g['original_native_glyphs']for r in review for g in r['complete_original_native_groups']],flush=True)
