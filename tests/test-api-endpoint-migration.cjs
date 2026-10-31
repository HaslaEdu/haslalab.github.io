const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),read=file=>fs.readFileSync(path.join(root,file),'utf8');
const EDGE='https://haslalab-community-edge.haslalab.workers.dev',LEGACY='https://haslalab-community.haslalab.workers.dev';
const cases=[['',EDGE],[LEGACY,EDGE],[LEGACY+'/',EDGE],[EDGE+'/',EDGE],['http://localhost:8765/','http://localhost:8765'],['https://custom-api.example/','https://custom-api.example']];
const storage=value=>({getItem:key=>key==='hlCmApi'?value:key==='hlCmTok'?'unchanged-account-token':null,setItem(){throw Error('migration must not rewrite account storage');},removeItem(){throw Error('migration must not remove account storage');}});

test('main, exam and payment API bases migrate only the known production override',()=>{
  for(const [file,name] of [['index.html','cmBase'],['sim/exam.html','apiBase'],['pay.html','apiBase']]){
    const source=read(file),constant=source.match(/^const COMMUNITY_API = .*;.*$/m)[0];
    const helper=file==='index.html'?source.match(/function cmBase\(\)\{[\s\S]*?\n\}/)[0]:source.match(/^function apiBase\(\).*$/m)[0];
    for(const [stored,expected] of cases){const context=vm.createContext({localStorage:storage(stored)});vm.runInContext(constant+'\n'+helper,context);assert.equal(vm.runInContext(name+'()',context),expected,file+' '+stored);}
    const context=vm.createContext({localStorage:{getItem(){throw Error('disabled');}}});vm.runInContext(constant+'\n'+helper,context);assert.equal(vm.runInContext(name+'()',context),EDGE,file+' storage disabled');
  }
});

test('existing scanner links and scanbench overrides migrate without changing upload codes or custom hosts',()=>{
  const phone=read('sim/scan.html'),constant=phone.match(/^const COMMUNITY_API = .*;$/m)[0],mapping=phone.match(/^const requestedAPI=.*$/m)[0];
  const bench=read('sim/scanbench.html'),benchConstant=bench.match(/^const COMMUNITY_API=.*$/m)[0],benchMapping=bench.match(/^const API = .*$/m)[0];
  for(const [stored,expected] of cases){
    const H=new URLSearchParams({c:'unchanged-upload-code',...(stored?{a:stored}:{})}),context=vm.createContext({H});vm.runInContext(constant+'\n'+mapping,context);assert.equal(vm.runInContext('API',context),expected);assert.equal(H.get('c'),'unchanged-upload-code');
    const scanbench=vm.createContext({localStorage:storage(stored)});vm.runInContext(benchConstant+'\n'+benchMapping,scanbench);assert.equal(vm.runInContext('API',scanbench),expected);
  }
});

test('the review client migrates its production base and retains the same token and one browser request',async()=>{
  const Review=require('../sim/contest-review.js');assert.equal(Review.DEFAULT_API,EDGE);
  for(const [stored,expected] of cases){
    const calls=[],client=Review.createClient({getBase:()=>stored,getToken:()=> 'unchanged-account-token',fetch:async(url,options)=>{calls.push({url,options});return{ok:true,json:async()=>({user:{nickname:'A'},tokens:2})};}});
    await client.bootstrap();assert.equal(calls.length,1);assert.equal(calls[0].url,expected+'/api/lab/bootstrap');assert.equal(calls[0].options.headers.Authorization,'Bearer unchanged-account-token');
  }
});

test('OMR saves use the edge gateway with the existing token while custom development overrides remain available',async()=>{
  for(const [stored,expected] of cases){
    const calls=[],status={innerHTML:'',textContent:''},context=vm.createContext({window:{},localStorage:storage(stored),AbortController,setTimeout,clearTimeout,document:{createElement:()=>({innerHTML:'',querySelector:()=>status})},fetch:async(url,options)=>{calls.push({url,options});return{ok:true,json:async()=>({attempt:{score:{officialScore:1,maximum:2,rawScore:1,penalty:0}},cohort:{n:1,upperPercent:null}})};}});
    vm.runInContext(read('sim/omr-server.js'),context);await context.window.OmrServer.mount({container:{children:[],insertBefore(){}},run:{done:true,id:'unchanged-attempt',marks:{1:'A'}},comp:'kphe',year:2026,part:'T',count:2,lang:'ko'});
    assert.equal(calls.length,1);assert.equal(calls[0].url,expected+'/api/omr/attempts');assert.equal(calls[0].options.headers.Authorization,'Bearer unchanged-account-token');assert.equal(JSON.parse(calls[0].options.body).client_id,'unchanged-attempt');
  }
});

test('virtual browser searches use the gateway and preserve explicit custom server overrides',()=>{
  const expression=read('sim/vbrowser.js').match(/^  const YT_API = .*$/m)[0];
  for(const [stored,expected] of cases){const context=vm.createContext({window:{HL_COMMUNITY_API:stored}});vm.runInContext(expression,context);assert.equal(vm.runInContext('YT_API()',context),expected+'/api/yt/');}
});
