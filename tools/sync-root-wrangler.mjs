#!/usr/bin/env node
// The repository-root wrangler.toml exists so Cloudflare Workers Builds, which starts at the repository root,
// can deploy haslalab-community. It used to be a hand-kept copy and drifted: it had lost the AI_EGRESS binding,
// the ACCOUNT_EMAIL sender and the physleague.kr origins, so a deploy from it would have broken grading, sign-up
// e-mail and CORS. It is now generated from community/wrangler.toml, the file the deploy workflow uses.
//   node tools/sync-root-wrangler.mjs           rewrite the root file
//   node tools/sync-root-wrangler.mjs --check   fail if it is out of date (CI)
import {readFileSync,writeFileSync} from 'node:fs';
const root=new URL('../wrangler.toml',import.meta.url),source=new URL('../community/wrangler.toml',import.meta.url);
const HEADER=`# GENERATED from community/wrangler.toml by tools/sync-root-wrangler.mjs: do not edit by hand.
# Cloudflare Workers Builds starts at the repository root; this copy only re-points the paths into community/.
`;
export function rootConfig(text){
  let out=text.replace(/^main = "src\//m,'main = "community/src/').replace(/^migrations_dir = "migrations"/m,'migrations_dir = "community/migrations"');
  if(!/^main = "community\/src\//m.test(out)||!/^migrations_dir = "community\/migrations"/m.test(out))throw Error('community/wrangler.toml: main or migrations_dir not in the expected form');
  return HEADER+out;
}
const want=rootConfig(readFileSync(source,'utf8'));
if(process.argv.includes('--check')){
  if(readFileSync(root,'utf8')!==want){console.error('wrangler.toml is out of date: run node tools/sync-root-wrangler.mjs');process.exit(1);}
  console.log('wrangler.toml matches community/wrangler.toml');
}else{writeFileSync(root,want);console.log('wrote wrangler.toml');}
