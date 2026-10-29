#!/usr/bin/env python3
"""USACO: the Gold and Platinum problems of every contest since December 2016, from tools/usaco.json, into usaco.js.

USACO publishes its statements and analyses as pages on usaco.org, not as PDFs, so the site links them where they
are: window.USACO = [{y, c: [[contest, division, [[title, statement url, analysis url or ""], ...]], ...]}, ...].
tools/usaco.json is the list scraped from the contests' results pages (2026: from the problem pages, no analyses yet).

    python3 tools/usaco_build.py
"""
import hashlib, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    src = json.load(open(os.path.join(ROOT, "tools", "usaco.json"), encoding="utf-8"))
    out = []
    for y in sorted(src["years"], key=lambda y: -y["y"]):
        out.append({"y": y["y"], "c": [[c["name"], c["division"], [[p["title"], p["url"], p.get("sol", "")] for p in c["problems"]]]
                                       for c in y["contests"]]})
    js = ("/* USACO Gold and Platinum problems, linked on usaco.org (tools/usaco_build.py) — do not edit by hand */\n"
          "window.USACO=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
    open(os.path.join(ROOT, "usaco.js"), "w", encoding="utf-8").write(js)
    ih = os.path.join(ROOT, "index.html")
    page = open(ih, encoding="utf-8").read()
    open(ih, "w", encoding="utf-8").write(re.sub(r'src="usaco\.js(?:\?v=[0-9a-f]+)?"',
        'src="usaco.js?v=%s"' % hashlib.sha1(js.encode("utf-8")).hexdigest()[:10], page))
    print("usaco.js:", len(out), "years,", sum(len(p) for y in out for _, _, p in y["c"]), "problems,", len(js), "bytes")

if __name__ == "__main__":
    main()
