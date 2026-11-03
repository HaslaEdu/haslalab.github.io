// Administrator-only photo transcription for the problem archive. This route
// does not create a monthly submission, store a photo or invoke a grader.
import { boundedForm } from './monthly-photos.js';
import { upstageParse } from './upstage-ocr.js';

export const PROBLEM_BANK_OCR_PATH='/api/problem-bank/ocr';
const MAX_IMAGE=8*1024*1024,MAX_TEXT=12000;
function imageType(bytes){
  if(bytes.length>=8&&[137,80,78,71,13,10,26,10].every((n,i)=>bytes[i]===n))return 'image/png';
  if(bytes.length>=3&&bytes[0]===255&&bytes[1]===216&&bytes[2]===255)return 'image/jpeg';
  if(bytes.length>=12&&String.fromCharCode(...bytes.subarray(0,4))==='RIFF'&&String.fromCharCode(...bytes.subarray(8,12))==='WEBP')return 'image/webp';
  return null;
}

export function createProblemBankOcrRouter({HttpError,currentUser,needUser,parse=upstageParse}){
  return async function problemBankOcr(req,env){
    if(req.method!=='POST')throw new HttpError(405,'method_not_allowed');
    // Recheck the real community session before reading even an invalid body.
    const user=needUser(await currentUser(req,env));
    if(user.role!=='admin')throw new HttpError(403,'admin_required');
    const url=new URL(req.url);
    for(const [key,value]of url.searchParams)if(key!=='mode'||value!=='math'||url.searchParams.getAll(key).length!==1)throw new HttpError(400,'invalid_scan');
    const form=await boundedForm(req,HttpError);
    if([...form.keys()].some(key=>key!=='image')||form.getAll('image').length!==1)throw new HttpError(400,'invalid_scan');
    const image=form.get('image');
    if(!image||typeof image==='string'||typeof image.arrayBuffer!=='function'||image.size<1)throw new HttpError(400,'invalid_scan');
    if(image.size>MAX_IMAGE)throw new HttpError(413,'image_too_big');
    if(!['image/png','image/jpeg','image/webp'].includes(image.type))throw new HttpError(415,'unsupported_scan_type');
    const bytes=new Uint8Array(await image.arrayBuffer());
    if(bytes.byteLength!==image.size||imageType(bytes)!==image.type)throw new HttpError(400,'invalid_scan');
    if(typeof env.UPSTAGE_API_KEY!=='string'||!env.UPSTAGE_API_KEY.trim())throw new HttpError(503,'ocr_unavailable');
    let result;
    try{
      // One explicit photo action makes at most one paid request. Other callers
      // retain upstageParse's existing retry policy and timeout defaults.
      result=await parse(env,bytes,image.type,{mode:'enhanced',timeoutMs:75000,maxAttempts:1});
    }catch(error){
      if(error?.code==='provider_unavailable')throw new HttpError(503,'ocr_unavailable');
      if(error?.code==='vision_provider_rate_limited')throw new HttpError(429,'ocr_rate_limited');
      if(['AbortError','TimeoutError'].includes(error?.name))throw new HttpError(504,'ocr_timeout');
      throw new HttpError(502,'ocr_failed');
    }
    const text=result?.markdown;
    if(typeof text!=='string'||text.trim().length<5||text.length>MAX_TEXT||text.includes('\0'))throw new HttpError(422,'ocr_text_unusable');
    return {text,confidence:null,engine:'upstage-document-parse',format:'markdown-latex'};
  };
}
