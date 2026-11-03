/* DRAFT additive pure report contract. No active publication integration. */
'use strict';
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const STATUS='DRAFT_ADDITIVE_REPORT_CONTRACT_NOT_PRODUCTION_AUTHORIZATION';
const number=v=>{assert.equal(typeof v,'number');assert.ok(Number.isFinite(v));return v;};
const integer=(v,min=0)=>{number(v);assert.ok(Number.isInteger(v)&&v>=min);return v;};
const vector=(v,n)=>{assert.ok(Array.isArray(v));assert.equal(v.length,n);return v.map(number);};
const near=(a,b,t)=>{assert.equal(a.length,b.length);for(let i=0;i<a.length;i++)assert.ok(Math.abs(number(a[i])-number(b[i]))<=t);};
const hash=v=>assert.match(v,/^[0-9a-f]{64}$/);
const white=c=>{const p=c.codePointAt(0);return (p>=9&&p<=13)||(p>=28&&p<=32)||[133,160,5760,8232,8233,8239,8287,12288].includes(p)||(p>=8192&&p<=8202);};
const count=(map,k,n=1)=>map.set(k,(map.get(k)||0)+n);
function multiply(a,b){a=vector(a,6);b=vector(b,6);return[a[0]*b[0]+a[1]*b[2],a[0]*b[1]+a[1]*b[3],a[2]*b[0]+a[3]*b[2],a[2]*b[1]+a[3]*b[3],a[4]*b[0]+a[5]*b[2]+b[4],a[4]*b[1]+a[5]*b[3]+b[5]];}
const rotation=a=>({0:[1,0,0,1,0,0],90:[0,1,-1,0,0,0],180:[-1,0,0,-1,0,0],270:[0,-1,1,0,0,0]})[a];
function geometry(g,n){assert.equal(g.passed,true);for(const k of['planned_glyphs','actual_glyphs','original_full_font_gids_verified'])assert.equal(g[k],n);assert.deepEqual(g.geometry_errors,[]);assert.deepEqual(g.original_full_font_gid_errors,[]);assert.ok(number(g.position_tolerance_pt)>0&&g.position_tolerance_pt<=.001);assert.ok(number(g.max_position_error_pt)>=0&&g.max_position_error_pt<=.001);}
function validate(audit,body,year=audit.year,layoutSHA=null,effectivePlan=null){
  assert.ok([2023,2024,2025,2026].includes(year));assert.equal(audit.year,year);assert.equal(audit.passed,true);assert.equal(audit.page,body.page);
  assert.equal(audit.proof_sha256,body.output_sha256);assert.equal(audit.target.sha256,body.output_sha256);
  if(layoutSHA!==null)assert.equal(audit.layout.sha256,layoutSHA);
  const specs=new Map(),bodyIDs=new Map(),labels=[],expectedChars=new Map();let total=0,spacesExpected=0;
  const add=(p,key,label)=>{
    assert.ok(!specs.has(key));assert.equal(typeof p.text,'string');
    const role=label?(year===2026?'sans':p.font_role||'sans'):p.font_role;
    const alias=label?(year===2026?'KO_Natural_Raster':'KO_Natural_Raster_'+role.replaceAll('-','_')):'KO_Natural_'+role.replaceAll('-','_');
    const angle=label?0:number(p.angle??0),turn=label&&year!==2026?integer(p.rotate??0):0;
    assert.ok([0,14].includes(angle));assert.ok([0,90,180,270].includes(turn));const chars=Array.from(p.text),sp=chars.filter(white).length;
    const size=number(p.size);assert.ok(size>0);specs.set(key,{placement:p,label,alias,angle,rotation:turn,count:chars.length,spaces:sp,size});
    total+=chars.length;spacesExpected+=sp;for(const c of chars)if(!white(c))count(expectedChars,alias+'\0'+c);
  };
  for(const[index,p]of body.placements.entries()){
    assert.equal(typeof p.id,'string');
    const key='body:'+index+':'+p.id+':'+JSON.stringify([p.target_char_start??null,p.target_char_end??null,p.baseline]);
    if(!bodyIDs.has(p.id))bodyIDs.set(p.id,[]);bodyIDs.get(p.id).push(key);add(p,key,false);
  }
  for(const[id,keys]of bodyIDs)if(keys.length>1){
    const parts=keys.map(key=>specs.get(key).placement),ranges=[];
    for(const p of parts){assert.equal(p.source_text,parts[0].source_text);const start=integer(p.target_char_start),end=integer(p.target_char_end);assert.equal(end-start,Array.from(p.text).length);ranges.push([start,end]);}
    ranges.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);assert.equal(ranges[0][0],0);
    if(effectivePlan!==null){
      assert.equal(typeof effectivePlan.raw_utf8,'string');
      const digest=crypto.createHash('sha256').update(effectivePlan.raw_utf8,'utf8').digest('hex');
      assert.equal(digest,effectivePlan.sha256);assert.equal(digest,body.effective_plan_sha256);
      const plan=JSON.parse(effectivePlan.raw_utf8.replace(/^\uFEFF/,''));assert.deepEqual(plan,effectivePlan.document);
      assert.equal(plan.page,body.page);assert.equal(plan.source_sha256,body.source_sha256);
      const slots=plan.slots.filter(p=>p.id===id);assert.equal(slots.length,1);assert.equal(slots[0].source,parts[0].source_text);
      assert.equal(typeof slots[0].text,'string');const full=Array.from(slots[0].text),ordered=[...parts].sort((a,b)=>a.target_char_start-b.target_char_start);
      assert.equal(ranges.at(-1)[1],full.length);
      for(const p of ordered){const start=p.target_char_start,end=p.target_char_end;assert.ok(start>=0&&end>=start&&end<=full.length);assert.equal(p.text,full.slice(start,end).join(''));}
      for(let i=1;i<ordered.length;i++){const a=ordered[i-1],b=ordered[i],end=a.target_char_end,start=b.target_char_start;assert.ok(end<=start);assert.ok(end===start||(start===end+1&&full.slice(end,start).join('')===' '));assert.ok(number(b.baseline)-number(a.baseline)>.002);}
    }else{
      for(let i=1;i<ranges.length;i++)assert.equal(ranges[i-1][1],ranges[i][0]);
    }
    const baselines=parts.map(p=>number(p.baseline)).sort((a,b)=>a-b);
    for(let i=1;i<baselines.length;i++)assert.ok(baselines[i]-baselines[i-1]>.002,'Ambiguous same-baseline source ID '+id);
  }
  for(const[i,p]of(body.raster_labels||[]).entries()){const key='raster:'+i;labels.push([key,p]);add(p,key,true);}
  const corrected=new Set();for(const c of body.r4_source_style_corrections){const candidates=(bodyIDs.get(c.source_slot_id)||[]).filter(key=>specs.get(key).placement.text===c.target_text&&Math.abs(number(specs.get(key).placement.baseline)-number(c.baseline))<=.001);assert.equal(candidates.length,1);const key=candidates[0],s=specs.get(key);assert.ok(s&&!corrected.has(key));assert.equal(s.angle,14);assert.equal(c.target_text,s.placement.text);assert.ok(Math.abs(number(c.baseline)-number(s.placement.baseline))<=.001);assert.equal(c.original_descriptor_angle,-14);assert.equal(c.physical_target_angle,14);assert.equal(c.original_point_size_and_logical_origin_unchanged,true);assert.ok(Math.abs(number(c.physical_pdf_shear_c)-Math.tan(14*Math.PI/180))<=1e-6);corrected.add(key);}
  assert.deepEqual([...corrected].sort(),[...specs].filter(([k,s])=>!s.label&&s.angle===14).map(([k])=>k).sort());
  const resolve=(id,baseline)=>{
    if(bodyIDs.has(id)){const found=bodyIDs.get(id).filter(key=>Math.abs(number(specs.get(key).placement.baseline)-number(baseline))<=.001);assert.equal(found.length,1,'Unknown or ambiguous source ID/baseline '+id);return found[0];}const found=[];
    for(const[key,p]of labels){const prefix='raster:'+p.source_text+':';if(id.startsWith(prefix)){try{assert.deepEqual(JSON.parse(id.slice(prefix.length)),p.rect);found.push(key);}catch(e){if(!(e instanceof SyntaxError)&&!(e instanceof assert.AssertionError))throw e;}}}
    assert.equal(found.length,1,'Unknown or ambiguous source ID '+id);return found[0];
  };
  const p=audit.actual_full_Tm_CTM_physical_transform_audit;assert.equal(p.passed,true);assert.equal(p.source_rotation_plan_bound_to_P0_layout,true);assert.equal(p.unaccounted_glyphs,0);assert.equal(p.unbound_streams,0);
  const mt=number(p.linear_matrix_tolerance),gt=number(p.glyph_origin_tolerance_pt);assert.ok(mt>0&&mt<=1e-6&&gt>0&&gt<=.001);
  const rows=p.source_bound_transform_streams;assert.equal(integer(p.all_actual_KO_streams_verified),rows.length);assert.ok(rows.length);
  const xrefs=new Set(),counts=new Map(),spaces=new Map(),italic=[],bound=[];
  for(const row of rows){
    const xref=integer(row.xref,1);assert.ok(!xrefs.has(xref));xrefs.add(xref);hash(row.raw_stream_sha256);assert.equal(row.source_ids.length,1);
    const key=resolve(row.source_ids[0],row.baseline),s=specs.get(key);assert.equal(row.source_label,s.label);assert.equal(row.font_alias,s.alias);assert.equal(row.planned_rotation,s.rotation);assert.equal(row.planned_physical_shear_angle,s.angle);
    const n=integer(row.glyphs_including_spaces,1),sp=integer(row.spaces);assert.ok(sp<=n);count(counts,key,n);count(spaces,key,sp);
    const entry=row.canonical_entry_graphics_state;near(vector(entry.ctm,6),[1,0,0,1,0,0],mt);assert.equal(number(entry.fill_alpha),1);assert.equal(number(entry.stroke_alpha),1);assert.deepEqual(entry.unsafe_styles,{});assert.equal(entry.clip,false);
    assert.deepEqual(Object.keys(entry.text).sort(),['Tc','Tw','Ts','Tz','Tr'].sort());for(const[k,v]of Object.entries({Tc:0,Tw:0,Ts:0,Tz:100,Tr:0}))assert.equal(number(entry.text[k]),v);
    assert.equal(number(row.actual_fill_opacity),1);assert.equal(number(row.actual_stroke_opacity),1);
    const composed=vector(row.composed_text_matrix_pdf,6),replay=multiply(row.actual_text_matrix,row.actual_CTM_at_paint);near(replay.slice(0,4),composed.slice(0,4),mt);near(replay.slice(4),composed.slice(4),gt);
    const residual=multiply(rotation((360-s.rotation)%360),composed).slice(0,4),expected=[1,0,Math.tan(s.angle*Math.PI/180),1];near(vector(row.rotation_removed_linear,4),residual,mt);near(vector(row.expected_rotation_removed_linear,4),expected,mt);
    const error=Math.max(...residual.map((v,i)=>Math.abs(v-expected[i])));assert.ok(error<=mt);assert.ok(number(row.max_linear_error)>=0&&row.max_linear_error<=mt&&Math.abs(row.max_linear_error-error)<=1e-9);assert.ok(Math.abs(number(row.physical_pdf_cm_c)-residual[2])<=mt);
    const length=Math.hypot(composed[0],composed[1]);assert.ok(length>0);const direction=[composed[0]/length,-composed[1]/length];near(vector(row.actual_baseline_direction,2),direction,mt);
    const horizontal=Math.abs(direction[1])<=1e-6&&Math.abs(Math.abs(direction[0])-1)<=1e-6;assert.equal(row.horizontal_for_row_pairs,horizontal);assert.ok(number(row.max_actual_replay_origin_error_pt)>=0&&row.max_actual_replay_origin_error_pt<=gt);
    number(row.baseline);if(!s.label)assert.ok(Math.abs(row.baseline-number(s.placement.baseline))<=gt);if(s.angle)italic.push(row);bound.push([row,s,composed]);
  }
  assert.deepEqual([...counts].filter(([k,v])=>v).map(([k])=>k).sort(),[...specs].filter(([k,s])=>s.count).map(([k])=>k).sort());
  for(const[key,s]of specs){assert.equal(counts.get(key)||0,s.count,'Source glyph coverage '+key);assert.equal(spaces.get(key)||0,s.spaces,'Source space coverage '+key);}
  assert.equal([...counts.values()].reduce((a,b)=>a+b,0),total);assert.equal(p.all_KO_glyphs_including_spaces_verified,total);assert.equal([...spaces.values()].reduce((a,b)=>a+b,0),spacesExpected);assert.equal(p.spaces_verified,spacesExpected);
  assert.deepEqual(p.source_bound_italic_streams,italic);assert.deepEqual(audit.actual_target_physical_shear,italic);
  const offsets=bound.filter(([r,s])=>!s.label).map(([r,s,m])=>number(s.placement.baseline)+m[5]);assert.ok(offsets.length&&Math.max(...offsets)-Math.min(...offsets)<=gt);
  for(const[row,s,m]of bound)assert.ok(Math.abs(row.baseline-(offsets[0]-m[5]))<=gt);
  const nonspace=total-spacesExpected;geometry(audit.original_full_master_geometry,nonspace);geometry(audit.actual_including_space_glyph_geometry,total);
  assert.equal(audit.actual_outline_and_encoded_W_audit_pending,false);const outline=audit.actual_outline_and_encoded_W_audit;assert.equal(outline.passed,true);assert.deepEqual(outline.errors,[]);assert.equal(outline.master_hmtx_and_gid_exact,true);assert.equal(outline.actual_CID_TJ_W_glyphs_verified,nonspace);assert.equal(outline.actual_master_outline_bounds_verified,nonspace);assert.ok(number(outline.tolerance_pt)>0&&outline.tolerance_pt<=.001);
  for(const key of['actual_W_TJ_replay_max_origin_error_pt','max_transformed_outline_error_pt'])assert.ok(number(outline[key])>=0&&outline[key]<=.001);
  const encoded=outline.encoded_glyph_details;assert.equal(encoded.length,nonspace);const observed=new Map();
  for(const g of encoded){assert.equal(typeof g.character,'string');assert.equal(Array.from(g.character).length,1);assert.equal(white(g.character),false);count(observed,g.alias+'\0'+g.character);integer(g.gid,1);integer(g.cid,1);assert.ok(Number.isFinite(Number(g.encoded_W))&&Number(g.encoded_W)>0);near(vector(g.actual_origin,2),vector(g.replayed_origin,2),.001);hash(outline.actual_font_program_sha256[g.alias]);}
  assert.deepEqual([...observed].sort(),[...expectedChars].sort());
  const ink=audit.actual_stream_interrow_ink;for(const key of['passed','all_target_KO_glyphs_accounted_for','each_extracted_row_glyph_trace_matches_target'])assert.equal(ink[key],true);assert.equal(ink.stream_count,rows.length);assert.equal(ink.scale,2);assert.equal(ink.threshold,220);assert.equal(ink.same_row_tolerance_pt,.001);assert.equal(ink.close_row_selection_em,1.1);
  const orthogonal=rows.filter(r=>!r.horizontal_for_row_pairs),excluded=ink.orthogonal_streams_excluded_from_horizontal_pairs;assert.equal(excluded.length,orthogonal.length);for(const[i,x]of excluded.entries()){const r=orthogonal[i];assert.equal(x.xref,r.xref);assert.deepEqual(x.aliases,[r.font_alias]);assert.deepEqual(x.tm,r.actual_text_matrix);}
  const grouped=[];for(const[row,s]of bound.filter(([r])=>r.horizontal_for_row_pairs).sort((a,b)=>a[0].baseline-b[0].baseline)){if(!grouped.length||Math.abs(grouped.at(-1)[0]-row.baseline)>.001)grouped.push([row.baseline,s.size]);else grouped.at(-1)[1]=Math.max(grouped.at(-1)[1],s.size);}
  const pairs=[];for(const[i,u]of grouped.entries())for(const d of grouped.slice(i+1))if(d[0]-u[0]<Math.max(u[1],d[1])*1.1)pairs.push([u[0],d[0],d[0]-u[0]]);
  assert.equal(ink.rows,grouped.length);assert.equal(ink.tested_close_row_pairs,pairs.length);assert.equal(ink.pairs.length,pairs.length);for(const[i,a]of ink.pairs.entries()){near([a.upper_baseline,a.lower_baseline,a.gap_pt],pairs[i],.001);assert.equal(a.contact_pixels_2x,0);}
  for(const pair of ink.corrected_special_pair_multiscale)assert.deepEqual(pair.contact_pixels_by_scale,{'2':0,'4':0,'8':0});assert.deepEqual(ink.failures,[]);
  const native=audit.actual_target_language_vs_native_ink;assert.equal(native.passed,true);assert.equal(native.actual_KO_vs_original_remaining_ink_contact_pixels_2x,0);assert.equal(native.original_font_resources_preserved_in_both_controls,true);
  return{status:STATUS,page:body.page,streams:rows.length,glyphs_including_spaces:total,spaces:spacesExpected,nonspace_glyphs:nonspace,source_ids:[...specs.values()].filter(s=>s.count).length,italic_streams:italic.length};
}
module.exports=validate;
module.exports.multiply=multiply;
