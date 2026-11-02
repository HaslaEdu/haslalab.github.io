"""Read-only actual embedded outline audit for named new PDF prose resources."""
from pathlib import Path
from io import BytesIO
import argparse,hashlib,json
import pikepdf,pymupdf as fitz
from fontTools.ttLib import TTFont
from izho_new_prose_outline_qa import trace_font_resources,outline_results

PREFIXES=('/Translation','/RasterTranslation','/FigureLanguage')

def audit(path):
    path=Path(path);report=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),delivered_pdf_modified=False,pages=[],passed=True)
    cache={}
    with pikepdf.open(path)as pdf,fitz.open(path)as doc:
        for index,page in enumerate(doc):
            aliases=[]
            for alias,font in pdf.pages[index].Resources.get('/Font',{}).items():
                if not str(alias).startswith(PREFIXES):continue
                descriptor=font.get('/DescendantFonts',[font])[0]['/FontDescriptor']
                field=next(k for k in ['/FontFile2','/FontFile3']if k in descriptor)
                with TTFont(BytesIO(descriptor[field].read_bytes()))as program:name=program['name'].getDebugName(6)
                if name not in{t['font']for t in page.get_texttrace()}:raise ValueError('Actual embedded face is absent from rendered traces')
                if str(font['/BaseFont'])!='/'+name:
                    aliases.append(dict(alias=str(alias),pdf_basefont=str(font['/BaseFont']),actual_postscript_name=name))
                    font['/BaseFont']=pikepdf.Name('/'+name)
            mapped,programs=trace_font_resources(pdf,page)
            new=[g for g in mapped if g['font_alias'].startswith(PREFIXES)and not g['c'].isspace()and g['gid']>=0]
            checked=[]
            for digest in sorted({g['font_program_sha256']for g in new}):
                if digest is None:raise ValueError('New prose font must be embedded')
                checked.extend(outline_results(dict(programs[digest],sha=digest),[g for g in new if g['font_program_sha256']==digest],cache))
            empty=[g for g in checked if g['outline_empty']]
            row=dict(page=index+1,new_nonspace_actual_gids_checked=len(checked),ascii_actual_gids_checked=sum(ord(g['c'])<128 for g in checked),empty_outlines=empty,analysis_only_alias_normalisation=aliases,passed=not empty)
            report['pages'].append(row);report['passed']&=row['passed']
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit(a.pdf);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8');print(r['file'],sum(x['new_nonspace_actual_gids_checked']for x in r['pages']),'actual outlines; passed',r['passed']);raise SystemExit(not r['passed'])
