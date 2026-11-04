"""CPhO2008: replace only reviewed language CIDs, keep native mathematics.

Original encoded CIDs/fonts/GIDs/fractional Tf/Tm/clips/graphics stay native.
No paragraph fitting, source font rewriting, mathematical transcription,
bitmap equation substitution or source image normalization is used.
"""
from pathlib import Path
from io import BytesIO
import sys,json,re,hashlib,argparse
import pikepdf,pymupdf as f
from fontTools.ttLib import TTFont
from fontTools import subset
from pdf_native_inline_reposition import reposition_inline
from cpho2008_original_inline_prose_colors import parts as colored_parts
B=Path(__file__).resolve().parents[1];S=B/'source/CPhO_2008_original_combined_ZH.pdf';SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
FONTS=Path('C:/Users/andre/CodexWork/HaslaLab/haslalab/tools/ko/fonts')

def font_path(lang,face):
 if lang=='ko':return Path('C:/Windows/Fonts/batang.ttc')if face=='SimSun'else FONTS/'NotoSansCJKkr-Regular.otf'
 return Path('D:/CodexBuilds/Hasla-original-style-20261031/english-face-repair/font-faces/SimSun-5.24.ttf')if face=='SimSun'else Path('D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simhei.ttf')

def new_font(path,text):
 path=Path(path);C=B/'font-cache';C.mkdir(exist_ok=True);key=hashlib.sha256(path.read_bytes()+text.encode()+b'C08-original-role-retain-GID-v1').hexdigest()[:18];out=C/(path.stem+'-'+key+'.ttf')
 if not out.exists():
  font=TTFont(path,fontNumber=0,recalcTimestamp=False);missing=[c for c in set(text)if ord(c)not in font.getBestCmap()];assert not missing,(path,missing)
  options=subset.Options();options.retain_gids=True;options.name_IDs=['*'];options.name_languages=['*'];options.name_legacy=True
  worker=subset.Subsetter(options=options);worker.populate(text=text);worker.subset(font);font.save(out);font.close()
 raw=out.read_bytes();metric=f.Font(fontbuffer=raw)
 with TTFont(BytesIO(raw),recalcTimestamp=False)as font:
  cmap=font.getBestCmap();assert all(ord(c)in cmap and font['hmtx'][cmap[ord(c)]][0]>0 for c in set(text)if not c.isspace())
 return raw,metric,dict(actual_original_role_donor_path=str(path),actual_original_role_donor_sha256=sha(path),subset_path=str(out),subset_sha256=sha(out),original_role_preserved=True,actual_new_prose_glyphs_and_advances_verified=True)

def width(metric,text,point):return sum(point/4 if c==' 'else metric.text_length(c,fontsize=point)for c in text)

def write_words(page,x,y,text,metric,size,alias,color):
 for part in re.findall(r' +|[^ ]+',text):
  if part.isspace():x+=len(part)*size/4;continue
  # PDF integer W widths can quantize a 2048-upem Batang Latin advance by
  # .001em. Place each original-donor glyph at its true font advance; never
  # scale glyphs or add tracking. Word spaces remain exactly quarter-em.
  for char in part:
   page.insert_text((x,y),char,fontname=alias,fontsize=size,color=color,fill=color,render_mode=0)
   x+=metric.text_length(char,fontsize=size)

def prepare(n,lang):
 p=B/f'authoring/page{n:02}-native-language.json';q=json.loads(p.read_text('utf8'));assert q['source_sha256']==SHA and q['all_source_language_and_native_expressions_manually_reviewed']
 strings={}
 for row in q['rows']:
  face=row['source_prose_face'];strings[face]=strings.get(face,'')+re.sub(r'\[\[\d+\]\]','',row[lang])
 fonts={face:new_font(font_path(lang,face),text)for face,text in strings.items()};erased=[];shifts=[];prose=[];placements=[]
 for row in q['rows']:
  assert row['reviewed'];face=row['source_prose_face'];raw,metric,fontqa=fonts[face];point=row['size'];parts=[];seen=[]
  for text in re.split(r'(\[\[\d+\]\])',row[lang]):
   if not text:continue
   if text.startswith('[['):
    i=int(text[2:-2]);a=row['native_atoms'][i];assert a['reviewed'];parts.append(dict(kind='native',atom=a,width=a['rect'][2]-a['rect'][0]));seen.append(i)
   else:
    for segment,color in colored_parts(n,row,lang,text):
     if segment:parts.append(dict(kind='prose',text=segment,width=width(metric,segment,point),color=color))
  assert sorted(seen)==list(range(len(row['native_atoms']))),(n,row['id'],lang,seen)
  total=sum(p['width']for p in parts);left,right=row['allowed_horizontal'];x=row['original_center']-total/2 if row.get('align')=='center'else row['left']
  if x<left-.001 or x+total>right+.001:raise ValueError(('Original-point translated row overflow',n,lang,row['id'],x,x+total,[left,right],row[lang]))
  start=x;tokens=[];erased.extend(row['erase_glyphs'])
  for part in parts:
   if part['kind']=='native':
    a=part['atom'];dx=x-a['rect'][0];shifts.append(dict(glyphs=a['glyphs'],dx=dx,vector_paths=a['vector_paths']));tokens.append(dict(kind='native',id=a['id'],source_rect=a['rect'],destination_rect=[a['rect'][0]+dx,a['rect'][1],a['rect'][2]+dx,a['rect'][3]],dx=dx,original_glyphs=a['glyphs'],original_paths=a['vector_paths']))
   else:
    item=dict(text=part['text'],x=x,y=row['baseline'],size=point,face=face,color=part['color']);prose.append(item);tokens.append(dict(kind='prose',**item))
   x+=part['width']
  placements.append(dict(id=row['id'],source_text=row['source_text'],translated_text=row[lang],source_prose_face=face,source_prose_font=row['source_prose_font'],source_size=point,actual_size=point,source_baselines=row['source_baselines'],actual_baseline=row['baseline'],alignment=row.get('align','left'),original_horizontal_center=row['original_center'],actual_bounds=[start,x],word_gap=point/4,tokens=tokens,font=fontqa))
 # Each language's actual producer input is immutable and independent of
 # later edits to the other language's prose in the bilingual review plan.
 compiled={k:v for k,v in q.items()if k!='rows'};compiled['language']=lang;compiled['rows']=[{k:v for k,v in row.items()if k not in({'ko','en'}-{lang})}for row in q['rows']]
 data=(json.dumps(compiled,ensure_ascii=False,indent=2)+'\n').encode('utf8');directory=B/'authoring/compiled';directory.mkdir(exist_ok=True);compiled_path=directory/f'page{n:02}-{lang}-{hashlib.sha256(data).hexdigest()[:20]}.json'
 if compiled_path.exists():assert compiled_path.read_bytes()==data
 else:compiled_path.write_bytes(data)
 return dict(plan=compiled_path,fonts=fonts,erased=erased,shifts=shifts,prose=prose,placements=placements,reviewed_plan=compiled)

def build(n,lang):
 assert sha(S)==SHA;job=prepare(n,lang);out=B/'proofs'/lang;out.mkdir(parents=True,exist_ok=True);stem=out/f'page{n:02}'
 target=stem.with_suffix('.pdf');assert not target.exists(),'Archive a rejected proof with its SHA before rebuilding'
 raw,nativeqa=reposition_inline(S,n,erased_glyphs=job['erased'],shifts=job['shifts'],text_shift_mode='ctm')
 control=stem.with_suffix('.native-control.pdf');control.write_bytes(raw)
 with f.open(stream=raw,filetype='pdf')as doc:
  page=doc[0]
  for face,(font,metric,qa)in job['fonts'].items():page.insert_font(fontname='C08Translated'+face,fontbuffer=font)
  for p in job['prose']:write_words(page,p['x'],p['y'],p['text'],job['fonts'][p['face']][1],p['size'],'C08Translated'+p['face'],p['color'])
  doc.save(target,garbage=0,deflate=False)
 bitmap=None
 if job['reviewed_plan'].get('source_bitmap_language_policy_path'):
  from cpho2008_bitmap_language import apply as apply_bitmap
  assert n==4;body=target.with_suffix('.before-bitmap-language.pdf');assert not body.exists();target.rename(body);bitmap=apply_bitmap(job['reviewed_plan'],lang,body,target,new_font,write_words)
 # A native page group must never be silently omitted by any intermediate.
 with pikepdf.open(S)as a,pikepdf.open(control)as c,pikepdf.open(target)as d:
  assert ('/Group'in a.pages[n-1].obj)==('/Group'in c.pages[0].obj)==('/Group'in d.pages[0].obj)
 report=dict(source_path=str(S),source_sha256=SHA,source_page=n,language=lang,output_sha256=sha(target),actual_immutable_producing_plan=str(job['plan']),plan_sha256=sha(job['plan']),source_point_sizes_and_baselines_unchanged=True,source_Page_Group_presence_retained=True,all_mathematics_native_not_retyped=True,source_original_images_not_replaced=True,native_control_sha256=sha(control),native_motion=nativeqa,erased_original_language_glyphs=job['erased'],native_shifts=job['shifts'],placements=job['placements'],fonts={face:v[2]for face,v in job['fonts'].items()},publication_ready=False)
 if bitmap:report['source_bitmap_language_overlay']=bitmap
 target.with_suffix('.composition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('C08_PRIVATE_NATIVE_PROOF',n,lang,sha(target),flush=True);return target
if __name__=='__main__':
 sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools');from pdf_memory_gate import page_worker
 p=argparse.ArgumentParser();p.add_argument('page',type=int);p.add_argument('language',choices=['ko','en']);a=p.parse_args()
 with page_worker():build(a.page,a.language)
