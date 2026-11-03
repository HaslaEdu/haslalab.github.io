from pathlib import Path
import json,hashlib
import pymupdf as f
import icho2019_write_guard as guard
doc=f.open(guard.SOURCE);out=[]
for name in ['Arial','Arial,Bold','Times New Roman','TimesNewRoman','Calibri','Helvetica','helv','Times-Roman','tiro']:
    try:
        font=f.Font(fontname=name)
        out.append(dict(requested=name,resolved_name=font.name,buffer_bytes=len(font.buffer),buffer_sha256=hashlib.sha256(font.buffer).hexdigest(),glyphs={ch:font.has_glyph(ord(ch))for ch in'IChO0123ABCDEabc.'}))
    except Exception as e:out.append(dict(requested=name,error=str(e)))
traces=[dict(font=t['font'],size=t['size'],chars=[dict(c=chr(cp),gid=gid)for cp,gid,origin,bbox in t['chars']])for t in doc[0].get_texttrace()]
embedded=[]
for xref,*_ in doc[0].get_fonts():
    name,ext,kind,data=doc.extract_font(xref)
    embedded.append(dict(xref=xref,name=name,extension=ext,font_type=kind,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()if data else None))
result=dict(probes=out,source_traces=traces,source_font_programs=embedded)
(Path(__file__).parent/'unembedded-font-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(dict(probes=out,source_font_programs=embedded,unembedded_trace_examples=[t for t in traces if t['font']in['Arial','TimesNewRomanPSMT']][:4]),ensure_ascii=False),flush=True)
