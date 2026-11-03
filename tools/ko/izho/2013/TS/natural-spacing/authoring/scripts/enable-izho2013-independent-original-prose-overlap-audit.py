from pathlib import Path
import hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');p=B/'engine/izho_natural_spacing_qa.py';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();text=p.read_text('utf8')
needle='        # Match input native physical glyphs to the ORIGINAL English source;'
assert text.count(needle)==1;history=B/'engine/history'/sha(p)[:16];history.mkdir(parents=True,exist_ok=True);shutil.copy2(p,history/p.name)
block="""        if plan.get('reviewed_original_prose_bitmap_overlap_references'):
            from izho_2013_prose_bitmap_overlap_reference import audit_reference
            figures=[audit_reference(plan,figure,original_figure_pixels,b,folder,fresh_render)for figure in figures]

"""
p.write_text(text.replace(needle,block+needle),'utf8');assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';print('INDEPENDENT_EXACT_ORIGINAL_ENGLISH_DESCENDER_REFERENCE_AUDIT_ENABLED',sha(p),flush=True)
