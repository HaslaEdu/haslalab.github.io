#!/usr/bin/env python3
"""IYPT: the seventeen problems of every tournament, from iypt.org, into iypt.js (window.IYPT).

The IYPT has no exam paper and no official solution: each year's problems are open research questions, so the
site shows the statements and links the official problem sheet (the signed PDF where iypt.org has one, else the
year's page).  Hosts are from the IYPT timeline (iypt.org past tournaments, Wikipedia's table).

    python3 tools/iypt_build.py            # fetches iypt.org, writes iypt.js
    python3 tools/iypt_build.py --cache D  # keeps / reuses the pages in D
"""
import hashlib, html, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = "https://iypt.org/problems/"
# year: (city ko, city en, country ko, country en, flag)
HOSTS = {
 1988: ("모스크바", "Moscow", "소련", "USSR", "su"), 1989: ("모스크바", "Moscow", "소련", "USSR", "su"),
 1990: ("모스크바", "Moscow", "소련", "USSR", "su"), 1991: ("모스크바", "Moscow", "소련", "USSR", "su"),
 1992: ("프로트비노", "Protvino", "러시아", "Russia", "ru"), 1993: ("프로트비노", "Protvino", "러시아", "Russia", "ru"),
 1994: ("흐로닝언", "Groningen", "네덜란드", "Netherlands", "nl"), 1995: ("스파와", "Spała", "폴란드", "Poland", "pl"),
 1996: ("츠칼투보", "Tskaltubo", "조지아", "Georgia", "ge"), 1997: ("헤프", "Cheb", "체코", "Czech Republic", "cz"),
 1998: ("도나우에싱겐", "Donaueschingen", "독일", "Germany", "de"), 1999: ("빈", "Vienna", "오스트리아", "Austria", "at"),
 2000: ("부다페스트", "Budapest", "헝가리", "Hungary", "hu"), 2001: ("에스포", "Espoo", "핀란드", "Finland", "fi"),
 2002: ("오데사", "Odesa", "우크라이나", "Ukraine", "ua"), 2003: ("웁살라", "Uppsala", "스웨덴", "Sweden", "se"),
 2004: ("브리즈번", "Brisbane", "호주", "Australia", "au"), 2005: ("빈터투어", "Winterthur", "스위스", "Switzerland", "ch"),
 2006: ("브라티슬라바", "Bratislava", "슬로바키아", "Slovakia", "sk"), 2007: ("서울", "Seoul", "대한민국", "South Korea", "kr"),
 2008: ("트로기르", "Trogir", "크로아티아", "Croatia", "hr"), 2009: ("톈진", "Tianjin", "중국", "China", "cn"),
 2010: ("빈", "Vienna", "오스트리아", "Austria", "at"), 2011: ("테헤란", "Tehran", "이란", "Iran", "ir"),
 2012: ("바트자울가우", "Bad Saulgau", "독일", "Germany", "de"), 2013: ("타이베이", "Taipei", "대만", "Chinese Taipei", "tw"),
 2014: ("슈루즈베리", "Shrewsbury", "영국", "United Kingdom", "gb"), 2015: ("나콘랏차시마", "Nakhon Ratchasima", "태국", "Thailand", "th"),
 2016: ("예카테린부르크", "Yekaterinburg", "러시아", "Russia", "ru"), 2017: ("싱가포르", "Singapore", "싱가포르", "Singapore", "sg"),
 2018: ("베이징", "Beijing", "중국", "China", "cn"), 2019: ("바르샤바", "Warsaw", "폴란드", "Poland", "pl"),
 2021: ("쿠타이시", "Kutaisi", "조지아", "Georgia", "ge"), 2022: ("티미쇼아라", "Timișoara", "루마니아", "Romania", "ro"),
 2023: ("머리", "Murree", "파키스탄", "Pakistan", "pk"), 2024: ("부다페스트", "Budapest", "헝가리", "Hungary", "hu"),
 2025: ("룬드", "Lund", "스웨덴", "Sweden", "se"), 2026: ("취리히", "Zürich", "스위스", "Switzerland", "ch"),
 2027: ("오클랜드", "Auckland", "뉴질랜드", "New Zealand", "nz"),
}
NOT_HELD = {2020: ("COVID-19로 열리지 않음", "Not held (COVID-19)")}

def get(url, cache):
    name = cache and os.path.join(cache, re.sub(r"[^A-Za-z0-9]+", "_", url) + ".html")
    if name and os.path.exists(name):
        return open(name, encoding="utf-8").read()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (HaslaLab IYPT index)"})
    s = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    if name:
        open(name, "w", encoding="utf-8").write(s)
    return s

MOJI = re.compile("[\u00c2-\u00ef][\u0080-\u00bf\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc\u2013\u2014"
                  "\u2018-\u201e\u2020-\u2022\u2026\u2030\u2039\u203a\u20ac\u2122]{1,3}")

def unmangle(t):
    """older pages hold UTF-8 that was once read as cp1252 («â€œ», «Ï‰»), next to text that is fine: each such
    run is put back on its own, and left as it is when it does not make UTF-8"""
    def fix(m):
        try:
            return m.group(0).encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return m.group(0)
    t = t.replace("\u00e2\u20ac\u009d", "\u201d")                 # ” : its last byte (9D) has no cp1252 letter
    return MOJI.sub(fix, t).replace("\u00e2\u20ac", "\u201d")

def lines_of(page):
    m = re.search(r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*)', page, re.S)
    b = m.group(1) if m else page
    b = re.split(r"<footer|class=\"[^\"]*(?:sharedaddy|post-navigation|comments-area)", b)[0]
    b = re.sub(r"<(script|style)\b.*?</\1>", "", b, flags=re.S)
    b = re.sub(r"<br\s*/?>|</(p|h[1-6]|li|div|tr|blockquote)>", "\n", b, flags=re.I)
    b = re.sub(r"<(sup)>(.*?)</sup>", r"^\2", b, flags=re.S)
    b = re.sub(r"<(sub)>(.*?)</sub>", r"_\2", b, flags=re.S)
    b = re.sub(r"<[^>]+>", "", b)
    b = unmangle(html.unescape(b)).replace("\xa0", " ")
    return [re.sub(r"[ \t]+", " ", x).strip() for x in b.split("\n")]

def problems(page):
    """«n. Title» then its statement; «a—b. Title» opens a problem whose parts a … b follow as «n. part» —
    each part becomes problem n under that title, with the shared statement before its own"""
    out, cur, grp = [], None, None
    for ln in lines_of(page):
        if not ln:
            continue
        if re.match(r"^(what is iypt|sponsored by|current tournament)\b", ln, re.I):
            break
        if out and re.match(r"^((problems )?submitted by|authors?\b|problem selection|special thanks|figure:|pictures:|references$"
                            r"|pdf for printing|printer-friendly|several websites|the selection of problems)", ln, re.I):
            break                                                   # the credits under the last problem
        n = len(out) + 1
        r = re.match(r"^(\d{1,2})\s*[\u2013\u2014-]\s*(\d{1,2})\s*\.\s*(.+)$", ln)
        if r and int(r.group(1)) == n:
            grp = [int(r.group(1)), int(r.group(2)), r.group(3).strip(), []]
            cur = None
            continue
        h = re.match(r"^(\d{1,2})\s*[.)]\s*(.+)$", ln)
        if h and int(h.group(1)) == n and grp and grp[0] <= n <= grp[1]:
            cur = [f"{grp[2]} ({n - grp[0] + 1}/{grp[1] - grp[0] + 1})", grp[3] + [h.group(2).strip()]]
            out.append(cur)
            if n == grp[1]:
                grp = None
            continue
        if h and int(h.group(1)) == n and len(h.group(2)) <= 90:
            cur, grp = [h.group(2).strip(), []], None
            out.append(cur)
        elif grp and cur is None:
            grp[3].append(ln)
        elif cur is not None:
            cur[1].append(ln)
    res = []
    for title, body in out:
        title = re.sub(r"\s*:\s*$", "", title)
        if body and body[0].startswith(":"):                      # "Invent Yourself" | ": Paper Boomerang"
            title, body = title + ": " + body[0][1:].strip(), body[1:]
        res.append([title, "\n".join(body).strip()])
    return res

def main():
    cache = sys.argv[sys.argv.index("--cache") + 1] if "--cache" in sys.argv else None
    if cache:
        os.makedirs(cache, exist_ok=True)
    idx = get(INDEX, cache)
    urls = sorted(set(re.findall(r'href="(https://(?:www\.)?iypt\.org/(?:problems/)?[^"]*?(?:19|20)\d\d[^"]*/)"', idx)))
    years = {}
    for u in urls:
        if "problem" not in u:
            continue
        y = int(re.findall(r"(?:19|20)\d\d", u)[-1])
        page = get(u, cache)
        ps = problems(page)
        pdf = [p for p in re.findall(r'href="([^"]+\.pdf)"', page) if re.search(r"problem", p, re.I)]
        years[y] = {"y": y, "src": u, "pdf": pdf[0].replace("http://", "https://") if pdf else None, "p": ps}
        print(y, len(ps), "pdf" if pdf else "", file=sys.stderr)
    out = []
    for y in sorted(years, reverse=True):
        e = years[y]
        if y in HOSTS:
            ck, ce, nk, ne, cc = HOSTS[y]
            e["host"] = {"ko": f"{nk} · {ck}" if ck != nk else ck, "en": f"{ce}, {ne}" if ce != ne else ce}
            e["cc"] = cc
        elif y in NOT_HELD:
            e["host"] = {"ko": NOT_HELD[y][0], "en": NOT_HELD[y][1]}
        out.append(e)
    js = ("/* IYPT problems, from iypt.org (tools/iypt_build.py) — do not edit by hand */\n"
          "window.IYPT=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
    open(os.path.join(ROOT, "iypt.js"), "w", encoding="utf-8").write(js)
    # index.html asks for iypt.js by its content, so a new build is fetched at once, not after the browser's cache
    ih = os.path.join(ROOT, "index.html")
    page = open(ih, encoding="utf-8").read()
    open(ih, "w", encoding="utf-8").write(re.sub(r'src="iypt\.js(?:\?v=[0-9a-f]+)?"',
        'src="iypt.js?v=%s"' % hashlib.sha1(js.encode("utf-8")).hexdigest()[:10], page))
    print("iypt.js:", len(out), "years,", sum(len(e["p"]) for e in out), "problems,", len(js), "bytes", file=sys.stderr)

if __name__ == "__main__":
    main()
