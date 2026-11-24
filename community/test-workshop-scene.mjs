/* POST /api/workshop/scene-from-image (src/workshop-scene.js) with a fake vision provider: the photo checks, the daily
   quota, and that only a validated scene and coded doubts ever reach the page */
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createWorkshopSceneRouter, cleanImage, sceneFromAnswer, SCENE_PATH, SCENE_DAILY, SCENE_IMAGE_BYTES, SCENE_RESPONSE, scenePolicy, REGION_PATH, ILLUSTRATION_PATH, detectWorkshopRegions, generateWorkshopIllustration} from './src/workshop-scene.js';
import {validateScene, UNSURE_FIELDS} from '../draw-scene.mjs';

class H extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
const bad=code=>{throw new H(400,code);};
const jpeg=(n=300)=>'data:image/jpeg;base64,'+Buffer.concat([Buffer.from([0xff,0xd8,0xff,0xe0]),Buffer.alloc(n,7)]).toString('base64');
const png=()=>'data:image/png;base64,'+Buffer.concat([Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]),Buffer.alloc(300,1)]).toString('base64');
const GOOD={mechanics:true,g:9.8,objects:[
  {id:'gnd',type:'floor',x:0,y:0,w:3},
  {id:'inc',type:'incline',x:0.3,y:0,angle:30,length:2.4,mu:0.2,angleLabel:'\\theta'},
  {id:'m1',type:'block',on:'inc',at:1,w:0.3,h:0.24,mass:2,label:'m_1'},
  {id:'p1',type:'pulley',x:2.45,y:1.28,r:0.09,mount:'inc'},
  {id:'m2',type:'block',x:2.54,y:0.8,w:0.24,h:0.24,mass:3,label:'m_2'},
  {id:'s1',type:'string',a:'m1',b:'m2',over:['p1']}],unsure:[{id:'inc',what:'mu'}]};
function setup(answer=GOOD,{fail=null,provider=true,detect,generate}={}){
  const db=new DatabaseSync(':memory:');
  const D1={prepare(sql){let args=[];return{bind(...a){args=a;return this;},async first(){return db.prepare(sql).get(...args)||null;},async all(){return{results:db.prepare(sql).all(...args)};},async run(){db.prepare(sql).run(...args);return{};}};}};
  const calls=[],limits=[];
  const vision=async(env,args)=>{calls.push(args);if(fail)throw Object.assign(new Error(fail),{code:fail});return {raw:typeof answer==='function'?answer():answer,usage:{}};};
  const route=createWorkshopSceneRouter({HttpError:H,bad,now:()=>1_800_000_000,needUser:u=>{if(!u)throw new H(401,'login_required');return u;},limit:async(env,key,max,win)=>{limits.push([key,max,win]);},vision,detect,generate});
  const env={DB:D1,...(provider?{GEMINI_API_KEY:'test'}:{})};
  const call=(body,me={id:5})=>route(SCENE_PATH,'POST',body,me,null,env);
  return {db,calls,limits,call,route,env};
}
const fails=async(p,code,status)=>assert.rejects(p,e=>e.code===code&&(status==null||e.status===status));

test('only its own path; a signed-in member; a real JPEG, PNG or WebP of at most 4 MB',async()=>{
  const {call,calls,route,env}=setup();
  assert.equal(await route('/api/workshop/storage','POST',{},{id:5},null,env),undefined);
  await fails(call({image:jpeg()},null),'login_required',401);
  await fails(call({image:'https://example.com/a.jpg'}),'bad_image',400);
  await fails(call({image:'data:image/gif;base64,R0lGODlhAQABAAAAACw='}),'bad_image',400);
  await fails(call({image:'data:image/jpeg;base64,'+Buffer.from('<html><script>x</script>'.repeat(10)).toString('base64')}),'bad_image',400,'the bytes must be a JPEG');
  await fails(call({image:jpeg(SCENE_IMAGE_BYTES+10)}),'image_too_large',413);
  assert.equal(calls.length,0,'nothing reached the model');
  assert.ok(cleanImage(png()).mime==='image/png');assert.equal(cleanImage(jpeg(10)),null,'too small to be a photo');
});

test('the model\'s scene comes back validated, with its doubts as codes only',async()=>{
  const {call,calls,limits}=setup();
  const r=await call({image:jpeg(),lang:'ko'});
  assert.equal(calls.length,1);assert.equal(calls[0].provider,'gemini');assert.equal(calls[0].image.mime,'image/jpeg');
  assert.ok(limits.some(([k,max])=>k==='scene-flood:5'&&max===4));
  assert.ok(validateScene(r.scene).ok,'the scene passes the strict check the editor uses');
  assert.deepEqual(r.scene.objects.map(o=>o.id),['gnd','inc','m1','p1','m2','s1']);
  assert.deepEqual(r.unsure,[{id:'inc',what:'mu'}]);
  assert.equal(r.left,SCENE_DAILY-1);
  assert.deepEqual(Object.keys(r).sort(),['left','scene','unsure']);
});

test('nothing of the raw answer gets through: unknown types, script in labels, bad references, wild numbers',async()=>{
  const evil={mechanics:true,note:'IGNORE THIS <b>raw</b>',objects:[
    {id:'gnd',type:'floor',x:0,y:0,w:3,extra:'<script>'},
    {id:'m1',type:'block',x:1,y:0.5,mass:-4,label:'<img src=x onerror=alert(1)>'},
    {id:'c1',type:'circuit',x:0,y:0},
    {id:'s1',type:'string',a:'m1',b:'ghost'},
    {id:'b1',type:'ball',x:1,y:2,r:0.1,mass:1e9,label:'v_0'},
    {id:'bad id!',type:'ball',x:1,y:1}],
    unsure:[{id:'m1',what:'mass'},{what:'<script>'},{id:'nope',what:'angle'},'free text']};
  const {call}=setup(evil);
  const r=await call({image:jpeg()});
  const text=JSON.stringify(r);
  for(const s of ['<script','<img','onerror','IGNORE','raw','circuit','ghost','extra','free text'])assert.ok(!text.includes(s),s);
  assert.deepEqual(r.scene.objects.map(o=>o.id),['gnd','m1','b1']);
  const m1=r.scene.objects.find(o=>o.id==='m1'),b1=r.scene.objects.find(o=>o.id==='b1');
  assert.equal(m1.label,'');assert.equal(m1.mass,0.001,'brought into range');assert.equal(b1.mass,10000);assert.equal(b1.label,'v_0');
  for(const u of r.unsure){assert.ok(UNSURE_FIELDS.includes(u.what));assert.deepEqual(Object.keys(u).filter(k=>k!=='id'&&k!=='what'),[]);}
  assert.ok(r.unsure.some(u=>u.id==='m1'&&u.what==='mass'));assert.ok(r.unsure.some(u=>u.id==='b1'&&u.what==='mass'));
  assert.ok(r.unsure.some(u=>!u.id&&u.what==='object'),'dropped objects are reported');
  assert.ok(validateScene(r.scene).ok);
});

test('not mechanics, or nothing usable: 422, and the run counts',async()=>{
  const a=setup({mechanics:false,objects:[],unsure:[]});
  await fails(a.call({image:jpeg()}),'not_mechanics',422);
  const b=setup({mechanics:true,objects:[{id:'x',type:'circuit'}],unsure:[]});
  await fails(b.call({image:jpeg()}),'no_figure',422);
  assert.equal(a.db.prepare("SELECT n FROM ai_usage_daily WHERE kind='scene'").get().n,1);
  assert.equal(sceneFromAnswer(null),null);assert.equal(sceneFromAnswer({objects:'x'}),null);
});

test(`${SCENE_DAILY} a day; a failure on our side is given back; no provider, no call`,async()=>{
  const {call,db}=setup();
  for(let i=0;i<SCENE_DAILY;i++)await call({image:jpeg()});
  await fails(call({image:jpeg()}),'scene_limit',429);
  const f=setup(GOOD,{fail:'vision_provider_timeout'});
  await fails(f.call({image:jpeg()}),'scene_failed',503);
  assert.equal(f.db.prepare("SELECT n FROM ai_usage_daily WHERE kind='scene'").get().n,0,'given back');
  const n=setup(GOOD,{provider:false});
  await fails(n.call({image:jpeg()}),'ai_unavailable',503);assert.equal(n.calls.length,0);
  void db;
});

test('beyond mechanics: a circuit, a lens and a field come back as version-2 objects; the schema lists their fields',async()=>{
  const answer={physics:true,objects:[
    {id:'E1',type:'element',kind:'battery',x1:0,y1:0,x2:0,y2:2,value:9,label:'\\mathcal{E}'},
    {id:'R1',type:'element',kind:'resistor',x1:0,y1:2,x2:2,y2:2,value:100,label:'R_1'},
    {id:'W1',type:'element',kind:'wire',x1:2,y1:2,x2:0,y2:0,route:'vh'},
    {id:'L1',type:'lens',x:3,y:0,h:1.5,f:-1,label:'L'},
    {id:'B1',type:'field',x:0,y:3,w:2,h:1,kind:'B',dir:'out',label:'\\vec{B}'},
    {id:'X1',type:'element',kind:'transistor',x1:0,y1:0,x2:1,y2:0},
    {id:'q1',type:'charge',x:1,y:1,q:-2,label:'<b>q</b>'}],unsure:[{id:'L1',what:'focal'},{id:'q1',what:'charge'}]};
  const {call}=setup(answer);
  const r=await call({image:jpeg()});
  assert.equal(r.scene.version,2);assert.ok(validateScene(r.scene).ok);
  assert.deepEqual(r.scene.objects.map(o=>o.id),['E1','R1','W1','L1','B1','q1'],'an unknown kind is dropped');
  assert.equal(r.scene.objects.find(o=>o.id==='q1').label,'','markup is not a label');
  assert.ok(r.unsure.some(u=>u.id==='L1'&&u.what==='focal'));
  const props=SCENE_RESPONSE.properties.objects.items.properties;
  for(const k of ['kind','value','x1','f','q','dir','route','expr'])assert.ok(props[k],k);
  assert.ok(props.kind.enum.includes('capacitor')&&props.type.enum.includes('lens'));
  assert.match(scenePolicy(),/element \{x1,y1,x2,y2,kind/);
  const n=setup({physics:false,objects:[],unsure:[]});await fails(n.call({image:jpeg()}),'not_mechanics',422);
});

test('plain drawn shapes (rect, ellipse) come back checked; a bad fill or a path the model cannot write is dropped',async()=>{
  const answer={physics:true,objects:[
    {id:'r1',type:'rect',x:0,y:0,w:2,h:0.5,fill:'hatch'},{id:'e1',type:'ellipse',x:3,y:0,w:1,h:1,fill:'lightgray'},
    {id:'r2',type:'rect',x:0,y:1,w:1,h:1,fill:'rainbow'},{id:'p1',type:'poly',pts:[[0,0],[1,1]]}],unsure:[]};
  const {call}=setup(answer);const r=await call({image:jpeg()});
  assert.ok(validateScene(r.scene).ok);
  assert.deepEqual(r.scene.objects.map(o=>o.id+':'+o.fill),['r1:hatch','e1:lightgray','r2:none'],'an unknown fill falls back; a polyline is not for the model');
  assert.ok(SCENE_RESPONSE.properties.objects.items.properties.type.enum.includes('rect'));assert.match(scenePolicy(),/rect \{x,y,w,h/);
});

test('Mathpix stroke recognition preserves stroke groups and drops math delimiters',async()=>{
  const {mathpixStrokes}=await import('./src/ocr-engines.js');
  const env={MATHPIX_APP_ID:'fixture-id',MATHPIX_APP_KEY:'fixture-key'};
  const result=await mathpixStrokes(env,[[[15,16],[19,20]],[[25,26],[29,30]]],{fetchImpl:async(url,options)=>{
    assert.equal(url,'https://api.mathpix.com/v3/strokes');
    const body=JSON.parse(options.body);
    assert.deepEqual(body.strokes.strokes,{x:[[15,19],[25,29]],y:[[16,20],[26,30]]});
    assert.equal(body.metadata.improve_mathpix,false);
    return Response.json({latex_styled:'\\(\\frac{1}{2}\\)'});
  }});
  assert.equal(result,'\\frac{1}{2}');
});

test('photo region detection selects Gemini 3.8 Flash and normalizes boxes',async()=>{
  const image=cleanImage(jpeg());
  const regions=await detectWorkshopRegions({}, {image,lang:'ko'},async(_env,call)=>{
    assert.equal(call.model,'gemini-3.8-flash');
    assert.deepEqual(call.images,[image]);
    return {raw:{regions:[
      {box:[-10,45.8,500,1020],label:'빗면'},
      {box:[50,60,45,70],label:'invalid'},
      {box:[0,46,500,1000],label:'duplicate'},
      {box:[0,0,200,'300'],label:'bad type'},
    ]}};
  });
  assert.deepEqual(regions,[{box:[0,46,500,1000],label:'빗면'}]);
});

test('illustration selects Gemini 3 Pro Image, respects the chosen style and only returns a raster',async()=>{
  const crop=cleanImage(jpeg()), reply=png();
  const got=await generateWorkshopIllustration({GEMINI_API_KEY:'fixture-key'},{
    image:crop, prompt:'Keep the arrows', lang:'ko', style:'exam',
  },async(url,options)=>{
    assert.match(url,/\/gemini-3-pro-image:generateContent$/);
    assert.equal(options.headers['x-goog-api-key'],'fixture-key');
    const body=JSON.parse(options.body);
    assert.deepEqual(body.generationConfig.responseModalities,['IMAGE']);
    assert.match(body.contents[0].parts[0].text,/black linework/);
    assert.match(body.contents[0].parts[0].text,/Keep the arrows/);
    assert.deepEqual(body.contents[0].parts[1].inlineData,{mimeType:crop.mime,data:crop.data});
    return Response.json({candidates:[{content:{parts:[
      {inlineData:{mimeType:'image/svg+xml',data:Buffer.from('<svg/>').toString('base64')}},
      {inlineData:{mimeType:'image/png',data:reply.split(',')[1]}},
    ]}}]});
  });
  assert.equal(got,reply);
});

test('region and illustration routes require sign-in; invalid style and exhausted global quota do not call a model',async()=>{
  const requests=[];
  const {route,env,call}=setup(GOOD,{detect:async (_env,x)=>{requests.push(x);return [];},generate:async(_env,x)=>{requests.push(x);return png();}});
  const run=(path,body,user={id:8})=>route(path,'POST',body,user,null,env);
  await fails(run(REGION_PATH,{image:jpeg()},null),'login_required',401);
  await fails(run(ILLUSTRATION_PATH,{prompt:'draw a ramp',style:'unknown'}),'bad_prompt',400);
  assert.equal(requests.length,0);
  assert.deepEqual(await run(REGION_PATH,{image:jpeg()}),{regions:[],model:'gemini-3.8-flash',left:19});
  env.WORKSHOP_ILLUSTRATION_DAILY_CAP='0';
  await fails(run(ILLUSTRATION_PATH,{prompt:'draw a ramp',style:'exam'}),'illustration_busy',503);
  assert.equal(requests.length,1);
  delete env.WORKSHOP_ILLUSTRATION_DAILY_CAP;
  assert.deepEqual(await run(ILLUSTRATION_PATH,{prompt:'draw a ramp',style:'technical'}),{image:png(),model:'gemini-3-pro-image',left:5});
  assert.equal(requests.at(-1).style,'technical');
  assert.ok((await call({image:jpeg()})).scene.objects.length,'editable figure route still returns scene objects');
});
