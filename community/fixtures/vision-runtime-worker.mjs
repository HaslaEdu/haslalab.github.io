import {visionJSON} from '../src/vision-provider.js';
import {modelTestProviderCall} from '../src/model-test.js';
const schema={type:'object',properties:{text:{type:'string'}},required:['text']};
const images=[{mime:'image/png',data:'iVBORw0KGgo='}]; // local provider fixture, never an external AI
export default {async fetch(request,env){
 const url=new URL(request.url),provider=url.searchParams.get('provider')==='gemini'?'gemini':'deepseek';
 if(url.pathname==='/old-option'){
  try{await fetch(env.FIXTURE_BASE+'/must-not-be-requested',{redirect:'error'});return Response.json({rejected:false});}
  catch(error){return Response.json({rejected:true,type:error.name});}
 }
 const settings={...env};
 if(url.searchParams.has('redirect')){settings.GEMINI_BASE+='/redirect';settings.DEEPSEEK_BASE+='/redirect';}
 try{
  const result=url.pathname==='/developer'?await modelTestProviderCall(settings,{provider,model:provider==='gemini'?'gemini-3.5-flash-lite':'deepseek-flash'},'ocr','Return JSON only.',{},images,schema,{fetchImpl:globalThis.fetch,timeoutMs:3000}):
   await visionJSON(settings,{provider,stage:'ocr',input:{task:'read fixture'},images,schema,timeoutMs:3000});
  return Response.json({text:result.raw.text,provider});
 }catch(error){return Response.json({error:error.code||'fixture_error',provider_status:error.provider_status},{status:error.status||500});}
}};
