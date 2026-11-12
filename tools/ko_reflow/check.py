# -*- coding: utf-8 -*-
"""Layout check for a tools/ko_reflow source: lays the pages out in headless Chrome and reports every pair of
absolutely placed blocks whose ink overlaps, and every block that runs past its page. Optionally writes
side-by-side PNGs (original | Korean) of a built PDF for visual review.

usage: python -I check.py SRC.html ORIGINAL.pdf [BUILT.pdf PNGDIR]
"""
import json, os, pathlib, re, subprocess, sys, tempfile, shutil
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build, pymupdf
sys.stdout.reconfigure(encoding="utf-8")

JS = r"""<script>
(function(){
 var out=[], k=0.75;
 document.querySelectorAll('.page').forEach(function(pg,pi){
  var P=pg.getBoundingClientRect(), boxes=[];
  Array.prototype.forEach.call(pg.children,function(el){
   var cs=getComputedStyle(el); if(cs.position!=='absolute') return;
   var rs=[];
   var r=document.createRange(); r.selectNodeContents(el);
   Array.prototype.forEach.call(r.getClientRects(),function(c){ if(c.width>0.5&&c.height>0.5) rs.push(c); });
   if(!rs.length){ var b=el.getBoundingClientRect(); if(b.width>0) rs=[b]; }
   if(!rs.length) return;
   var x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
   rs.forEach(function(c){x0=Math.min(x0,c.left);y0=Math.min(y0,c.top);x1=Math.max(x1,c.right);y1=Math.max(y1,c.bottom);});
   var label=(el.textContent||'').trim().slice(0,40)||el.className;
   boxes.push({x0:(x0-P.left)*k,y0:(y0-P.top)*k,x1:(x1-P.left)*k,y1:(y1-P.top)*k,rs:rs.map(function(c){return [(c.left-P.left)*k,(c.top-P.top)*k,(c.right-P.left)*k,(c.bottom-P.top)*k];}),t:label});
  });
  boxes.forEach(function(a,i){
   if(a.y1>P.height*k-8||a.x1>P.width*k-8) out.push({page:pi+1,kind:'off-page',a:a.t,box:[a.x0,a.y0,a.x1,a.y1].map(Math.round)});
   for(var j=i+1;j<boxes.length;j++){ var b=boxes[j], hit=0;
    a.rs.forEach(function(p){ b.rs.forEach(function(q){
      var w=Math.min(p[2],q[2])-Math.max(p[0],q[0]), h=Math.min(p[3],q[3])-Math.max(p[1],q[1]);
      if(w>1.5&&h>2.5) hit=Math.max(hit,h); }); });
    if(hit) out.push({page:pi+1,kind:'overlap',dy:Math.round(hit*10)/10,a:a.t,b:b.t});
   }
  });
 });
 var pre=document.createElement('pre'); pre.id='qa'; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>"""


def run(src, orig):
    html, od, figs = build.prepare(src, orig)
    html = html.replace('</body>', JS + '</body>', 1)
    tmp = pathlib.Path(tempfile.mkdtemp(dir=build.KIT / "tmp" if (build.KIT / "tmp").exists() else None))
    hp = tmp / 'page.html'
    hp.write_text(html, encoding='utf-8')
    try:
        r = subprocess.run([build.CHROME, '--headless=new', '--disable-gpu', '--allow-file-access-from-files',
                            '--virtual-time-budget=8000', '--no-first-run', '--disable-extensions',
                            f'--user-data-dir={tmp / "profile"}', '--dump-dom', hp.as_uri()],
                           capture_output=True, timeout=180, env=dict(os.environ, TEMP=str(tmp), TMP=str(tmp)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    dom = r.stdout.decode('utf-8', 'replace')
    m = re.search(r'<pre id="qa">(.*?)</pre>', dom, re.S)
    if not m:
        sys.exit('no QA output (KaTeX error?)\n' + r.stderr.decode('utf-8', 'replace')[-2000:])
    issues = json.loads(m.group(1).replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"'))
    for i in issues:
        print(json.dumps(i, ensure_ascii=False))
    print(f'{len(issues)} layout issues')
    return issues


def sidebyside(orig, built, outdir, dpi=55):
    a, b = pymupdf.open(orig), pymupdf.open(built)
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for i in range(len(b)):
        pa = a[i].get_pixmap(dpi=dpi) if i < len(a) else None
        pb = b[i].get_pixmap(dpi=dpi)
        w = (pa.width if pa else 0) + pb.width + 6
        h = max(pa.height if pa else 0, pb.height)
        pm = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, w, h), False)
        pm.clear_with(128)
        if pa:
            pa = pymupdf.Pixmap(pymupdf.csRGB, pa) if pa.n != 3 or pa.alpha else pa
            pm.copy(pa, pa.irect)
        pb = pymupdf.Pixmap(pymupdf.csRGB, pb) if pb.n != 3 or pb.alpha else pb
        pb.set_origin((pa.width if pa else 0) + 6, 0)
        pm.copy(pb, pb.irect)
        pm.save(str(outdir / f'p{i + 1:02d}.png'))
    print('wrote', len(b), 'side-by-side pages to', outdir)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 4:
        sidebyside(sys.argv[2], sys.argv[3], sys.argv[4])
