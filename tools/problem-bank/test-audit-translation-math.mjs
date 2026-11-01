import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const audit=fileURLToPath(new URL('./audit-translation-math.mjs',import.meta.url));
const prefix='haslalab-math-audit-';
async function runAudit(question){
  const tempRoot=path.resolve(tmpdir());
  const folder=await mkdtemp(path.join(tempRoot,prefix));
  try{
    await writeFile(path.join(folder,'001.json'),JSON.stringify({items:[{locator:'synthetic/1',...question}]}));
    const result=spawnSync(process.execPath,['--max-old-space-size=128',audit,folder],{encoding:'utf8',maxBuffer:1024*1024});
    assert.ifError(result.error);
    assert.equal(result.stderr,'');
    return {status:result.status,report:JSON.parse(result.stdout)};
  }finally{
    const resolved=path.resolve(folder);
    assert.equal(path.dirname(resolved),tempRoot);
    assert.ok(path.basename(resolved).startsWith(prefix));
    await rm(resolved,{recursive:true,force:true});
  }
}

test('display delimiters allow equation tags while all four math delimiters are counted',async()=>{
  const text=String.raw`Inline $x+1$ and \(y^2\).
$$\begin{aligned}a&=b\\c&=d\end{aligned}\tag{1.65}$$
\[\frac{x}{y}\tag{2}\]`;
  const {status,report}=await runAudit({text_en:text,text_ko:`수식 ${text}`});
  assert.equal(status,0);
  assert.equal(report.questions,1);
  assert.equal(report.latex_expressions,8);
  assert.equal(report.parse_errors,0);
  assert.deepEqual(report.failures,[]);
});

test('inline dollar and parenthesis math still reject display-only tags',async()=>{
  const {status,report}=await runAudit({text_en:String.raw`$x\tag{1}$`,text_ko:String.raw`\(y\tag{2}\)`});
  assert.equal(status,1);
  assert.equal(report.latex_expressions,2);
  assert.equal(report.parse_errors,2);
  assert.deepEqual(report.failures.map(f=>f.language),['en','ko']);
  for(const failure of report.failures){
    assert.equal(failure.file,'001.json');
    assert.equal(failure.locator,'synthetic/1');
    assert.match(failure.error,/tag works only in display equations/);
  }
});

test('malformed display math still fails with its source location',async()=>{
  const {status,report}=await runAudit({text_en:String.raw`$$\frac{x}$$`,text_ko:String.raw`\[\frac{y}\]`});
  assert.equal(status,1);
  assert.equal(report.latex_expressions,2);
  assert.equal(report.parse_errors,2);
  assert.ok(report.failures.every(f=>f.locator==='synthetic/1'));
});
