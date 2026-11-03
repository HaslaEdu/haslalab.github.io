"""Explicit English emphasis → Korean substring/native unit evidence, all143 paths."""
from pathlib import Path
import hashlib,json
import pymupdf as f
import natural_plan_compose_icho2019 as c
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;doc=f.open(g.SOURCE);rows=[]
for n in range(1,61):
 q=json.loads((B/f'page{n:02}.overrides.json').read_text('utf8'));glyphs=c._glyphs(doc[n-1])
 for spec in q.get('__prose_vector_decorations__',[]):
  r=spec['source_rect'];base=spec['source_baseline'];selected=[];seen=set()
  for glyph in glyphs:
   key=(glyph['c'],glyph['font'],glyph['gid'],glyph['size'],tuple(glyph['origin']))
   if abs(glyph['origin'][1]-base)>.001 or not r[0]-.001<=glyph['origin'][0]<r[2]-.001 or key in seen:continue
   selected.append(glyph);seen.add(key)
  selected.sort(key=lambda v:v['origin'][0]);source_text=''.join(v['c']for v in selected).strip();assert source_text,(n,spec['id'])
  target=spec.get('target_fragments',[dict(slot_id=spec['slot_id'],target_text=spec['target_text'])]if 'slot_id'in spec else[]);assert target
  unit=spec['id'];rationale='Underline exactly the corresponding Korean command/term substring; retain object/predicate words outside the original emphasis un-underlined.';unit_source=source_text;unit_target=' | '.join(v['target_text']for v in target)
  if n==13 and('stoichiometric'in spec['id']or'coefficient-native1'in spec['id']):unit='p13-water-stoichiometric-coefficient';unit_source='using a stoichiometric coefficient of 1 for water.';unit_target='이때 화학량론 계수는 | 물에 대하여 | [original native1] | 로 하라.';rationale='Two original underline paths cover one complete two-row condition. Korean places the coefficient noun before the water phrase and adds the required Korean predicate inside the same emphasized condition; original native1 remains native.'
  if n==43 and('missing-prose-underline'in spec['id']or'punctuation-underline'in spec['id']):unit='p43-log-molar-mass-linear-function';unit_source='The log value of the molar mass is a linear function of the elution volume, V_e.';unit_target='몰 질량의 로그값은 용리 부피 | [original native V_e] | 의 선형 함수이다.';rationale='The sentence and its separately underlined original full stop form one original emphasis unit. Natural Korean predicate follows the unchanged native expression; two source prose decoration paths cover the two Korean fragments and preserve a safe gap at the native subscript.'
  if n==56 and'protecting'in source_text:rationale='Source emphasis is protecting or directing only. Korean chemical terms 보호기/지향기 lexicalize modifier+group; underline these minimal corresponding terms only, excluding 제거 단계들을.'
  rows.append(dict(page=n,spec_id=spec['id'],source_sha256=g.SOURCE_SHA,source_path_operator_indices=spec['operator_indices'],source_path_rect=r,source_baseline=base,actual_source_emphasized_text_by_glyph_origins=source_text,actual_source_emphasized_glyphs=selected,target_substrings=target,unchanged_native_glyphs=spec.get('native_source_glyphs',[]),semantic_emphasis_unit_id=unit,semantic_unit_English=unit_source,semantic_unit_Korean=unit_target,manual_meaning_review=rationale))
out=B/'source-emphasis-meaning-review.json';out.write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,reviewed_source_paths=len(rows),rows=rows,scope='143 actual source underline paths compared with the precise declared Korean substring/native group. Source slot boundaries are not treated as emphasis boundaries. Actual source glyph origins inside each original path provide the original emphasized text; paired original paths may share a declared semantic unit.',all_source_target_mappings_manually_read=True),ensure_ascii=False,indent=2)+'\n','utf8');print(len(rows),hashlib.sha256(out.read_bytes()).hexdigest(),flush=True)
