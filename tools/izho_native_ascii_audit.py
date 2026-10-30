"""Audit newly inserted native-font prose against actual PDF Widths / W.

The suppression-only control identifies the untouched original content stream;
only appended Korean/prose streams are inspected. Original math is never edited.
"""
from pathlib import Path
import argparse,hashlib,json
import pikepdf
from pdf_original_text_ops import cmap,widths

def streams(contents):return list(contents)if isinstance(contents,pikepdf.Array)else[contents]

def audit(pdf_path,control_folder):
    results=[]
    with pikepdf.open(pdf_path)as pdf:
        for i,page in enumerate(pdf.pages):
            control=control_folder/f'page{i+1}.control.pdf'
            with pikepdf.open(control)as source:
                originals={s.read_bytes()for s in streams(source.pages[0].Contents)}
                source_aliases=set(source.pages[0].Resources.Font.keys())
            found=set();checked=ascii_checked=0;issues=[];aliases=set();codes_seen={}
            for stream in streams(page.Contents):
                payload=stream.read_bytes()
                if payload in originals:found.add(payload);continue
                current=None
                for item in pikepdf.parse_content_stream(stream):
                    operator=str(item.operator);operands=item.operands
                    if operator=='Tf':current=operands[0]
                    if operator not in['Tj','TJ']:continue
                    if current is None:raise ValueError('A new text stream inherits an unknown font')
                    if str(current).startswith('/KO_'):continue
                    if current not in source_aliases:raise ValueError('Unexpected new non-Korean font alias '+str(current))
                    font=page.Resources.Font[current];encoding=str(font.get('/Encoding'))
                    count=1 if encoding=='/WinAnsiEncoding'else 2 if encoding=='/Identity-H'else 0
                    if not count:raise ValueError('Unknown native prose encoding '+encoding)
                    ws,default=widths(font);mapping=cmap(font);aliases.add(str(current))
                    strings=[operands[0]]if operator=='Tj'else[value for value in operands[0]if isinstance(value,pikepdf.String)]
                    for value in strings:
                        raw=bytes(value)
                        if len(raw)%count:raise ValueError('Truncated native text code')
                        for pos in range(0,len(raw),count):
                            code=int.from_bytes(raw[pos:pos+count],'big');char=mapping.get(code)
                            width=ws.get(code,default);checked+=1
                            if char is not None and len(char)==1 and ord(char)<128:ascii_checked+=1
                            codes_seen.setdefault(str(current),{})[str(code)]={'text':char,'width':width}
                            if width is None or width<=0:
                                issues.append(dict(font=str(current),basefont=str(font.get('/BaseFont')),code=code,text=char,width=width))
            if found!=originals:raise ValueError('Original suppression-control stream not identified exactly')
            results.append(dict(page=i+1,native_prose_codes_checked=checked,ascii_codes_checked=ascii_checked,
                                source_font_aliases=sorted(aliases),nonpositive_or_missing_widths=issues,
                                actual_pdf_widths_by_font_and_code=codes_seen))
    report=dict(pdf=str(pdf_path),sha256=hashlib.sha256(pdf_path.read_bytes()).hexdigest(),pages=len(results),
                new_native_prose_codes_checked=sum(r['native_prose_codes_checked']for r in results),
                ascii_codes_checked=sum(r['ascii_codes_checked']for r in results),
                nonpositive_or_missing_width_count=sum(len(r['nonpositive_or_missing_widths'])for r in results),page_audits=results)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf',type=Path);p.add_argument('controls',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    result=audit(a.pdf,a.controls);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items()if k!='page_audits'},ensure_ascii=False,indent=2))
    raise SystemExit(bool(result['nonpositive_or_missing_width_count']))
