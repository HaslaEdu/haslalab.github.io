from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent
p=B/'page06.overrides.json';q=json.loads(p.read_text('utf8'));q.setdefault('__slot_edits__',{})['p6:b3:l261:s0-0']=dict(text=':알데히드')
q['source_nmr_plot_aldehyde_review']='The established Korean term 알데히드 labels the same aldehyde class. Preserve the source colon adjacency and12pt type size within the original white interval between unchanged spectral bars; no chart path or threshold changes.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
p=B/'page25.overrides.json';q=json.loads(p.read_text('utf8'));edits=q.setdefault('__slot_edits__',{});edits.setdefault('p25:b28:l0:s0-0',{})['text']='w% (';edits.setdefault('p25:b28:l2:s0-0',{})['text']='및 ('
doc=f.open(g.SOURCE);raw=doc[24].get_text('rawdict');extras=[]
for li in[0,2]:
    span=raw['blocks'][28]['lines'][li]['spans'][2];source=''.join(c['c']for c in span['chars']);assert source==': '
    extras.append(dict(id=f'p25:b28:l{li}:s2-2:mass-percent-label-close',page=25,at=[28,li,2,2],source=source,rect=list(span['bbox']),point=list(span['chars'][0]['origin']),font=span['font'],font_role='serif',size=span['size'],dir=list(raw['blocks'][28]['lines'][li]['dir']),text='):'))
q['__extra_slots__']=[s for s in q.get('__extra_slots__',[])if s['id']not in{v['id']for v in extras}]+extras
q['mass_percent_label_review']='Original English field w% of A / and of B is expressed compactly as w%(A) / 및(B). The original w% unit and A/B glyph programs remain native, original answer-area geometry is unchanged; only English prose/punctuation becomes the corresponding Korean field notation.'
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('NMR label and native-first mass-percent answer labels refined.',flush=True)
