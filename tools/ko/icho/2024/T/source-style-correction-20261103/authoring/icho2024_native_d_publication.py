"""Narrow publication contract for the six original orbital glyphs on page57."""
import math

SOURCE='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
PROFILE='f3efb347598737eb8505f8f529e044e15ee4307a8bdf5caaced7e88f2b09ff3d'
AUDITOR='f3129c8888eedf9a9d51c82c5533e6f4bcb50a74d84c8cc44dff3f23da5b3207'
FONTS=[('/F3','NotoSans','186a06d556fbf461b1fd7799d76ae932f78c515e8d47a62bf86dc941d6dea53e',10368),
       ('/F7','LatinModernMath-Regular','7eee87a2a9a92e361674a0586bffdd483efa519fd45648ca496b5376b4597819',2343)]

def validate(body,audit,profile,layout_sha256):
    assert body['source_sha256']==audit['source_sha256']==SOURCE
    assert body['page']==audit['page']==profile['page']==57
    assert audit['status']=='PASS'and audit['proof_sha256']==body['output_sha256']
    assert audit['layout_sha256']==layout_sha256 and audit['source_profile_sha256']==PROFILE
    assert audit['program_sha256']==AUDITOR
    tolerance=audit['glyph_tolerance_pt']
    assert 0<tolerance<=.001 and 0<audit['native_vector_tolerance_pt']<=1e-7
    assert audit['actual_original_native_glyphs']==len(audit['glyphs'])==6
    assert 0<=audit['actual_common_dx_spread_pt']<=tolerance
    expected=[profile['actual_original_d_glyph']]+profile['original_adjacent_native_subscript_group']['glyphs']
    assert len(expected)==6
    dx=[]
    for row,reference in zip(audit['glyphs'],expected):
        source,actual=row['source'],row['actual']
        for field in ('c','gid','font','size','origin','bbox'):
            assert source[field]==reference[field],('Unbound source orbital glyph',field)
        for field in ('c','gid','font','size','paint','opacity','color','direction'):
            assert actual[field]==source[field],('Changed native orbital glyph',field)
        assert source['paint']==0 and source['opacity']==1 and source['direction']==[1.,0.]
        assert source['color']==[0.,0.,0.]
        delta=actual['origin'][0]-source['origin'][0]
        assert math.isfinite(delta)and abs(delta-row['actual_dx'])<=1e-9
        assert abs(actual['origin'][1]-source['origin'][1])<=tolerance
        for index in range(4):
            assert abs(actual['bbox'][index]-source['bbox'][index]-(delta if index in(0,2)else 0))<=tolerance
        dx.append(delta)
    assert max(dx)-min(dx)<=tolerance
    assert abs(max(dx)-min(dx)-audit['actual_common_dx_spread_pt'])<=1e-9
    assert len(audit['source_and_actual_embedded_font_resources'])==2
    for row,(resource,family,digest,size)in zip(audit['source_and_actual_embedded_font_resources'],FONTS):
        assert row['trace_family']==family
        source,actual=row['source'],row['actual']
        assert {k:v for k,v in source.items()if k!='object_reference'}=={k:v for k,v in actual.items()if k!='object_reference'}
        assert source['resource']==resource and source['base_family']==source['descriptor_family']==family
        assert source['internal_PostScript_names']==[family] and source['Encoding']=='/Identity-H'
        assert source['embedded_program_sha256']==digest and source['embedded_program_bytes']==size
    for key in ('actual_visible_new_Korean_d_count_at_orbital_row',
                'measured_source_ordinary_space_glyphs_between_d_and_subscript',
                'measured_actual_ordinary_space_glyphs_between_d_and_subscript'):
        assert audit[key]==0
    for key in ('source_ordinary_spaces','actual_ordinary_spaces','actual_new_Korean_d_glyphs'):
        assert audit[key]==[]
    source_gap=audit['glyphs'][1]['source']['origin'][0]-audit['glyphs'][0]['source']['origin'][0]
    target_gap=audit['glyphs'][1]['actual']['origin'][0]-audit['glyphs'][0]['actual']['origin'][0]
    assert abs(source_gap-audit['source_d_to_first_subscript_dx'])<=1e-9
    assert abs(target_gap-audit['actual_d_to_first_subscript_dx'])<=1e-9
    assert abs(source_gap-target_gap)<=tolerance
