"""Read-only final-PDF audit: every new prose GID must have actual ink.

Encoded PDF text shows are matched to MuPDF traces in exact family/paint order
to identify the actual font resource, including duplicated subset face names.
The original source glyphs and extraction continuations are excluded. Positive
Widths, cmap coverage, and nonzero GIDs are never used as ink substitutes.
"""
from pathlib import Path
from collections import Counter,defaultdict
from io import BytesIO
import argparse,gc,hashlib,html,json,re,xml.etree.ElementTree as ET
import pikepdf
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.cffLib import CFFFontSet
from fontTools.pens.boundsPen import BoundsPen
from pdf_original_text_ops import family_name,cmap,source_code_bytes
from pdf_original_style_audit import key,glyphs

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-outline-audit')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trace_font_resources(pdf,page):
    """Read-only encoded-CID/trace association, preserving all source bytes."""
    queues=defaultdict(list);traces=page.get_texttrace();i=0
    while i<len(traces):
        t=traces[i];mode=t['type'];i+=1
        if mode==0 and i<len(traces):
            following=traces[i]
            if following['type']==1 and all(following[k]==t[k]for k in ['font','size','chars'])and following['seqno']==t['seqno']+1:
                mode=2;i+=1
        for cp,gid,origin,bbox in t['chars']:
            queues[family_name(t['font'])].append(dict(c=chr(cp),gid=gid,font=family_name(t['font']),size=t['size'],
                origin=list(origin),bbox=list(bbox),color=list(t['color']),render_type=mode))
    counts=Counter();mapped=[];programs={}

    def resources_fonts(resources):
        result={}
        for alias,font in resources.get('/Font',{}).items():
            family=family_name(bytes(font['/BaseFont']).decode('latin1'))
            if family not in queues:
                folded=lambda value:re.sub('[^a-z0-9]','',value.lower())
                aliases=[name for name in queues if folded(family)==folded(name)]
                if not aliases:aliases=[name for name in queues if family.startswith(name)or name.startswith(family)]
                if len(aliases)==1:family=aliases[0]
            if family not in queues:continue
            descriptor=font.get('/DescendantFonts',[font])[0].get('/FontDescriptor',{})
            program=None
            for field in ['/FontFile2','/FontFile3','/FontFile']:
                if field not in descriptor:continue
                stream=descriptor[field];raw=stream.read_bytes();digest=hashlib.sha256(raw).hexdigest()
                programs.setdefault(digest,dict(raw=raw,kind=field,subtype=str(stream.get('/Subtype'))))
                program=digest;break
            child=font.get('/DescendantFonts',[font])[0]
            identity=(str(font.get('/Encoding'))=='/Identity-H'and str(child.get('/CIDToGIDMap'))=='/Identity'and'/FontFile2'in descriptor)
            result[str(alias)]=dict(family=family,encoding=cmap(font),bytes=source_code_bytes(font),identity=identity,
                program=program,basefont=str(font['/BaseFont']))
        return result

    def walk(container,resources,state=('',0),ancestors=()):
        active,mode=state;stack=[];fonts=resources_fonts(resources)
        if len(ancestors)>20:raise ValueError('Excessive original Form nesting')
        for inst in pikepdf.parse_content_stream(container):
            op=str(inst.operator);args=inst.operands
            if op=='q':stack.append((active,mode))
            elif op=='Q':active,mode=stack.pop()
            elif op=='Tf':active=str(args[0])
            elif op=='Tr':mode=int(args[0])
            elif op=='Do':
                child=resources.get('/XObject',{}).get(args[0])
                if child is not None and str(child.get('/Subtype'))=='/Form':
                    if child.objgen in ancestors:raise ValueError('Recursive Form')
                    walk(child,child.get('/Resources',resources),(active,mode),ancestors+(child.objgen,))
            if op not in['Tj','TJ',"'",'"']or active not in fonts:continue
            font=fonts[active];family=font['family']
            strings=[value for value in args[0]if isinstance(value,pikepdf.String)]if op=='TJ'else[args[-1]]
            for string in strings:
                raw=bytes(string)
                if len(raw)%font['bytes']:raise ValueError('Incomplete final glyph code')
                for at in range(0,len(raw),font['bytes']):
                    code=int.from_bytes(raw[at:at+font['bytes']],'big');decoded=font['encoding'].get(code)
                    if not decoded:
                        pending=queues[family][counts[family]:counts[family]+1]
                        if not(font['identity']and len(pending)==1 and pending[0]['c']=='\ufffd'and pending[0]['gid']==code):
                            raise ValueError(('Unmapped final glyph',family,code))
                        decoded='\ufffd'
                    cluster=queues[family][counts[family]:counts[family]+len(decoded)]
                    if ''.join(g['c']for g in cluster)!=decoded or any(g['render_type']!=mode for g in cluster):
                        raise ValueError(('Final encoded font/trace association differs',family,code,decoded,cluster))
                    if len(cluster)>1 and(any(g['gid']!=-1 or g['origin']!=cluster[0]['origin']or g['size']!=cluster[0]['size']or abs(g['bbox'][2]-g['bbox'][0])>1e-6 for g in cluster[1:])):
                        raise ValueError('Unsupported final multi-Unicode glyph cluster')
                    for g in cluster:mapped.append(dict(g,font_alias=active,font_basefont=font['basefont'],font_program_sha256=font['program'],encoded_code=code))
                    counts[family]+=len(decoded)
        if stack:raise ValueError('Unbalanced final graphics stack')
    walk(pdf.pages[page.number],pdf.pages[page.number].Resources)
    if any(counts[family]!=len(q)for family,q in queues.items()):
        raise ValueError(('Final text traces were not completely associated',[(family,counts[family],len(q))for family,q in queues.items()if counts[family]!=len(q)]))
    return mapped,programs


def svg_outline_status(page,records):
    root=ET.fromstring(page.get_svg_image(text_as_path=True));defs={n.get('id'):n for n in root.iter()if n.get('id')}
    uses=[]
    for node in root.iter():
        if'data-text'not in node.attrib:continue
        matrix=re.search(r'matrix\(([^)]+)\)',node.get('transform',''))
        if not matrix:continue
        coords=[float(v)for v in matrix[1].replace(',',' ').split()]
        ref=node.get('{http://www.w3.org/1999/xlink}href')or node.get('href')or''
        outline=defs.get(ref.lstrip('#'));d=outline.get('d','')if outline is not None else''
        uses.append((node.attrib['data-text'],coords[-2:],bool(d.strip()),ref))
    results=[]
    for g in records:
        matches=[(ink,ref)for c,origin,ink,ref in uses if c==g['c']and all(abs(a-b)<.03 for a,b in zip(origin,g['origin']))]
        results.append(dict(g,outline_method='MuPDF actual resolved SVG outline (original font is unembedded)',
            outline_empty=not any(ink for ink,_ in matches),svg_outline_references=[ref for _,ref in matches]))
    return results


def outline_results(program,records,cache):
    pending={g['gid']for g in records if(program['sha'],g['gid'])not in cache}
    if pending:
        raw=program['raw'];font=None
        if raw[:4]in[b'\x00\x01\x00\x00',b'OTTO',b'true',b'ttcf']:
            font=TTFont(BytesIO(raw),lazy=True);order=font.getGlyphOrder();glyphset=font.getGlyphSet()
        elif program['kind']=='/FontFile3'and program['subtype']in['/Type1C','/CIDFontType0C']:
            cff=CFFFontSet();cff.decompile(BytesIO(raw),None);top=cff[cff.fontNames[0]];order=top.charset;glyphset=top.CharStrings
        else:raise ValueError(('Unsupported embedded final font program',program['kind'],program['subtype']))
        for gid in pending:
            if not 0<=gid<len(order):raise ValueError(('Final GID outside actual embedded program',gid,len(order)))
            pen=BoundsPen(glyphset);glyphset[order[gid]].draw(pen)
            bounds=pen.bounds
            empty=bounds is None or bounds[0]==bounds[2]or bounds[1]==bounds[3]
            cache[program['sha'],gid]=dict(outline_empty=empty,outline_bounds_units=list(bounds)if bounds else None,
                outline_glyph_name=order[gid],outline_method='final texttrace GID -> actual embedded font BoundsPen')
        if font is not None:font.close()
    return[dict(g,**cache[program['sha'],g['gid']])for g in records]


def edition(year,kind,path,plans,cache):
    rows=[];issues=[];new_ascii=total_new=unembedded=0
    with fitz.open(path)as target,pikepdf.open(path)as final:
        if len(target)!=len(plans):raise ValueError('Final page count differs from reviewed source plans')
        sources={}
        for pi,plan in enumerate(plans):
            p=json.loads(plan.read_text('utf8'));source_path=ROOT/p['source']
            if source_path not in sources:sources[source_path]=fitz.open(source_path)
            source_page=sources[source_path][p['page']];original_glyphs=glyphs(source_page);original=Counter(key(g)for g in original_glyphs)
            candidates=defaultdict(list)
            for g in original_glyphs:
                k=key(g);candidates[k[:4]+k[6:]].append((k,g['origin']))
            def consume_original(g):
                k=key(g)
                if original[k]:original[k]-=1;return True
                # Source/control TJ compensation can differ by one float32
                # ULP; this is the existing reviewed1e-4pt native tolerance.
                for source_key,origin in candidates[k[:4]+k[6:]]:
                    if original[source_key]and all(abs(a-b)<=.0001 for a,b in zip(origin,g['origin'])):
                        original[source_key]-=1;return True
                return False
            mapped,programs=trace_font_resources(final,target[pi]);new=[];excluded=continuations=0
            for g in mapped:
                if g['gid']<0:continuations+=1;continue
                # A Tr2 glyph represents the exact paired fill/stroke paints.
                if g['render_type']==2:
                    saved=original.copy()
                    if consume_original(dict(g,render_type=0))and consume_original(dict(g,render_type=1)):
                        excluded+=1;continue
                    original=saved
                elif consume_original(g):excluded+=1;continue
                if g['c'].isspace():continue
                new.append(g)
            by_program=defaultdict(list)
            for g in new:by_program[g['font_program_sha256']].append(g)
            checked=[]
            for digest,group in by_program.items():
                if digest is None:checked.extend(svg_outline_status(target[pi],group));unembedded+=len(group)
                else:checked.extend(outline_results(dict(programs[digest],sha=digest),group,cache))
            bad=[g for g in checked if g['outline_empty']]
            for g in bad:g.update(page=pi+1,source_page=p['page']+1,file=path.name)
            issues.extend(bad);ascii_count=sum(len(g['c'])==1 and ord(g['c'])<128 for g in checked)
            new_ascii+=ascii_count;total_new+=len(checked)
            rows.append(dict(page=pi+1,source_page=p['page']+1,source=str(source_path.relative_to(ROOT)),source_sha256=sha(source_path),
                identical_original_glyphs_excluded=excluded,zero_width_continuations_excluded=continuations,
                new_nonspace_glyphs_checked=len(checked),new_ascii_glyphs_checked=ascii_count,
                embedded_gids_checked=sum(g['font_program_sha256']is not None for g in checked),
                unembedded_resolved_outlines_checked=sum(g['font_program_sha256']is None for g in checked),
                empty_outlines=bad,font_programs_checked=sorted(d for d in by_program if d),
                checked_outline_records=checked))
            print(path.name,pi+1,'new',len(checked),'empty',len(bad),flush=True);gc.collect()
        for src in sources.values():src.close()
    report=dict(year=year,kind=kind,pdf=str(path.relative_to(ROOT)),sha256=sha(path),pages=len(rows),
        method='Original source identities excluded; exact final PDF CID/font-resource/trace association, then actual embedded GID bounds. Unembedded source fonts use the actually resolved SVG paths.',
        source_identity_origin_tolerance_pt=.0001,
        new_nonspace_glyphs_checked=total_new,new_ascii_glyphs_checked=new_ascii,
        unembedded_resolved_outlines_checked=unembedded,empty_outline_count=len(issues),empty_outlines=issues,page_audits=rows)
    OUT.mkdir(parents=True,exist_ok=True);(OUT/(path.stem+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--years',nargs='+',type=int);args=parser.parse_args()
    reports=[];cache={}
    for folder in sorted((ROOT/'tools/ko/izho').glob('*/*/original_style')):
        year=int(folder.parents[1].name);kind=folder.parent.name
        if args.years and year not in args.years:continue
        plans=sorted(folder.glob('page*.json'),key=lambda p:int(p.stem[4:]))
        if not plans:continue
        name=f'IZhO_{year}_{kind}_KO.pdf';path=ROOT/'pdfx/izho/original-style'/name
        if not path.exists():path=ROOT/'tmp/original-style-repair'/str(year)/kind/name
        if not path.exists():continue
        report=edition(year,kind,path,plans,cache)
        reports.append({k:v for k,v in report.items()if k!='page_audits'})
        summary=dict(editions=len(reports),pages=sum(r['pages']for r in reports),
            new_nonspace_glyphs_checked=sum(r['new_nonspace_glyphs_checked']for r in reports),
            new_ascii_glyphs_checked=sum(r['new_ascii_glyphs_checked']for r in reports),
            empty_outline_count=sum(r['empty_outline_count']for r in reports),edition_audits=reports)
        (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in summary.items()if k!='edition_audits'}),flush=True)


if __name__=='__main__':main()
