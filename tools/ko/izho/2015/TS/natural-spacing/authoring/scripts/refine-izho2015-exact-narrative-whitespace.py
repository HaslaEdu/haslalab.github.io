from pathlib import Path
import hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2015-complete-solutions');E=B/'engine'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p):
 h=E/'history'/sha(p)[:16];h.mkdir(parents=True,exist_ok=True);shutil.copy2(p,h/p.name)
p=E/'izho_initial_fixed_style.py';save(p);t=p.read_text('utf8')
a="        math_keys={glyph_key(c)for c in math_spaces+form_glyphs if c['c'].isspace()}"
b="""        math_keys={glyph_key(c)for c in math_spaces+form_glyphs if c['c'].isspace()}-literal_label_keys
        if data['source_sha256']=='c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde'and pi==8:
            # This source has a real Times prose-space at the exact origin of
            # a separate protected zero-advance combining dot. Identity, not
            # a coordinate alone, distinguishes these two original glyphs.
            spec['reviewed_source2015_narrative_whitespace_policy']=dict(source_sha256=data['source_sha256'],page=9,conjunction_glyph_keys=[list(k)for k in literal_label_keys],shared_origin_space=dict(c=' ',font='Times New Roman',size=12.,origin=[361.5799865722656,646.0299682617188]),protected_zero_advance_accent=dict(c='̇',font='Times New Roman',size=12.,origin=[361.5799865722656,646.0299682617188]))"""
assert t.count(a)==1;t=t.replace(a,b);p.write_text(t,'utf8')
p=E/'pdf_original_style_audit.py';save(p);t=p.read_text('utf8')
a="    result=set()\n    for entry in journal:"
b="""    result=set()
    policy=spec.get('reviewed_source2015_narrative_whitespace_policy');math_prose=set();shared=None
    if policy:
        if policy['source_sha256']!='c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde'or policy['page']!=spec['source_page']or spec['source_page']!=9:raise ValueError('Unexpected source2015 narrative whitespace policy')
        math_prose={tuple(k)for k in policy['conjunction_glyph_keys']}
        from pdf_original_text_ops import glyph_key
        if any(k[1]!='Cambria Math'or k[0]not in ' and'or not(311<k[3]<370 and 610<k[4]<640)for k in math_prose):raise ValueError('Unreviewed mathematical-font prose range')
        shared=whitespace_identity(policy['shared_origin_space']);accent=policy['protected_zero_advance_accent']
        if accent['c']!='̇'or not any(whitespace_identity(g)==whitespace_identity(accent)for g in spec['protected_glyphs'])or not any(whitespace_identity(g)==whitespace_identity(accent)for g in old):raise ValueError('Separate source zero-advance accent is not protected')
    for entry in journal:"""
assert t.count(a)==1;t=t.replace(a,b)
a="        if token in protected or re.search(r'Cambria.?Math|Symbol|MT.?Extra',entry['font'],re.I)or any(close_origin(entry['origin'],p)for p in spec.get('protected_glyph_origins',[])):"
b="""        reviewed_literal=bool(policy)and glyph_key(entry)in math_prose
        shared_prose_space=shared==token
        if token in protected or(re.search(r'Cambria.?Math|Symbol|MT.?Extra',entry['font'],re.I)and not reviewed_literal)or(any(close_origin(entry['origin'],p)for p in spec.get('protected_glyph_origins',[]))and not shared_prose_space):"""
assert t.count(a)==1;t=t.replace(a,b);p.write_text(t,'utf8')
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
print('SOURCE2015_EXACT_SELECTED_PROSE_SPACE_DISTINGUISHED_FROM_SEPARATE_PROTECTED_COMBINING_DOT')
