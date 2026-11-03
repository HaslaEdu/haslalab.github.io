from pathlib import Path
import sys,json,hashlib,shutil,re
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');F=B/'natural/2013/TS';sys.path.insert(0,str(B/'engine'));from pdf_native_inline_reposition import _traces
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
engine=B/'engine/izho_natural_spacing_rebuild.py';text=engine.read_text('utf8');needle="            reading_order_reports.append(report);return lines\n";assert text.count(needle)==1
replacement="""            anchors=[]
            for rule in d.get('reviewed_offset_source_prose_row_start_positions',[]):
                if options['allowed_line_rects'][0]!=rule['selection_rect']:continue
                candidates=[line for line in lines if abs(line['baseline']-rule['original_baseline'])<.001]
                if len(candidates)!=1 or not rule.get('reason'):raise ValueError('Reviewed source offset-row start is not unique')
                first=candidates[0]['tokens'][0]
                if first['kind']!='korean' or first.get('text')!=rule['first_authored_prose_text'] or abs(first['x0']-rule['original_first_token_x'])>.001:raise ValueError('Reviewed source offset-row start no longer matches its exact initial prose')
                candidates[0]['tokens'][0]=dict(first,x0=rule['natural_start_x'])
                anchors.append(dict(rule,original_physical_prose_glyph_origins_unchanged=True,only_layout_cursor_start_changes=True))
            report['reviewed_offset_source_prose_row_start_positions']=anchors
            reading_order_reports.append(report);return lines
"""
saved=B/'engine/history'/sha(engine)[:16];saved.mkdir(parents=True,exist_ok=True);shutil.copy2(engine,saved/engine.name);engine.write_text(text.replace(needle,replacement),'utf8')
for n in[5,7,8,9]:
 path=F/f'plans/page{n:02}.json';d=json.loads(path.read_text('utf8'));saved=F/'history'/('plan-before-native-row-profile-'+sha(path)[:16]);saved.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved/path.name)
 if n==5:
  q=json.loads((F/'page05.qa.json').read_text('utf8'));a=next(r for r in q['lines']if abs(r['baseline']-640.8699951171875)<.001);b=next(r for r in q['lines']if abs(r['baseline']-643.8699951171875)<.001);assert sha(F/'page05.pdf')==q['output_sha256'];gap=3.
  d['reviewed_offset_source_prose_row_start_positions']=[dict(selection_rect=b['rect'],original_baseline=b['baseline'],first_authored_prose_text='이므로, 다음 식들로 구한다: ',original_first_token_x=266.3299865722656,natural_start_x=a['new_right']+gap,preceding_original_row_baseline=a['baseline'],independently_reviewed_preceding_row_final_right=a['new_right'],preceding_reviewed_proof_sha256=q['output_sha256'],natural_word_gap_pt=gap,reason='Full source page5 shows the trailing clause on the same visual sentence but with a source Word3pt baseline offset. Preserve both original y values and all original native condition/reference glyphs. Start the trailing translated clause one normal quarter-em after the already independently audited condition-row endpoint, removing the English-width horizontal hole. Selection rectangles remain disjoint, no font/point/Y change, no glyph omission and no collision/audit threshold changes.')]
 with f.open(d['original_english_source'])as original:rows=_traces(original[n-1])
 if n==7:
  refs=[r for r in d['reviewed_source_prose_native_reference_glyphs']if r['source_at']==[3,6,0]];assert {r['source_text']for r in refs}=={'N','S'}
  atoms=list(d.get('explicit_native_math_atoms',[]))
  for ref in refs:
   wanted=ref['source_glyphs'];glyphs=[g for g in rows if g['c'].strip()and any(g['c']==h['c']and g['font']==h['font']and abs(g['size']-h['size'])<.0001 and max(abs(a-b)for a,b in zip(g['origin'],h['origin']))<.0001 for h in wanted)];assert len(glyphs)==1
   box=f.Rect(glyphs[0]['bbox'])+(-.002,-.002,.002,.002)
   atoms.append(dict(rect=list(box),baseline=glyphs[0]['origin'][1],font_regex=re.escape(glyphs[0]['font']),source_native_glyphs=glyphs,original_source_only=True,reviewed=True,reason='Full source/final page7 table review: N and S are separate original prose references with Korean words between them. Treat each exact original glyph as its own native atom, preserving font/GID/point/Y and allowing independent horizontal packing. Never keep the erased English-phrase width between N and S, and never move the Korean conjunction after S. No glyph retyping or native guard changes.'))
  d['explicit_native_math_atoms']=atoms
 if n in[8,9]:
  rect=[104,603,232,642]if n==8 else[104,233,270,273];label='Original complete display equation(7)'if n==8 else'Original complete display equation(13)';box=f.Rect(rect);glyphs=[g for g in rows if g['c'].strip()and box.contains(f.Point(g['origin']))];assert len(glyphs)>=12,(n,glyphs)
  d['reviewed_stationary_expression_groups']=[dict(label=label,glyphs=glyphs,reviewed=True,original_source_rect=rect,reason='Complete original expression and surrounding paragraph visually read. Its small exponent belongs to its own native base inside this complete stationary display, rather than a nearby prose-reference/inline-variable glyph on the preceding line. Every native member remains included in strict font/GID/point/Y and common-dx auditing; no script exclusion or tolerance change.')]
 files=sorted(p for p in F.glob(f'page{n:02}*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];archive=F/'history'/f'preserved-before-native-row-review-{version}';archive.mkdir(parents=True,exist_ok=True)
 for item in files:
  target=archive/item.name;assert item.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(item);item.rename(target);assert sha(target)==digest
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE_NATIVE_ROW_OR_EXPRESSION_PROFILE_READY',n,flush=True)
assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
