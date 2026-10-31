import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { inflateSync } from 'node:zlib';
import { init } from './src/vendor/pdfium/engine.js';
import { referenceImages } from './src/reference-images.js';
// Public in-memory vector-arrow fixture, no student data or network access.
function fixture(pages=2){
 const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Count '+pages+' /Kids ['+Array.from({length:pages},(_,i)=>(3+i*2)+' 0 R').join(' ')+'] >>'];
 for(let n=0;n<pages;n++){
  const drawing='1 0 0 RG 3 w 10 20 m 70 70 l S 0 0 1 RG 3 w 70 70 m 50 65 l S';
  objects.push('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << >> /Contents '+(4+n*2)+' 0 R >>','<< /Length '+drawing.length+' >>\nstream\n'+drawing+'\nendstream');
 }
 let pdf='%PDF-1.4\n',offsets=[0];
 for(let i=0;i<objects.length;i++){offsets.push(Buffer.byteLength(pdf));pdf+=(i+1)+' 0 obj\n'+objects[i]+'\nendobj\n';}
 const start=Buffer.byteLength(pdf);pdf+='xref\n0 '+(objects.length+1)+'\n0000000000 65535 f \n'+offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')+'trailer\n<< /Size '+(objects.length+1)+' /Root 1 0 R >>\nstartxref\n'+start+'\n%%EOF\n';
 return new Uint8Array(Buffer.from(pdf));
}
let count=0,instance;
const env={REFERENCE_PDFIUM_LOAD:async()=>{
 count++;if(!instance){
  const module=new WebAssembly.Module(fs.readFileSync(new URL('./src/vendor/pdfium/pdfium.wasm',import.meta.url)));
  instance=await init({instantiateWasm(imports,receive){const created=new WebAssembly.Instance(module,imports);receive(created,module);return created.exports;},print(){},printErr(){}});
  instance.PDFiumExt_Init();
 }return instance;
}};
test('actual PDFium renders complete color pages with labels and independent cached objects',async()=>{
 const bytes=fixture(),pages=await referenceImages(env,{bytes,source:'official-fixture.pdf',label:'problem'});
 assert.equal(pages.length,2);assert.deepEqual(pages.map(p=>p.page),[1,2]);
 const png=Buffer.from(pages[0].data,'base64');
 assert.equal(png.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
 let offset=8;const compressed=[];
 while(offset<png.length){const length=png.readUInt32BE(offset),name=png.toString('ascii',offset+4,offset+8);if(name==='IDAT')compressed.push(png.subarray(offset+8,offset+8+length));offset+=length+12;}
 const pixels=inflateSync(Buffer.concat(compressed));let red=0,blue=0;
 for(let y=0;y<pages[0].height;y++)for(let x=0;x<pages[0].width;x++){const d=y*(pages[0].width*4+1)+1+x*4;if(pixels[d]>180&&pixels[d+1]<80&&pixels[d+2]<80)red++;if(pixels[d+2]>180&&pixels[d]<80&&pixels[d+1]<80)blue++;}
 assert.ok(red>100&&blue>100,'colored directional marks survive rendering');
 pages[0].label='tampered';
 const before=count,cached=await referenceImages(env,{bytes,source:'official-fixture.pdf',label:'solution'});
 assert.equal(count,before);assert.match(cached[0].label,/solution.*PDF page 1/);
});
test('page range is exact and page limits never silently return partial references',async()=>{
 const bytes=fixture();
 await assert.rejects(referenceImages(env,{bytes,maxPages:1}),e=>e.code==='reference_too_large');
 assert.deepEqual((await referenceImages(env,{bytes,firstPage:2,lastPage:2})).map(p=>p.page),[2]);
 await assert.rejects(referenceImages(env,{bytes,firstPage:1,lastPage:3}),e=>e.code==='reference_too_large');
});
test('malformed input fails and renderer recovers for the next request',async()=>{
 await assert.rejects(referenceImages(env,{bytes:new Uint8Array([1,2,3])}),e=>e.code==='reference_invalid');
 await assert.rejects(referenceImages(env,{bytes:new TextEncoder().encode('%PDF-1.4 invalid')}),e=>e.code==='reference_unavailable');
 assert.equal((await referenceImages(env,{bytes:fixture(1)})).length,1);
});
