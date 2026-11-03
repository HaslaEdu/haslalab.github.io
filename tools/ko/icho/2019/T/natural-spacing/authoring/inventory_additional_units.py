from pathlib import Path
import hashlib,json,re
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;pattern=re.compile(r'(?<![A-Za-z])(?:mL|kPa|kHz|mW|kW|μL|µL|µM|μM)(?![A-Za-z])');rows=[]
for n in range(1,61):
    plan=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'));p=B/f'page{n:02}.overrides.json';over=json.loads(p.read_text('utf8'))
    for original in plan['slots']+over.get('__extra_slots__',[]):
        s=dict(original,**over.get('__slot_edits__',{}).get(original['id'],{}))
        if s.get('skip'):continue
        found=list(pattern.finditer(s['source']))
        if not found:continue
        target=over.get(s['id'],s.get('text',''));source_units=[m.group()for m in found];target_units=[m.group()for m in pattern.finditer(target)]
        rows.append(dict(page=n,slot_id=s['id'],source=s['source'],text=target,source_units=source_units,target_units=target_units,same_order=source_units==target_units,override_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(B/'additional-unit-literals-inventory.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,rows=rows),ensure_ascii=False,indent=2)+'\n','utf8')
for r in rows:print(json.dumps(r,ensure_ascii=False),flush=True)
