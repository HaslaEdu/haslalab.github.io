/* The problem and test maker's own arithmetic (teach.html), kept apart so Node can test it:
   - number variants: a problem written with named values in braces ("a mass {m} kg falls {h} m"), a range and a step
     for each value, and an answer formula in calculator syntax ("sqrt(2 g h)"); each variant draws the values and the
     answer is computed by math-input.js's parser and evaluator (no eval, no new Function);
   - the exam blueprint (이원목적분류표): the paper's problems counted by unit and by level, with their points.
   window.HL_TEACH_TOOLS in the browser, module.exports in Node. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.HL_TEACH_TOOLS=api;})(typeof self!=='undefined'?self:this,function(root){
  'use strict';
  const M=()=>root.HL_MATH||(typeof require==='function'?require('./math-input.js'):null);
  const LEVELS=['know','understand','apply','analyze'];
  /* a value's name is what the formula parser reads as one variable: a letter with an optional subscript (v_0, m_1)
     or a Greek name (theta) */
  const NAME=/^(?:[A-Za-z]|alpha|beta|gamma|delta|epsilon|theta|lambda|mu|omega|phi|rho|sigma|tau)(?:_[A-Za-z0-9]{1,4})?$/;
  const MAX_VALUES=8,MAX_VARIANTS=30;

  /* the names in braces, in the order they first appear */
  function namesIn(template){
    const out=[];
    for(const m of String(template||'').matchAll(/\{\s*([A-Za-z][A-Za-z0-9_]{0,12})\s*\}/g))if(!out.includes(m[1]))out.push(m[1]);
    return out;
  }
  const decimals=x=>{const s=String(x);if(/e-/i.test(s))return Math.min(10,+s.split(/e-/i)[1]);const d=s.split('.')[1];return d?d.length:0;};
  /* a number for the paper: a value keeps its step's decimals; an answer is rounded to sig significant figures */
  function fmtValue(x,step){const d=decimals(step);return (+x.toFixed(d)).toFixed(d);}
  function fmtSig(x,sig=3){
    if(!Number.isFinite(x))return '';
    if(x===0)return '0';
    const a=Math.abs(x);
    if(a>=1e5||a<1e-3){const [m,e]=x.toExponential(sig-1).split('e');return '$'+m+'\\times 10^{'+(+e)+'}$';}
    const s=x.toPrecision(sig);return /e/.test(s)?String(Number(s)):s;   /* 12345 → 12300, 9.9 → 9.90 */
  }
  /* what is wrong with a template, its values and its formula, as codes the page turns into words; [] when it can run */
  function check(t){
    const errs=[],names=namesIn(t.template),M_=M();
    if(!String(t.template||'').trim())errs.push({code:'no_template'});
    if(!names.length)errs.push({code:'no_values'});
    if(names.length>MAX_VALUES)errs.push({code:'too_many_values'});
    const params=t.params||{};
    for(const n of names){
      if(!NAME.test(n)){errs.push({code:'bad_name',name:n});continue;}
      const p=params[n];
      if(!p){errs.push({code:'no_range',name:n});continue;}
      const [lo,hi,st]=[+p.min,+p.max,+p.step];
      if(![lo,hi,st].every(Number.isFinite)||st<=0||hi<lo)errs.push({code:'bad_range',name:n});
      else if((hi-lo)/st>1e6)errs.push({code:'bad_range',name:n});
    }
    let ast=null;
    if(!String(t.formula||'').trim())errs.push({code:'no_formula'});
    else{
      try{ast=M_.parse(t.formula);}catch(e){errs.push({code:'bad_formula'});}
      if(ast){const known=new Set(names.concat(Object.keys(t.constants||{})));for(const v of M_.vars(ast))if(!known.has(v))errs.push({code:'unknown_in_formula',name:v});}
    }
    return errs;
  }
  /* the values a range allows: lo, lo+step, … up to hi */
  function choices(p){const lo=+p.min,hi=+p.max,st=+p.step,n=Math.floor((hi-lo)/st+1e-9)+1;return {lo,st,n};}
  function seeded(seed){let s=(seed>>>0)||1;return()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;};}
  /* n variants, each with different values (as far as the ranges allow); the answer is computed for each */
  function variants(t,n,{rand=Math.random,sig=3}={}){
    const errs=check(t);if(errs.length)return {errors:errs,items:[]};
    const M_=M(),names=namesIn(t.template),ast=M_.parse(t.formula),ranges=Object.fromEntries(names.map(k=>[k,choices(t.params[k])]));
    const room=names.reduce((a,k)=>a*ranges[k].n,1),want=Math.max(1,Math.min(MAX_VARIANTS,n|0||1,room));
    const seen=new Set(),items=[];let tries=0;
    while(items.length<want&&tries<want*200){
      tries++;
      const env={...(t.constants||{})},shown={};
      for(const k of names){const r=ranges[k],x=r.lo+Math.floor(rand()*r.n)*r.st;shown[k]=fmtValue(x,t.params[k].step);env[k]=+shown[k];}
      const key=names.map(k=>shown[k]).join('|');if(seen.has(key))continue;seen.add(key);
      let ans;try{ans=M_.evaluate(ast,env);}catch(e){ans=NaN;}
      if(!Number.isFinite(ans))continue;     /* a value that divides by zero or takes the root of a negative is skipped */
      const text=String(t.template).replace(/\{\s*([A-Za-z][A-Za-z0-9_]{0,12})\s*\}/g,(m,k)=>k in shown?shown[k]:m);
      items.push({values:shown,answer:ans,answerText:fmtSig(ans,sig),text});
    }
    return {errors:items.length?[]:[{code:'no_valid_values'}],items};
  }

  /* constants the formula may use besides the values: "g = 9.8, c = 3e8" gives {g:9.8,c:3e8}; null when one is not a number */
  function constants(text){
    const out={};
    for(const part of String(text||'').split(/[,;\n]/).map(x=>x.trim()).filter(Boolean)){
      const m=/^([A-Za-z][A-Za-z0-9_]{0,12})\s*=\s*(.+)$/.exec(part);if(!m||!NAME.test(m[1]))return null;
      let v;try{const ast=M().parse(m[2]);if(M().vars(ast).size)return null;v=M().evaluate(ast,{});}catch(e){return null;}
      if(!Number.isFinite(v))return null;out[m[1]]=v;
    }
    return out;
  }
  /* the blueprint: rows are units (in the order they first appear), columns the four levels */
  function blueprint(rows){
    const units=[],cells={},byLevel=Object.fromEntries(LEVELS.map(l=>[l,{n:0,pts:0}]));let n=0,pts=0;
    rows.forEach((r,i)=>{
      const unit=String(r.unit||'').trim()||'-',level=LEVELS.includes(r.level)?r.level:'understand',p=+r.pts||0;
      if(!units.includes(unit))units.push(unit);
      const c=(cells[unit]||={});const cell=(c[level]||={n:0,pts:0,nos:[]});
      cell.n++;cell.pts+=p;cell.nos.push(i+1);byLevel[level].n++;byLevel[level].pts+=p;n++;pts+=p;
    });
    const rowTotals=Object.fromEntries(units.map(u=>[u,LEVELS.reduce((a,l)=>({n:a.n+(cells[u][l]?.n||0),pts:a.pts+(cells[u][l]?.pts||0)}),{n:0,pts:0})]));
    return {levels:LEVELS,units,cells,rowTotals,byLevel,total:{n,pts}};
  }
  return {LEVELS,NAME,namesIn,fmtValue,fmtSig,constants,check,variants,seeded,blueprint,MAX_VARIANTS};
});
