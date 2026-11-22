#!/usr/bin/env node
/* Writes hpho/samples/<set>/manifest.json from the sources and the built PDFs, for the HPhO page's sample-paper list.
     node tools/hpho-mock/manifest.mjs mock-1 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {parse} from './build.mjs';
const HERE = path.dirname(fileURLToPath(import.meta.url)), ROOT = path.resolve(HERE, '../..');
const set = process.argv[2];
if (!set) { console.error('usage: manifest.mjs <set>'); process.exit(2); }
const dir = path.join(HERE, set), out = path.join(ROOT, 'hpho/samples', set);
const pages = buf => (buf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length;
const ids = [...new Set(fs.readdirSync(dir).filter(f => /^[TE]\d+\.(ko|en)\.md$/.test(f)).map(f => f.split('.')[0]))]
  .sort((a, b) => (a[0] === b[0] ? +a.slice(1) - +b.slice(1) : a[0] === 'T' ? -1 : 1));
const problems = ids.map(id => {
  const p = {id, title: {}, files: {}};
  for (const lang of ['ko', 'en']) {
    const m = parse(fs.readFileSync(path.join(dir, `${id}.${lang}.md`), 'utf8'), id).meta;
    Object.assign(p, {kind: m.kind, no: +m.no, points: +m.points});
    p.title[lang] = m.title;
    const f = {};
    for (const [k, name] of [['question', `${id}-question.pdf`], ['answer', `${id}-answer.pdf`], ['writing', `${id}-writing.pdf`], ['solution', `${id}-solution.pdf`]]) {
      const file = path.join(out, lang, name);
      if (!fs.existsSync(file)) throw new Error('not built: ' + path.relative(ROOT, file));
      const buf = fs.readFileSync(file);
      f[k] = {href: `hpho/samples/${set}/${lang}/${name}`, pages: pages(buf), kb: Math.round(buf.length / 1024), v: crypto.createHash('sha256').update(buf).digest('hex').slice(0, 10)};
    }
    p.files[lang] = f;
  }
  return p;
});
const fileOf = (lang, name) => {
  const file = path.join(out, lang, name);
  if (!fs.existsSync(file)) throw new Error('not built: ' + path.relative(ROOT, file));
  const buf = fs.readFileSync(file);
  return {href: `hpho/samples/${set}/${lang}/${name}`, pages: pages(buf), kb: Math.round(buf.length / 1024), v: crypto.createHash('sha256').update(buf).digest('hex').slice(0, 10)};
};
/* the general instructions, one booklet per exam */
const guides = Object.fromEntries(['theory', 'experiment'].filter(k => fs.existsSync(path.join(dir, `G-${k}.ko.md`)))
  .map(k => [k, {ko: fileOf('ko', `G-${k}.pdf`), en: fileOf('en', `G-${k}.pdf`)}]));
fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify({set, guides, problems}, null, 1) + '\n');
console.log(path.relative(ROOT, path.join(out, 'manifest.json')), problems.length);
