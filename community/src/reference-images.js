// Canonical public PDF pages only. Callers resolve the source from the server
// catalogue; client-provided reference URLs/images must never enter this path.
import { VisionProviderError } from './vision-provider.js';
const MAX_PDF=8*1024*1024,MAX_PAGES=20,MAX_PNG=16*1024*1024;
let loading,queue=Promise.resolve();
const cache=new Map();
let cacheBytes=0;
const fail=(code='reference_unavailable',status=502)=>{throw new VisionProviderError(status,code);};
const base64=data=>{const out=[];for(let i=0;i<data.length;i+=24576)out.push(btoa(String.fromCharCode(...data.subarray(i,i+24576))));return out.join('');};
const u32=n=>new Uint8Array([(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255]);
const crcTable=Uint32Array.from({length:256},(_,n)=>{let c=n;for(let k=0;k<8;k++)c=c&1?0xedb88320^(c>>>1):c>>>1;return c>>>0;});
function chunk(type,bytes){const name=new TextEncoder().encode(type),out=new Uint8Array(bytes.length+12);out.set(u32(bytes.length));out.set(name,4);out.set(bytes,8);
  let crc=0xffffffff;for(let i=4;i<out.length-4;i++)crc=crcTable[(crc^out[i])&255]^(crc>>>8);out.set(u32((crc^0xffffffff)>>>0),out.length-4);return out;}
async function png(bgra,width,height,stride){
  const rows=new Uint8Array((width*4+1)*height);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){const s=y*stride+x*4,d=y*(width*4+1)+1+x*4;rows[d]=bgra[s+2];rows[d+1]=bgra[s+1];rows[d+2]=bgra[s];rows[d+3]=255;}
  const packed=new Uint8Array(await new Response(new Blob([rows]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());
  const ihdr=new Uint8Array(13);ihdr.set(u32(width));ihdr.set(u32(height),4);ihdr[8]=8;ihdr[9]=6;
  const blocks=[new Uint8Array([137,80,78,71,13,10,26,10]),chunk('IHDR',ihdr),chunk('IDAT',packed),chunk('IEND',new Uint8Array())];
  const out=new Uint8Array(blocks.reduce((sum,b)=>sum+b.length,0));let at=0;for(const b of blocks){out.set(b,at);at+=b.length;}return out;
}
async function library(env){
  if(typeof env.REFERENCE_PDFIUM_LOAD==='function')return env.REFERENCE_PDFIUM_LOAD(); // local fixture only; never accepted from HTTP
  if(!loading)loading=import('./pdfium-runtime.js').then(module=>module.loadReferencePdfium()).catch(error=>{loading=null;throw error;});
  return loading;
}
async function render(env,{bytes,source='',label='Official reference',firstPage=1,lastPage,maxPages=MAX_PAGES}){
  if(bytes instanceof ArrayBuffer)bytes=new Uint8Array(bytes);
  if(!(bytes instanceof Uint8Array)||bytes.length<8||bytes.length>MAX_PDF||new TextDecoder().decode(bytes.subarray(0,5))!=='%PDF-')fail('reference_invalid',400);
  const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
  const key=digest+':'+firstPage+':'+(lastPage??'all');
  const cached=cache.get(key);if(cached&&cached.expires>Date.now()){
    if(cached.pages.length>Math.min(MAX_PAGES,maxPages))fail('reference_too_large',413);
    return cached.pages.map(p=>({...p,label:`${label}: ${source}; PDF page ${p.page}`}));
  }
  if(cached){cacheBytes-=cached.bytes;cache.delete(key);}
  const lib=await library(env),memory=lib.pdfium,ptr=memory.wasmExports.malloc(bytes.length);let doc;
  try{
    memory.HEAPU8.set(bytes,ptr);doc=lib.FPDF_LoadMemDocument(ptr,bytes.length,null);if(!doc)fail();
    const count=lib.FPDF_GetPageCount(doc),end=lastPage??count;
    if(!Number.isInteger(firstPage)||!Number.isInteger(end)||firstPage<1||end<firstPage||end>count||end-firstPage+1>Math.min(MAX_PAGES,maxPages))fail('reference_too_large',413);
    const pages=[];let total=0;
    for(let index=firstPage-1;index<end;index++){
      let page,bitmap;
      try{
        page=lib.FPDF_LoadPage(doc,index);if(!page)fail();
        const w=lib.FPDF_GetPageWidthF(page),h=lib.FPDF_GetPageHeightF(page);
        if(!(w>0&&h>0)||!Number.isFinite(w+h))fail();
        const scale=Math.min(2000/Math.max(w,h),200/72),width=Math.max(1,Math.round(w*scale)),height=Math.max(1,Math.round(h*scale));
        bitmap=lib.FPDFBitmap_Create(width,height,0);if(!bitmap)fail();
        lib.FPDFBitmap_FillRect(bitmap,0,0,width,height,0xffffffff);
        lib.FPDF_RenderPageBitmap(bitmap,page,0,0,width,height,0,1); // include annotations
        const buffer=lib.FPDFBitmap_GetBuffer(bitmap),stride=lib.FPDFBitmap_GetStride(bitmap);
        const image=await png(memory.HEAPU8.subarray(buffer,buffer+stride*height),width,height,stride);
        total+=image.length;if(total>MAX_PNG)fail('reference_too_large',413);
        pages.push({mime:'image/png',data:base64(image),page:index+1,width,height});
      }finally{if(bitmap)lib.FPDFBitmap_Destroy(bitmap);if(page)lib.FPDF_ClosePage(page);}
    }
    // Bounded process-local public reference cache, never student answers.
    const stored=pages.reduce((sum,page)=>sum+page.data.length,0);
    if(stored<=8*1024*1024){cache.set(key,{expires:Date.now()+600000,pages,bytes:stored});cacheBytes+=stored;}
    while(cache.size>4||cacheBytes>8*1024*1024){const oldest=cache.keys().next().value;cacheBytes-=cache.get(oldest).bytes;cache.delete(oldest);}
    return pages.map(p=>({...p,label:`${label}: ${source}; PDF page ${p.page}`}));
  }finally{if(doc)lib.FPDF_CloseDocument(doc);memory.wasmExports.free(ptr);}
}
export async function referenceImages(env,options){
  // One WASM renderer at a time bounds memory even while the Worker consumes jobs.
  const job=queue.then(()=>render(env,options));queue=job.catch(()=>{});return job;
}
