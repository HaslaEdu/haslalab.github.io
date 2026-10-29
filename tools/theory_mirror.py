# -*- coding: utf-8 -*-
"""Copy the theory papers listed in tools/theory/*.json into the GitHub releases pdf-<prefix>.

Run by .github/workflows/theory-pdfs.yml with GH_TOKEN set (the workflow's own token, contents: write); it needs the
gh command.  For every file: skipped when the release already holds an asset of that name; otherwise downloaded from
its source, checked to be a PDF and uploaded.  A source that fails is reported and left for the next run.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get('GITHUB_REPOSITORY', 'HaslaEdu/haslalab.github.io')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 HaslaLab-archive'


def gh(*args, check=True):
    return subprocess.run(['gh', *args, '--repo', REPO], capture_output=True, text=True, check=check)


def assets(tag, cache={}):
    if tag not in cache:
        r = gh('release', 'view', tag, '--json', 'assets', check=False)
        if r.returncode:
            gh('release', 'create', tag, '--title', tag, '--notes', 'Problem sheets and solutions (%s), served by the PDF Worker.' % tag)
            cache[tag] = set()
        else:
            cache[tag] = {a['name'] for a in json.loads(r.stdout)['assets']}
    return cache[tag]


def fetch(url, path):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/pdf,*/*'})
            with urllib.request.urlopen(req, timeout=180) as r, open(path, 'wb') as f:
                f.write(r.read())
            with open(path, 'rb') as f:
                head = f.read(1024)
            if b'%PDF' not in head:
                return 'not a PDF'
            return None
        except Exception as e:
            err = str(e)[:160]
            time.sleep(5 * (i + 1))
    return err


def main():
    only = set(sys.argv[1:])
    done, skipped, failed = [], 0, []
    tmp = tempfile.mkdtemp()
    for path in sorted(glob.glob(os.path.join(ROOT, 'tools', 'theory', '*.json'))):
        m = json.load(open(path, encoding='utf-8'))
        if only and m['comp'] not in only:
            continue
        tag = 'pdf-' + m['prefix'].lower()
        for y in m.get('years', []):
            for f in y.get('files', []):
                name = f['file']
                if not f.get('url'):                 # kept on the site (pdfx/…), not in a release
                    continue
                if name in assets(tag):
                    skipped += 1
                    continue
                local = os.path.join(tmp, name)
                err = fetch(f['url'], local)
                if not err and os.path.getsize(local) > 95e6:
                    err = 'too large'
                if err:
                    failed.append((name, f['url'], err))
                    continue
                r = gh('release', 'upload', tag, local, check=False)
                if r.returncode:
                    failed.append((name, f['url'], 'upload: ' + r.stderr.strip()[:160]))
                else:
                    assets(tag).add(name)
                    done.append(name)
                os.remove(local)
    lines = ['## Theory papers', '', 'uploaded %d · already there %d · failed %d' % (len(done), skipped, len(failed)), '']
    if failed:
        lines += ['| file | source | why |', '|---|---|---|'] + ['| %s | %s | %s |' % x for x in failed]
    report = '\n'.join(lines)
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        open(os.environ['GITHUB_STEP_SUMMARY'], 'a').write(report + '\n')
    json.dump({'uploaded': done, 'failed': failed}, open(os.path.join(tmp, '..', 'theory-mirror.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
