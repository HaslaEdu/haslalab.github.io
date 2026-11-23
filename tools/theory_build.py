# -*- coding: utf-8 -*-
"""Build theory.js — the theory papers the site lists — from tools/theory/<comp>.json.

    python tools/theory_build.py

Each manifest names, per year, the official theory paper(s) and solutions in their original language and where
they were found (tools/theory/README.md).  The PDFs themselves are copied into the GitHub releases (pdf-<prefix>)
by .github/workflows/theory-pdfs.yml (tools/theory_mirror.py); the site and the PDF Worker serve them from there.
theory.js keeps only what the site needs:

  window.THEORY = {ipho: {"2024": {p: [["T1", "title"], ...], f: {"T1": {paper, sol, mark, answer}, ...}}}}
  (NBPhO also x: the experimental problems' numbers, c: {"5": {paper, sol}} the problems cut out of the booklet)

Korean translations come from tools/theory_ko.json (uploaded with tools/pdf_release.py, not mirrored): a part's own
go under ko ({paper, sol, mark, answer, rev}), a translation of the whole paper where the site has only the problems
under w, Korean titles under pk, the general instructions under g ({ko, en}), a Korean working sheet under wk (an English one,
the manifest year's ws, under we); NBPhO's experiments
in Korean (the booklet numbers in x) under xk.

A file marked "direct": true (USABO, USNCO) is not mirrored: the site links its url as it is, and its part is not
offered in exam mode (the exam reads the papers from the releases).

The general instructions (kind "general", files <Prefix>_<year>_GT.pdf for the theory, _GE.pdf, _GE2.pdf … for the
experiments or the observation rounds, with an optional label) go to the theory's g.en and to
window.GENERAL = {ipho: {"2017": [["", "IPhO_2017_GE.pdf"]], ioaa: {"2025": [["Telescope", "IOAA_2025_GE.pdf"], ...]}}.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
from kphe_review import review_questions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = re.compile(r'^([A-Za-z]+)_(\d{4})_((?:T|MC)\d*[a-z]?)(?:_([A-Z]{2})|([SMAK]))\.pdf$')
ARCHIVE_FILE = re.compile(r'^([A-Za-z]+)_(\d{4})_((?:DMT|ITFI|ESP|[PEF])\d*[a-z]?)(?:_([A-Z]{2})|([SMAK]))\.pdf$')
PRACTICAL_PART = re.compile(r'^(?:ITFI|ESP|[PEF])\d*[a-z]?$')
GENERIC = re.compile(r'^(?:problem|question|task|theory|theoretical problem|part)\s*[A-Za-z]?\d*[a-z]?\.?$', re.I)
KINDS = {'paper': 'paper', 'solution': 'sol', 'marking': 'mark', 'answer': 'answer', 'key': 'key'}


def load(practical=None):
    practical = {} if practical is None else practical
    out, bad, gen, meta = {}, [], {}, {}
    kphe_review = review_questions()
    for path in sorted(glob.glob(os.path.join(ROOT, 'tools', 'theory', '*.json'))):
        m = json.load(open(path, encoding='utf-8'))
        comp, prefix = m['comp'], m['prefix']
        # a competition the site lists only for its papers names itself here (full, since, scope): window.THEORY_META
        if m.get('full'):
            meta[comp] = {'abbr': m.get('abbr', prefix), 'full': m['full'], 'since': m.get('since'), 'scope': m.get('scope', {'ko': '', 'en': ''}), 'plain': bool(m.get('plain')), 'rounds': bool(m.get('rounds')), 'omr': bool(m.get('omr'))}
            for field in ('officialWebsite', 'resourceNote', 'resources'):
                if m.get(field):
                    meta[comp][field] = m[field]
        for y in m.get('years', []):
            # a year is "2026", or "2026-1" / "2026-2" for a competition sat twice a year (KPhE); file names keep the 4 digits
            year, files, practical_files, gt = str(y['y']), {}, {}, None
            for f in y.get('files', []):
                if f.get('kind') == 'general' and re.match(r'^%s_%s_G[TE]\d*\.pdf$' % (prefix, year[:4]), f.get('file', '')) \
                        and re.match(r'^https?://', f.get('url', '')):
                    if f.get('for') == 'theory':
                        gt = f['file']
                    else:
                        gen.setdefault(comp, {}).setdefault(year, []).append([f.get('label', ''), f['file']])
                    continue
                # data a problem hands out (ISPhO 2026 T2's detector table): kept on the site, linked from its card
                if f.get('kind') == 'data' and re.match(r'^pdfx/[a-z]+/[\w.-]+\.(xlsx|csv|txt|zip)$', f.get('local', '')) \
                        and f.get('part'):
                    files.setdefault(f['part'], {})['data'] = f['local']
                    continue
                g = FILE.match(f.get('file', '')) or ARCHIVE_FILE.match(f.get('file', ''))
                kind = KINDS.get(f.get('kind'))
                # a file comes from its source (url, copied into a release) or is kept on the site (local: pdfx/…)
                if not g or g.group(1) != prefix or g.group(2) != year[:4] or not kind or not (re.match(r'^https?://', f.get('url', '')) or re.match(r'^pdfx/[a-z]+/', f.get('local', ''))):
                    bad.append((path, f.get('file')))
                    continue
                part = g.group(3)
                group = practical_files if PRACTICAL_PART.fullmatch(part) else files
                slot = group.setdefault(part, {})
                value = f['local'] if f.get('local') else f['url'] if f.get('direct') else f['file']
                # Keep every available source language even when the default is
                # an English edition. Practice and exam language are separate
                # from the language of the site's interface.
                language = (f.get('lang') or g.group(4) or '').lower()
                if kind == 'paper' and re.fullmatch(r'[a-z]{2}', language):
                    slot.setdefault('papers', {})[language] = value
                    if f.get('source_type'):
                        slot.setdefault('paperSourceTypes', {})[language] = f['source_type']
                    if f.get('source_type') == 'unofficial_translation' and f.get('note'):
                        slot.setdefault('paperNotes', {})[language] = f['note']
                    if f.get('contains_solutions'):
                        slot.setdefault('paperContainsSolutions', {})[language] = True
                # one paper per part: English first, then whatever was published
                if kind == 'paper' and 'paper' in slot and not (g.group(4) == 'EN' and not slot['paper'].endswith('_EN.pdf')):
                    continue
                # direct: linked where it is published, never copied (the organiser does not allow redistribution)
                slot[kind] = value
                if kind == 'key' and f.get('standalone_key') is True:
                    slot['keyOnly'] = True
                    if f.get('title'):
                        slot['title'] = f['title']
                if f.get('supplements'):
                    supplements = slot.setdefault('supplements', [])
                    supplements.extend(item for item in f['supplements'] if item not in supplements)
                if kind == 'paper':
                    for prop in ('title', 'round', 'component'):
                        if f.get(prop):
                            slot[prop] = f[prop]
                    if f.get('study_only') is True:
                        slot['kx'] = 1
                    if f.get('problem_ids'):
                        slot['problemIds'] = f['problem_ids']
                    if f.get('practice_sheets'):
                        slot['practiceSheets'] = f['practice_sheets']
                    if f.get('contains_solutions'):
                        slot['containsSolutions'] = True
                    else:
                        slot.pop('containsSolutions', None)
                    if f.get('source_pages') and all(isinstance(page, int) and page > 0 for page in f['source_pages']):
                        slot['sourcePages'] = f['source_pages']
                    else:
                        slot.pop('sourcePages', None)
                if kind == 'paper' and language:
                    slot['paperLang'] = language
            if practical_files:
                for problem in y.get('problems', []):
                    slot = practical_files.get(problem.get('id'))
                    if slot is not None and 'title' not in slot and problem.get('title'):
                        slot['title'] = {'en': problem['title'], 'ko': problem.get('title_ko', problem['title'])}
                sheets = {part: slot for part, slot in practical_files.items() if 'paper' in slot}
                if sheets:
                    practical.setdefault(comp, {})[year] = {'f': sheets, 'h': y.get('host'), 'cc': y.get('cc')}
            # one booklet for the whole paper and per-problem files for the rest (or the other way round): each problem
            # gets what the whole paper has, so it can be read, sat and graded on its own
            for part, slot in files.items():
                g = re.match(r'^(T|MC)(\d+)([a-z]?)$', part)
                whole = files.get(g.group(1) + g.group(3)) if g else None
                if whole and not slot.get('keyOnly') and not slot.get('kx'):
                    for k in ('paper', 'sol', 'mark', 'answer'):
                        if k not in slot and k in whole:
                            slot[k] = whole[k]
                            if k == 'paper':
                                for prop in ('papers', 'paperLang', 'containsSolutions', 'paperContainsSolutions', 'paperSourceTypes', 'paperNotes', 'sourcePages'):
                                    if prop in whole:
                                        slot[prop] = whole[prop].copy() if isinstance(whole[prop], dict) else whole[prop]
            # OPhO 2022 Open saved only an English solutions booklet, but the
            # supplied Korean problem paper is available. Keep that source slot
            # until korean() attaches its paper instead of dropping the round.
            supplied = {}
            if comp == 'opho':
                ko_path = os.path.join(ROOT, 'tools', 'theory_ko.json')
                if os.path.exists(ko_path):
                    supplied = json.load(open(ko_path, encoding='utf-8')).get(comp, {}).get(year, {})
            files = {k: v for k, v in files.items()
                     if 'paper' in v or v.get('keyOnly') or supplied.get(k, {}).get('paper')}
            if not files:
                continue
            # a title that only repeats the number («Problem A1», «Question 3») says nothing: left out
            probs = [[str(p.get('id', ''))[:8], str(p.get('title', '')).strip()[:160]] for p in y.get('problems', [])
                     if p.get('title') and not PRACTICAL_PART.fullmatch(str(p.get('id', '')))
                     and not GENERIC.match(str(p['title']).strip())]
            out.setdefault(comp, {})[year] = {'p': probs, 'f': files}
            # shortlist / backup problems (sl): not part of the competition's paper — sat and graded one at a time
            shortlist = [str(p['id']) for p in y.get('problems', []) if p.get('shortlist') and str(p.get('id')) in files]
            if shortlist:
                out[comp][year]['sl'] = shortlist
            # where it was held, for a year the site knows only from its theory papers (h: {ko, en}, cc: flag code)
            if y.get('host'):
                out[comp][year]['h'] = y['host']
            if y.get('cc'):
                out[comp][year]['cc'] = y['cc']
            # an English working sheet for the theory, kept on the site (ISPhO 2024–2026: HaslaLab's, in the 2026
            # answer-sheet layout); the Korean one comes from theory_ko.json (wk)
            if re.match(r'^pdfx/[a-z]+/[\w.-]+\.pdf$', y.get('ws', '')):
                out[comp][year]['we'] = y['ws']
            # the answer key of a multiple-choice paper, per part (KPhE): exam mode grades it on the screen, not by AI
            if y.get('keys'):
                out[comp][year]['k'] = {k: v for k, v in y['keys'].items() if k in files}
            if comp == 'kphe':
                if year in kphe_review:
                    out[comp][year]['keyReview'] = kphe_review[year]
                out[comp][year]['keySources'] = {f['part']: f['source_type'] for f in y.get('files', [])
                    if f.get('kind') == 'key' and f.get('source_type')}
            if y.get('corrections'):
                out[comp][year]['corrections'] = y['corrections']
            if y.get('note'):
                out[comp][year]['note'] = y['note']
            if y.get('source_type'):
                out[comp][year]['sourceType'] = y['source_type']
            if y.get('source_page'):
                out[comp][year]['sourcePage'] = y['source_page']
            if re.match(r'^https://', y.get('solution_page', '')):
                out[comp][year]['solutionPage'] = y['solution_page']
            if gt:
                out[comp][year]['g'] = {'en': gt}
    split(out)
    korean(out, bad, practical)
    # Print editions are local, checked PDFs; the source manifests retain the
    # official downloads. A key is distinct from a worked solution or blank sheet.
    print_path = os.path.join(ROOT, 'tools', 'kphe_print.json')
    if os.path.exists(print_path):
        for comp, years in json.load(open(print_path, encoding='utf-8')).items():
            for year, edition in years.items():
                target = out.get(comp, {}).get(year)
                if not target:
                    raise ValueError('A4 edition has no source: %s %s' % (comp, year))
                for part, files in edition.get('f', {}).items():
                    if part not in target['f']:
                        raise ValueError('A4 edition has no source part: %s %s %s' % (comp, year, part))
                    for kind, filename in files.items():
                        if not os.path.isfile(os.path.join(ROOT, filename)):
                            raise ValueError('Missing A4 edition: ' + filename)
                        target['f'][part][kind] = filename
                for prop in ('exam', 'questionRegions', 'questionPages', 'points'):
                    if prop in edition:
                        target[prop] = edition[prop]
    return out, bad, gen, meta


def korean(out, bad, practical):
    """tools/theory_ko.json: the Korean translations, laid over the parts the originals made."""
    path = os.path.join(ROOT, 'tools', 'theory_ko.json')
    if not os.path.exists(path):
        return
    for comp, years in json.load(open(path, encoding='utf-8')).items():
        for year, parts in years.items():
            practical_guide = parts.get('experimentGuide')
            if practical_guide:
                archive = practical.get(comp, {}).get(year)
                if archive is None:
                    bad.append((path, '%s %s: no experiment for general instructions' % (comp, year)))
                else:
                    archive['g'] = practical_guide
            for part, ko in parts.items():
                if PRACTICAL_PART.fullmatch(part):
                    slot = practical.setdefault(comp, {}).setdefault(year, {'f': {}})['f'].setdefault(part, {})
                    edition = dict(ko)
                    en = edition.pop('en', None)
                    if en:
                        english_edition(slot, en)
                    slot['ko'] = edition
                    if edition.get('containsSolutions'):
                        slot.setdefault('paperContainsSolutions', {})['ko'] = True
            parts = {part: ko for part, ko in parts.items() if part != 'experimentGuide' and not PRACTICAL_PART.fullmatch(part)}
            if not parts:
                continue
            t = out.get(comp, {}).get(year)
            if not t:
                bad.append((path, '%s %s: no originals for this year' % (comp, year)))
                continue
            rev = parts.get('rev')
            rev_at = 'T2' if 'T2' in parts else 'T'
            whole = t['f'].get('T')
            for part, ko in parts.items():
                if part == 'guide':
                    t['g'] = dict(t.get('g', {}), **ko)     # a translation keeps the original found in the manifest
                    continue
                if part == 'rev':
                    continue
                if part == 'ws':
                    t['wk'] = ko          # the Korean working sheet, for the theory exam only
                    continue
                ko = dict(ko)
                title, en = ko.pop('title', None), ko.pop('en', None)
                if en and en.get('shortlist'):
                    en = {k: v for k, v in en.items() if k != 'shortlist'}
                    if part not in t.get('sl', []):
                        t.setdefault('sl', []).append(part)
                # NBPhO: a booklet number that is an experiment — its Korean problem goes to the experiment card (xk)
                if re.match(r'^T\d+$', part) and int(part[1:]) in t.get('x', []):
                    if ko.get('paper'):
                        t.setdefault('xk', {})[part[1:]] = ko['paper']
                    if ko.get('sol'):
                        t.setdefault('xs', {})[part[1:]] = ko['sol']     # and its Korean solution (xs)
                    continue
                if part == rev_at and rev:
                    ko['rev'] = rev
                if not ko and part not in t['f'] and re.match(r'^T\d+$', part):
                    pass                  # only the Korean title of a problem in a paper published whole (EuPhO)
                elif part in t['f']:
                    # A diagram/layout edition can accompany the Korean
                    # translation while the source manifest keeps the original.
                    if en and comp in SIDE_BY_SIDE:
                        english_beside_original(t['f'][part], en)
                    elif en:
                        english_edition(t['f'][part], en)
                    t['f'][part]['ko'] = ko
                    if ko.get('containsSolutions'):
                        t['f'][part].setdefault('paperContainsSolutions', {})['ko'] = True
                elif part == 'T':
                    t['w'] = ko           # the whole paper in Korean, where the site lists only its problems
                elif whole and re.match(r'^T\d+$', part) and ko.get('paper'):
                    # the original was published whole, the translation cut per problem: the problem's card opens the
                    # Korean problem and the whole original; kx keeps it out of the theory exam, which sits the whole T
                    t['f'][part] = dict({k: v for k, v in whole.items() if k != 'ko'}, ko=ko, kx=1)
                elif en:                  # a part the originals' list does not have (IPhO 2025's backup problem)
                    t['f'][part] = {k: v for k, v in en.items() if k != 'title'}
                    t['f'][part]['ko'] = ko
                    if en.get('title'):
                        t['p'].append([part, en['title']])
                else:
                    bad.append((path, '%s %s %s: no such part' % (comp, year, part)))
                    continue
                if title:
                    t.setdefault('pk', []).append([part, title])


# Competitions whose English editions are shown beside the original (sim/compare.html): the original paper and
# solution stay the part's own files and the English edition is added as slot.en.
SIDE_BY_SIDE = ('rupho', 'ruphow', 'ruphox', 'ruphoy')


def english_beside_original(slot, edition):
    """Add an English edition without replacing the original: slot.en = {paper, sol}, papers.en = the English paper."""
    slot['en'] = {key: value for key, value in edition.items() if key in ('paper', 'sol') and value}
    if edition.get('paper'):
        slot.setdefault('papers', {})['en'] = edition['paper']


def english_edition(slot, edition):
    """Apply a reviewed English edition to either theory or practical papers."""
    slot.update({key: value for key, value in edition.items()
                 if key in ('paper', 'sol', 'mark', 'answer') and value})
    if edition.get('paper'):
        slot.setdefault('papers', {})['en'] = edition['paper']
        slot['paperLang'] = 'en'
        if isinstance(edition.get('paperStart'), int) and edition['paperStart'] > 0:
            slot['paperStart'] = edition['paperStart']
        if edition.get('containsSolutions'):
            slot.setdefault('paperContainsSolutions', {})['en'] = True
        if edition.get('sourceType'):
            slot.setdefault('paperSourceTypes', {})['en'] = edition['sourceType']
    if edition.get('solutionNotice'):
        slot['solutionNotice'] = True


def split(out):
    """NBPhO: the booklet cut into one PDF per problem (pdfx/nbpho, tools/nbpho_split.py) — each theory problem becomes a
    part of its own for practice; x lists the experimental problems' numbers and c the cut files of every problem, so the
    experiment cards and the combined exam use them too.  The whole booklet stays as part T."""
    path = os.path.join(ROOT, 'pdfx', 'nbpho', 'index.json')
    if not os.path.exists(path):
        return
    for year, e in json.load(open(path, encoding='utf-8')).items():
        t = out.get('nbpho', {}).get(year)
        if not t:
            continue
        t['x'] = e['exp']
        t['c'] = {k: {'paper': 'pdfx/nbpho/' + e['paper'][k], **({'sol': 'pdfx/nbpho/' + e['sol'][k]} if k in e['sol'] else {})}
                  for k in e['paper']}
        whole = t['f'].get('T', {})
        for k, v in t['c'].items():
            if int(k) not in e['exp']:
                # a year whose solutions could not be cut per problem (2024, 2026) opens the whole solution booklet
                t['f']['T' + k] = dict(v) if 'sol' in v or 'sol' not in whole else dict(v, sol=whole['sol'])


def main():
    practical = {}
    data, bad, gen, meta = load(practical)
    pdf_versions = {}
    for year in data.get('kphe', {}).values():
        for files in year['f'].values():
            for filename in files.values():
                if isinstance(filename, str) and filename.startswith('pdfx/kphe/'):
                    with open(os.path.join(ROOT, filename), 'rb') as pdf:
                        pdf_versions[filename] = hashlib.sha256(pdf.read()).hexdigest()[:12]
    js = ('/* The theory papers (original problems and solutions) — generated by tools/theory_build.py from tools/theory/*.json.\n'
          '   Do not edit by hand. */\nwindow.THEORY=' + json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + ';\n'
          'window.GENERAL=' + json.dumps(gen, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + ';\n'
          'window.ARCHIVE_PRACTICAL=' + json.dumps(practical, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + ';\n'
          'window.THEORY_META=' + json.dumps(meta, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + ';\n'
          'window.KPHE_PDF_VERSIONS=' + json.dumps(pdf_versions, separators=(',', ':'), sort_keys=True) + ';\n')
    open(os.path.join(ROOT, 'theory.js'), 'w', encoding='utf-8').write(js)
    # browsers keep theory.js for a while: index.html asks for it by its content, so a new build is fetched at once
    page = os.path.join(ROOT, 'index.html')
    html = open(page, encoding='utf-8', newline='').read()
    stamped = re.sub(r'src="theory\.js(?:\?v=[0-9a-f]+)?"', 'src="theory.js?v=%s"' % hashlib.sha1(js.encode('utf-8')).hexdigest()[:10], html)
    if stamped != html:
        open(page, 'w', encoding='utf-8', newline='').write(stamped)
    # The standalone mock exam must receive the same corrected key immediately.
    omr_path = os.path.join(ROOT, 'sim', 'omr.html')
    omr = open(omr_path, encoding='utf-8').read()
    for filename in ('../theory.js', 'omr-core.js', 'omr-server.js', 'omr-app.js', 'omr.css'):
        asset = os.path.normpath(os.path.join(ROOT, 'sim', filename))
        digest = hashlib.sha1(open(asset, 'rb').read()).hexdigest()[:10]
        omr = re.sub(r'((?:src|href)=")' + re.escape(filename) + r'(?:\?v=[0-9a-f]+)?"',
                     lambda m: m[1] + filename + '?v=' + digest + '"', omr)
    open(omr_path, 'w', encoding='utf-8', newline='').write(omr)
    n = sum(len(v['f']) for c in data.values() for v in c.values())
    print('theory.js: %d competitions, %d years, %d papers, %.0f kB' % (len(data), sum(len(c) for c in data.values()), n, len(js) / 1024))
    for path, f in bad:
        print('skipped', os.path.basename(path), f)
    # The front end fetches per-competition chunks; refresh them with the authoritative catalogue.
    lazy_builder = os.path.join(ROOT, 'tools', 'build-site-catalogue.cjs')
    if os.path.isfile(lazy_builder):
        subprocess.run(['node', lazy_builder], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
