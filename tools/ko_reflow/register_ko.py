# -*- coding: utf-8 -*-
"""Record a Korean edition in tools/theory_ko.json, keeping the file's own layout (2-space indent, CRLF, years in order).

usage: python -I tools/ko_reflow/register_ko.py COMP YEAR PART SLOT FILE [TITLE]
  e.g. ipho 2014 T1 paper pdfx/ipho/IPhO_2014_T1_KO.pdf "세 개의 문제"
SLOT is paper, sol, answer or mark. Afterwards run tools/theory_build.py and tools/build-site-catalogue.cjs.
"""
import json, pathlib, sys

P = pathlib.Path(__file__).resolve().parents[1] / 'theory_ko.json'


def main(comp, year, part, slot, file, title=None):
    d = json.loads(P.read_bytes())
    years = d.setdefault(comp, {})
    if year not in years:
        years[year] = {}
        d[comp] = dict(sorted(years.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0))
    y = d[comp][year]
    e = y.setdefault(part, {})
    e[slot] = file
    if title:
        e['title'] = title
    y[part] = dict(sorted(e.items()))
    d[comp][year] = dict(sorted(y.items()))
    P.write_bytes((json.dumps(d, ensure_ascii=False, indent=2) + '\n').replace('\n', '\r\n').encode('utf-8'))


if __name__ == '__main__':
    main(*sys.argv[1:])
