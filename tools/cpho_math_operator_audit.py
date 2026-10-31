"""Find source math operators accidentally excluded from inline math sprites."""
from pathlib import Path
import argparse,json,hashlib
import pymupdf as fitz
from cpho_cjk_translate import characters,resolve_source
OPERATORS=set('−－＋＝<>＜＞±×÷≤≥≠')

def audit(manifest,pages=None,pdf=None):
    data=json.loads(manifest.read_text(encoding='utf8'));source=resolve_source(data);doc=fitz.open(source)
    missing=[];seen=set();assets=0;prose=[];native=0
    for entry in data['entries']:
        if pages and entry['page']+1 not in pages:continue
        chars=[c for c in characters(doc[entry['page']]) if c['c'] in OPERATORS]
        for mi,math in enumerate(entry['math']):
            if mi in entry.get('preserved_math',[]):
                native+=1
                continue
            assets+=1;box=fitz.Rect(math['source_rect']);origins=math.get('glyph_origins',[])
            for char in chars:
                x,y=char['origin']
                if not box.contains(fitz.Point(x,y)):continue
                seen.add((entry['page'],char['index']))
                if not any(abs(x-a)<.03 and abs(y-b)<.03 for a,b in origins):
                    item={'id':entry['id'],'page':entry['page']+1,'math':mi,'operator':char['c'],'origin':[x,y],'font':char['font']}
                    normalized={'＞':'>','＜':'<','－':'−','＋':'+','＝':'='}.get(char['c'],char['c'])
                    def count(value):return sum(value.count(c) for c in {normalized,char['c']})
                    required=count(entry['source'])
                    # Relational operators may legitimately be translated as
                    # prose characters between two separate math sprites.
                    if required and all(count(entry.get(lang,''))>=required for lang in ['ko','en']):prose.append(item)
                    else:missing.append(item)
    report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'math_assets':assets,'native_math_fields_preserved':native,'source_operators_checked':len(seen),'operators_preserved_in_prose':prose,'omitted_operators':missing}
    if pdf:report['pdf_sha256']=hashlib.sha256(pdf.read_bytes()).hexdigest()
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('manifest',type=Path)
    parser.add_argument('--pages',nargs='+',type=int);parser.add_argument('--pdf',type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();report=audit(args.manifest,args.pages,args.pdf)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False));raise SystemExit(bool(report['omitted_operators']))
