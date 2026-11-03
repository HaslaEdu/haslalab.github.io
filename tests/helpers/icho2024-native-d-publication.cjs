const assert=require('node:assert/strict');
const SOURCE='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a';
const PROFILE='f3efb347598737eb8505f8f529e044e15ee4307a8bdf5caaced7e88f2b09ff3d';
const AUDITOR='f3129c8888eedf9a9d51c82c5533e6f4bcb50a74d84c8cc44dff3f23da5b3207';
const FONTS=[['/F3','NotoSans','186a06d556fbf461b1fd7799d76ae932f78c515e8d47a62bf86dc941d6dea53e',10368],
  ['/F7','LatinModernMath-Regular','7eee87a2a9a92e361674a0586bffdd483efa519fd45648ca496b5376b4597819',2343]];

module.exports=function validateNativeD(body,audit,profile,layoutSHA,qa) {
  assert.equal(body.source_sha256,SOURCE);assert.equal(audit.source_sha256,SOURCE);
  assert.equal(body.page,57);assert.equal(audit.page,57);assert.equal(profile.page,57);
  assert.equal(audit.status,'PASS');assert.equal(audit.proof_sha256,body.output_sha256);
  assert.equal(audit.layout_sha256,layoutSHA);assert.equal(audit.source_profile_sha256,PROFILE);
  assert.equal(audit.program_sha256,AUDITOR);
  assert.ok(qa.authoring_programs.some(p=>p.sha256===AUDITOR),'Missing actual native-d auditor');
  const tolerance=audit.glyph_tolerance_pt;
  assert.ok(tolerance>0&&tolerance<=.001);
  assert.ok(audit.native_vector_tolerance_pt>0&&audit.native_vector_tolerance_pt<=1e-7);
  assert.equal(audit.actual_original_native_glyphs,6);assert.equal(audit.glyphs.length,6);
  assert.ok(audit.actual_common_dx_spread_pt>=0&&audit.actual_common_dx_spread_pt<=tolerance);
  const expected=[profile.actual_original_d_glyph,...profile.original_adjacent_native_subscript_group.glyphs];
  assert.equal(expected.length,6);
  const dx=[];
  for(const [i,row]of audit.glyphs.entries()) {
    const {source,actual}=row;
    for(const field of ['c','gid','font','size','origin','bbox']) assert.deepEqual(source[field],expected[i][field]);
    for(const field of ['c','gid','font','size','paint','opacity','color','direction']) assert.deepEqual(actual[field],source[field]);
    assert.equal(source.paint,0);assert.equal(source.opacity,1);
    assert.deepEqual(source.direction,[1,0]);assert.deepEqual(source.color,[0,0,0]);
    const delta=actual.origin[0]-source.origin[0];
    assert.ok(Number.isFinite(delta)&&Math.abs(delta-row.actual_dx)<=1e-9);
    assert.ok(Math.abs(actual.origin[1]-source.origin[1])<=tolerance);
    for(let k=0;k<4;k++) assert.ok(Math.abs(actual.bbox[k]-source.bbox[k]-([0,2].includes(k)?delta:0))<=tolerance);
    dx.push(delta);
  }
  const spread=Math.max(...dx)-Math.min(...dx);
  assert.ok(spread<=tolerance&&Math.abs(spread-audit.actual_common_dx_spread_pt)<=1e-9);
  assert.equal(audit.source_and_actual_embedded_font_resources.length,2);
  for(const [i,row]of audit.source_and_actual_embedded_font_resources.entries()) {
    const [resource,family,digest,size]=FONTS[i];
    assert.equal(row.trace_family,family);
    const {object_reference:_sourceRef,...source}=row.source;
    const {object_reference:_actualRef,...actual}=row.actual;
    assert.deepEqual(actual,source);
    assert.equal(source.resource,resource);assert.equal(source.base_family,family);assert.equal(source.descriptor_family,family);
    assert.deepEqual(source.internal_PostScript_names,[family]);assert.equal(source.Encoding,'/Identity-H');
    assert.equal(source.embedded_program_sha256,digest);assert.equal(source.embedded_program_bytes,size);
  }
  for(const key of ['actual_visible_new_Korean_d_count_at_orbital_row',
    'measured_source_ordinary_space_glyphs_between_d_and_subscript',
    'measured_actual_ordinary_space_glyphs_between_d_and_subscript']) assert.equal(audit[key],0);
  for(const key of ['source_ordinary_spaces','actual_ordinary_spaces','actual_new_Korean_d_glyphs']) assert.deepEqual(audit[key],[]);
  const sourceGap=audit.glyphs[1].source.origin[0]-audit.glyphs[0].source.origin[0];
  const actualGap=audit.glyphs[1].actual.origin[0]-audit.glyphs[0].actual.origin[0];
  assert.ok(Math.abs(sourceGap-audit.source_d_to_first_subscript_dx)<=1e-9);
  assert.ok(Math.abs(actualGap-audit.actual_d_to_first_subscript_dx)<=1e-9);
  assert.ok(Math.abs(sourceGap-actualGap)<=tolerance);
};
