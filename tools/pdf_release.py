# -*- coding: utf-8 -*-
"""Upload the problem sheets and solutions to GitHub Releases, one release per competition.

    python tools/pdf_release.py <folder> [<folder> ...]

Each file goes to the release `pdf-<prefix>`, where <prefix> is the part of the
name before the first underscore in lower case (IPhO_2025_E1_EN.pdf -> pdf-ipho).
A release holds at most about 1,000 assets; the largest competition has 244.
The Worker in pdf-worker/ serves them back as https://.../pdf/<name>.

Safe to run again: a file already uploaded with the same SHA-256 digest is
skipped. Changed translations are replaced even if their byte count is equal.
The GitHub token is the one git already uses to push (git credential fill).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = 'HaslaEdu/haslalab.github.io'
API = 'https://api.github.com/repos/' + REPO
NAME = re.compile(r'^([A-Za-z]+)_[A-Za-z0-9._-]+\.pdf$')


def token():
    out = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                         capture_output=True, text=True, check=True).stdout
    return dict(l.split('=', 1) for l in out.splitlines() if '=' in l)['password']


TOKEN = token()


def call(method, url, data=None, ctype='application/json', tries=4):
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
            'body': 'Problem sheets and solutions served on haslalab.org (one release per competition).'})
    assets, page = {}, 1
    while True:
        got = call('GET', '%s/releases/%d/assets?per_page=100&page=%d' % (API, r['id'], page))
        assets.update({a['name']: a for a in got})
        if len(got) < 100:
            break
        page += 1
    cache[tag] = (r, assets)
    return cache[tag]


def main(folders):
    files = []
    for d in folders:
        files += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith('.pdf')]
    up = same = repl = 0
    for i, path in enumerate(files, 1):
        name = os.path.basename(path)
        m = NAME.match(name)
        if not m:
            print('skip (name):', name)
            continue
        tag = 'pdf-' + m.group(1).lower()
        rel, assets = release(tag)
        size = os.path.getsize(path)
        old = assets.get(name)
        digest = 'sha256:' + hashlib.sha256(open(path, 'rb').read()).hexdigest()
        if old and old['size'] == size and old['state'] == 'uploaded' and old.get('digest') == digest:
            same += 1
            continue
        if old:
            call('DELETE', '%s/releases/assets/%d' % (API, old['id']))
            repl += 1
        with open(path, 'rb') as fh:
            a = call('POST', rel['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(name),
                     fh.read(), ctype='application/pdf')
        assert a['name'] == name, (name, a['name'])
        assets[name] = a
        up += 1
        if up % 25 == 0:
            print('%d/%d uploaded' % (i, len(files)), flush=True)
    print('uploaded %d (of which replaced %d), already there %d' % (up, repl, same))
    manifest()


def manifest():
    """pdf-assets.json: every file in the pdf-* releases with its size, for build_seo.js."""
    out, page = {}, 1
    while True:
        rels = call('GET', '%s/releases?per_page=100&page=%d' % (API, page))
        for r in rels:
            if r['tag_name'].startswith('pdf-'):
                out.update({a['name']: a['size'] for a in release(r['tag_name'])[1].values()
                            if a['state'] == 'uploaded'})
        if len(rels) < 100:
            break
        page += 1
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pdf-assets.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(dict(sorted(out.items())), fh, indent=0)
        fh.write('\n')
    print('pdf-assets.json: %d files, %.1f MB' % (len(out), sum(out.values()) / 1e6))


if __name__ == '__main__':
    if sys.argv[1:] == ['--manifest']:
        manifest()
    else:
        main(sys.argv[1:])
