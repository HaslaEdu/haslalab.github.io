"""Audit early Korean IZhO papers, including original vector diagrams.

Small Word equation bitmaps are not figures.  Unlike the general archive audit,
this audit checks the reviewed diagram ink boxes and also detects vector figures
whose source area would otherwise be covered by a translated paragraph.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re
import pymupdf as fitz
from izho_translate import ROOT,resolve_source

def metadata(year,kind):
    p=ROOT/f'tools/ko/izho/{year}/{kind}/translation.json'
    return json.loads(p.read_text(encoding='utf8'))

def audit(year,kind):
    base=metadata(year,kind);parts=[base]
    if year==2010 and kind=='TS':parts.append(metadata(2010,'T3S'))
    name=f'IZhO_{year}_'+('T3_S' if kind=='T3S' else kind)+'_KO.pdf'
    target=ROOT/'pdfx/izho'/name;doc=fitz.open(target);expected=[];issues=[];caption_candidates=[];vectors=[]
    entries=0;formula_crops=0;offset=0;source_hashes=[]
    for data in parts:
        fitz.TOOLS.set_small_glyph_heights(bool(data.get('small_glyph_heights')))
        source_path=resolve_source(data);source=fitz.open(source_path)
        if data.get('source_pages') is not None:source.select(data['source_pages'])
        source_hashes.append({'file':source_path.name,'sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'pages':data.get('source_pages')})
        for entry in data['entries']:
            if not entry['ko'].strip():issues.append('untranslated '+entry['id'])
            a=Counter(re.findall(r'\[\[\d+\]\]',entry['source']));b=Counter(re.findall(r'\[\[\d+\]\]',entry['ko']))
            if a!=b:issues.append('math placeholder mismatch '+entry['id'])
            formula_crops+=sum(b.values());entries+=1
        for pi,page in enumerate(source):
            expected.append(list(page.rect))
            if offset+pi>=len(doc):continue
            out=doc[offset+pi];korean=[]
            for block in out.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        if ('Noto' in span['font'] or 'Droid' in span['font']) and ('\x00' in span['text'] or '\ufffd' in span['text']):
                            issues.append({'missing_glyph':{'page':offset+pi+1,'text':repr(span['text']),'font':span['font']}})
                        if re.search('[가-힣]',span['text']):korean.append((fitz.Rect(span['bbox']),span['text']))
            if not korean:issues.append(f'no Korean on page {offset+pi+1}')
            figs=[fitz.Rect(f['rect']) for f in data.get('preserve_rects',[]) if f['page']==pi and f.get('kind')=='original_diagram_ink']
            for rect,text in korean:
                for figure in figs:
                    q=rect&figure
                    if q.width<=2 or q.height<=2:continue
                    overlays=[fitz.Rect(p['rect']) for p in data.get('post_overlays',[]) if p['page']==pi]
                    if any((rect&r).get_area()>rect.get_area()*.5 for r in overlays):continue
                    hit={'page':offset+pi+1,'text':text,'intersection':list(q)}
                    if re.fullmatch(r'그림\s*[12]',text.strip()):caption_candidates.append(hit)
                    else:issues.append({'diagram_intersection':hit})
            # A whole paragraph covering a native vector circuit/cube is a real
            # risk even when the original PDF has no corresponding bitmap.
            visible=[d for d in page.get_drawings() if any(c is not None and min(c)<.8 for c in (d.get('color'),d.get('fill')))]
            for r in page.cluster_drawings(drawings=visible,x_tolerance=8,y_tolerance=8):
                if r.width<60 or r.height<45 or r.y0<60:continue
                if any((r&f).get_area()>r.get_area()*.7 for f in figs):continue
                blockers=[]
                for e in data['entries']:
                    if e['page']!=pi or e.get('original_table_cell') or e.get('formula_adjacent_prose'):continue
                    q=fitz.Rect(e.get('redact_rect',e['rect']))&r
                    if q.get_area()>r.get_area()*.12:blockers.append(e['id'])
                if blockers:vectors.append({'page':offset+pi+1,'rect':list(r),'paragraphs':blockers})
            pix=out.get_pixmap(matrix=fitz.Matrix(.15,.15),colorspace=fitz.csGRAY)
            if min(pix.samples)>245:issues.append(f'blank page {offset+pi+1}')
        offset+=len(source);source.close()
    if len(expected)!=len(doc):issues.append(f'page count {len(doc)} != {len(expected)}')
    for i,(actual,wanted) in enumerate(zip(doc,expected)):
        if list(actual.rect)!=wanted:issues.append(f'page geometry differs {i+1}')
    item={'file':name,'pages':len(doc),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
          'translated_regions':entries,'lossless_inline_equation_placements':formula_crops,'sources':source_hashes,
          'issues':issues,'vector_candidates':vectors,'caption_bbox_candidates':caption_candidates,
          'design_review':'source page geometry, original figures, native equation objects, table cells, and original header rules'}
    doc.close();return item

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('years',type=int,nargs='+');p.add_argument('--kind',choices=['T','TS','T3S']);a=p.parse_args()
    report=[]
    for year in a.years:
        for kind in [a.kind] if a.kind else ['T','TS']:
            item=audit(year,kind);report.append(item)
            print(json.dumps(item,ensure_ascii=False),flush=True)
    target=ROOT/'tools/izho_early_validation.json'
    old=json.loads(target.read_text(encoding='utf8')) if target.exists() else []
    names={x['file'] for x in report};old=[x for x in old if x['file'] not in names]
    target.write_text(json.dumps(sorted(old+report,key=lambda x:x['file']),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if any(x['issues'] for x in report):raise SystemExit(1)
