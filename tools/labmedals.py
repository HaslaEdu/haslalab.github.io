"""The experimental scores of past olympiads, for exam mode's «which medal would the experiment alone have earned».

    python3 -I tools/labmedals.py IPHO.json APHO_DIR > sim/labmedals.json

IPHO.json: per year {n, n_exp, awards: {award: count}, exp: [[score, award], ...]} from the per-contestant tables
of ipho-unofficial.org (timeline/<year>/individual).  APHO_DIR: apho_<year>.json {exp_max, complete, rows: [[award,
score], ...]} from the published APhO results.  Only years with experimental scores are kept, and only what the
estimate needs: the medal counts and the experimental scores, sorted, without names or countries.
`complete` is false when the published list holds the award winners only (the scores of the rest are unknown, so
a rank among them is a best case).
"""
import glob, json, re, sys

AW = {"Gold Medal": "g", "Silver Medal": "s", "Bronze Medal": "b", "Honourable Mention": "hm"}


def year(rows, mx, complete):
    cnt = {k: 0 for k in AW.values()}
    for aw, _ in rows:
        if aw in AW:
            cnt[AW[aw]] += 1
    exp = sorted((round(float(x), 2) for _, x in rows if x is not None), reverse=True)
    return {"max": mx, "complete": complete, "n": len(rows), **cnt, "exp": exp}


def main():
    out = {"ipho": {}, "apho": {}}
    for y, v in json.load(open(sys.argv[1])).items():
        if v.get("n_exp"):
            rows = [[aw, sc] for sc, aw in v["exp"]]
            out["ipho"][y] = year(rows, 20, "None" in v.get("awards", {}) and v["n_exp"] == v["n"])
    for f in sorted(glob.glob(sys.argv[2] + "/apho_*.json")):
        d = json.load(open(f))
        out["apho"][str(d["year"])] = year(d["rows"], d.get("exp_max") or 20, bool(d.get("complete")))
    print(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
