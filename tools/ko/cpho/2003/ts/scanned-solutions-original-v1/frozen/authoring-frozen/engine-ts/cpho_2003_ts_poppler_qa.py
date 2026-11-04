"""Independent Poppler source/ink/single-original-math controls at144dpi."""
from pathlib import Path
import sys,json,subprocess,math,argparse
import numpy as np,pymupdf as fitz
from PIL import Image
from cpho_2003_ts_compose import BASE,SOURCE,sha
from cpho_2003_ts_qa import single_math_reference
from pdf_scanned_translation_ink_qa import include,summary
EXE=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
def render(path,prefix,page=1,crop=None):
 cmd=[str(EXE),'-f',str(page),'-singlefile','-r','144','-png']
 if crop:cmd +=['-x',str(crop[0]),'-y',str(crop[1]),'-W',str(crop[2]),'-H',str(crop[3])]
 p=subprocess.run([*cmd,str(path),str(prefix)],capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr)
 with Image.open(str(prefix)+'.png')as image:return np.array(image.convert('RGB'))
def audit(number,lang):
 target=BASE/f'proofs/{lang}/page{number:02}.pdf';composition=json.loads(target.with_suffix('.composition.json').read_text('utf8'));layout=json.loads((BASE/f'authoring/page{number:02}-layout.json').read_text('utf8'))
 if sha(target)!=composition['output_sha256']:raise ValueError('Pinned proof changed')
 out=target.parent/f'page{number:02}-poppler';out.mkdir(exist_ok=True)
 before=render(SOURCE,out/'original-source',number);actual=render(target,out/'final')
 control=render(target.with_suffix('.math-control.pdf'),out/'math-control');prose=render(target.with_suffix('.prose-only.pdf'),out/'prose-only')
 if not before.shape==actual.shape==control.shape==prose.shape:raise ValueError('Independent renderer page geometry differs')
 shape=before.shape[:2];allowed=np.zeros(shape,bool);language=np.zeros(shape,bool);original_inline=np.zeros(shape,bool);protected=np.zeros(shape,bool);native=np.zeros(shape,bool)
 for row in layout['rows']:
  for rect in row['erase_rects']:include(allowed,rect,2,1);include(language,rect,2,1)
  for atom in row['atoms']:include(allowed,atom['rect'],2,1);include(original_inline,atom['rect'],2,1)
 for row in composition['body_placements']:include(allowed,[row['left']-1,row['baseline']-row['size']*1.3,row['right']+1,row['baseline']+row['size']*.4],2,1)
 for atom in composition['inline_math_replay']['atoms']:include(allowed,atom['destination_rect'],2,1)
 slots=json.loads((BASE/'inputs/native-slots.json').read_text('utf8'))['pages'][number-1]['slots']
 headers=[c['bbox']for slot in slots for c in slot['source_characters']]+[[r['left']-1,r['baseline']-r['size']*1.4,r['right']+1,r['baseline']+r['size']*.4]for r in composition['header']['placements']]
 for rect in headers:include(allowed,rect,2,3);include(native,rect,2,3)
 for rect in layout['protected_source_display_and_figure_rects']:include(protected,rect,2)
 outside=np.any(before!=actual,axis=2)&~allowed
 stationary=np.any(before<160,axis=2)&np.all(actual>240,axis=2)&~language&~original_inline&~native
 protected_lost=np.any(before<160,axis=2)&np.all(actual>240,axis=2)&protected
 new=np.any(prose<180,axis=2);existing=np.any(control<180,axis=2);collision=existing&new;missing=new&np.all(actual>240,axis=2)
 blank=np.zeros(shape,bool)
 for record in layout.get('reviewed_blank_background_rects',[]):
  if record.get('reviewed')is not True or not record.get('evidence')or record.get('source_sha256')!=sha(SOURCE):raise ValueError('Original paper background needs reviewed source evidence and exact source hash')
  if record.get('source_crop')and sha(Path(record['source_crop']))!=record.get('source_crop_sha256'):raise ValueError('Reviewed source paper crop differs')
  include(blank,record['rect'],2)
 for rect in [*layout['protected_source_display_and_figure_rects'],*[a['rect']for row in layout['rows']for a in row['atoms']],*[a['destination_rect']for a in composition['inline_math_replay']['atoms']]]:
  mask=np.zeros(shape,bool);include(mask,rect,2);blank[mask]=False
 raw_collision=collision.copy();collision=collision&~blank
 records=[]
 for atom in composition['inline_math_replay']['atoms']:
  source=out/(atom['id']+'.original-single-math.pdf');source.write_bytes(single_math_reference(number,atom))
  x0,y0,x1,y1=atom['destination_rect'];x=math.floor(x0*2);y=math.floor(y0*2);w=math.ceil(x1*2)-x;h=math.ceil(y1*2)-y
  expected=render(source,out/(atom['id']+'.reference'),crop=[x,y,w,h]);observed=actual[y:y+h,x:x+w]
  if expected.shape!=observed.shape:raise ValueError('Independent native math crop geometry differs')
  deep=int(np.any(expected<150,axis=2).sum())
  if not deep:raise ValueError(('Independent Poppler native math control has no dark glyph ink',atom['id']))
  changed=np.any(expected!=observed,axis=2);records.append(dict(id=atom['id'],RGB_errors=int(changed.sum()),source_control_sha256=sha(source),expected_actual_dark_glyph_pixels=deep))
  if changed.any():
   witness=Image.new('RGB',(w*2+8,h),'white');witness.paste(Image.fromarray(expected),(0,0));witness.paste(Image.fromarray(observed),(w+8,0));witness.save(out/(atom['id']+'.math-diff.png'))
 fields=dict(outside_declared_language_and_math=summary(outside,2),stationary_source_ink_lost=summary(stationary,2),protected_source_display_or_figure_ink_lost=summary(protected_lost,2),new_prose_collision=summary(collision,2),new_prose_missing=summary(missing,2))
 report=dict(renderer='Poppler',dpi=144,proof=str(target),proof_sha256=sha(target),source_sha256=sha(SOURCE),source_page=number,language=lang,**fields,raw_collision_including_reviewed_scan_background=summary(raw_collision,2),reviewed_blank_background_records=layout.get('reviewed_blank_background_rects',[]),actual_single_source_math_controls=records,actual_math_RGB_errors=sum(r['RGB_errors']for r in records),passed=not any(v['pixels']for v in fields.values())and not any(r['RGB_errors']for r in records),publication_ready=False,full_edition_complete=False)
 target.with_suffix('.poppler-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
 print(lang,number,'POPLLER_PASS',report['passed'],{k:v['pixels']for k,v in fields.items()},'math_RGB_errors',report['actual_math_RGB_errors'],flush=True)
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('page',type=int);p.add_argument('language',choices=['ko','en']);a=p.parse_args();audit(a.page,a.language)
