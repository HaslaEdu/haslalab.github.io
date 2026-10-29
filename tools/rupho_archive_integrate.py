#!/usr/bin/env python3
"""Apply only the RuPhO stage UI changes to index.html, preserving other edits.

Run after copying rupho-archive.js to a checkout. Safe to run again.
"""
from pathlib import Path
import argparse


def integrate(path):
    source = path.read_text(encoding='utf8')
    if 'const RUPHO_ARCHIVE=window.RUPHO_ARCHIVE;' in source:
        assert '<script src="rupho-archive.js"></script>' in source
        assert 'return ruphoPage(key,`' in source
        print('RuPhO stage UI already integrated:', path)
        return

    def once(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('Expected one integration point: ' + old[:100])
        source = source.replace(old, new)

    once('<script src="rupho-selection.js"></script>', '<script src="rupho-selection.js"></script>\n<script src="rupho-archive.js"></script>')
    once('const thyOf=(key,y)=>', '''/* Stage catalogues share one public competition; source paper keys stay unchanged. */
const RUPHO_ARCHIVE=window.RUPHO_ARCHIVE;
if(RUPHO_ARCHIVE) RUPHO_ARCHIVE.initialize(DATA,THEORY);
const compOf=key=>RUPHO_ARCHIVE?.catalogue(key)||DATA[key];
const ruphoPage=(key,html,year="")=>RUPHO_ARCHIVE?RUPHO_ARCHIVE.decorate(key,html,year,lang):html;
const thyOf=(key,y)=>''')
    source = source.replace('DATA[key]', 'compOf(key)')
    once('const compOf=key=>RUPHO_ARCHIVE?.catalogue(key)||compOf(key);', 'const compOf=key=>RUPHO_ARCHIVE?.catalogue(key)||DATA[key];')
    once('list.map(key=>[key,compOf(key)])', 'list.map(key=>[key,DATA[key]])')
    once('const probs=hasExpC(c)?c.years.reduce', 'const probs=c.theoryCount?c.theoryCount+c.years.reduce((n,y)=>n+y.problems.length,0):hasExpC(c)?c.years.reduce')
    once('${hasExpC(c)?LB(c,"problems"):TL(c,"thyPapers")}</dt><dd>${probs}', '${c.theoryCount?(lang==="ko"?"문제 · 시험지":"Problems / papers"):hasExpC(c)?LB(c,"problems"):TL(c,"thyPapers")}</dt><dd>${probs}')
    once('"cpho","rupho","ruphow","ruphox","ruphoy","kphe"', '"cpho","rupho","kphe"')
    once('const subjOf=key=>(SUBJ.find(x=>x.comps.includes(key))||SUBJ[0]).k;', 'const subjOf=key=>(SUBJ.find(x=>x.comps.includes(RUPHO_ARCHIVE?.isStage(key)?"rupho":key))||SUBJ[0]).k;')
    for name, args in [('viewComp', 'key,mode'), ('viewYear', 'key,year')]:
        once(f'function {name}({args}){{\n  const d=', f'function {name}({args}){{\n  if(key==="rupho"&&RUPHO_ARCHIVE) key=RUPHO_ARCHIVE.route(location.hash).key;\n  const d=')
    for name, endmark, tail in [
        ('viewComp', '/* the exam portal', ',mode==="exam"?"exam":"")'),
        ('viewYear', '/* ══════════════════════════════════════════════════════════════\n   RAIL', ',String(year))')
    ]:
        start = source.index('function ' + name + '(')
        end = source.index(endmark, start)
        part = source[start:end].replace('  return `', '  return ruphoPage(key,`', 1)
        last = part.rfind('`;')
        if last < 0:
            raise ValueError('Missing template end: ' + name)
        part = part[:last + 1] + tail + ';' + part[last + 2:]
        source = source[:start] + part + source[end:]
    once('function render(){\n  if(animId)', 'function render(){\n  const legacyRuPhO=RUPHO_ARCHIVE?.canonical(location.hash);\n  if(legacyRuPhO){ history.replaceState(null,"",legacyRuPhO); }\n  if(animId)')
    once('if(active==="comps" && second==="exam") xmMount(first);', 'if(active==="comps" && second==="exam") xmMount(first==="rupho"&&RUPHO_ARCHIVE?RUPHO_ARCHIVE.route(location.hash).key:first);')
    once('const c=DATA[first];\n    parts.push(second', 'const c=first==="rupho"&&RUPHO_ARCHIVE?compOf(RUPHO_ARCHIVE.route(location.hash).key):DATA[first];\n    parts.push(second')
    css = '''.rupho-stages{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 22px}
.rupho-stages a{padding:10px 14px;border:1px solid var(--grid-bold);border-radius:8px;background:#fff;font-size:13px;color:var(--ink)}
.rupho-stages a:hover{border-color:var(--rail)}
.rupho-stages a[aria-current="page"]{border-color:var(--ink);box-shadow:inset 0 0 0 1px var(--ink);font-weight:700}
'''
    once('.modesw{display:grid;', css + '.modesw{display:grid;')
    path.write_text(source, encoding='utf8', newline='\n')
    print('Integrated RuPhO stage UI:', path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=Path(__file__).resolve().parents[1] / 'index.html')
    integrate(parser.parse_args().index)
