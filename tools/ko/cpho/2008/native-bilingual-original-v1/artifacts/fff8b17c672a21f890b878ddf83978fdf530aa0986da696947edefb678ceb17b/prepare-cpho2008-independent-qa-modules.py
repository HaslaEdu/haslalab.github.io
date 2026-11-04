from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parents[1];E=B/'engine';R=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native/engine')
names=['pdf_moved_native_ink.py','pdf_original_graphics_ink.py','pdf_original_image_ink.py','pdf_native_geometry_motion.py','pdf_native_script_motion_audit.py','pdf_new_prose_native_text_overlap.py','pdf_hangul_visibility.py','pdf_new_hangul_graphics_overlap.py','pdf_text_motion_ink.py','izho_new_prose_outline_qa.py','izho_native_math_audit.py','izho_translate.py','izho_extract_word.py','izho_math_clean.py']
records=[]
for name in names:
 p=R/name;q=E/name
 if not q.exists():q.write_bytes(p.read_bytes())
 assert q.read_bytes()==p.read_bytes();records.append(dict(module=name,read_only_parent=str(p),sha256=hashlib.sha256(q.read_bytes()).hexdigest(),copied_exactly=True))
(E/'independent-qa-module-provenance.json').write_text(json.dumps(records,indent=2)+'\n','utf8')
# Only this new-prose-resource selector changes in the private2008 copy.
# Original/native math never participates in the translation-font audit.
p=E/'pdf_new_prose_outlines.py';s=p.read_text('utf8');old="PREFIXES=('/Translation','/RasterTranslation','/FigureLanguage')";new="PREFIXES=('/Translation','/RasterTranslation','/FigureLanguage','/C08Translated')"
if old in s:p.write_text(s.replace(old,new),'utf8')
else:assert new in s
primitive=(R/'izho_new_prose_outline_qa.py').read_text('utf8');needle="program=program,basefont=str(font['/BaseFont']))";replacement="program=program,basefont=bytes(font['/BaseFont']).decode('latin1'))"
assert needle in primitive;primitive=primitive.replace(needle,replacement)
primitive=primitive.replace('counts=Counter();mapped=[];programs={}','counts=Counter();mapped=[];programs={};source2008_literal_identity_suffix=set()')
anchor="family=family_name(bytes(font['/BaseFont']).decode('latin1'))"
strict=anchor+'''
            # Closed original2008 Symbol+FPEF identity resource. MuPDF exposes
            # only FPEF; validate every actual original GID against the encoded
            # CID below. No source font, ToUnicode or glyph is changed.
            child=font.get('/DescendantFonts',[font])[0]
            if family=='Symbol+FPEF' and 'FPEF'in queues and str(font.get('/Encoding'))=='/Identity-H' and str(child.get('/CIDToGIDMap'))=='/Identity' and '/FontFile2'in child.get('/FontDescriptor',{}):
                family='FPEF';source2008_literal_identity_suffix.add(font.objgen)
'''
assert anchor in primitive;primitive=primitive.replace(anchor,strict)
primitive=primitive.replace("program=program,basefont=bytes(font['/BaseFont']).decode('latin1'))","program=program,basefont=bytes(font['/BaseFont']).decode('latin1'),source2008_exact_original_identity_suffix=font.objgen in source2008_literal_identity_suffix)")
anchor="if len(cluster)>1 and(any(g['gid']!=-1"
check="if font['source2008_exact_original_identity_suffix'] and (cluster[0]['gid']!=code or any(g['gid']!=-1 for g in cluster[1:])):raise ValueError('Source2008 original Identity CID/GID mapping changed')\n                    "+anchor
assert anchor in primitive;primitive=primitive.replace(anchor,check)
(E/'cpho2008_prose_outline_primitives.py').write_text(primitive,'utf8')
p=E/'pdf_new_prose_outlines.py';s=p.read_text('utf8');p.write_text(s.replace('from izho_new_prose_outline_qa import trace_font_resources,outline_results','from cpho2008_prose_outline_primitives import trace_font_resources,outline_results'),'utf8')
(E/'source2008-raw-name-byte-presentation-policy.json').write_text(json.dumps(dict(original_source_sha256='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d',private_primitive_parent=str(R/'izho_new_prose_outline_qa.py'),parent_sha256=hashlib.sha256((R/'izho_new_prose_outline_qa.py').read_bytes()).hexdigest(),changes=['BaseFont metadata uses reversible Latin1 of literal PDF Name bytes instead of invalid UTF8 str().','Closed original /Symbol+FPEF Identity-H and Identity CIDToGIDMap with embedded FontFile2 associates actual MuPDF trace FPEF only after every original CID equals its actual trace GID; no fabricated Unicode or generic font substitution.'],actual_font_dictionary_resource_bytes_checked_separately=True,source_font_CID_GID_Tf_Tm_Unicode_paint_and_all_loss_thresholds_unchanged=True,PDF_bytes_not_modified=True),indent=2)+'\n','utf8')
print('C08_PRIVATE_EXACT_QA_MODULES',len(records))
