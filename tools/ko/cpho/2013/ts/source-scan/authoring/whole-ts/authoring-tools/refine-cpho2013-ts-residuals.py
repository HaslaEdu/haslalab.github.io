"""Document-only source ink classifications and three reviewed crop repairs."""
from pathlib import Path
import json,hashlib,shutil
import pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
REVIEW=B/'residual-contact-review';W=REVIEW/'witness-pdfs';W.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
records=json.loads((REVIEW/'components.json').read_text('utf8'))
for number in [12,13]:
 P=B/f'authoring/page{number}-layout.json'
 before=REVIEW/f'page{number}-before-residual-revision.json'
 if not before.exists():shutil.copyfile(P,before)
 plan=json.loads(before.read_text('utf8'))
 selected=[];proofs=[]
 for record in records:
  if record['page']!=number:continue
  pdf=B/f"proofs/{record['language']}/page{number}.pdf";target=W/(record['proof_sha256']+'.pdf')
  if not target.exists():shutil.copyfile(pdf,target)
  if sha(target)!=record['proof_sha256']:raise ValueError('Original four-column contact proof witness changed')
  proofs.append(dict(language=record['language'],proof=str(target),sha256=sha(target),contact=record['contact'],contact_sha256=sha(record['contact'])))
  for i,c in enumerate(record['components']):
   # Other page13 components are CJK/punctuation crops, repaired below.
   if number==13 and not((record['language']=='ko'and i==4)or(record['language']=='en'and i==1)):continue
   selected.append((record,c))
 for i,(record,c)in enumerate(selected):
  rect=c['bbox'];key=(record['language'],tuple(rect))
  if any(fitz.Rect(rect).intersects(fitz.Rect(r))for r in plan.get('protected_source_display_and_figure_rects',[])):raise ValueError('Dust classification overlaps an independently protected source mathematical/figure rectangle')
  if any(fitz.Rect(rect).intersects(fitz.Rect(a['rect']))for row in plan['rows']for a in row['atoms']):raise ValueError('Dust classification overlaps an original mathematical atom')
  for lang in [record['language']]:
   comp=json.loads((B/f'proofs/{lang}/page{number}.composition.json').read_text('utf8'))
   if any(fitz.Rect(rect).intersects(fitz.Rect(a['destination_rect']))for a in comp['inline_math_replay']['atoms']):raise ValueError('Dust classification overlaps moved mathematical ink')
  item=dict(id=f'page{number}-source-blank-{i+1:02d}',languages=[record['language']],rect=rect,reviewed=True,source_sha256=plan['source_sha256'],reason='Scan dust in manually reviewed blank prose background; original paper/image pixels are retained, never erased or white-filled by this classification.',evidence=dict(review_contact=record['contact'],review_contact_sha256=sha(record['contact']),review_proof_sha256=record['proof_sha256'],review_proofs=proofs,collision_component_pixels=c['pixels'],actual_original_dust_ink_bbox_at4x=rect,review='Original/control/new-prose/final four-column crop shows isolated paper speck or the original dotted scan-background stripe, with no meaningful line, Chinese character, equation, variable, numeral or figure ink. Applicable-language source mathematical and figure rectangles and all original/destination mathematical atoms have zero geometric intersection. Language scope matters because the other edition can move a true mathematical atom into this formerly blank source coordinate.'))
  plan.setdefault('reviewed_blank_background_rects',[]).append(item)
 if number==13:
  for row in plan['rows']:
   if row['id']=='fringe-spacing':
    row['erase_rects'].append([133,126.5,136.75,132.25])
    row['prose_punctuation_review']='The stationary original comma after D lies outside the original mathematical atom ending132.75pt. Translate this prose punctuation with the surrounding sentence; explicitly erase comma133–136.75, leaving the entire mathematical source object unchanged.'
   if row['id']=='proper-time-a':
    for atom in row['atoms']:
     if atom['id']=='S-Zhang-proper':atom['rect'][3]=384
   if row['id']=='event1-definition-a':
    for atom in row['atoms']:atom['rect'][3]=443
  plan['residual_math_crop_review']='Original S-prime complete ink is above384pt; its former387.1pt bottom copied the next prose line Chinese 其. The event1 row complete numeral/Sprime/scripts are above443pt; former444.6pt copied the next line 学分别. Only empty/math-padding edges were narrowed; source mathematical scale/font/relative geometry remains unchanged.'
 plan['residual_review_contact_inventory']=str(REVIEW/'components.json')
 P.write_text(json.dumps(plan,ensure_ascii=False,indent=2),'utf8');print(number,'dust source classifications',len(selected),'protected/math rectangle intersections0')
