"""Keep revised archive download URLs distinct in browser PDF caches."""
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[1]
items=json.loads((ROOT/'tools/original_style_publication.json').read_text(encoding='utf8'))
versions={name:item['sha256'][:16]for item in items for name in[item['file'],*item.get('aliases',[])]}
block='/* ORIGINAL_LAYOUT_PDF_VERSIONS */\nconst ORIGINAL_LAYOUT_PDF_VERSIONS='+json.dumps(dict(sorted(versions.items())),separators=(',',':'))+';\n/* END_ORIGINAL_LAYOUT_PDF_VERSIONS */'
path=ROOT/'index.html';text=path.read_text(encoding='utf8')
if '/* ORIGINAL_LAYOUT_PDF_VERSIONS */'in text:
    text=re.sub(r'/\* ORIGINAL_LAYOUT_PDF_VERSIONS \*/[\s\S]*?/\* END_ORIGINAL_LAYOUT_PDF_VERSIONS \*/',lambda _:block,text,count=1)
else:
    marker='const thyUrl='
    assert text.count(marker)==1
    text=text.replace(marker,block+'\n'+marker,1)
start=text.index('const thyUrl=');end=text.index('/* Competition or organiser websites',start)
text=text[:start]+'''const thyUrl=f=>{
  const url=/^(pdfx\\/|https?:)/.test(f)?f:PDF_BASE+f;
  const key=(f.startsWith(PDF_BASE)?f.slice(PDF_BASE.length):f).split(/[?#]/)[0];
  const version=ORIGINAL_LAYOUT_PDF_VERSIONS[key]||(window.KPHE_PDF_VERSIONS||{})[f];
  return version?url+(url.includes("?")?"&":"?")+"v="+encodeURIComponent(version):url;
};   /* a release name, a site file, or a paper only linked */
'''+text[end:]
path.write_text(text,encoding='utf8')
print('Versioned original-layout archive downloads:',len(versions))
