"""Document-specific parameter adapter demonstrating the generic scan QA API."""
import json
import pymupdf as fitz
from cpho_2013_ts_compose import BASE,ROOT,SOURCE,new_font,font_path,row_layout,write_row_token
from pdf_scanned_translation_ink_qa import audit_scan_page

def audit(number,lang):
 out=BASE/'proofs'/lang;target=out/f'page{number:02d}.pdf'
 composition=json.loads(target.with_suffix('.composition.json').read_text('utf8'));layout=json.loads((BASE/'authoring'/f'page{number:02d}-layout.json').read_text('utf8'))
 text=''.join(t['text']for row in composition['body_placements']for t in row['tokens']if t['kind']=='prose')
 raw_font,metric,_=new_font(font_path(lang),text)
 with fitz.open(SOURCE)as source:bounds=source[number-1].rect
 ref=fitz.open();page=ref.new_page(width=bounds.width,height=bounds.height);page.insert_font(fontname='TSScanBody',fontbuffer=raw_font)
 for row in layout['rows']:
  tokens,_=row_layout(row,lang,metric)
  for token in tokens:
   if token['kind']=='prose':write_row_token(page,row,token,metric,'TSScanBody',lang)
 prose=target.with_suffix('.prose-only.pdf');ref.save(prose,garbage=0,deflate=False);ref.close()
 slots=json.loads((ROOT/'tools/ko/cpho/2013/original/native-slots.json').read_text('utf8'))['pages'][number-1]['slots']
 header_rects=[c['bbox']for slot in slots for c in slot['source_characters']]
 header_rects +=[[r['left']-1,r['baseline']-r['size']*1.4,r['right']+1,r['baseline']+r['size']*.4]for r in composition['header']['placements']]
 math=composition['inline_math_replay']['atoms']
 report=audit_scan_page(SOURCE,number,target,target.with_suffix('.pre-prose.pdf'),prose,
  language_erase_rects=[rect for row in layout['rows']for rect in row['erase_rects']],
  new_prose_rects=[[r['left']-1,r['baseline']-r['size']*1.3,r['right']+1,r['baseline']+r['size']*.4]for r in composition['body_placements']],
  original_inline_math_rects=[atom['rect']for row in layout['rows']for atom in row['atoms']],
  moved_inline_math_rects=[r['destination_rect']for r in math],
  protected_source_rects=layout.get('protected_source_display_and_figure_rects',[]),native_header_change_rects=header_rects,
  replayed_math_records=math,reviewed_blank_records=[r for r in layout.get('reviewed_blank_background_rects',[])if lang in r.get('languages',['ko','en'])])
 target.with_suffix('.generic-scan-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
 print('generic',number,lang,report['passed'],flush=True);return report
