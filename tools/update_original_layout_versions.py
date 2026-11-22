"""Keep revised archive download URLs distinct in browser PDF caches."""
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'index.html';text=path.read_text(encoding='utf8')
existing=re.search(r'const ORIGINAL_LAYOUT_PDF_VERSIONS=(\{[^\n]+\});',text)
versions=json.loads(existing[1]) if existing else {}
items=json.loads((ROOT/'tools/original_style_publication.json').read_text(encoding='utf8'))
versions.update({name:item['sha256'][:16]for item in items for name in[item['file'],*item.get('aliases',[])]})
block='/* ORIGINAL_LAYOUT_PDF_VERSIONS */\nconst ORIGINAL_LAYOUT_PDF_VERSIONS='+json.dumps(dict(sorted(versions.items())),separators=(',',':'))+';\n/* END_ORIGINAL_LAYOUT_PDF_VERSIONS */'
if '/* ORIGINAL_LAYOUT_PDF_VERSIONS */'in text:
    text=re.sub(r'/\* ORIGINAL_LAYOUT_PDF_VERSIONS \*/[\s\S]*?/\* END_ORIGINAL_LAYOUT_PDF_VERSIONS \*/',lambda _:block,text,count=1)
else:
    marker='const thyUrl='
    assert text.count(marker)==1
    text=text.replace(marker,block+'\n'+marker,1)
start=text.index('const thyUrl=');end=text.index('/* Competition or organiser websites',start)
text=text[:start]+'''const thyUrl=f=>{
  const url=/^https?:/.test(f)?f:/^pdfx\\//.test(f)?PDF_BASE+f.replace(/^pdfx\\/(?:([a-z]+)\\/)?/,(m,d)=>"l/"+(d?d+"/":"")):PDF_BASE+f;   /* pdfx/: tools/pdfx_release.py */
  const key=(f.startsWith(PDF_BASE)?f.slice(PDF_BASE.length):f).split(/[?#]/)[0];
  const version=ORIGINAL_LAYOUT_PDF_VERSIONS[key]||(window.KPHE_PDF_VERSIONS||{})[f];
  if(!version) return url;
  const hash=url.indexOf("#"), base=hash<0?url:url.slice(0,hash);
  return base+(base.includes("?")?"&":"?")+"v="+encodeURIComponent(version)+"&cv="+PDF_LINK_CACHE_REVISION+(hash<0?"":url.slice(hash));
};   /* a release name, a site file, or a paper only linked */
'''+text[end:]
path.write_text(text,encoding='utf8')
print('Versioned original-layout archive downloads:',len(versions))
