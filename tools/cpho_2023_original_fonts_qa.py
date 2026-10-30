"""Audit actual new PDF font codes and original source font programs."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re
from io import BytesIO
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import pikepdf
import pymupdf as fitz
from pdf_original_text_ops import source_code_bytes,widths,cmap
from pdf_original_style_audit import glyphs,key
import cpho_2023_original_style as b

def audit(path):
    path=Path(path);source=fitz.open(b.SOURCE);final=fitz.open(path)
    report=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pages=[],nonpositive_width_codes=[],new_missing_or_han_glyphs=[],empty_new_nonspace_glyphs=[],passed=True)
    with pikepdf.open(path)as pdf:
        for index,page in enumerate(pdf.pages):
            aliases={a for a in page.Resources.Font.keys()if str(a).startswith(('/Translation','/FigureLanguage'))}
            current=None;codes_checked=0;ascii_checked=0;issues=[];empty=[];programs_by_alias={};checked_ink=set()
            for item in pikepdf.parse_content_stream(page):
                op=str(item.operator);values=item.operands
                if op=='Tf':current=values[0]
                if op not in['Tj','TJ']or current not in aliases:continue
                font=page.Resources.Font[current];count=source_code_bytes(font);ws,default=widths(font);mapping=cmap(font)
                strings=[values[0]]if op=='Tj'else[v for v in values[0]if isinstance(v,pikepdf.String)]
                for string in strings:
                    raw=bytes(string);assert len(raw)%count==0
                    for pos in range(0,len(raw),count):
                        code=int.from_bytes(raw[pos:pos+count],'big');width=ws.get(code,default);char=mapping.get(code);codes_checked+=1
                        if char and len(char)==1 and ord(char)<128:ascii_checked+=1
                        if width is None or width<=0:issues.append(dict(alias=str(current),code=code,text=char,width=width))
                        if char and not char.isspace()and(current,code)not in checked_ink:
                            checked_ink.add((current,code))
                            if current not in programs_by_alias:
                                programs_by_alias[current]=TTFont(BytesIO(final.extract_font(font.objgen[0])[3]))
                            ft=programs_by_alias[current];desc=font.DescendantFonts[0];gid_mapping=desc.get('/CIDToGIDMap')
                            if isinstance(gid_mapping,pikepdf.Stream):
                                raw_map=gid_mapping.read_bytes();gid=int.from_bytes(raw_map[code*2:code*2+2],'big')
                            elif'CFF 'in ft and hasattr(ft['CFF '].cff.topDictIndex[0],'ROS'):
                                name=f'cid{code:05d}';gid=ft.getGlyphID(name)if name in ft.getGlyphOrder()else 0
                            else:gid=code
                            name=ft.getGlyphOrder()[gid];gs=ft.getGlyphSet();pen=BoundsPen(gs);gs[name].draw(pen)
                            if gid==0 or pen.bounds is None:empty.append(dict(alias=str(current),code=code,text=char,actual_gid=gid,glyph_name=name))
            original=Counter(key(g)for g in glyphs(source[index]));added=[]
            for g in glyphs(final[index]):
                token=key(g)
                if original[token]:original[token]-=1
                else:added.append(g)
            invalid=[g for g in added if g['gid']==0 or g['c']in['\x00','\ufffd']or re.search('[\u3400-\u9fff]',g['c'])]
            def programs(doc,page):
                return Counter((f[3],hashlib.sha256(doc.extract_font(f[0])[3]).hexdigest())for f in page.get_fonts(full=True)if not f[4].startswith(('Translation','FigureLanguage')))
            same=programs(source,source[index])==programs(final,final[index])
            row=dict(page=index+1,new_font_codes_checked=codes_checked,ascii_codes_checked=ascii_checked,new_glyphs_checked=len(added),nonpositive_width_codes=issues,new_missing_or_han_glyphs=invalid,empty_new_nonspace_glyphs=empty,actual_nonspace_glyph_outlines_checked=len(checked_ink),original_font_programs_identical=same)
            report['pages'].append(row);report['nonpositive_width_codes']+=issues;report['new_missing_or_han_glyphs']+=invalid;report['empty_new_nonspace_glyphs']+=empty;report['passed']&=not issues and not invalid and not empty and same
            for ft in programs_by_alias.values():ft.close()
    source.close();final.close();return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit(a.pdf);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8');print(r['file'],'codes',sum(p['new_font_codes_checked']for p in r['pages']),'invalid',len(r['nonpositive_width_codes'])+len(r['new_missing_or_han_glyphs']));raise SystemExit(not r['passed'])
