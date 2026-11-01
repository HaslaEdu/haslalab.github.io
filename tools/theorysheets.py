"""Item labels and points of the theory problems without an official answer sheet, for HaslaLab's printed Answer
sheets (sim/sheets.html, theory mode).

    python3 -I tools/theorysheets.py LIST.json CACHE_DIR > sim/theorysheets.json

LIST.json: [{key, y, task, paper}] — the theory problems (from theory.js) whose olympiad published no answer sheet;
`paper` is a release name (served by the PDF Worker) or a site file (pdfx/…).  Each paper is downloaded into
CACHE_DIR once and read with `pdftotext -layout`.  A problem's items are kept only when they look like its whole
marking table: at least three labelled items whose points add up to the total printed in the paper (or 10 when it
prints none) within 2 %.  Everything else keeps HaslaLab's boxes with a blank label (the candidate writes it).
"""
import json, os, re, subprocess, sys

PDF_BASE = "https://haslalab-pdf.haslalab.workers.dev/pdf/"
SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# labels: A.1, A1, A-1, 1.1, 2.3a, 1a, Task 1.1 (not «Q1.1», the problem's own number)
LABEL = r"(?:Task\s+|Question\s+)?((?:[A-Z]\.?\d{1,2}(?:\.\d)?[a-z]?)|(?:\d{1,2}\.\d{1,2}(?:\.\d)?[a-z]?)|(?:\d{1,2}[a-z]))"
# points: (0.3 points), [0.2 point], 0.5pt, 1.7 pt., (1.5 pts), 2 marks, 0.5점
PTS = r"[\(\[]?\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:pt|pts|points?|marks?|점)\.?\s*[\)\]]?\.?"
LAB_LINE = re.compile(r"^\s*" + LABEL + r"(?=[\s:)\-]|$)")
PTS_END = re.compile(r"(?:^|\s)" + PTS + r"\s*$")
TOTAL = re.compile(r"[\(\[]\s*(\d{1,2}(?:\.\d)?)\s*(?:pt|pts|points?|marks?|점)\s*[\)\]]", re.I)


def items_of(text, task):
    lines = text.splitlines()
    labs = [(i, m.group(1).replace("-", ".")) for i, l in enumerate(lines) for m in [LAB_LINE.match(l)] if m]
    pts = {i: float(m.group(1).replace(",", ".")) for i, l in enumerate(lines) for m in [PTS_END.search(l)] if m}
    used, out, seen = set(), [], set()
    for i, lab in labs:
        if lab in seen or lab.upper() == task.upper() or re.fullmatch(r"\d{4}", lab):
            continue
        near = [j for j in sorted(pts, key=lambda j: (abs(j - i), j < i)) if abs(j - i) <= 4 and j not in used
                and not any(k != i and min(i, j) <= k <= max(i, j) for k, _ in labs)]
        if not near:
            continue
        j = near[0]
        if not 0 < pts[j] <= 10:
            continue
        used.add(j); seen.add(lab)
        out.append([lab, pts[j]])
    return out


LETTER = re.compile(r"(?:^|\s)([a-h])\)\s*\(\s*(\d{1,2}(?:\.\d{1,2})?)\s*pts?\s*\)", re.M)
HEADER = re.compile(r"(?:^|\n)\s*(?:T|Problem\s+|Theory\s+problem\s+)(\d)\s*[:.]", re.I)


def letter_items(plain, task):
    """EuPhO-style «a) (8 pts)» items, read in reading order; in a paper of several problems only those under the
    task's own header («T2:», «Problem 2.») count"""
    n = re.sub(r"\D", "", task)
    heads = [(m.start(), m.group(1)) for m in HEADER.finditer(plain)]
    if heads:
        own = [i for i, (_, k) in enumerate(heads) if k == n]
        if not own:
            return []
        i = own[0]
        plain = plain[heads[i][0]: heads[i + 1][0] if i + 1 < len(heads) else len(plain)]
    out, seen = [], set()
    for m in LETTER.finditer(plain):
        if m.group(1) in seen:
            break                      # the next problem's a) — the segment is over
        seen.add(m.group(1)); out.append([m.group(1), float(m.group(2))])
    return out


def total_of(text):
    """the problem's total: the largest «(N points)» near the top (the title's, not a part's)"""
    found = [float(m.group(1)) for line in text.splitlines()[:80] for m in [TOTAL.search(line)] if m and 5 <= float(m.group(1)) <= 20]
    return max(found) if found else None


def fetch(paper, cache):
    name = paper.split("/")[-1]
    path = os.path.join(cache, name)
    if not os.path.exists(path):
        if paper.startswith("pdfx/"):
            src = os.path.join(SITE, paper)
            data = open(src, "rb").read()
        else:
            data = subprocess.run(["curl", "-sSfL", "--max-time", "120", PDF_BASE + paper], check=True, capture_output=True).stdout
        open(path, "wb").write(data)
    txt, raw = path[:-4] + ".txt", path[:-4] + ".raw.txt"
    if not os.path.exists(txt):
        subprocess.run(["pdftotext", "-layout", path, txt], check=True, capture_output=True)
    if not os.path.exists(raw):
        subprocess.run(["pdftotext", path, raw], check=True, capture_output=True)
    return open(txt, encoding="utf-8", errors="replace").read(), open(raw, encoding="utf-8", errors="replace").read()


def main():
    groups, cache = json.load(open(sys.argv[1])), sys.argv[2]
    os.makedirs(cache, exist_ok=True)
    res, report = {}, []
    for g in groups:
        try:
            text, plain = fetch(g["paper"], cache)
        except Exception as e:  # a missing paper keeps HaslaLab's blank boxes
            report.append(f"!! {g['key']}{g['y']} {g['task']} {e}")
            continue
        its, tot = items_of(text, g["task"]), total_of(text)
        if not any(abs(round(sum(p for _, p in its), 2) - t) <= 0.02 * t for t in ({tot, 10.0} - {None})):
            alt = letter_items(plain, g["task"])
            if len(alt) >= 2 and abs(sum(p for _, p in alt) - 10.0) <= 0.2:
                its, tot = alt, 10.0
        s = round(sum(p for _, p in its), 2)
        # the whole marking table: the points add up to the printed total, or to the usual 10 when none is printed
        ok = len(its) >= (2 if its and its[0][0] == "a" else 3) and any(abs(s - t) <= 0.02 * t for t in ({tot, 10.0} - {None}))
        report.append(f"{'OK ' if ok else '-- '}{g['key']}{g['y']} {g['task']:4} n={len(its):2} sum={s:5} total={tot}")
        if ok:
            # the total the points matched: the printed one, else the usual 10 (a part's printed total is not kept)
            total = next(t for t in (tot, 10.0) if t and abs(s - t) <= 0.02 * t)
            res.setdefault(f"{g['key']}{g['y']}", {})[g["task"]] = {"items": its, "points": s, "total": total}
    print(json.dumps(res, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    print("\n".join(report), file=sys.stderr)


if __name__ == "__main__":
    main()
