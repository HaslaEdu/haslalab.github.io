// Offline syntax checks only; successful parsing is not a scientific review.
import {readFile,readdir} from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const katex=require('../../vendor/katex/katex.min.js');
const folder=process.argv[2];
if(!folder)throw new Error('Usage: node audit-translation-math.mjs PRIVATE_TRANSLATIONS_DIR');
const files=(await readdir(folder)).filter(name=>/^\d+(?:-\d+)?\.json$/.test(name)).sort();
if(!files.length)throw new Error('No numbered translation batches found');
let questions=0,expressions=0;
const failures=[];
for(const name of files){
  const data=JSON.parse(await readFile(path.join(folder,name),'utf8'));
  for(const question of data.items??data.questions??[]){
    questions++;
    for(const [language,text] of [['en',question.text_en??question.en],['ko',question.text_ko??question.ko]]){
      if(typeof text!=='string'||!text.trim())throw new Error(`Missing ${language} in ${name}`);
      const pattern=/\$\$([\s\S]*?)\$\$|(?<!\\)\$([^$]*?)(?<!\\)\$|\\\[([\s\S]*?)\\\]|\\\(([\s\S]*?)\\\)/g;
      for(const match of text.matchAll(pattern)){
        expressions++;
        try{katex.renderToString(match.slice(1).find(value=>value!==undefined),{throwOnError:true,strict:'ignore'});}
        catch(error){failures.push({file:name,locator:question.locator??question.original_number,language,error:error.message});}
      }
    }
  }
}
console.log(JSON.stringify({batches:files.length,questions,latex_expressions:expressions,parse_errors:failures.length,failures}));
if(failures.length)process.exitCode=1;
