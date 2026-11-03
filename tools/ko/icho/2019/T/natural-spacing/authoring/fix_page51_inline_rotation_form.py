from pathlib import Path
import json
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;p=B/'page51.overrides.json';q=json.loads(p.read_text('utf8'));ed=q.setdefault('__slot_edits__',{});sc=q['__layout_scope__']
ed.setdefault('p51:b4:l0:s0-0:c0-4',{})['source_word_right_aligned_label']=True
sc['inline_native_form_atoms']=[dict(id='p51-inline-rotation-icon',source_sha256=g.SOURCE_SHA,source_form_path=[511],source_raw_sha256='7cabc031619a8c9d7592fe26dfb8571adf55e088c46df7768dd055797c0b786d',source_rect=[155.46,238.3593033943363,176.36060587008,256.6099829101563],source_line=[8,1],source_baseline=256.5799560546875,semantic_label='[rotation icon]',review='Original glyphless vector Form is a mathematical rotation notation inline between prose fields. Pack the complete original Form as one native atom with ordinary word gaps; move only its original invocation horizontally. Raw stream, vector coordinates within the Form, colour, physical size/y and original drawing remain exact. It is never erased, redrawn or treated as blank English width.')]
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
