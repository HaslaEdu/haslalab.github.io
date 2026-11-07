# -*- coding: utf-8 -*-
"""Copy the PDFs under pdfx/ to GitHub Releases, so the PDF Worker serves them instead of GitHub Pages.

    python tools/pdfx_release.py            # run by .github/workflows/pdfx-release.yml (GH_TOKEN set)

pdfx/<sub>/<name>.pdf  ->  release pdf-x<sub>,  asset X<sub>_<name>.pdf
pdfx/<name>.pdf        ->  release pdf-xroot,   asset Xroot_<name>.pdf

The prefix keeps them apart from the problem sheets already in pdf-<competition> (180 file names are shared), and
the Worker's rule (release = pdf-<part before the first underscore, lower case>) finds them unchanged:
https://haslalab-pdf.haslalab.workers.dev/pdf/Xipho_<name>.pdf.  The site links them through pdfxUrl() in index.html.

Safe to run again: an asset whose SHA-256 digest matches is skipped, a changed file replaces the old asset.
Only PDFs move; the zip/xlsx/json files in pdfx/ stay on the site.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = os.environ.get('GITHUB_REPOSITORY', 'HaslaEdu/haslalab.github.io')
API = 'https://api.github.com/repos/' + REPO
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')


def call(method, url, data=None, ctype='application/json', tries=5):
    body = json.dumps(data).encode() if isinstance(data, dict) else data
    for i in range(tries):
        req = urllib.request.Request(url, data=body, method=method, headers={
            'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code in (502, 503, 504) or (e.code == 403 and 'rate' in e.read().decode('utf-8', 'replace').lower()):
                time.sleep(20 * (i + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(20 * (i + 1))
    raise RuntimeError('gave up: %s %s' % (method, url))


def release(tag, cache={}):
    if tag in cache:
        return cache[tag]
    try:
        r = call('GET', API + '/releases/tags/' + tag)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        r = call('POST', API + '/releases', {
            'tag_name': tag, 'name': tag, 'make_latest': 'false',
            'body': 'PDFs from pdfx/ served on haslalab.org through the PDF Worker (tools/pdfx_release.py).'})
    assets, page = {}, 1
    while True:
        got = call('GET', '%s/releases/%d/assets?per_page=100&page=%d' % (API, r['id'], page))
        assets.update({a['name']: a for a in got})
        if len(got) < 100:
            break
        page += 1
    cache[tag] = (r, assets)
    return cache[tag]


def asset_name(rel):
    """pdfx-relative path -> (release tag, asset name)."""
    parts = rel.split('/')
    sub = parts[0] if len(parts) == 2 else 'root'
    return 'pdf-x' + sub.lower(), 'X%s_%s' % (sub, parts[-1])


def files():
    base = os.path.join(ROOT, 'pdfx')
    for d, _, fs in os.walk(base):
        for f in sorted(fs):
            if f.endswith('.pdf'):
                rel = os.path.relpath(os.path.join(d, f), base).replace(os.sep, '/')
                if rel.count('/') <= 1:
                    yield rel


def main():
    if not TOKEN:
        sys.exit('GH_TOKEN is not set')
    todo = sorted(files())
    up = same = repl = 0
    for i, rel in enumerate(todo, 1):
        tag, name = asset_name(rel)
        r, assets = release(tag)
        path = os.path.join(ROOT, 'pdfx', rel)
        data = open(path, 'rb').read()
        digest = 'sha256:' + hashlib.sha256(data).hexdigest()
        old = assets.get(name)
        if old and old['state'] == 'uploaded' and old['size'] == len(data) and old.get('digest') == digest:
            same += 1
            continue
        if old:
            call('DELETE', '%s/releases/assets/%d' % (API, old['id']))
            repl += 1
        a = call('POST', r['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(name), data,
                 ctype='application/pdf')
        assert a['name'] == name, (name, a['name'])
        assets[name] = a
        up += 1
        if up % 25 == 0:
            print('%d/%d' % (i, len(todo)), flush=True)
    print('uploaded %d (replaced %d), unchanged %d, total %d' % (up, repl, same, len(todo)))


if __name__ == '__main__':
    main()
