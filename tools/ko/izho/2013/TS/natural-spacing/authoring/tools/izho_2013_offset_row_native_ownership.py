from pdf_original_text_ops import glyph_key
def filter_wrong_row(items,rect,rules,reports,kind):
 result=[]
 for item in items:
  keys={glyph_key(g)for g in item['glyphs']if g['c'].strip()};drop=False
  for rule in rules:
   if list(rect)!=rule['nonowning_source_row_rect']:continue
   owned={glyph_key(g)for g in rule['original_native_glyphs']if g['c'].strip()}
   if not(keys&owned):continue
   if not keys<=owned or item.get('native_image_paths'):raise ValueError('Source row ownership must identify a complete exact native expression, never a partial mathematical group')
   reports.append(dict(kind=kind,nonowning_source_row_rect=list(rect),original_owner_baseline=rule['original_owner_baseline'],complete_original_native_glyphs=rule['original_native_glyphs'],physical_glyphs=len(keys),reason=rule['reason']));drop=True
  if not drop:result.append(item)
 return result
def verify_native_owner_moves(qa,rules):
 result=[]
 for rule in rules:
  expected={glyph_key(g)for g in rule['original_native_glyphs']if g['c'].strip()};moves={}
  for shift in qa['native_shifts']:
   for g in shift['glyphs']:
    key=glyph_key(g)
    if key in expected:moves.setdefault(key,[]).append(shift['dx'])
  if set(moves)!=expected or any(len(v)!=1 for v in moves.values()):raise ValueError('Every original native row-owned glyph must still be painted and moved exactly once by its original owning row')
  values=[v[0]for v in moves.values()]
  if max(values)-min(values)>.001:raise ValueError('The original complete row-owned expression has split horizontal motion')
  result.append(dict(original_owner_baseline=rule['original_owner_baseline'],physical_native_glyphs=len(expected),each_original_native_glyph_moved_exactly_once=True,one_common_dx=values[0],reason=rule['reason']))
 return result
