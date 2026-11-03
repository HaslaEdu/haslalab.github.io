"""Exact approved clause strings and source style/baseline-pool verification."""
from pathlib import Path
import json,hashlib
import pymupdf as f
import natural_plan_compose_icho2024_style as c
ROOT=Path('D:/CodexBuilds/Hasla-poi-natural-20261102/style-corrections/icho2024-20261103')
REV=Path(__file__).resolve().parents[2];APP=REV/'approved-translation-manifest.json';MAP=ROOT/'semantic-underline-mapping-68-v2.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(n,folder):
 assert sha(MAP)=='ad5990b8ceb44b2dabbfc7a53ce8c344907d4b5b243f58e4e7cd88fba0dfde8a'
 approved=json.loads(APP.read_text('utf8'));assert sha(APP)==c.style_rules.APP_SHA
 mapping=json.loads(MAP.read_text('utf8'));rows=[r for r in mapping['rows']if r['page']==n];edits={id:d for id,d in approved['edits'].items()if d['page']==n}
 path=Path(folder)/f'page{n:02}.pdf';q=json.loads(path.with_suffix('.layout.json').read_text('utf8'));old=json.loads((ROOT/f'frozen/publication/page{n:02}.qa.json').read_text('utf8'));ep=json.loads((ROOT/f'frozen/publication/page{n:02}.effective-plan.json').read_text('utf8'));slots={s['id']:s for s in ep['slots']};oldp={}
 for p in old['placements']:oldp.setdefault(p['id'],[]).append(p)
 rules={};semantic=[];expected={id:edits[id]['after']if id in edits else s.get('text','')for id,s in slots.items()if not s.get('skip')};used={};refs={};pools={}
 with f.open(ROOT/'frozen/source/IChO_2024_T_EN.pdf')as source:
  blocks=source[n-1].get_text('rawdict')['blocks']
  def ref(id):
   if id not in refs:
    ss=slots[id];gs=c._plain_source(ss,blocks);g=next((v for v in gs if v['c'].strip()),gs[0]);default=oldp[id][0]['font_role']if oldp.get(id)else ss.get('font_role',c._role(g['font']));refs[id]=(default,g)
   return refs[id]
  for id,s in slots.items():
   if s.get('skip'):continue
   gs=c._plain_source(s,blocks)
   if gs:pools.setdefault(s['at'][0],set()).add(next((v for v in gs if v['c'].strip()),gs[0])['origin'][1])
  for id,d in edits.items():assert slots[id]['source']==d['original_English_guard']and slots[id]['at']==d['source_at']and slots[id]['text']==d['before']
  for row in rows:
   role,g=ref(row['source_slot_id']);assert role==row['source_style_reference']['font_role']and g['font']==row['source_guard']['source_font']and g['size']==row['source_guard']['source_pointsize']and g['origin'][1]==row['source_guard']['source_prose_baseline']
   rules.setdefault(row['target_slot_id'],[]).append((row['target_codepoint_start'],row['target_codepoint_end'],role))
   matches=[p for p in q['placements']if p.get('semantic_binding_index')==row['inventory_index']];assert len(matches)==1;target=matches[0]
   assert target['original_source_slot_id']==row['target_slot_id']and target['text']==row['target_literal']and target['font_role']==role
   assert target['source_korean_char_start']==row['target_codepoint_start']and target['source_korean_char_end']==row['target_codepoint_end']
   assert target['baseline']==row['target_existing_baseline']and target['size']==row['target_existing_pointsize']
   semantic.append(dict(index=row['inventory_index'],source_English=row['source_English'],source_original_font=g['font'],source_pointsize=g['size'],source_original_baseline=g['origin'][1],target_literal=target['text'],target_fragment_id=target['id'],target_font_role=role,actual_target_baseline=target['baseline']))
   for d in row['regular_style_restoration']:
    plain,g2=ref(d['source_plain_style_reference_slot_id']);assert plain in ['sans','serif']and slots[d['slot_id']]['text'][d['start']:d['end']]==d['literal'];rules.setdefault(d['slot_id'],[]).append((d['start'],d['end'],plain))
 italic={r['slot_id']:r for r in mapping['new_Korean_italic_placements']if r['page']==n}
 for p in q['placements']:
  id=p.get('original_source_slot_id',p['id']);default,g=ref(id);text=expected[id]
  assert p['size']==g['size']and p['source_font']==g['font']
  assert p['baseline']in pools[slots[id]['at'][0]],(n,id,'not in exact raw original prose paragraph baseline pool',p['baseline'],pools[slots[id]['at'][0]])
  a=p.get('source_korean_char_start',p.get('target_char_start',0));z=p.get('source_korean_char_end',p.get('target_char_end',len(text)));assert text[a:z]==p['text'],(n,id,a,z,text,p['text'])
  for k in range(a,z):
   if text[k].isspace():continue
   roles=[role for lo,hi,role in rules.get(id,[])if lo<=k<hi];assert len(roles)<=1;role=roles[0]if roles else default;assert p['font_role']==role,(n,id,p['text'],role,p['font_role'])
   assert(id,k)not in used,(n,id,k,'duplicate Korean');used[(id,k)]=1
  angle=italic[id]['proposed_new_Korean_only_angle']if id in italic else next((v['angle']for v in oldp.get(id,[])),0);assert p['angle']==angle
  if id in italic:assert p['source_font_descriptor_italic_angle']==italic[id]['source_descriptor_ItalicAngle']
 for id,text in expected.items():
  for k,ch in enumerate(text or''):
   if not ch.isspace():assert used.get((id,k))==1,(n,id,k,ch,'missing exact approved/unchanged Korean')
 assert len(q['prose_vector_decorations'])==len(rows)
 result=dict(page=n,passed=True,proof_sha256=sha(path),source_sha256=q['source_sha256'],mapping_sha256=sha(MAP),approved_source_clause_manifest_sha256=sha(APP),exact_approved_text_edits=len(edits),all_expected_Korean_nonspace_characters_preserved_once=len(used),all_requested_font_roles_bound_to_actual_original_source_styles=True,exact_original_sizes_and_raw_prose_baseline_pool_membership_preserved=True,no_other_bold_or_italic_changes=True,semantic_mappings=semantic,new_Korean_italic_placements=len(italic),program_sha256=sha(__file__))
 q['independent_source_semantic_style_audit']=result;path.with_suffix('.layout.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');path.with_suffix('.semantic-style-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');return result
