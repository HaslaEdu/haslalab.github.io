"""Source candidates only. Every translation/expression needs source review."""
from pathlib import Path
import json,re,statistics
B=Path(__file__).resolve().parents[1];O=B/'inspection';A=B/'authoring'
HAN=re.compile('[\u3400-\u9fff]');PUNCT='，。；、：（）？！“”‘’．'
FACES={'ËÎÌå+FPEF':'SimSun','ºÚÌå+FPEF':'SimHei'}
NATIVE_FIGURES={1:[[363,308,494,359]],3:[[384,492,476,567],[375,750,493,802]]}
# Source2008-only, full-page/context-read mathematical lists. These are
# original CJK comma CIDs, not permission to redraw ASCII punctuation.
KEEP_COMMAS={1:[131],2:[50,141,227],4:[235],5:[60,63,591],7:[193,676],8:[589,733,737,819,822,874,877,913],9:[125,206,689,901,904,940,944,1062,1065,1068],10:[8,11,14],11:[144],12:[195,252],13:[809],14:[66],15:[464],16:[13,257,474],17:[187],18:[407],19:[190]}
MATH_PARENS={2:[[78,79,80]],5:[[588,589,591,592,593]]}
def contains(r,g):return r[0]-.01<=g['origin'][0]<=r[2]+.01 and r[1]-.01<=g['origin'][1]<=r[3]+.01
for n in range(1,22):
 inv=json.loads((O/f'page{n:02}-original-native-programs.json').read_text('utf8'));gs=inv['actual_original_glyphs'];ex=NATIVE_FIGURES.get(n,[])+[i['bbox']for i in inv['images']]
 chars=[dict(g,source_trace_index=i)for i,g in enumerate(gs)if g['c'].strip()and not any(contains(r,g)for r in ex)]
 hans=[g for g in chars if HAN.search(g['c'])];ys=[]
 for g in sorted(hans,key=lambda g:g['origin'][1]):
  y=g['origin'][1]
  if not ys or y-ys[-1][-1]>1.05:ys.append([y])
  else:ys[-1].append(y)
 # Parentheses belonging to actual original numbered/Roman subparts stay
 # native with their digits/letters; proximity to Chinese is not ownership.
 counter_indices=set();counter_groups={};paren_groups={};keep_comma=set(KEEP_COMMAS.get(n,[]))
 for j,indices in enumerate(MATH_PARENS.get(n,[])):
  assert all(gs[i]['c']not in'，。；、：？！“”‘’．'or gs[i]['c']=='，'for i in indices)
  for i in indices:paren_groups[i]=j
 for y in sorted({round(g['origin'][1],2)for g in chars}):
  cc=sorted([g for g in chars if abs(g['origin'][1]-y)<.05],key=lambda g:g['origin'][0]);text=''.join(g['c']for g in cc)
  for match in re.finditer(r'[（(][IVXivx0-9]+[）)]',text):
   groupid=tuple(g['source_trace_index']for g in cc[match.start():match.end()]);counter_indices.update(groupid)
   for i in groupid:counter_groups[i]=groupid
 rows=[];used=set()
 for ri,yvalues in enumerate(ys):
  y=statistics.median(yvalues);owned=[g for g in hans if abs(g['origin'][1]-y)<1.05];assert owned
  faces={FACES[g['font']]for g in owned};sizes={g['size']for g in owned};assert len(faces)==len(sizes)==1,(n,ri,faces,sizes);size=owned[0]['size'];face=next(iter(faces))
  language=list(owned)
  for c in chars:
   if c['source_trace_index']in counter_indices or c['source_trace_index']in keep_comma or c['source_trace_index']in paren_groups or c['c']not in PUNCT or c['font']not in FACES or abs(c['origin'][1]-y)>1.05:continue
   # Only nearby actual Chinese prose owns punctuation. A display's distant
   # comma/full stop or a mathematical list remains the original native CID.
   if any(min(abs(c['origin'][0]-g['bbox'][2]),abs(g['origin'][0]-c['bbox'][2]))<size*.6 for g in owned):language.append(c)
  language.sort(key=lambda c:c['origin'][0]);keys={g['source_trace_index']for g in language};used|=keys
  # Original native fraction/script levels attach only to a nearby prose
  # baseline. Display equations farther away stay native and stationary.
  native=[]
  for g in chars:
   if g['source_trace_index']in keys or HAN.search(g['c']):continue
   nearest=min(range(len(ys)),key=lambda i:abs(statistics.median(ys[i])-g['origin'][1]))
   if nearest!=ri or abs(g['origin'][1]-y)>10.4:continue
   if g['origin'][0]<85 or g['origin'][0]>510:continue
   # Detached right display equation counters are protected, stationary.
   if g['origin'][0]>395 and max(c['bbox'][2]for c in language)<300 and abs(g['origin'][1]-y)>3:continue
   native.append(g)
  allchars=sorted(language+native,key=lambda c:(c['origin'][0],c['origin'][1]));atoms=[];current=[]
  last_special=None
  for g in allchars:
   idx=g['source_trace_index'];special=('paren',paren_groups[idx])if idx in paren_groups else('counter',counter_groups[idx])if idx in counter_groups else None
   if g['source_trace_index']in keys:
    if current:atoms.append(current);current=[]
    last_special=None
   else:
    if current and (special!=last_special and(special is not None or last_special is not None)):atoms.append(current);current=[]
    if g['c']in'，；。．'and idx not in keep_comma and special is None:
     if current:atoms.append(current);current=[]
     atoms.append([g]);last_special=None
    else:current.append(g);last_special=special
  if current:atoms.append(current)
  aa=[]
  for ai,part in enumerate(atoms):
   r=[min(g['bbox'][0]for g in part),min(g['bbox'][1]for g in part),max(g['bbox'][2]for g in part),max(g['bbox'][3]for g in part)]
   paths=[v for v in inv['vector_paths']if v['rect'][0]>=r[0]-.5 and v['rect'][2]<=r[2]+.5 and v['rect'][1]>=r[1]-3 and v['rect'][3]<=r[3]+3 and v['rect'][3]-v['rect'][1]<max(14,size*1.3)]
   aa.append(dict(id=f'r{ri:02}a{ai}',source_text=''.join(g['c']for g in part),glyphs=part,rect=r,proposed_vector_paths=paths,reviewed=False))
  # A readable source string places each complete native candidate once.
  elements=[(g['origin'][0],g['origin'][1],g['c'])for g in language]
  elements +=[(a['rect'][0],y,f'[[{i}]]')for i,a in enumerate(aa)];elements.sort()
  left=min(g['origin'][0]for g in allchars);right=max(g['bbox'][2]for g in allchars)
  rows.append(dict(id=f'r{ri:02}',source_baselines=sorted(set(yvalues)),baseline=y,size=size,source_prose_face=face,source_prose_font=owned[0]['font'],source_prose_color=owned[0]['color'],source_text=''.join(v[2]for v in elements),original_source_glyphs=allchars,erase_glyphs=language,native_atoms=aa,left=left,source_right=right,original_center=(left+right)/2,source_language_rect=[min(g['bbox'][0]for g in language),min(g['bbox'][1]for g in language),max(g['bbox'][2]for g in language),max(g['bbox'][3]for g in language)],reviewed=False))
 assert used=={g['source_trace_index']for g in hans}|{g['source_trace_index']for r in rows for g in r['erase_glyphs']},'All visible native Chinese must be represented'
 q=dict(source_sha256='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d',source_page=n,source_only_proposal=True,excluded_source_figure_rects=ex,source_read_original_CJK_math_list_comma_trace_indices=KEEP_COMMAS.get(n,[]),source_read_complete_original_CJK_math_parenthesis_trace_groups=MATH_PARENS.get(n,[]),rows=rows)
 (A/f'page{n:02}-native-row-proposals.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 lines=['PAGE '+str(n)]+[f"{r['id']} y={r['baseline']:.3f} pt={r['size']:.8f} {r['source_prose_face']} | {r['source_text']} | "+'; '.join(f"{i}:{a['source_text']} ({len(a['proposed_vector_paths'])}paths)"for i,a in enumerate(r['native_atoms']))for r in rows]
 (A/f'page{n:02}-source-row-transcript.txt').write_text('\n'.join(lines)+'\n','utf8');print(n,len(rows),sum(len(r['native_atoms'])for r in rows),flush=True)
