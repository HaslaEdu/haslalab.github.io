"""Item labels and points of every experiment in exam mode, for the printed Answer sheets (sim/sheets.html).

    python3 -I tools/labsheets.py GROUPS.json TEXTDIR > sim/labsheets.json

GROUPS.json: [{key, y, task, en, ...}] — the experiments of exam mode and their problem PDFs (read from DATA in
index.html).  TEXTDIR holds `<pdf name>.txt`: `pdftotext -layout` page by page, each page after a line «@@PAGE n».
A task's items are the lines that start with a label (A.1, A-1, B2, 1.3, Task E1.2 …) and end with its points
(0.4 pt, (1.0 pts), 2 marks, 0.5점).  The list is kept only when it looks like the marking table of the problem:
at least three items whose points add up to (at least 70 % of) the problem's total, or to 10 or 20 where the
problem states none.  Spare boxes with a blank label follow on the sheet in any case.
"""
import json, re, sys

LABEL = r"(?:Task\s+|문항\s*)?((?:[A-Z]{1,2}\d{0,2}[.\-]\d{1,2}(?:\.\d)?[a-z]?)|(?:[A-Z]\d{1,2}[a-z]?)|(?:\d{1,2}\.\d{1,2}(?:\.\d)?[a-z]?)|(?:\d{1,2}[a-z]))"
PTS = r"\(?\s*(\d{1,2}(?:\.\d{1,2})?)\s*(?:pt|pts|points?|marks?|점)\s*\)?\.?"
ITEM = re.compile(r"^\s*" + LABEL + r"(?=[\s:)\-]).{0,160}?\s" + PTS + r"\s*$")
TOTAL = re.compile(r"[\(\[]\s*(\d{1,2}(?:\.\d)?)\s*(?:pt|pts|points?|marks?|점)\s*[\)\]]")


LAB_LINE = re.compile(r"^\s*" + LABEL + r"(?:\s{2,}|\s*$|\s+(?=[A-Z\u0080-\uffff(]))")
PTS_END = re.compile(r"\s" + PTS + r"\s*$")


def items_of(text, task):
    """labels in reading order with their points; the points may sit a few lines above or below the label
    (a label beside a figure, the points at the end of a wrapped line)"""
    lines = text.splitlines()
    labs = [(i, m.group(1).replace("-", ".")) for i, l in enumerate(lines) for m in [LAB_LINE.match(l)] if m]
    pts = {i: float(m.group(1)) for i, l in enumerate(lines) for m in [PTS_END.search(l)] if m}
    used, out, seen = set(), [], set()
    for i, lab in labs:
        if lab in seen or lab.upper() == task.upper():
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


def total_of(text):
    for line in text.splitlines()[:80]:
        m = TOTAL.search(line)
        if m and 5 <= float(m.group(1)) <= 20:
            return float(m.group(1))
    return None


def main():
    groups, tdir = json.load(open(sys.argv[1])), sys.argv[2]
    res, report = {}, []
    for g in groups:
        name = (g.get("en") or "").split("/")[-1]
        try:
            text = open(f"{tdir}/{name}.txt", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        its, tot = items_of(text, g["task"]), total_of(text)
        s = round(sum(p for _, p in its), 2)
        shared = sum(1 for x in groups if x.get("en") == g.get("en")) > 1      # one PDF for several problems: the labels repeat
        ok = not shared and len(its) >= 3 and (0.7 * tot <= s <= 1.051 * tot if tot else any(abs(s - t) <= 0.05 * t for t in (10, 20)))
        report.append(f"{'OK ' if ok else '-- '}{g['key']}{g['y']} {g['task']:4} n={len(its):2} sum={s:5} total={tot} {name}")
        if ok:
            res.setdefault(f"{g['key']}{g['y']}", {})[g["task"]] = {"items": its, "points": s, **({"total": tot} if tot else {})}
    print(json.dumps(res, ensure_ascii=False, separators=(",", ":")))
    print("\n".join(report), file=sys.stderr)


if __name__ == "__main__":
    main()
