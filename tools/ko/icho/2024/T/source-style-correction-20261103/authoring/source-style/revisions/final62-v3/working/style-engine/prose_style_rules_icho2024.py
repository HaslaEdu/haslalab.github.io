"""Explicit source-style → Korean-codepoint bindings; no text or row rewrite."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path('D:/CodexBuilds/Hasla-poi-natural-20261102/style-corrections/icho2024-20261103')
MAP=ROOT/'semantic-underline-mapping-68-v2.json'
EXPECTED='ad5990b8ceb44b2dabbfc7a53ce8c344907d4b5b243f58e4e7cd88fba0dfde8a'
def mapping_sha():return hashlib.sha256(MAP.read_bytes()).hexdigest()
assert mapping_sha()==EXPECTED
M=json.loads(MAP.read_text('utf8'))
REV=Path(__file__).resolve().parents[2]
APP=REV/'approved-translation-manifest.json'
APP_SHA='bc06cca28d8b2f3ed93b437a5c3ed12f37cc8dd40d096f174314e5e2dffa68b2'
assert hashlib.sha256(APP.read_bytes()).hexdigest()==APP_SHA
APPROVED=json.loads(APP.read_text('utf8'))
def mapping_rows(n):return[r for r in M['rows']if r['page']==n]
def apply(anchors,slots,blocks,metrics,fontinfo,plain_source,width,clean):
 byid={s['id']:s for s in slots};page=slots[0]['page'];rows=mapping_rows(page);rules={};journal=[]
 def actual_style(id):
  ss=byid[id];chars=plain_source(ss,blocks);g=next(c for c in chars if c['c'].strip());name=g['font'];role=ss.get('font_role')
  if role is None:raise ValueError('Style reference requires explicit original font role')
  return dict(font_role=role,source_font=name,source_angle=fontinfo(name)['angle'],size=g['size'],baseline=g['origin'][1])
 for r in rows:
  guard=r['source_guard'];ss=byid[r['source_slot_id']]
  if ss['source']!=r['source_English']or ss['at']!=guard['at']:raise ValueError('Semantic original source literal/at changed')
  ref=actual_style(r['source_slot_id'])
  if ref['source_font']!=guard['source_font']or ref['size']!=guard['source_pointsize']or ref['baseline']!=guard['source_prose_baseline']:raise ValueError('Semantic source style changed')
  target=byid[r['target_slot_id']];a,z=r['target_codepoint_start'],r['target_codepoint_end']
  if target['text']!=r['current_target_slot_text']or target['text'][a:z]!=r['target_literal']or target['text'].count(r['target_literal'])!=1:raise ValueError('Exact semantic target literal/codepoints changed')
  if target['at'][:2]!=ss['at'][:2]:raise ValueError('Semantic binding may not move across original rows')
  rules.setdefault(target['id'],[]).append(dict(a=a,z=z,ref=ref,index=r['inventory_index'],kind='emphasis',literal=r['target_literal']))
  for d in r['regular_style_restoration']:
   ref2=actual_style(d['source_plain_style_reference_slot_id']);dest=byid[d['slot_id']]
   if dest['text'][d['start']:d['end']]!=d['literal']or ref2['font_role']not in ['sans','serif']:raise ValueError('Exact plain source style/target changed')
   rules.setdefault(d['slot_id'],[]).append(dict(a=d['start'],z=d['end'],ref=ref2,index=r['inventory_index'],kind='restore-plain',literal=d['literal']))
 if page==39:
  cfg=APPROVED['p39_explicit_same_physical_row_fragment_order'];id=cfg['source_condition_slot'];slot=byid[id];ref=actual_style(id)
  if slot['source']!=cfg['source_condition_English']or slot['text']!='필요할 때.'or ref['baseline']!=cfg['baseline']:raise ValueError('Explicit when-relevant source clause guard')
  rules.setdefault(id,[]).extend([dict(a=0,z=5,ref=ref,index=None,kind='explicit-row-fragment',tag='condition'),dict(a=5,z=6,ref=ref,index=None,kind='explicit-row-fragment',tag='period')])
 for id,d in APPROVED['edits'].items():
  if d['page']!=page:continue
  slot=byid[id]
  if slot['source']!=d['original_English_guard']or slot['at']!=d['source_at']or slot['text']!=d['after']:raise ValueError('Approved exact source-clause/text union guard')
 italic={r['slot_id']:r for r in M['new_Korean_italic_placements']if r['page']==page}
 used_rules=set();used_italics=set()
 for line in anchors.values():
  replacement=[]
  for old in line['prose']:
   entry=dict(old);id=entry['id'];text=entry['text'];source_angle=entry['angle']
   if source_angle:
    r=italic.get(id)
    if r is None or text!=r['existing_Korean']or source_angle!=-12 or entry['size']!=r['pointsize']or entry['baseline']!=r['baseline']:raise ValueError('Only exact approved new Korean italic runs may change')
    entry['source_font_descriptor_italic_angle']=source_angle;entry['angle']=-source_angle;used_italics.add(id)
    journal.append(dict(kind='new-Korean-only-italic-direction',id=id,original_source_angle=source_angle,new_angle=entry['angle'],baseline=entry['baseline'],pointsize=entry['size']))
   rr=rules.get(id,[])
   if not rr:replacement.append(entry);continue
   cuts=sorted({0,len(text)}|{r[k]for r in rr for k in ['a','z']});pieces=[]
   for a,z in zip(cuts,cuts[1:]):
    covering=[r for r in rr if r['a']<=a and z<=r['z']]
    if len(covering)>1:raise ValueError('Overlapping semantic style rules')
    raw=text[a:z];literal=clean(raw)
    if not literal:continue
    lead=len(raw)-len(raw.lstrip());tail=len(raw.rstrip());aa=a+lead;zz=a+tail
    p=dict(entry,id=id+'#style'+str(len(pieces)),original_source_slot_id=id,source_korean_char_start=aa,source_korean_char_end=zz,text=literal)
    p['join_left']=entry.get('join_left',False)if aa==0 else not text[aa-1].isspace()
    p['join_right']=entry.get('join_right',False)if zz==len(text)else not text[zz].isspace()
    if pieces:p['optical_gap_left_pt']=None
    if covering:
     r=covering[0];ref=r['ref']
     if ref['size']!=entry['size']:raise ValueError('Semantic source style cannot change physical point size')
     p['font_role']=ref['font_role'];p['semantic_source_style_font']=ref['source_font']
     if ref['source_angle']!=source_angle:raise ValueError('No unreviewed italic style transfer')
     if r['kind']=='emphasis':p['semantic_binding_index']=r['index']
     if r['kind']=='explicit-row-fragment':
      p['explicit_row_fragment']=r['tag']
      if r['tag']=='condition':p['join_right']=False
      else:p['join_left']=True
     p['source_semantic_style_kind']=r['kind'];used_rules.add((id,r['a'],r['z']))
    p['width']=width(metrics[p['font_role']],p['text'],p['size']);pieces.append(p)
   for r in rr:
    if (id,r['a'],r['z'])not in used_rules:raise ValueError('Semantic style rule unused')
   journal.append(dict(kind='Korean-style-fragmentation',original_slot_id=id,original_Korean_text=text,baseline=entry['baseline'],pointsize=entry['size'],fragments=[dict(id=p['id'],text=p['text'],source_range=[p['source_korean_char_start'],p['source_korean_char_end']],font_role=p['font_role'],join_left=p['join_left'],join_right=p['join_right'])for p in pieces],source_original_encoded_suppression_unchanged=True))
   replacement.extend(pieces)
  line['prose']=replacement
 if used_italics!=set(italic):raise ValueError('Approved italic placement missing')
 return journal

def permute_line(page,line,tokens):
 if page!=39 or abs(line['baseline']-APPROVED['p39_explicit_same_physical_row_fragment_order']['baseline'])>.001:return tokens
 cfg=APPROVED['p39_explicit_same_physical_row_fragment_order']
 condition=[t for t in tokens if t.get('explicit_row_fragment')=='condition'];period=[t for t in tokens if t.get('explicit_row_fragment')=='period'];body=[t for t in tokens if t['kind']=='prose'and t['id']==cfg['source_stereostructure_slot']];native=[t for t in tokens if t['kind']=='native'and t['text']==cfg['native_atom_text']]
 if not all(len(v)==1 for v in [condition,period,body,native]):raise ValueError('Exact p39 physical-row atom membership '+repr([(t['kind'],t.get('id'),t['text'])for t in tokens]))
 selected=condition+body+native+period
 if len(selected)!=len(tokens)or len({id(t)for t in selected})!=len(tokens):raise ValueError('Explicit p39 row order must be a bijection')
 if any(t['kind']=='prose'and t['baseline']!=line['baseline']for t in selected):raise ValueError('p39 row permutation may not alter original baselines')
 return selected

def guard_approved_reflow(paragraph_flow):
 for flow in paragraph_flow:
  id=flow['slot_id'].split('#style')[0]
  if id in APPROVED['edits']:raise ValueError('Approved clause needs concise original-row authoring, not automatic carry: '+repr(flow))

ATOM_FILE=REV/'p39-reviewed-whole-inline-wedge-atom-v2.json'
ATOM_SHA='60f010c33b97f27a5347f187c141dddc46e740bb3023cb98ba66f43413f5153e'
assert hashlib.sha256(ATOM_FILE.read_bytes()).hexdigest()==ATOM_SHA
ATOM=json.loads(ATOM_FILE.read_text('utf8'))
def attach_reviewed_inline_atom(page,token,paths,claimed):
 if page!=39 or token['text']!=ATOM['native_text']:return
 fields=['c','gid','font','size','origin','bbox','paint']
 actual=[{k:g[k]for k in fields}for g in token['glyphs']]
 if actual!=ATOM['source_glyphs']:raise ValueError('Exact original inline wedge atom glyphs changed')
 for ref in ATOM['source_paths']:
  matches=[p for p in paths if p['operator_indices']==ref['operator_indices']]
  if len(matches)!=1:raise ValueError('Named wedge/dash vector source missing')
  path=matches[0];key=tuple(path['operator_indices'])
  if path['rect']!=ref['rect']or path['paint_operator']!=ref['paint_operator']:raise ValueError('Named wedge/dash vector source changed')
  if key in claimed:
   matches=[p for p in token['vector_paths']if p['operator_indices']==ref['operator_indices']]
   if len(matches)!=1:raise ValueError('Inline wedge path claimed elsewhere')
   matches[0].update(source_sha256=ref['source_sha256'],reviewed_whole_inline_atom_sha256=ATOM_SHA,**({'source_graphics_clip_program':ref['source_graphics_clip_program']}if 'source_graphics_clip_program'in ref else{}))
  else:
   token['vector_paths'].append(dict(path,source_sha256=ref['source_sha256'],reviewed_whole_inline_atom_sha256=ATOM_SHA,**({'source_graphics_clip_program':ref['source_graphics_clip_program']}if 'source_graphics_clip_program'in ref else{})));claimed.add(key)
 token['reviewed_whole_inline_atom_sha256']=ATOM_SHA
