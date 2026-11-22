/* Typed answers for the practice page: a learner types a number or a formula the way a calculator takes it
   (2*sqrt(g*L), 3.2e4, 1/2 m v^2, π r^2) — no LaTeX — and it is checked against the problem's answer, which is kept as
   a number or as the LaTeX of the correct choice. Formulas are compared by value at random points, so any equivalent
   form counts. window.HL_MATH in the browser, module.exports in Node (tests). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.HL_MATH=api;})(typeof self!=='undefined'?self:this,function(){
  'use strict';
  const FUNCS=['sqrt','sin','cos','tan','arcsin','arccos','arctan','ln','log','exp','abs'];
  const GREEK=['alpha','beta','gamma','delta','epsilon','varepsilon','zeta','eta','theta','vartheta','iota','kappa','lambda','mu','nu','xi','rho','sigma','tau','upsilon','phi','varphi','chi','psi','omega',
    'Gamma','Delta','Theta','Lambda','Xi','Sigma','Phi','Psi','Omega'];
  const GREEK_CHAR={alpha:'α',beta:'β',gamma:'γ',delta:'δ',epsilon:'ε',varepsilon:'ε',zeta:'ζ',eta:'η',theta:'θ',vartheta:'θ',iota:'ι',kappa:'κ',lambda:'λ',mu:'μ',nu:'ν',xi:'ξ',rho:'ρ',sigma:'σ',tau:'τ',upsilon:'υ',phi:'φ',varphi:'φ',chi:'χ',psi:'ψ',omega:'ω',
    Gamma:'Γ',Delta:'Δ',Theta:'Θ',Lambda:'Λ',Xi:'Ξ',Sigma:'Σ',Phi:'Φ',Psi:'Ψ',Omega:'Ω'};
  const CHAR_GREEK=Object.fromEntries(Object.entries(GREEK_CHAR).filter(([k])=>!k.startsWith('var')).map(([k,v])=>[v,k]));

  /* ── tokens: numbers (3, .5, 2.5e-3), names (single letters with an optional subscript, functions, greek, pi), operators ── */
  function tokenize(src){
    let s=String(src).replace(/[−–]/g,'-').replace(/[×·∙]/g,'*').replace(/÷/g,'/').replace(/√/g,'sqrt').replace(/π/g,'pi')
      .replace(/²/g,'^2').replace(/³/g,'^3').replace(/\*\*/g,'^');
    for(const [ch,name] of Object.entries(CHAR_GREEK))s=s.split(ch).join(' '+name+' ');
    const out=[];let i=0;
    while(i<s.length){
      const c=s[i];
      if(/\s/.test(c)){i++;continue;}
      let m=/^(\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+(?![a-zA-Z]))?/.exec(s.slice(i));
      if(m){out.push({t:'n',v:Number(m[0])});i+=m[0].length;continue;}
      m=/^[A-Za-z]+/.exec(s.slice(i));
      if(m){
        let w=m[0];i+=w.length;
        /* a run of letters is a function, a greek name or pi when it is one; otherwise single-letter variables (mg = m·g) */
        const known=[...FUNCS,...GREEK,'pi'].sort((a,b)=>b.length-a.length);
        while(w){
          const k=known.find(n=>w.startsWith(n));
          const name=k&&w.startsWith(k)?k:w[0];w=w.slice(name.length);
          let sub='';
          if(!w&&s[i]==='_'){const r=/^_(\{([A-Za-z0-9]+)\}|[A-Za-z0-9])/.exec(s.slice(i));if(r){sub=r[2]||r[1];i+=r[0].length;}}
          out.push(FUNCS.includes(name)&&!sub?{t:'f',v:name}:{t:'v',v:sub?name+'_'+sub:name});
        }
        continue;
      }
      if('+-*/^(),'.includes(c)){out.push({t:c});i++;continue;}
      if(c==='['){out.push({t:'('});i++;continue;}if(c===']'){out.push({t:')'});i++;continue;}
      throw new Error('char '+c);
    }
    return out;
  }
  /* ── a small Pratt parser: + - * / ^, unary minus, functions, implicit products (2mg, 2(x+1), g sin θ) ── */
  function parse(src){
    const tk=tokenize(src);let p=0;
    const peek=()=>tk[p],next=()=>tk[p++];
    const startsPrimary=t=>t&&(t.t==='n'||t.t==='v'||t.t==='f'||t.t==='(');
    function primary(){
      const t=next();if(!t)throw new Error('end');
      if(t.t==='n')return{k:'n',v:t.v};
      if(t.t==='v')return t.v==='pi'?{k:'n',v:Math.PI,pi:true}:{k:'v',v:t.v};
      if(t.t==='('){const e=expr(0);if(next()?.t!==')')throw new Error(')');return e;}
      if(t.t==='f'){
        let arg;
        if(peek()?.t==='('){next();arg=expr(0);if(next()?.t!==')')throw new Error(')');}
        else arg=power();     /* sin x, sqrt 2 */
        return{k:'f',f:t.v,a:arg};
      }
      if(t.t==='-')return{k:'neg',a:power()};
      if(t.t==='+')return power();
      throw new Error('token '+t.t);
    }
    function power(){let b=primary();if(peek()?.t==='^'){next();const e=peek()?.t==='-'?(next(),{k:'neg',a:power()}):power();b={k:'^',a:b,b:e};}return b;}
    function product(){
      let l=power();
      for(;;){
        const t=peek();
        if(t&&(t.t==='*'||t.t==='/')){next();const r=power();l={k:t.t,a:l,b:r};}
        else if(startsPrimary(t)){l={k:'*',a:l,b:power()};}
        else return l;
      }
    }
    function expr(){
      let l=peek()?.t==='-'?(next(),{k:'neg',a:product()}):product();
      for(;;){const t=peek();if(t&&(t.t==='+'||t.t==='-')){next();l={k:t.t,a:l,b:product()};}else return l;}
    }
    const e=expr();if(p<tk.length)throw new Error('extra');return e;
  }
  function evaluate(e,env){
    switch(e.k){
      case 'n':return e.v;
      case 'v':{if(!(e.v in env))throw new Error('var '+e.v);return env[e.v];}
      case 'neg':return-evaluate(e.a,env);
      case '+':return evaluate(e.a,env)+evaluate(e.b,env);
      case '-':return evaluate(e.a,env)-evaluate(e.b,env);
      case '*':return evaluate(e.a,env)*evaluate(e.b,env);
      case '/':return evaluate(e.a,env)/evaluate(e.b,env);
      case '^':return Math.pow(evaluate(e.a,env),evaluate(e.b,env));
      case 'f':{const x=evaluate(e.a,env);return{sqrt:Math.sqrt,sin:Math.sin,cos:Math.cos,tan:Math.tan,arcsin:Math.asin,arccos:Math.acos,arctan:Math.atan,ln:Math.log,log:Math.log10,exp:Math.exp,abs:Math.abs}[e.f](x);}
    }
    throw new Error('node');
  }
  function vars(e,set=new Set()){if(e.k==='v')set.add(e.v);for(const c of [e.a,e.b])if(c)vars(c,set);return set;}
  /* ── a formula typed by the learner, shown as math while it is typed ── */
  const texVar=v=>{const[n,s]=v.split('_');const b=GREEK.includes(n)?'\\'+n:n;return s?`${b}_{${s}}`:b;};
  const prec={'+':1,'-':1,'*':2,'/':2,neg:3,'^':4,n:5,v:5,f:5};
  function toTex(e,parent=0){
    let s,pr=prec[e.k];
    switch(e.k){
      case 'n':s=e.pi?'\\pi':(Math.abs(e.v)>=1e5||Math.abs(e.v)<1e-3&&e.v)?(()=>{const[m,x]=e.v.toExponential().split('e');return `${+(+m).toPrecision(6)}\\times10^{${+x}}`;})():String(+e.v.toPrecision(10));break;
      case 'v':s=texVar(e.v);break;
      case 'neg':s='-'+toTex(e.a,3);break;
      case '+':s=toTex(e.a,1)+'+'+toTex(e.b,1);break;
      case '-':s=toTex(e.a,1)+'-'+toTex(e.b,2);break;
      case '*':{const a=toTex(e.a,2),b=toTex(e.b,2);s=a+(/^[\d.]/.test(b)||e.b.k==='n'&&!e.b.pi?'\\cdot ':' ')+b;break;}
      case '/':s=`\\frac{${toTex(e.a)}}{${toTex(e.b)}}`;pr=5;break;
      case '^':s=`${toTex(e.a,5)}^{${toTex(e.b)}}`;break;
      case 'f':s=e.f==='sqrt'?`\\sqrt{${toTex(e.a)}}`:e.f==='abs'?`\\left|${toTex(e.a)}\\right|`:`\\${['arcsin','arccos','arctan','sin','cos','tan','ln','log','exp'].includes(e.f)?e.f:'operatorname{'+e.f+'}'}\\left(${toTex(e.a)}\\right)`;break;
    }
    return pr<parent?`\\left(${s}\\right)`:s;
  }
  /* ── the answer side: the LaTeX of a choice becomes the same calculator syntax ── */
  function group(s,i){   /* s[i]==='{' → [content, index after the closing brace] */
    let d=0;for(let j=i;j<s.length;j++){if(s[j]==='{')d++;else if(s[j]==='}'&&!--d)return[s.slice(i+1,j),j+1];}
    throw new Error('brace');
  }
  function fromLatex(tex){
    let s=String(tex).replace(/\\left|\\right|\\displaystyle|\\,|\\;|\\!|\\:|\\ /g,' ').replace(/\\(?:mathrm|text|mathit)\{\s*\}/g,'');
    let out='',i=0;
    while(i<s.length){
      const c=s[i];
      if(c==='\\'){
        const m=/^\\([A-Za-z]+)/.exec(s.slice(i));if(!m){i+=2;continue;}
        const name=m[1];i+=m[0].length;
        while(s[i]===' ')i++;
        if(name==='frac'||name==='dfrac'||name==='tfrac'){const[a,j]=group(s,i);const[b,k]=group(s,j);out+=`((${fromLatex(a)})/(${fromLatex(b)}))`;i=k;}
        else if(name==='sqrt'){
          if(s[i]==='['){const j=s.indexOf(']',i);const n=s.slice(i+1,j);const[a,k]=group(s,j+1);out+=`((${fromLatex(a)})^(1/(${fromLatex(n)})))`;i=k;}
          else{const[a,k]=s[i]==='{'?group(s,i):[s[i],i+1];out+=`sqrt(${fromLatex(a)})`;i=k;}
        }
        else if(name==='cdot'||name==='times')out+='*';
        else if(name==='div')out+='/';
        else if(name==='pi')out+=' pi ';
        else if(GREEK.includes(name))out+=' '+(name.startsWith('var')?name.slice(3):name)+' ';
        else if(FUNCS.includes(name))out+=' '+name+' ';
        else if(name==='text'||name==='mathrm'||name==='mathit'||name==='operatorname'){const[a,k]=group(s,i);out+=' '+a+' ';i=k;}
        else if(name==='circ')out+='*(pi/180)';
        else throw new Error('cmd '+name);
        continue;
      }
      if(c==='^'||c==='_'){i++;while(s[i]===' ')i++;const[a,k]=s[i]==='{'?group(s,i):[s[i],i+1];out+=c==='^'?`^(${fromLatex(a)})`:`_{${a.replace(/[^A-Za-z0-9]/g,'')}}`;i=k;continue;}
      if(c==='{'){const[a,k]=group(s,i);out+=`(${fromLatex(a)})`;i=k;continue;}
      out+=c;i++;
    }
    return out;
  }
  /* units that may follow a numeric answer ("12 m/s", "$3.0\times10^{8}$ m/s"); they are shown, not typed */
  const UNIT=/^(?:[a-zA-ZΩμ°%][a-zA-ZΩμ°%·\/\^\-0-9 ]*|°C?)$/;
  /* The free-response form of a correct choice: a number (with the unit it was given in) or a formula; null when the
     choice is words (a concept question keeps its choices). */
  function answerOf(choice){
    const raw=String(choice??'').trim();if(!raw)return null;
    const math=[...raw.matchAll(/\$\$?([^$]+)\$\$?/g)].map(m=>m[1]);
    const outside=raw.replace(/\$\$?[^$]+\$\$?/g,' ').replace(/\s+/g,' ').trim();
    let tex,unit='';
    if(math.length===1){tex=math[0];unit=outside;}
    else if(!math.length){const m=/^([-−]?\d[\d.,]*(?:\s*[×x]\s*10\^?\{?[-−]?\d+\}?)?)\s*(.*)$/.exec(raw);if(!m)return null;tex=m[1].replace(/,/g,'').replace(/[×x]\s*10\^?\{?([-−]?\d+)\}?/,'\\times10^{$1}');unit=m[2];}
    else return null;
    if(unit&&!UNIT.test(unit))return null;
    /* a unit written inside the math ($12\ \mathrm{m/s}$): split it off the end */
    let body=tex.trim();const tail=/^(.*?)(?:\\[ ,;]|\s)*\\(?:mathrm|text)\{([^{}]*)\}\s*$/.exec(body);
    if(tail&&/[\d}]\s*(?:\\[ ,;]|\s)*$/.test(tail[1].trim())){body=tail[1];unit=(tail[2]+' '+unit).trim();}
    let ast;try{ast=parse(fromLatex(body));}catch(e){return null;}
    const vs=[...vars(ast)];
    if(!vs.length){let v;try{v=evaluate(ast,{});}catch(e){return null;}return Number.isFinite(v)?{kind:'num',value:v,unit,tex:body}:null;}
    return {kind:'expr',ast,vars:vs,unit,tex:body};
  }
  /* is what the learner typed the answer? num: within a relative tolerance; expr: equal at six random points */
  function check(input,answer,tol=0.01){
    let ast;try{ast=parse(input);}catch(e){return{ok:false,error:'syntax'};}
    const used=[...vars(ast)];
    if(answer.kind==='num'){
      if(used.length)return{ok:false,error:'vars',used};
      const v=evaluate(ast,{});if(!Number.isFinite(v))return{ok:false,error:'syntax'};
      return{ok:tol>0?Math.abs(v-answer.value)<=tol*Math.abs(answer.value)+1e-12:Math.abs(v-answer.value)<1e-9,value:v};
    }
    const extra=used.filter(v=>!answer.vars.includes(v));
    if(extra.length)return{ok:false,error:'vars',extra};
    let seed=7;const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647;
    for(let t=0;t<6;t++){
      const env=Object.fromEntries(answer.vars.map(v=>[v,0.6+2.4*rnd()]));
      let a,b;try{a=evaluate(answer.ast,env);b=evaluate(ast,env);}catch(e){return{ok:false,error:'syntax'};}
      if(!Number.isFinite(a))continue;
      if(!(Math.abs(a-b)<=1e-6*Math.max(1,Math.abs(a))))return{ok:false};
    }
    return{ok:true};
  }
  function preview(input){try{return toTex(parse(input));}catch(e){return null;}}
  return {parse,evaluate,vars,toTex,fromLatex,answerOf,check,preview,texVar,GREEK_CHAR};
});
